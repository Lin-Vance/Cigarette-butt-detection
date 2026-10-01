"""市民素材智能预检：调用项目根目录 cigarette-detector.pt 做烟头目标检测。

产出的是**结构化 AI 报告**（而不是只有一个 detected 布尔值）：市民端当场展示，
并把这份快照随上报一起落库，供管理端复核时对照。

口径（答辩时经得起追问）：
  · 模型只做**目标检测**（cigarette / hand / person 三类），输出候选框与置信度；
  · 单张静态图片**无法**证明完整抛掷动作 —— 报告里明确写「证据链不完整」，
    三段式状态机（持烟 → 抛掷 → 落地）在图片素材下只做**推断标注**，不给动作结论；
  · 任何结果都不自动定责、不触发处罚，报告始终带免责说明。
"""

import asyncio
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..errors import ApiError
from ..media_validation import validate_image_bytes

# 必须在导入 ultralytics 之前设置：关闭联网检查（更新检查/字体下载）。
# 内网或代理受限环境下，这些检查会各卡十几秒，把单次预检拖到 30s 以上。
os.environ.setdefault("ULTRALYTICS_OFFLINE", "1")
os.environ.setdefault("YOLO_OFFLINE", "1")

router = APIRouter(prefix="/public/ai", tags=["inference"])
MODEL_PATH = Path(__file__).resolve().parents[3] / "cigarette-detector.pt"
_model = None
_device: str | None = None
_inference_gate = asyncio.Semaphore(2)

LABEL_ZH = {"cigarette": "烟头", "hand": "手部", "person": "人员"}
NOTICE = "模型结果仅生成候选线索，不会自动认定违规或触发处罚；判定需授权人员人工复核。"


def _pick_device() -> str:
    """有 CUDA 用 GPU，否则退回 CPU。结果缓存，避免每次请求都探一遍 GPU。"""
    global _device
    if _device is not None:
        return _device
    device = "cpu"
    try:
        import torch

        if torch.cuda.is_available():
            device = "0"
    except Exception:
        pass
    _device = device
    return device


def get_model():
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        raise ApiError("AI_MODEL_MISSING", "未找到 cigarette-detector.pt 模型文件", 503)
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ApiError("AI_RUNTIME_MISSING", "AI运行环境未安装，请安装后端 requirements.txt", 503) from exc
    try:
        from ultralytics import settings as ul_settings

        if ul_settings.get("sync"):
            ul_settings.update({"sync": False})
    except Exception:
        pass
    _model = YOLO(str(MODEL_PATH))
    return _model


def warmup() -> dict:
    """启动时预热：把 torch/ultralytics 的导入、CUDA 上下文与首次前向挪到服务启动阶段。

    实测（本机 CPU + 24 核）：`import ultralytics` 约 47 秒、首次前向约 3 秒，
    之后单次推理约 0.1 秒。不预热的话，市民第一次上传要等近 50 秒。
    """
    if not MODEL_PATH.exists():
        return {"ok": False, "reason": "cigarette-detector.pt 不存在"}
    try:
        import numpy as np

        t0 = time.perf_counter()
        model = get_model()
        device = _pick_device()
        blank = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(source=blank, conf=0.10, device=device, imgsz=1280, verbose=False)
        return {"ok": True, "device": device, "seconds": round(time.perf_counter() - t0, 1)}
    except ApiError as exc:
        return {"ok": False, "reason": exc.message}
    except Exception as exc:  # 预热失败不能拖垮服务启动
        return {"ok": False, "reason": str(exc)}


def _stage_states(labels: list[str]) -> list[dict]:
    """三段式状态机的**推断标注**（图片素材只做说明，不给动作结论）。"""
    has_cig = "cigarette" in labels
    has_body = "person" in labels or "hand" in labels
    return [
        {
            "key": "holding",
            "label": "持烟 · 点燃",
            "state": "hit" if has_cig else "miss",
            "note": "检出烟头目标，可能存在持烟 / 点燃状态" if has_cig else "未检出烟头目标",
        },
        {
            "key": "throw",
            "label": "抛掷动作",
            "state": "unknown",
            "note": "静态图片无法判定动作过程，需连续视频与时间码",
        },
        {
            "key": "landing",
            "label": "落地 · 现场状态",
            "state": "hit" if has_cig else ("unknown" if has_body else "miss"),
            "note": "画面中存在烟头落地痕迹，可用于清理与热点治理" if has_cig else "未见明确落地目标",
        },
    ]


def _build_report(detections: list[dict], timings: dict) -> dict:
    """把原始检测结果整理成市民端可读的 AI 报告。

    判定口径：**必须检出 cigarette 才算"疑似烟头目标"**。
    只检出 person / hand（比如画面里只有路过的人）不能算烟头线索，
    否则会出现"明明没看到烟头却提示疑似烟头"的假阳性，答辩时会被追问。
    """
    labels = [d["label"] for d in detections]
    cig = [d for d in detections if d["label"] == "cigarette"]
    candidate_cig = [d for d in cig if d["confidence"] >= 60]
    top_cig = max((d["confidence"] for d in cig), default=0.0)
    top_all = max((d["confidence"] for d in detections), default=0.0)

    if cig and top_cig >= 60:
        verdict, verdict_label, tone = "candidate", "疑似烟头目标", "ok"
        summary = (
            f"模型检出 {len(cig)} 个烟头目标，最高置信度 {top_cig}%。"
            "可作为候选线索进入人工复核；单张图片只能说明现场状态，不能证明完整抛掷动作。"
        )
    elif cig:
        verdict, verdict_label, tone = "low", "烟头信号较弱 · 建议人工判断", "warn"
        summary = (
            f"模型检出 {len(cig)} 个置信度较低的烟头目标（最高 {top_cig}%）。"
            "建议补充更清晰的素材，或改为提交现场卫生线索。"
        )
    elif detections:
        verdict, verdict_label, tone = "scene", "仅检出人员 / 手部，未见烟头", "warn"
        summary = (
            f"模型检出 {len(detections)} 个目标（最高 {top_all}%），但**没有** cigarette 类目标。"
            "画面可作为公共空间环境线索，不能作为烟头抛掷线索。"
        )
    else:
        verdict, verdict_label, tone = "scene", "未检出烟头目标", "muted"
        summary = (
            "模型未检出 cigarette / hand / person 中的相关目标。"
            "若画面确实是公共空间卫生问题，仍可提交为环境线索，用于清理与热点治理。"
        )

    return {
        "engine": "cigarette-detector.pt · Ultralytics YOLO（cigarette / hand / person）",
        "demo": True,
        "detected": bool(candidate_cig),
        "confidence": top_cig,
        "count": len(candidate_cig),
        "detections": detections[:12],
        "labels_seen": sorted(set(labels)),
        "verdict": verdict,
        "verdict_label": verdict_label,
        "verdict_tone": tone,
        "summary": summary,
        "stages": _stage_states(labels),
        "evidence": {
            "frames": 1,
            "chain": "不完整",
            "note": "本次素材为单张图片：可记录现场状态，不足以证明完整抛掷动作。完整证据链需要连续视频帧 + 时间码。",
        },
        "risk_notes": [
            "不要为了取证跟拍、拦截或靠近陌生人。",
            "素材仅用于治理研判，不会在公开平台传播他人画面。",
            "若对模型判断有异议，可在上报记录中提交反馈，由授权人员复核。",
        ],
        "notice": NOTICE,
        "timings": timings,
    }


def _nms(detections: list[dict], iou_threshold: float = 0.45) -> list[dict]:
    """合并相邻切片重叠区域里的重复框。"""
    ordered = sorted(detections, key=lambda item: item["confidence"], reverse=True)
    kept: list[dict] = []
    for candidate in ordered:
        ax1, ay1, ax2, ay2 = candidate["box"]
        duplicate = False
        for existing in kept:
            bx1, by1, bx2, by2 = existing["box"]
            left, top = max(ax1, bx1), max(ay1, by1)
            right, bottom = min(ax2, bx2), min(ay2, by2)
            inter = max(0.0, right - left) * max(0.0, bottom - top)
            area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
            area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
            iou = inter / max(area_a + area_b - inter, 1e-6)
            if iou >= iou_threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def _normalize_roi(
    roi_polygon: list[list[float]] | None, width: int, height: int
) -> list[list[int]]:
    """把归一化/像素 ROI 统一为原图像素；缺省使用画面下方 55%。"""
    if not roi_polygon or len(roi_polygon) < 3:
        top = int(height * 0.45)
        return [[0, top], [width - 1, top], [width - 1, height - 1], [0, height - 1]]
    normalized = all(
        isinstance(point, (list, tuple))
        and len(point) >= 2
        and 0 <= float(point[0]) <= 1
        and 0 <= float(point[1]) <= 1
        for point in roi_polygon
    )
    result: list[list[int]] = []
    for point in roi_polygon:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        x = float(point[0]) * width if normalized else float(point[0])
        y = float(point[1]) * height if normalized else float(point[1])
        result.append([max(0, min(width - 1, round(x))), max(0, min(height - 1, round(y)))])
    if len(result) < 3:
        raise ApiError("AI_ROI_INVALID", "地面 ROI 至少需要三个有效坐标点", 422)
    return result


def _extract_detections(result, labels: set[str], *, offset=(0, 0), scale=1.0) -> list[dict]:
    names = result.names or {}
    detections: list[dict] = []
    if result.boxes is None:
        return detections
    boxes = result.boxes.xyxy.tolist() if result.boxes.xyxy is not None else []
    for index, (cls_id, confidence) in enumerate(zip(result.boxes.cls.tolist(), result.boxes.conf.tolist())):
        label = str(names.get(int(cls_id), int(cls_id)))
        if label not in labels or index >= len(boxes):
            continue
        x1, y1, x2, y2 = boxes[index]
        mapped = [
            float(x1) / scale + offset[0],
            float(y1) / scale + offset[1],
            float(x2) / scale + offset[0],
            float(y2) / scale + offset[1],
        ]
        detections.append(
            {
                "label": label,
                "label_zh": LABEL_ZH.get(label, label),
                "confidence": round(float(confidence) * 100, 1),
                "box": [round(value, 1) for value in mapped],
            }
        )
    return detections


async def infer_camera_frame(data: bytes, roi_polygon: list[list[float]] | None) -> dict:
    """地面 ROI 切片放大检测烟头，同时在整帧检测人员/手部。

    地面区域按 640px 切片并保留 20% 重叠，每片放大 2 倍后以 1280 输入模型。
    因此不会把整张 1080p/4K 帧先压成 640，10–20px 小目标仍保留细节。
    """
    model = get_model()
    device = _pick_device()

    def _infer_sync() -> dict:
        import cv2
        import numpy as np

        started = time.perf_counter()
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ApiError("AI_IMAGE_INVALID", "无法解码摄像头帧", 422)
        height, width = frame.shape[:2]
        roi = _normalize_roi(roi_polygon, width, height)
        polygon = np.asarray(roi, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(polygon)
        if w < 32 or h < 32:
            raise ApiError("AI_ROI_INVALID", "地面 ROI 范围过小", 422)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [polygon], 255)

        names = model.names if hasattr(model, "names") else {}
        name_to_id = {str(name): int(class_id) for class_id, name in names.items()}
        cigarette_ids = [name_to_id["cigarette"]] if "cigarette" in name_to_id else None
        people_ids = [name_to_id[name] for name in ("person", "hand") if name in name_to_id] or None

        cigarettes: list[dict] = []
        tile_size, stride, scale = 640, 512, 2.0
        x_starts = list(range(x, max(x + 1, x + w - tile_size + 1), stride))
        y_starts = list(range(y, max(y + 1, y + h - tile_size + 1), stride))
        last_x, last_y = max(x, x + w - tile_size), max(y, y + h - tile_size)
        if not x_starts or x_starts[-1] != last_x:
            x_starts.append(last_x)
        if not y_starts or y_starts[-1] != last_y:
            y_starts.append(last_y)
        x_starts, y_starts = sorted(set(x_starts)), sorted(set(y_starts))

        for tile_y in y_starts:
            for tile_x in x_starts:
                tile_x2, tile_y2 = min(width, tile_x + tile_size), min(height, tile_y + tile_size)
                tile = frame[tile_y:tile_y2, tile_x:tile_x2]
                tile_mask = mask[tile_y:tile_y2, tile_x:tile_x2]
                if tile.size == 0 or cv2.countNonZero(tile_mask) < tile_mask.size * 0.05:
                    continue
                masked = cv2.bitwise_and(tile, tile, mask=tile_mask)
                enlarged = cv2.resize(masked, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                result = model.predict(
                    source=enlarged,
                    conf=0.10,
                    device=device,
                    imgsz=1280,
                    classes=cigarette_ids,
                    verbose=False,
                )[0]
                cigarettes.extend(
                    _extract_detections(result, {"cigarette"}, offset=(tile_x, tile_y), scale=scale)
                )

        scene = model.predict(
            source=frame,
            conf=0.15,
            device=device,
            imgsz=1280,
            classes=people_ids,
            verbose=False,
        )[0]
        people = _extract_detections(scene, {"person"})
        hands = _extract_detections(scene, {"hand"})
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "image_width": width,
            "image_height": height,
            "roi": {"polygon": roi, "source": "camera" if roi_polygon else "default_bottom_55_percent"},
            "cigarettes": _nms(cigarettes),
            "people": people,
            "hands": hands,
            "timings": {
                "total_ms": elapsed_ms,
                "device": device,
                "ground_tiles": len(x_starts) * len(y_starts),
                "tile_size": tile_size,
                "tile_scale": scale,
            },
        }

    async with _inference_gate:
        return await run_in_threadpool(_infer_sync)


@router.post("/inspect")
async def inspect_material(file: UploadFile = File(...)) -> dict:
    """市民上传素材 → 当场返回 AI 报告。

    `predict` 是同步阻塞调用，必须丢到线程池：否则会堵住事件循环，
    把其它请求（含本请求的排队时间）一起拖到几十秒。
    """
    t_start = time.perf_counter()
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise ApiError(
            "AI_IMAGE_REQUIRED",
            "当前模型预检仅支持图片；视频请直接提交，提交后由授权人员在复核环节抽帧分析",
            422,
        )
    data = await file.read(20 * 1024 * 1024 + 1)
    if not data:
        raise ApiError("AI_FILE_EMPTY", "上传文件为空", 422)
    if len(data) > 20 * 1024 * 1024:
        raise ApiError("AI_FILE_TOO_LARGE", "图片不能超过20MB", 422)
    try:
        validate_image_bytes(data)
    except ValueError as exc:
        raise ApiError("AI_IMAGE_INVALID", str(exc), 422) from exc
    t_read = time.perf_counter()

    suffix = Path(file.filename or "upload.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        suffix = ".jpg"

    temp_path = ""
    infer_ms = 0
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(data)
            temp_path = temp.name

        model = get_model()
        device = _pick_device()

        def _infer():
            t0 = time.perf_counter()
            out = model.predict(
                # 烟头在手机远景照片里通常只占几十个像素。640 输入会把这类
                # 小目标进一步压缩（实测用户样本在 640 下漏检、1280 下为 62.7%）。
                # 0.10 用作“候选框”阈值，最终仍按 60% 区分明确候选与弱信号。
                source=temp_path, conf=0.10, device=device, imgsz=1280, verbose=False
            )[0]
            return out, int((time.perf_counter() - t0) * 1000)

        async with _inference_gate:
            result, infer_ms = await run_in_threadpool(_infer)

        names = result.names or {}
        detections: list[dict] = []
        if result.boxes is not None:
            boxes = result.boxes.xyxy.tolist() if result.boxes.xyxy is not None else []
            for idx, (cls_id, confidence) in enumerate(
                zip(result.boxes.cls.tolist(), result.boxes.conf.tolist())
            ):
                label = str(names.get(int(cls_id), int(cls_id)))
                detections.append(
                    {
                        "label": label,
                        "label_zh": LABEL_ZH.get(label, label),
                        "confidence": round(float(confidence) * 100, 1),
                        "box": [round(float(v), 1) for v in boxes[idx]] if idx < len(boxes) else [],
                    }
                )

        timings = {
            "read_ms": int((t_read - t_start) * 1000),
            "infer_ms": infer_ms,
            "total_ms": int((time.perf_counter() - t_start) * 1000),
            "device": device,
            "image_height": int(result.orig_shape[0]),
            "image_width": int(result.orig_shape[1]),
        }
        return _build_report(detections, timings)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


@router.get("/status")
async def model_status() -> dict:
    """模型是否已加载：市民端可据此提示「模型正在加载，请稍候」。"""
    return {
        "loaded": _model is not None,
        "exists": MODEL_PATH.exists(),
        "device": _pick_device(),
        "labels": ["cigarette", "hand", "person"],
    }

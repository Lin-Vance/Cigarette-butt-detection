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

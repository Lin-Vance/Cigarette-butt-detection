"""合规事件生成器。

背景（修订说明「模拟数据引擎要求」）：三段式状态机、ByteTrack、光流法、抛物线拟合
均未实现，因此后端内置本生成器，替代真实 AI 管道，产出**合规事件**。

合规 = 必须通过 `validate_evidence_chain()`：
1. 三段证据帧齐全（holding / throwing / landed），且每帧 `path` **非空**（对应缺陷 A4）
2. 三帧时间戳**严格递增**
3. 轨迹点 ≥ 5（PRD §5.2.1）
4. 全部时间戳为 ISO 8601 **带 +08:00 时区**（对应缺陷 C3）
5. 采样率口径 100 fps（10 ms/帧）

时间口径与前端 frontend/src/mock/engine.ts 的 buildEvent() **完全一致**，
所以后端接管后页面上的数值不会跳变：

    录制窗口 clip_start   = 事件时刻 - 7400 ms
    持烟帧 holding        = clip_start + 1000 ms   → F-0100
    抛掷帧 throwing       = clip_start + 6200 ms   → F-0620
    落地帧 landed         = clip_start + 7300 ms   → F-0730（= event_timestamp）
"""

import random
import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .errors import evidence_chain_invalid
from .models import Camera, Event, EvidenceFrame
from .timeutil import FPS, MS_PER_FRAME, frame_no, iso_ms, plus_ms

# 单帧时长（ms）
FRAME_MS = 1000 // FPS

# 录制窗口相对事件时刻的偏移
CLIP_LEAD_MS = 7400
HOLDING_OFFSET_MS = 1000
THROWING_OFFSET_MS = 6200
LANDED_OFFSET_MS = 7300

TRAJECTORY_POINTS = 12
EVIDENCE_TYPES = ("holding", "throwing", "landed")

# 证据帧素材池（复用主站已归档的设计稿实景图，来源可追溯）
POOL_SOURCES: dict[str, list[str]] = {
    "holding": [
        "cameras/pedestrian-smoking.png",
        "cameras/sidewalk-pedestrian.png",
    ],
    "throwing": [
        "evidence/event-detection.png",
        "cameras/roadside-pedestrian.png",
    ],
    "landed": [
        "evidence/incident-cigarette.png",
        "cameras/urban-vehicle.png",
    ],
}


# ---------------- 素材池 ----------------


def _fallback_svg(kind: str, camera_id: str) -> bytes:
    """素材图片缺失时的兜底：生成一张带帧标注的 SVG。
    宁可退化成示意图，也不能让 path 为空（那就是缺陷 A4）。"""
    label = {"holding": "持烟", "throwing": "抛掷", "landed": "落地"}[kind]
    cyan = {"holding": "#17697A", "throwing": "#D9482B", "landed": "#2E6B4F"}[kind]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#F3F0E7"/>
  <g stroke="#C9C2B4" stroke-width="1">
    {"".join(f'<line x1="{x}" y1="0" x2="{x}" y2="360"/>' for x in range(0, 641, 40))}
    {"".join(f'<line x1="0" y1="{y}" x2="640" y2="{y}"/>' for y in range(0, 361, 40))}
  </g>
  <rect x="16" y="16" width="608" height="328" fill="none" stroke="#101418" stroke-width="2"/>
  <rect x="240" y="150" width="90" height="120" fill="none" stroke="{cyan}" stroke-width="3"/>
  <text x="32" y="52" font-family="monospace" font-size="20" fill="#101418">{label} 帧 · {camera_id}</text>
  <text x="32" y="326" font-family="monospace" font-size="14" fill="#8C8578">演示素材（算法管道未实现，非真实推理输出）</text>
</svg>
"""
    return svg.encode("utf-8")


def ensure_pool() -> dict[str, list[Path]]:
    """把素材池复制进后端自己的 storage，之后可脱离前端目录独立运行。"""
    settings = get_settings()
    settings.pool_dir.mkdir(parents=True, exist_ok=True)

    pool: dict[str, list[Path]] = {}
    for kind, sources in POOL_SOURCES.items():
        paths: list[Path] = []
        for i, rel in enumerate(sources):
            src = settings.asset_source_dir / rel
            dest = settings.pool_dir / f"{kind}_{i}.png"
            if not dest.exists():
                try:
                    if src.exists():
                        shutil.copyfile(src, dest)
                    else:
                        raise FileNotFoundError(src)
                except OSError:
                    # 写成 .svg 而不是 .png，避免扩展名与内容不符
                    dest = settings.pool_dir / f"{kind}_{i}.svg"
                    if not dest.exists():
                        dest.write_bytes(_fallback_svg(kind, "pool"))
            if dest.exists():
                paths.append(dest)
        if not paths:
            dest = settings.pool_dir / f"{kind}_fallback.svg"
            dest.write_bytes(_fallback_svg(kind, "pool"))
            paths.append(dest)
        pool[kind] = paths
    return pool


def materialize_frames(event_id: str, pool: dict[str, list[Path]], rng: random.Random) -> dict[str, str]:
    """为一条事件落盘三段证据帧，返回 {type: 相对 storage 的路径}。"""
    settings = get_settings()
    target_dir = settings.evidence_dir / event_id
    target_dir.mkdir(parents=True, exist_ok=True)

    out: dict[str, str] = {}
    for kind in EVIDENCE_TYPES:
        candidates = pool.get(kind) or []
        src = rng.choice(candidates) if candidates else None
        suffix = src.suffix if src else ".svg"
        dest = target_dir / f"{kind}{suffix}"
        if src is not None:
            try:
                shutil.copyfile(src, dest)
            except OSError:
                dest = target_dir / f"{kind}.svg"
                dest.write_bytes(_fallback_svg(kind, event_id[:8]))
        else:
            dest.write_bytes(_fallback_svg(kind, event_id[:8]))
        # 库里存相对 storage 的路径，URL 由 services.url() 拼
        out[kind] = str(dest.relative_to(settings.storage_dir)).replace("\\", "/")
    return out


# ---------------- 事件构造 ----------------


def new_event_id() -> str:
    return str(uuid.uuid4())


def build_trajectory(holding, landed, rng: random.Random) -> list[dict]:
    """轨迹点：12 个，从持烟到落地等间隔，时间戳严格递增。
    x 线性右移、y 抛物线加速下坠（与前端 mock/engine.ts 同形）。"""
    total_ms = int((landed - holding).total_seconds() * 1000)
    points = []
    for i in range(TRAJECTORY_POINTS):
        p = i / (TRAJECTORY_POINTS - 1)
        dt = plus_ms(holding, int(total_ms * p))
        points.append(
            {
                "x": round(940 + p * 190 + (rng.random() - 0.5) * 12, 1),
                "y": round(300 + p * p * 420 + (rng.random() - 0.5) * 8, 1),
                "ts": iso_ms(dt),
            }
        )
    return points


def validate_evidence_chain(frames: list[dict], trajectory: list[dict]) -> None:
    """证据链校验。任何一项不过就抛 422，不允许把残缺事件写进库。"""
    if len(frames) != len(EVIDENCE_TYPES):
        raise evidence_chain_invalid(f"需要 {len(EVIDENCE_TYPES)} 帧，实际 {len(frames)} 帧")

    by_type = {f["type"]: f for f in frames}
    for kind in EVIDENCE_TYPES:
        if kind not in by_type:
            raise evidence_chain_invalid(f"缺少 {kind} 帧")
        if not str(by_type[kind].get("path") or "").strip():
            raise evidence_chain_invalid(f"{kind} 帧 path 为空（缺陷 A4）")

    ts = [by_type[k]["frame_ts"] for k in EVIDENCE_TYPES]
    if not (ts[0] < ts[1] < ts[2]):
        raise evidence_chain_invalid("三段式时间戳必须严格递增（持烟 → 抛掷 → 落地）")

    for value in ts:
        if not (value.endswith("+08:00") or value.endswith("+0800")):
            raise evidence_chain_invalid(f"时间戳缺少 +08:00 时区：{value}")

    if len(trajectory) < 5:
        raise evidence_chain_invalid(f"轨迹点需 ≥ 5，实际 {len(trajectory)}")

    traj_ts = [p["ts"] for p in trajectory]
    if any(traj_ts[i] >= traj_ts[i + 1] for i in range(len(traj_ts) - 1)):
        raise evidence_chain_invalid("轨迹点时间戳必须严格递增")


def build_event(
    camera: Camera,
    *,
    at,
    rng: random.Random | None = None,
    source: str = "camera",
    report_no: str = "",
    pool: dict[str, list[Path]] | None = None,
) -> Event:
    """构造一条合规事件（含三段证据帧落盘）。"""
    rng = rng or random.Random()
    pool = pool or ensure_pool()

    landed_at = at
    holding_at = plus_ms(landed_at, -(LANDED_OFFSET_MS - HOLDING_OFFSET_MS))
    throwing_at = plus_ms(landed_at, -(LANDED_OFFSET_MS - THROWING_OFFSET_MS))

    event_id = new_event_id()
    rel_paths = materialize_frames(event_id, pool, rng)

    frames = [
        {"frame_ts": iso_ms(holding_at), "type": "holding", "path": rel_paths["holding"]},
        {"frame_ts": iso_ms(throwing_at), "type": "throwing", "path": rel_paths["throwing"]},
        {"frame_ts": iso_ms(landed_at), "type": "landed", "path": rel_paths["landed"]},
    ]
    trajectory = build_trajectory(holding_at, landed_at, rng)
    validate_evidence_chain(frames, trajectory)

    clip_start = plus_ms(landed_at, -CLIP_LEAD_MS)
    frame_rows: list[EvidenceFrame] = []
    for f in frames:
        offset_ms = int((_parse(f["frame_ts"]) - clip_start).total_seconds() * 1000)
        frame_rows.append(
            EvidenceFrame(
                event_id=event_id,
                frame_ts=f["frame_ts"],
                type=f["type"],
                path=f["path"],
                frame_no=offset_ms // FRAME_MS,
            )
        )

    event = Event(
        event_id=event_id,
        camera_id=camera.camera_id,
        camera_name=camera.name,
        track_id=1000 + int(rng.random() * 8000),
        stage="THROW_CONFIRMED",
        confidence=round(0.78 + rng.random() * 0.2, 3),
        bbox=[930, 690, 26, 19],
        trajectory=trajectory,
        event_timestamp=iso_ms(landed_at),
        # 摄像头侧产出即为「待复核」；市民上报派生的先落「候选」，等分析任务推进
        status="pending_review" if source == "camera" else "candidate",
        has_workorder=False,
        video_clip_path="",  # 真实视频片段属 M1 算法阶段，当前不伪造
        source=source,
        report_no=report_no,
        created_at=iso_ms(landed_at),
    )
    event.frames = frame_rows
    return event


def _parse(value: str):
    from .timeutil import parse_iso

    return parse_iso(value)


async def generate_camera_event(
    session: AsyncSession,
    camera: Camera,
    *,
    at,
    rng: random.Random | None = None,
) -> Event:
    """固定摄像头侧产出的事件（已过状态机、进入待复核）。"""
    pool = ensure_pool()
    event = build_event(camera, at=at, rng=rng, source="camera", pool=pool)
    session.add(event)
    await session.flush()
    return event


__all__ = [
    "CLIP_LEAD_MS",
    "EVIDENCE_TYPES",
    "FRAME_MS",
    "build_event",
    "build_trajectory",
    "ensure_pool",
    "generate_camera_event",
    "materialize_frames",
    "new_event_id",
    "validate_evidence_chain",
    "frame_no",
]

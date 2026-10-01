"""摄像头与 AI 控制：/cameras、/ai/config、/ai/preprocess/toggle、/ai/metrics。"""

import json
import random

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import CurrentUser, require_pages, require_roles
from ..errors import camera_duplicate, camera_not_found, not_found
from ..models import Camera, User
from ..redis_client import get_redis, redis_key
from ..schemas import AiConfigRequest, CameraCreate, CameraUpdate, PreprocessToggle
from ..services import client_ip, paged, write_audit
from ..timeutil import iso, now_cn

router = APIRouter(prefix="/cameras", tags=["camera"])
ai_router = APIRouter(prefix="/ai", tags=["camera"])

def camera_dict(cam: Camera) -> dict:
    return {
        "id": cam.id,
        "camera_id": cam.camera_id,
        "name": cam.name,
        "location_name": cam.location_name,
        "latitude": cam.latitude,
        "longitude": cam.longitude,
        "status": cam.status,
        "fps": cam.fps,
        "preprocess_enabled": cam.preprocess_enabled,
        "preprocess_algorithm": cam.preprocess_algorithm,
        "online_rate": cam.online_rate,
        "rtsp_url": cam.rtsp_url,
        "roi_polygon": cam.roi_polygon,
        "created_at": cam.created_at,
    }


@router.get("")
async def list_cameras(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    _: object = Depends(require_pages("device-status")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(Camera)
    if status:
        stmt = stmt.where(Camera.status == status)
    rows = list((await session.execute(stmt.order_by(Camera.id))).scalars())
    total = len(rows)
    page = max(1, page)
    size = min(200, max(1, size))
    return paged([camera_dict(c) for c in rows[(page - 1) * size : page * size]], total, page, size)


@router.post("", status_code=201)
async def create_camera(
    payload: CameraCreate,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    exists = (
        await session.execute(select(Camera).where(Camera.camera_id == payload.camera_id))
    ).scalar_one_or_none()
    if exists is not None:
        raise camera_duplicate(payload.camera_id)

    cam = Camera(
        camera_id=payload.camera_id,
        name=payload.name,
        location_name=payload.location_name or payload.name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status="online",
        fps=25.0,
        rtsp_url=payload.rtsp_url,
        roi_polygon=payload.roi_polygon,
        created_at=iso(now_cn()),
    )
    session.add(cam)
    await session.flush()
    await write_audit(
        session,
        "CAMERA_CREATE",
        actor=user,
        target=f"camera:{cam.camera_id}",
        detail=f"新增摄像头 {cam.name}",
        ip=client_ip(request),
    )
    await session.commit()
    return camera_dict(cam)


@router.get("/{camera_id}")
async def get_camera(
    camera_id: str,
    _: object = Depends(require_pages("device-status")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cam = (await session.execute(select(Camera).where(Camera.camera_id == camera_id))).scalar_one_or_none()
    if cam is None:
        raise camera_not_found(camera_id)
    return camera_dict(cam)


@router.patch("/{camera_id}")
async def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cam = (await session.execute(select(Camera).where(Camera.camera_id == camera_id))).scalar_one_or_none()
    if cam is None:
        raise camera_not_found(camera_id)

    changed = payload.model_dump(exclude_none=True)
    for field, value in changed.items():
        setattr(cam, field, value)
    await write_audit(
        session,
        "CAMERA_UPDATE",
        actor=user,
        target=f"camera:{cam.camera_id}",
        detail=f"修改摄像头字段：{', '.join(changed) or '无'}",
        ip=client_ip(request),
    )
    await session.commit()
    return camera_dict(cam)


# ---------------- AI 控制 ----------------


@ai_router.post("/config")
async def apply_ai_config(
    payload: AiConfigRequest,
    request: Request,
    user: User = Depends(require_pages("ai-config")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cam = (
        await session.execute(select(Camera).where(Camera.camera_id == payload.camera_id))
    ).scalar_one_or_none()
    if cam is None:
        raise camera_not_found(payload.camera_id)

    updated_at = iso(now_cn())
    ai_config = {
        "confidence_threshold": payload.confidence_threshold,
        "state_machine_params": payload.state_machine_params,
        "roi": payload.roi,
        "updated_at": updated_at,
    }
    await get_redis().set(
        redis_key("ai", "config", payload.camera_id),
        json.dumps(ai_config, ensure_ascii=False),
    )
    if payload.roi and payload.roi.get("polygon"):
        cam.roi_polygon = payload.roi["polygon"]

    await write_audit(
        session,
        "AI_CONFIG_UPDATE",
        actor=user,
        target=f"camera:{payload.camera_id}",
        detail=f"置信度阈值调整为 {payload.confidence_threshold}",
        ip=client_ip(request),
    )
    await session.commit()
    return {
        "status": "ok",
        "applied_config": {
            "camera_id": payload.camera_id,
            "confidence_threshold": payload.confidence_threshold,
            "updated_at": updated_at,
        },
    }


@ai_router.post("/preprocess/toggle")
async def toggle_preprocess(
    payload: PreprocessToggle,
    request: Request,
    user: User = Depends(require_pages("ai-config")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cam = (
        await session.execute(select(Camera).where(Camera.camera_id == payload.camera_id))
    ).scalar_one_or_none()
    if cam is None:
        raise camera_not_found(payload.camera_id)

    cam.preprocess_enabled = payload.enabled
    cam.preprocess_algorithm = payload.algorithm
    updated_at = iso(now_cn())
    preprocess_config = {
        "enabled": payload.enabled,
        "algorithm": payload.algorithm,
        "auto_mode": payload.auto_mode,
        "updated_at": updated_at,
    }
    await get_redis().set(
        redis_key("ai", "preprocess", payload.camera_id),
        json.dumps(preprocess_config, ensure_ascii=False),
    )
    await write_audit(
        session,
        "AI_PREPROCESS_TOGGLE",
        actor=user,
        target=f"camera:{payload.camera_id}",
        detail=f"预处理{'开启' if payload.enabled else '关闭'}（{payload.algorithm}）",
        ip=client_ip(request),
    )
    await session.commit()
    return {
        "status": "ok",
        "camera_id": payload.camera_id,
        "preprocess_enabled": payload.enabled,
        "algorithm": payload.algorithm,
        "updated_at": updated_at,
    }


@ai_router.get("/metrics")
async def ai_metrics(
    _: object = Depends(require_pages("ai-config", "ai-model")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """运行指标。

    注意：GPU / 推理耗时 / 丢帧数均为**演示数值**——算法管道未实现，
    此处如实标注，不伪造真实推理性能。
    """
    rng = random.Random(20260927)
    cameras = list((await session.execute(select(Camera).order_by(Camera.id))).scalars())
    items = []
    for cam in cameras:
        items.append(
            {
                "camera_id": cam.camera_id,
                "status": cam.status,
                "current_fps": cam.fps,
                "gpu_memory_used_mb": 3200 + rng.randint(0, 900),
                "gpu_memory_total_mb": 24576,
                "inference_queue_length": rng.randint(0, 18),
                "preprocess_enabled": cam.preprocess_enabled,
                "dropped_frames": 0 if cam.status == "online" else rng.randint(20, 260),
                "avg_inference_ms": round(32 + rng.random() * 18, 1),
                "demo": True,
            }
        )
    return {
        "cameras": items,
        "gpu_summary": {
            "device": "演示数值（算法管道未实现）",
            "utilization": 0.72,
            "memory_used_mb": 7300,
            "memory_total_mb": 24576,
            "temperature_c": 68,
            "demo": True,
        },
    }


async def find_camera(session: AsyncSession, camera_id: str) -> Camera:
    cam = (await session.execute(select(Camera).where(Camera.camera_id == camera_id))).scalar_one_or_none()
    if cam is None:
        raise not_found("摄像头")
    return cam

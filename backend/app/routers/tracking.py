"""固定摄像头连续帧的地面小目标检测与跨帧跟踪接口。"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_pages
from ..errors import ApiError, camera_not_found
from ..ground_tracking import ground_tracker
from ..media_validation import validate_image_bytes
from ..models import Camera
from .inference import infer_camera_frame

router = APIRouter(prefix="/ai/ground-tracking", tags=["camera-ai-tracking"])


@router.post("/frame")
async def process_frame(
    camera_id: str = Form(..., min_length=2, max_length=32),
    file: UploadFile = File(...),
    timestamp_ms: int | None = Form(default=None),
    ground_roi: str | None = Form(default=None),
    _: object = Depends(require_pages("ai-model", "ai-config")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """处理一个摄像头帧。调用方必须按时间顺序发送，同一摄像头不要并发提交。"""
    camera = (
        await session.execute(select(Camera).where(Camera.camera_id == camera_id))
    ).scalar_one_or_none()
    if camera is None:
        raise camera_not_found(camera_id)
    if not (file.content_type or "").lower().startswith("image/"):
        raise ApiError("AI_IMAGE_REQUIRED", "连续帧接口只接收图片帧", 422)
    data = await file.read(20 * 1024 * 1024 + 1)
    if not data or len(data) > 20 * 1024 * 1024:
        raise ApiError("AI_IMAGE_INVALID", "帧为空或超过20MB", 422)
    try:
        validate_image_bytes(data)
    except ValueError as exc:
        raise ApiError("AI_IMAGE_INVALID", str(exc), 422) from exc

    roi = camera.roi_polygon
    if ground_roi:
        try:
            parsed = json.loads(ground_roi)
            if not isinstance(parsed, list):
                raise ValueError
            roi = parsed
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ApiError("AI_ROI_INVALID", "ground_roi 必须是二维坐标数组 JSON", 422) from exc

    inference = await infer_camera_frame(data, roi)
    tracking = await run_in_threadpool(
        ground_tracker.process,
        camera_id,
        int(timestamp_ms or time.time() * 1000),
        (inference["image_width"], inference["image_height"]),
        inference["cigarettes"],
        inference["people"],
        inference["hands"],
    )
    return {
        **tracking,
        "roi": inference["roi"],
        "detections": {
            "cigarettes": inference["cigarettes"],
            "people": inference["people"],
            "hands": inference["hands"],
        },
        "timings": inference["timings"],
        "model": "cigarette-detector.pt",
    }


@router.get("/{camera_id}/status")
async def tracking_status(
    camera_id: str,
    _: object = Depends(require_pages("ai-model", "ai-config")),
) -> dict:
    return ground_tracker.status(camera_id)


@router.post("/{camera_id}/reset")
async def reset_tracking(
    camera_id: str,
    _: object = Depends(require_pages("ai-config")),
) -> dict:
    """仅在摄像头换位、ROI 改动或明确要求重新建立历史基线时调用。"""
    ground_tracker.reset(camera_id)
    return {"status": "ok", "camera_id": camera_id, "message": "跟踪状态已清空，将重新建立历史基线"}


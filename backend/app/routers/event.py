"""事件接口：查询、详情、热力、复核、一键演示一次违规。"""

import random

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import CurrentUser, require_pages, require_roles
from ..errors import event_not_found
from ..generator import ensure_pool, generate_camera_event
from ..models import Camera, Event, User, WorkOrder
from ..orders import create_workorder
from ..rules import compute_heatmap, recompute_suggestions
from ..schemas import EventReview, SimulateRequest
from ..services import client_ip, event_dict, paged, url, write_audit
from ..statemachine import EVENT_FLOW, assert_transition
from ..timeutil import now_cn
from ..ws import CHANNEL_ALERTS, CHANNEL_WORKORDERS, manager

router = APIRouter(prefix="/events", tags=["event"])

REVIEW_TARGET = {"confirm": "confirmed", "reject": "false_alarm", "refer": "referred", "close": "closed"}
REVIEW_ACTION = {
    "confirm": "EVENT_CONFIRM",
    "reject": "EVENT_REJECT",
    "refer": "EVENT_REFER",
    "close": "EVENT_CLOSE",
}


async def _order_of(session: AsyncSession, event_id: str) -> WorkOrder | None:
    return (
        await session.execute(select(WorkOrder).where(WorkOrder.event_id == event_id))
    ).scalar_one_or_none()


@router.get("")
async def list_events(
    page: int = 1,
    size: int = 20,
    camera_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_confidence: float | None = None,
    status: str | None = None,
    source: str | None = None,
    _: object = Depends(require_pages("alerts")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(Event)
    if camera_id:
        stmt = stmt.where(Event.camera_id == camera_id)
    if status:
        stmt = stmt.where(Event.status == status)
    if source:
        stmt = stmt.where(Event.source == source)
    if min_confidence is not None:
        stmt = stmt.where(Event.confidence >= min_confidence)
    # ISO 8601 同偏移量字符串字典序 = 时间序，可直接范围比较
    if start_date:
        stmt = stmt.where(Event.event_timestamp >= f"{start_date}T00:00:00")
    if end_date:
        stmt = stmt.where(Event.event_timestamp <= f"{end_date}T23:59:59.999+08:00")

    rows = list((await session.execute(stmt.order_by(Event.event_timestamp.desc()))).scalars())
    total = len(rows)
    page = max(1, page)
    size = min(200, max(1, size))
    sliced = rows[(page - 1) * size : page * size]

    orders = {
        o.event_id: o
        for o in (
            await session.execute(select(WorkOrder).where(WorkOrder.event_id.in_([r.event_id for r in sliced])))
        ).scalars()
    }
    return paged([event_dict(ev, orders.get(ev.event_id)) for ev in sliced], total, page, size)


@router.get("/heatmap")
async def heatmap(
    days: int = 7,
    _: object = Depends(require_pages("governance", "gis", "overview")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await compute_heatmap(session, days)


@router.get("/summary")
async def event_summary(
    _: object = Depends(require_pages("alerts", "overview")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = list((await session.execute(select(Event))).scalars())
    by_status: dict[str, int] = {}
    for ev in rows:
        by_status[ev.status] = by_status.get(ev.status, 0) + 1
    return {
        "total": len(rows),
        "by_status": by_status,
        "with_workorder": sum(1 for e in rows if e.has_workorder),
        "avg_confidence": round(sum(e.confidence for e in rows) / len(rows), 3) if rows else 0.0,
        "source": {
            "camera": sum(1 for e in rows if e.source == "camera"),
            "citizen": sum(1 for e in rows if e.source == "citizen"),
        },
    }


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    _: object = Depends(require_pages("alerts")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ev = (await session.execute(select(Event).where(Event.event_id == event_id))).scalar_one_or_none()
    if ev is None:
        raise event_not_found(event_id)
    return event_dict(ev, await _order_of(session, event_id))


@router.post("/{event_id}/review")
async def review_event(
    event_id: str,
    payload: EventReview,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ev = (await session.execute(select(Event).where(Event.event_id == event_id))).scalar_one_or_none()
    if ev is None:
        raise event_not_found(event_id)

    target = REVIEW_TARGET[payload.action]
    assert_transition(EVENT_FLOW, ev.status, target)

    if payload.action == "reject" and len(payload.note.strip()) < 4:
        from ..errors import ApiError

        raise ApiError("EVT_REJECT_NEEDS_REASON", "驳回必须填写驳回原因", 422)

    ev.status = target
    ev.review_note = payload.note
    ev.reviewed_by = user.real_name or user.username

    # 确认后自动建单，进入调度任务池（「审核 → 派单」不靠人工搬运）
    order = None
    if target in ("confirmed", "referred"):
        cam = (
            await session.execute(select(Camera).where(Camera.camera_id == ev.camera_id))
        ).scalar_one_or_none()
        order = await create_workorder(session, ev, cam)

    await write_audit(
        session,
        REVIEW_ACTION[payload.action],
        actor=user,
        target=f"event:{event_id}",
        detail=f"{ev.status} · {payload.note or '无备注'}",
        ip=client_ip(request),
    )
    await session.commit()

    if order is not None:
        await manager.broadcast(
            CHANNEL_WORKORDERS, {"type": "workorder.created", "order_no": order.order_no}
        )

    return {"event": event_dict(ev, order), "order_no": order.order_no if order else None}


@router.post("/simulate", status_code=201)
async def simulate_violation(
    payload: SimulateRequest,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """一键演示一次违规（答辩核心操作）。

    完整链路：生成合规事件 → WebSocket 推送 → 告警列表新增 → 自动建单 → 调度任务池出现 → 建议重算。
    """
    cameras = list((await session.execute(select(Camera).order_by(Camera.id))).scalars())
    if not cameras:
        from ..errors import not_found

        raise not_found("摄像头")

    if payload.camera_id:
        cameras = [c for c in cameras if c.camera_id == payload.camera_id] or cameras
    cam = cameras[0] if payload.camera_id else random.Random().choice(cameras)

    ensure_pool()
    ev = await generate_camera_event(session, cam, at=now_cn())
    ev.status = "pending_review"

    order = await create_workorder(session, ev, cam) if payload.create_workorder else None
    await write_audit(
        session,
        "EVENT_SIMULATE",
        actor=user,
        target=f"event:{ev.event_id}",
        detail="一键演示一次违规（演示数据，非真实识别结果）",
        ip=client_ip(request),
    )
    await session.commit()

    thumb = url(ev.frames[0].path) if ev.frames else ""
    await manager.broadcast(
        CHANNEL_ALERTS,
        {
            "type": "event.created",
            "event_id": ev.event_id,
            "camera_id": cam.camera_id,
            "camera_name": cam.name,
            "location_name": cam.location_name,
            "timestamp": ev.event_timestamp,
            "confidence": ev.confidence,
            "thumbnail_url": thumb,
            "demo": True,
        },
    )
    if order is not None:
        await manager.broadcast(
            CHANNEL_WORKORDERS, {"type": "workorder.created", "order_no": order.order_no}
        )

    # 建议随数据变化重算
    await recompute_suggestions(session)
    await session.commit()

    return {
        "event": event_dict(ev, order),
        "order_no": order.order_no if order else None,
        "demo": True,
        "message": "已生成 1 条演示事件（三段证据链齐全，非真实识别结果）",
    }

"""工单创建与编号。事件侧与市民上报侧共用。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Camera, Event, WorkOrder
from .timeutil import iso_ms, now_cn, parse_iso


async def next_order_no(session: AsyncSession, when=None) -> str:
    year = (when or now_cn()).year
    prefix = f"GD{year}"
    rows = list((await session.execute(select(WorkOrder.order_no))).scalars())
    seq = 0
    for value in rows:
        if value.startswith(prefix):
            try:
                seq = max(seq, int(value[len(prefix) :]))
            except ValueError:
                continue
    return f"{prefix}{seq + 1:06d}"


async def create_workorder(
    session: AsyncSession,
    event: Event,
    camera: Camera | None = None,
    *,
    priority: str | None = None,
) -> WorkOrder:
    """由事件创建待派发工单。已存在工单的事件直接返回原工单。"""
    existing = (
        await session.execute(select(WorkOrder).where(WorkOrder.event_id == event.event_id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    created = event.event_timestamp or iso_ms()
    order = WorkOrder(
        order_no=await next_order_no(session, parse_iso(created)),
        event_id=event.event_id,
        camera_id=event.camera_id,
        location_name=camera.location_name if camera else event.camera_name,
        latitude=camera.latitude if camera else 0.0,
        longitude=camera.longitude if camera else 0.0,
        status="pending",
        assigned_to="待派发",
        priority=priority or ("high" if event.confidence >= 0.9 else "normal"),
        created_at=created,
    )
    session.add(order)
    event.has_workorder = True
    await session.flush()
    return order


def is_overdue(order: WorkOrder, minutes: int = 30) -> bool:
    """超过 30 分钟未接收即视为超时（PRD §5.2.3）。"""
    if order.status != "pending":
        return False
    created = parse_iso(order.created_at)
    return (now_cn() - created).total_seconds() > minutes * 60

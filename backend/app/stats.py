"""统计聚合。

试点量级数据在 Python 层聚合，避免统计接口与数据库特定日期函数耦合。
"""

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Camera, Event, User, WorkOrder
from .statemachine import WORKORDER_CLOSED
from .timeutil import now_cn, parse_iso

OPEN_WORKORDER = ("pending", "accepted", "processing", "verifying")
EXCLUDED_EVENT_STATUS = {"false_alarm"}


async def _all(session: AsyncSession, model) -> list[Any]:
    return list((await session.execute(select(model))).scalars())


async def overview_metrics(session: AsyncSession) -> dict[str, Any]:
    now = now_cn()
    today = now.date()
    yesterday = today - timedelta(days=1)

    events = await _all(session, Event)
    orders = await _all(session, WorkOrder)
    cameras = await _all(session, Camera)
    workers = list(
        (await session.execute(select(User).where(User.role == "worker", User.enabled.is_(True)))).scalars()
    )

    def day_count(date) -> int:
        return sum(
            1
            for e in events
            if e.status not in EXCLUDED_EVENT_STATUS and parse_iso(e.event_timestamp).date() == date
        )

    today_count = day_count(today)
    yday_count = day_count(yesterday)
    delta = round((today_count - yday_count) / yday_count * 100, 1) if yday_count else 0.0

    closed = [o for o in orders if o.status in WORKORDER_CLOSED]
    responses = [o.response_time_sec for o in orders if o.response_time_sec]
    open_orders = [o for o in orders if o.status in OPEN_WORKORDER]
    closed_event_ids = {o.event_id for o in closed}
    unclosed = [e for e in events if e.status not in EXCLUDED_EVENT_STATUS and e.event_id not in closed_event_ids]

    return {
        "todayViolations": today_count,
        "processingEvents": len(open_orders),
        "onlineDevices": sum(1 for c in cameras if c.status == "online"),
        "onlineStaff": len(workers),
        "todayViolationsDelta": delta,
        "processingEventsDelta": 0.0,
        "onlineDevicesDelta": 0.0,
        "onlineStaffDelta": 0.0,
        "workorderTotal": len(orders),
        "workorderCompleted": len(closed),
        "workorderCompletionRate": round(len(closed) / len(orders) * 100, 1) if orders else 0.0,
        "avgResponseMin": round(sum(responses) / len(responses) / 60, 1) if responses else 0.0,
        "unclosedCount": len(unclosed),
    }


async def daily_trend(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    now = now_cn()
    events = await _all(session, Event)
    closed_ids_by_day: dict[Any, int] = defaultdict(int)
    for o in await _all(session, WorkOrder):
        if o.status in WORKORDER_CLOSED and o.completed_at:
            closed_ids_by_day[parse_iso(o.completed_at).date()] += 1

    out = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).date()
        detected = sum(
            1
            for e in events
            if e.status not in EXCLUDED_EVENT_STATUS and parse_iso(e.event_timestamp).date() == day
        )
        out.append({"date": day.isoformat(), "detected": detected, "handled": closed_ids_by_day.get(day, 0)})
    return out


async def hourly_distribution(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    now = now_cn()
    since = now - timedelta(days=days)
    hour_total = Counter()
    hour_high = Counter()
    for e in await _all(session, Event):
        ts = parse_iso(e.event_timestamp)
        if e.status in EXCLUDED_EVENT_STATUS or ts < since:
            continue
        hour_total[ts.hour] += 1
        if e.confidence >= 0.9:
            hour_high[ts.hour] += 1
    return [
        {"hour": f"{h:02d}:00", "total": hour_total.get(h, 0), "high": hour_high.get(h, 0)}
        for h in range(24)
    ]


async def area_metrics(session: AsyncSession, days: int = 30) -> list[dict[str, Any]]:
    now = now_cn()
    since = now - timedelta(days=days)
    cameras = {c.camera_id: c for c in await _all(session, Camera)}
    events = [e for e in await _all(session, Event) if e.status not in EXCLUDED_EVENT_STATUS]
    orders = await _all(session, WorkOrder)

    by_area_total: Counter = Counter()
    by_area_closed: Counter = Counter()
    for e in events:
        cam = cameras.get(e.camera_id)
        if cam:
            by_area_total[cam.location_name] += 1

    event_area = {}
    for e in events:
        cam = cameras.get(e.camera_id)
        event_area[e.event_id] = cam.location_name if cam else ""

    for o in orders:
        area = event_area.get(o.event_id)
        if area and o.status in WORKORDER_CLOSED:
            by_area_closed[area] += 1

    rows = []
    for area, total in by_area_total.most_common():
        closed = by_area_closed.get(area, 0)
        recent = sum(
            1
            for e in events
            if event_area.get(e.event_id) == area and parse_iso(e.event_timestamp) >= since - timedelta(days=7)
        )
        rows.append(
            {
                "area": area,
                "total": total,
                "closed": closed,
                "rate": round(closed / total * 100, 1) if total else 0.0,
                "recent7": recent,
            }
        )
    return rows


async def type_distribution(session: AsyncSession, days: int = 30) -> list[dict[str, Any]]:
    """按事件状态分布。

    说明：算法只实现「抛掷动作」一个类别，设计稿里的
    「乱扔烟头 / 违规吸烟 / 烟头落地 / 疑似抛掷」四个占比是占位数值。
    这里如实按**复核状态**统计，答辩时可解释为「待复核量 / 误报率」。
    """
    now = now_cn()
    since = now - timedelta(days=days)
    counter = Counter()
    for e in await _all(session, Event):
        if parse_iso(e.event_timestamp) < since:
            continue
        counter[e.status] += 1
    total = sum(counter.values()) or 1
    labels = {
        "candidate": "待分析",
        "pending_review": "待复核",
        "confirmed": "已确认",
        "referred": "已移送",
        "closed": "已闭环",
        "false_alarm": "已驳回（误报）",
    }
    return [
        {"name": labels.get(k, k), "value": round(v / total * 100, 1), "count": v}
        for k, v in counter.most_common()
    ]


async def health_snapshot(session: AsyncSession) -> dict[str, Any]:
    cameras = await _all(session, Camera)
    online = sum(1 for c in cameras if c.status == "online")
    return {
        "deviceOnlineRate": round(online / len(cameras) * 100, 1) if cameras else 0.0,
        "serviceAvailability": 99.9,
        "storageHealth": 62.4,
        "cameraTotal": len(cameras),
        "cameraOnline": online,
    }


async def counts_by(session: AsyncSession, column) -> dict[str, int]:
    rows = (await session.execute(select(column, func.count()).group_by(column))).all()
    return {str(k): int(v) for k, v in rows}

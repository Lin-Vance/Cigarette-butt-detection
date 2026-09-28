"""调度建议规则引擎（decision 模块的真实实现）。

不写死文案：全部从库里的事件记录按阈值推导，规则与阈值在文件顶部集中声明，
便于答辩时解释「建议是怎么算出来的」。
"""

from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Camera, Event, Suggestion
from .timeutil import iso, now_cn, parse_iso

# 阈值
FACILITY_SURGE_PCT = 30  # 近 7 天日均超出 30 天基线 30% → 建议增设设施
PEAK_SHARE_PCT = 25  # 某小时占全天 ≥ 25% → 建议调整班次
REPEAT_THRESHOLD = 3  # 同一区域 7 天内 ≥ 3 次 → 复发预警
EFFECTIVE_DROP_PCT = 20  # 近 7 天较前 7 天下降 ≥ 20% → 治理有效

# 不参与统计的状态
EXCLUDED_STATUS = {"false_alarm"}


def _group(events: list[Event], since, until) -> list[Event]:
    return [e for e in events if since <= parse_iso(e.event_timestamp) < until]


def pct_over(recent_daily: float, baseline: float) -> int:
    if baseline <= 0:
        return 100 if recent_daily > 0 else 0
    return round(((recent_daily - baseline) / baseline) * 100)


async def recompute_suggestions(session: AsyncSession) -> list[Suggestion]:
    """按当前事件数据重算建议。

    已有建议中，若 (type, area_name, time_range) 命中，保留其处理状态与反馈说明；
    不再命中的置为 expired（保留历史，不物理删除）。
    """
    now = now_cn()
    d7 = now - timedelta(days=7)
    d14 = now - timedelta(days=14)
    d30 = now - timedelta(days=30)

    events = list((await session.execute(select(Event))).scalars())
    events = [e for e in events if e.status not in EXCLUDED_STATUS]
    cameras = {c.camera_id: c for c in (await session.execute(select(Camera))).scalars()}

    def area_of(ev: Event) -> str:
        cam = cameras.get(ev.camera_id)
        return (cam.location_name if cam else ev.camera_name) or "未标注区域"

    last7 = _group(events, d7, now)
    prev7 = _group(events, d14, d7)
    last30 = _group(events, d30, now)

    drafts: list[dict] = []

    # 规则 1：区域高频 → 增设设施
    area_recent = Counter(area_of(e) for e in last7)
    baseline_daily = len(last30) / 30 if last30 else 0.0
    if area_recent and baseline_daily > 0:
        top_area, top_count = area_recent.most_common(1)[0]
        recent_daily = top_count / 7
        over = pct_over(recent_daily, baseline_daily)
        if over >= FACILITY_SURGE_PCT:
            drafts.append(
                {
                    "type": "add_facility",
                    "area_name": top_area,
                    "time_range": "",
                    "content": (
                        f"建议在 {top_area} 附近增设烟蒂收集设施。该区域近 7 天日均违规 "
                        f"{recent_daily:.1f} 次，高于近 30 天日均基线 {baseline_daily:.1f} 次（超出 {over}%）。"
                    ),
                    "frequency_data": {
                        "area": top_area,
                        "recent_count": top_count,
                        "recent_daily": round(recent_daily, 2),
                        "baseline_daily": round(baseline_daily, 2),
                        "over_pct": over,
                    },
                }
            )

    # 规则 2：时段峰值 → 调整班次
    hours = Counter(parse_iso(e.event_timestamp).hour for e in last7)
    if hours:
        peak_hour, peak_count = hours.most_common(1)[0]
        share = round(peak_count / len(last7) * 100)
        if share >= PEAK_SHARE_PCT:
            drafts.append(
                {
                    "type": "adjust_schedule",
                    "area_name": "",
                    "time_range": f"{peak_hour:02d}:00-{peak_hour + 1:02d}:00",
                    "content": (
                        f"建议在 {peak_hour:02d}:00-{peak_hour + 1:02d}:00 增派巡查人员。"
                        f"该时段近 7 天累计 {peak_count} 次，占全天违规的 {share}%，为全天峰值时段。"
                    ),
                    "frequency_data": {
                        "hour": peak_hour,
                        "recent_count": peak_count,
                        "share_pct": share,
                    },
                }
            )

    # 规则 3：同一区域重复发生 → 复发预警
    repeated = [(a, c) for a, c in area_recent.items() if c >= REPEAT_THRESHOLD]
    for area, count in sorted(repeated, key=lambda x: -x[1])[:1]:
        drafts.append(
            {
                "type": "warning",
                "area_name": area,
                "time_range": "",
                "content": (
                    f"{area} 近 7 天重复发生 {count} 次，属于复发点位。"
                    f"建议核查该处是否存在设施缺失、照明不足或管理盲区。"
                ),
                "frequency_data": {"area": area, "recent_count": count},
            }
        )

    # 规则 4：环比下降 → 治理有效
    prev_area = Counter(area_of(e) for e in prev7)
    for area, count in area_recent.most_common():
        before = prev_area.get(area, 0)
        if before >= 3:
            drop = round((before - count) / before * 100)
            if drop >= EFFECTIVE_DROP_PCT:
                drafts.append(
                    {
                        "type": "treatment_effective",
                        "area_name": area,
                        "time_range": "",
                        "content": (
                            f"{area} 治理措施生效：违规频次近 7 天较前 7 天下降 {drop}%，"
                            f"建议保持当前保洁与巡查方案。"
                        ),
                        "frequency_data": {"area": area, "drop_pct": drop},
                    }
                )
                break

    # 与既有建议合并：命中则保留处理状态
    existing = list((await session.execute(select(Suggestion))).scalars())
    index = {(s.type, s.area_name, s.time_range): s for s in existing}
    kept: set[int] = set()

    for draft in drafts:
        key = (draft["type"], draft["area_name"], draft["time_range"])
        found = index.get(key)
        if found is None:
            session.add(
                Suggestion(
                    type=draft["type"],
                    area_name=draft["area_name"],
                    time_range=draft["time_range"],
                    content=draft["content"],
                    frequency_data=draft["frequency_data"],
                    status="pending",
                    created_at=iso(now),
                )
            )
        else:
            found.content = draft["content"]
            found.frequency_data = draft["frequency_data"]
            kept.add(found.id)

    for s in existing:
        if s.id not in kept and s.status == "pending":
            s.status = "expired"

    await session.flush()
    return list((await session.execute(select(Suggestion).order_by(Suggestion.id))).scalars())


async def compute_heatmap(session: AsyncSession, days: int = 7) -> dict:
    """按摄像头坐标聚合权重，输出热力网格 + 包围盒。"""
    now = now_cn()
    since = now - timedelta(days=days)
    events = list((await session.execute(select(Event))).scalars())
    cameras = {c.camera_id: c for c in (await session.execute(select(Camera))).scalars()}

    grid = defaultdict(float)
    for ev in events:
        if ev.status in EXCLUDED_STATUS:
            continue
        if parse_iso(ev.event_timestamp) < since:
            continue
        cam = cameras.get(ev.camera_id)
        if cam is None:
            continue
        grid[(round(cam.latitude, 5), round(cam.longitude, 5))] += ev.confidence

    if not grid:
        return {"grid": [], "bbox": []}

    peak = max(grid.values())
    items = [
        {"lat": lat, "lon": lon, "weight": round(weight / peak, 3)}
        for (lat, lon), weight in sorted(grid.items(), key=lambda kv: -kv[1])
    ]
    lats = [i["lat"] for i in items]
    lons = [i["lon"] for i in items]
    # bbox 加一点外扩，避免单点退化成零面积
    pad = 0.002
    return {
        "grid": items,
        "bbox": [min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad],
    }

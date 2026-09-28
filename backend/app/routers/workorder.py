"""工单接口：查询、接单、开始处理、提交闭环、验收。

与 FDD §9.4 的**有意偏差**：FDD 把「上传闭环照片」直接置为 closed。
《竞赛风险逐项解决规划》§5.1 的黄金路径是
「移动工作台接单并上传清理后照片 → **审核员确认闭环**」两步，
所以这里拆成 `/complete`（作业端提交）与 `/verify`（管理端验收），
否则「审核员确认」这一步在系统里无处落地。
"""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..deps import CurrentUser, require_pages, require_roles
from ..errors import duplicate_submission, upload_invalid, workorder_conflict, workorder_not_found
from ..models import User, WorkOrder
from ..orders import is_overdue
from ..services import client_ip, paged, workorder_dict, write_audit
from ..statemachine import WORKORDER_CLOSED, WORKORDER_FLOW, assert_transition
from ..timeutil import iso_ms, now_cn, parse_iso
from ..ws import CHANNEL_WORKORDERS, manager
from .report import sync_report_with_order

router = APIRouter(prefix="/workorders", tags=["workorder"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".webp"}


def _assert(current: str, target: str) -> None:
    assert_transition(WORKORDER_FLOW, current, target, code="WO_INVALID_STATE")


async def _get(session: AsyncSession, order_id: int) -> WorkOrder:
    order = await session.get(WorkOrder, order_id)
    if order is None:
        raise workorder_not_found(order_id)
    return order


async def _sweep_timeouts(session: AsyncSession) -> int:
    """超 30 分钟未接收 → 标记超时（幂等，每次列表查询顺手跑一次）。"""
    rows = list((await session.execute(select(WorkOrder).where(WorkOrder.status == "pending"))).scalars())
    changed = 0
    for order in rows:
        if is_overdue(order):
            order.status = "timeout"
            order.escalated = True
            changed += 1
    if changed:
        await session.flush()
    return changed


@router.get("")
async def list_workorders(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    assigned_to: int | None = None,
    location: str | None = None,
    _: object = Depends(require_pages("dispatch-pool", "dispatch-records", "workboard")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _sweep_timeouts(session)
    await session.commit()

    stmt = select(WorkOrder)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if assigned_to:
        stmt = stmt.where(WorkOrder.assigned_to_id == assigned_to)
    if location:
        stmt = stmt.where(WorkOrder.location_name.like(f"%{location}%"))

    rows = list((await session.execute(stmt.order_by(WorkOrder.created_at.desc()))).scalars())
    total = len(rows)
    page = max(1, page)
    size = min(200, max(1, size))
    return paged([workorder_dict(o) for o in rows[(page - 1) * size : page * size]], total, page, size)


@router.get("/stats")
async def workorder_stats(
    _: object = Depends(require_pages("dispatch-pool", "dispatch-records", "workboard")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = list((await session.execute(select(WorkOrder))).scalars())
    by_status: dict[str, int] = {}
    for o in rows:
        by_status[o.status] = by_status.get(o.status, 0) + 1
    closed = [o for o in rows if o.status in WORKORDER_CLOSED]
    responses = [o.response_time_sec for o in rows if o.response_time_sec]
    return {
        "total": len(rows),
        "by_status": by_status,
        "closed": len(closed),
        "completion_rate": round(len(closed) / len(rows) * 100, 1) if rows else 0.0,
        "avg_response_min": round(sum(responses) / len(responses) / 60, 1) if responses else 0.0,
        "overdue": sum(1 for o in rows if o.escalated),
    }


@router.get("/{order_id}")
async def get_workorder(
    order_id: int,
    _: object = Depends(require_pages("dispatch-pool", "dispatch-records", "workboard")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return workorder_dict(await _get(session, order_id))


@router.post("/{order_id}/accept")
async def accept_workorder(
    order_id: int,
    request: Request,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    order = await _get(session, order_id)
    if order.status in WORKORDER_CLOSED:
        raise workorder_conflict("工单已闭环，无法再次接单")
    _assert(order.status, "accepted")

    order.status = "accepted"
    order.assigned_to = user.real_name or user.username
    order.assigned_to_id = user.id
    order.accepted_at = iso_ms(now_cn())
    order.escalated = False
    if order.created_at:
        order.response_time_sec = max(
            0, int((now_cn() - parse_iso(order.created_at)).total_seconds())
        )

    # 联动市民上报：已受理 → 处理中（一端操作、另一端可见）
    report = await sync_report_with_order(session, order.event_id, order)

    await write_audit(
        session,
        "WORKORDER_ACCEPT",
        actor=user,
        target=f"order:{order.order_no}",
        detail=f"接单，响应 {order.response_time_sec} 秒",
        ip=client_ip(request),
    )
    await session.commit()
    await manager.broadcast(
        CHANNEL_WORKORDERS,
        {
            "type": "workorder.accepted",
            "order_no": order.order_no,
            "assigned_to": order.assigned_to,
            "report_no": report.report_no if report else "",
        },
    )
    return workorder_dict(order)


@router.post("/{order_id}/start")
async def start_workorder(
    order_id: int,
    request: Request,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    order = await _get(session, order_id)
    _assert(order.status, "processing")
    order.status = "processing"
    order.started_at = iso_ms(now_cn())
    await write_audit(
        session,
        "WORKORDER_START",
        actor=user,
        target=f"order:{order.order_no}",
        detail="开始处理",
        ip=client_ip(request),
    )
    await session.commit()
    await manager.broadcast(
        CHANNEL_WORKORDERS, {"type": "workorder.processing", "order_no": order.order_no}
    )
    return workorder_dict(order)


@router.post("/{order_id}/complete")
async def complete_workorder(
    order_id: int,
    request: Request,
    user: CurrentUser,
    note: str = Form(""),
    photo: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """作业端提交清理后照片 → 进入待验收。"""
    order = await _get(session, order_id)
    if order.completion_submitted:
        raise duplicate_submission("该工单已提交过闭环材料，请勿重复提交")
    _assert(order.status, "verifying")

    saved_rel = ""
    if photo is not None:
        from pathlib import Path

        settings = get_settings()
        suffix = Path(photo.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIX:
            raise upload_invalid(f"仅支持 {', '.join(sorted(ALLOWED_SUFFIX))} 格式")
        data = await photo.read()
        if not data:
            raise upload_invalid("上传文件为空")
        if len(data) > MAX_PHOTO_BYTES:
            raise upload_invalid("闭环照片不得超过 10MB")

        target_dir = settings.evidence_dir / order.event_id
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / f"closure{suffix}"
        dest.write_bytes(data)
        saved_rel = str(dest.relative_to(settings.storage_dir)).replace("\\", "/")

    order.status = "verifying"
    order.completion_submitted = True
    order.completion_note = note
    if saved_rel:
        order.closure_photo_path = saved_rel
    if order.started_at is None:
        order.started_at = iso_ms(now_cn())

    await write_audit(
        session,
        "WORKORDER_COMPLETE",
        actor=user,
        target=f"order:{order.order_no}",
        detail=f"提交闭环材料{('（含照片）' if saved_rel else '（未附照片）')}：{note or '无备注'}",
        ip=client_ip(request),
    )
    await session.commit()
    await manager.broadcast(
        CHANNEL_WORKORDERS, {"type": "workorder.verifying", "order_no": order.order_no}
    )
    return workorder_dict(order)


@router.post("/{order_id}/verify")
async def verify_workorder(
    order_id: int,
    request: Request,
    passed: bool = Form(True),
    note: str = Form(""),
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """管理端验收：通过 → 已闭环；不通过 → 打回处理中。"""
    order = await _get(session, order_id)
    target = "closed" if passed else "processing"
    assert_transition(WORKORDER_FLOW, order.status, target, code="WO_INVALID_STATE")

    order.status = target
    now = iso_ms(now_cn())
    if passed:
        order.verified_at = now
        order.completed_at = now
    else:
        order.completion_submitted = False
        order.completion_note = (order.completion_note + f" / 验收未通过：{note}").strip(" /")

    # 联动市民上报：工单闭环 → 上报「已完成」，并写入公开回复
    report = await sync_report_with_order(session, order.event_id, order)

    await write_audit(
        session,
        "WORKORDER_VERIFY",
        actor=user,
        target=f"order:{order.order_no}",
        detail=f"验收{'通过' if passed else '不通过'}：{note or '无备注'}",
        ip=client_ip(request),
    )
    await session.commit()
    await manager.broadcast(
        CHANNEL_WORKORDERS,
        {
            "type": "workorder.closed" if passed else "workorder.reopened",
            "order_no": order.order_no,
            "report_no": report.report_no if report else "",
        },
    )
    return workorder_dict(order)

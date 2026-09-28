"""市民上报：市民端提交/查询/补充/撤回/申诉 + 管理端受理/不予受理/完成。

这条链就是《竞赛风险逐项解决规划》§5.1 的黄金路径前半段：
市民上传 → 分析任务 → 事件候选 → 审核员确认 →（工单生成）→ 市民端看到进度。

2026-09-28 补充：上传素材时当场产出的 **AI 报告快照**会随上报一起落库，
管理端复核时能看到当时的置信度 / 检出框 / 证据链口径；市民也可以对 AI 判断提交异议反馈。
"""

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import CurrentCitizen, require_roles
from ..errors import ApiError, report_not_found, report_status_locked
from ..generator import ensure_pool
from ..models import AnalysisTask, Camera, CitizenReport, Event, User, WorkOrder
from ..orders import create_workorder
from ..schemas import AiFeedback, ReportReject, ReportReply, ReportSubmit, ReportSupplement
from ..services import client_ip, loads_json, paged, report_dict, write_audit
from ..statemachine import REPORT_FLOW, TASK_FLOW, assert_transition
from ..timeutil import iso_ms, now_cn, plus_ms
from ..ws import CHANNEL_WORKORDERS, manager

citizen_router = APIRouter(prefix="/citizen/reports", tags=["report"])
public_router = APIRouter(prefix="/public/cases", tags=["report"])
admin_router = APIRouter(prefix="/reports", tags=["report"])

# 受理前可撤回；受理后只能申诉（三端架构 §5.6）
WITHDRAWABLE = {"submitted", "analyzing", "pending_review"}

# AI 报告快照大小上限：超出只留结论字段，避免把整份报告塞进库
AI_REPORT_MAX_CHARS = 8000


def _assert_report(current: str, target: str) -> None:
    assert_transition(REPORT_FLOW, current, target, code="RPT_INVALID_STATE")


def _assert_task(current: str, target: str) -> None:
    assert_transition(TASK_FLOW, current, target, code="TASK_INVALID_STATE")


async def _get(session: AsyncSession, report_no: str) -> CitizenReport:
    row = (
        await session.execute(select(CitizenReport).where(CitizenReport.report_no == report_no))
    ).scalar_one_or_none()
    if row is None:
        raise report_not_found(report_no)
    return row


async def _next_report_no(session: AsyncSession) -> str:
    rows = list((await session.execute(select(CitizenReport.report_no))).scalars())
    year = now_cn().year
    prefix = f"SB{year}"
    seq = 0
    for value in rows:
        if value.startswith(prefix):
            try:
                seq = max(seq, int(value[len(prefix) :]))
            except ValueError:
                continue
    return f"{prefix}{seq + 1:05d}"


async def sync_report_with_order(session: AsyncSession, event_id: str, order: WorkOrder) -> CitizenReport | None:
    """工单状态变化时推进市民上报状态——这是「一端操作、另一端可见」的落点。"""
    if not event_id:
        return None
    report = (
        await session.execute(select(CitizenReport).where(CitizenReport.event_id == event_id))
    ).scalar_one_or_none()
    if report is None:
        return None

    now = iso_ms(now_cn())
    if order.status in ("accepted", "processing") and report.status == "accepted":
        report.status = "processing"
        report.started_at = report.started_at or now
    elif order.status in ("closed",) and report.status in ("accepted", "processing"):
        report.status = "finished"
        report.finished_at = now
        if not report.public_reply:
            report.public_reply = "已核实并完成清理，现场已恢复整洁。感谢你的安全上报。"
    return report


# ---------------- 市民端 ----------------


@citizen_router.post("", status_code=201)
async def submit_report(
    payload: ReportSubmit,
    request: Request,
    phone: CurrentCitizen,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not payload.safe_confirmed:
        raise ApiError("RPT_SAFETY_NOT_CONFIRMED", "请先确认素材不是通过跟拍、拦截等危险方式取得", 422)
    if not payload.location.strip():
        raise ApiError("RPT_LOCATION_REQUIRED", "请填写发生地点", 422)

    now = now_cn()
    report_no = await _next_report_no(session)
    task_id = f"TK{now.year}{int(now.timestamp()) % 100000:05d}"

    # AI 报告快照：只留市民端上传时当场拿到的那份，便于管理端复核对照
    ai_snapshot = ""
    if payload.ai_report:
        try:
            dumped = json.dumps(payload.ai_report, ensure_ascii=False)
        except (TypeError, ValueError):
            dumped = ""
        if dumped:
            if len(dumped) > AI_REPORT_MAX_CHARS:
                trimmed = {
                    k: payload.ai_report.get(k)
                    for k in ("verdict", "verdict_label", "confidence", "count", "detected", "summary", "notice")
                }
                dumped = json.dumps({"trimmed": True, **trimmed}, ensure_ascii=False)[:AI_REPORT_MAX_CHARS]
            ai_snapshot = dumped

    report = CitizenReport(
        report_no=report_no,
        phone=phone,
        kind=payload.kind,
        media_name=payload.media_name,
        location=payload.location.strip(),
        description=payload.description.strip(),
        status="submitted",
        submitted_at=iso_ms(now),
        task_id=task_id,
        risk_flag=payload.has_risk,
        ai_report=ai_snapshot,
    )
    session.add(report)
    session.add(
        AnalysisTask(
            task_id=task_id,
            report_no=report_no,
            status="uploading",
            progress=0,
            stage_detail="素材已接收，等待排队",
            created_at=iso_ms(now),
        )
    )
    await write_audit(
        session,
        "REPORT_SUBMIT",
        actor_name=phone,
        role="citizen",
        target=f"report:{report_no}",
        detail=f"市民提交 {payload.kind} 线索，地点 {report.location}",
        ip=client_ip(request),
    )
    # 模型判定为候选线索时额外留一条审计：管理端的「三端协同动态」会立刻看到
    snapshot = loads_json(ai_snapshot)
    if snapshot and snapshot.get("verdict") == "candidate":
        await write_audit(
            session,
            "REPORT_AI_CANDIDATE",
            actor_name=phone,
            role="citizen",
            target=f"report:{report_no}",
            detail=f"AI 预检判定为候选线索（置信度 {snapshot.get('confidence', 0)}%），待人工复核",
            ip=client_ip(request),
        )
    await session.commit()
    return report_dict(report, include_phone=True)


@citizen_router.post("/{report_no}/ai-feedback")
async def ai_feedback(
    report_no: str,
    payload: AiFeedback,
    request: Request,
    phone: CurrentCitizen,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """市民对 AI 判断的反馈：同意 / 不同意（附理由与期望处理）。

    这是「AI 只做候选、人来做决定」的落点：市民可以明确表达"我不同意模型结论"，
    该反馈与 AI 报告一起出现在管理端，并且只允许提交一次，避免反复覆盖。
    """
    report = await _get(session, report_no)
    if report.phone != phone:
        raise report_not_found(report_no)
    if report.ai_feedback:
        raise ApiError("RPT_AI_FEEDBACK_ONCE", "该上报已经提交过 AI 反馈", 409)
    if not payload.agree and not payload.reason.strip():
        raise ApiError("RPT_AI_FEEDBACK_REASON", "不同意模型判断时请说明理由", 422)

    report.ai_feedback = json.dumps(
        {
            "agree": payload.agree,
            "reason": payload.reason.strip(),
            "expect": payload.expect.strip(),
        },
        ensure_ascii=False,
    )
    report.ai_feedback_at = iso_ms(now_cn())

    await write_audit(
        session,
        "REPORT_AI_FEEDBACK",
        actor_name=phone,
        role="citizen",
        target=f"report:{report_no}",
        detail=("市民认可 AI 判断" if payload.agree else f"市民不认可 AI 判断：{payload.reason.strip()[:60]}"),
        ip=client_ip(request),
    )
    await session.commit()
    return report_dict(report, include_phone=True)


@citizen_router.get("")
async def my_reports(phone: CurrentCitizen, session: AsyncSession = Depends(get_session)) -> dict:
    rows = list(
        (
            await session.execute(
                select(CitizenReport)
                .where(CitizenReport.phone == phone)
                .order_by(CitizenReport.submitted_at.desc())
            )
        ).scalars()
    )
    return paged([report_dict(r, include_phone=True) for r in rows], len(rows), 1, len(rows) or 1)


@citizen_router.get("/{report_no}")
async def my_report(report_no: str, phone: CurrentCitizen, session: AsyncSession = Depends(get_session)) -> dict:
    report = await _get(session, report_no)
    if report.phone != phone:
        raise report_not_found(report_no)
    return report_dict(report, include_phone=True)


@citizen_router.post("/{report_no}/supplement")
async def supplement_report(
    report_no: str,
    payload: ReportSupplement,
    phone: CurrentCitizen,
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    if report.phone != phone:
        raise report_not_found(report_no)
    if report.status in ("withdrawn",):
        raise report_status_locked("已撤回的上报不能补充材料")

    if payload.description.strip():
        report.description = f"{report.description}\n【补充】{payload.description.strip()}".strip()
    if payload.media_name.strip():
        report.media_name = payload.media_name.strip()
    await session.commit()
    return report_dict(report, include_phone=True)


@citizen_router.post("/{report_no}/withdraw")
async def withdraw_report(
    report_no: str,
    request: Request,
    phone: CurrentCitizen,
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    if report.phone != phone:
        raise report_not_found(report_no)
    if report.status not in WITHDRAWABLE:
        raise report_status_locked("已受理的上报不能直接撤回，请改用申诉")

    _assert_report(report.status, "withdrawn")
    report.status = "withdrawn"
    await write_audit(
        session,
        "REPORT_WITHDRAW",
        actor_name=phone,
        role="citizen",
        target=f"report:{report_no}",
        detail="市民撤回上报",
        ip=client_ip(request),
    )
    await session.commit()
    return report_dict(report, include_phone=True)


@citizen_router.post("/{report_no}/appeal")
async def appeal_report(
    report_no: str,
    payload: ReportSupplement,
    phone: CurrentCitizen,
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    if report.phone != phone:
        raise report_not_found(report_no)
    if report.status not in ("finished", "rejected"):
        raise report_status_locked("只有已完结或不予受理的上报可以申诉")
    if report.appeal_note:
        raise ApiError("RPT_APPEAL_ONCE", "每条上报只允许申诉一次", 409)

    _assert_report(report.status, "appealing")
    report.status = "appealing"
    report.appeal_note = payload.description.strip() or "申请复核"
    await session.commit()
    return report_dict(report, include_phone=True)


# ---------------- 公开结果（无需登录，供官网「查询线索」） ----------------


@public_router.get("/{report_no}")
async def public_case(report_no: str, session: AsyncSession = Depends(get_session)) -> dict:
    report = await _get(session, report_no)
    return report_dict(report, include_phone=False)


# ---------------- 管理端 ----------------


@admin_router.get("")
async def list_reports(
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    keyword: str = "",
    _: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(CitizenReport)
    if status:
        stmt = stmt.where(CitizenReport.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            (CitizenReport.report_no.like(like))
            | (CitizenReport.location.like(like))
            | (CitizenReport.phone.like(like))
        )
    rows = list((await session.execute(stmt.order_by(CitizenReport.submitted_at.desc()))).scalars())
    total = len(rows)
    page = max(1, page)
    size = min(200, max(1, size))
    return paged([report_dict(r) for r in rows[(page - 1) * size : page * size]], total, page, size)


@admin_router.get("/{report_no}")
async def admin_report_detail(
    report_no: str,
    _: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return report_dict(await _get(session, report_no))


@admin_router.post("/{report_no}/analyze")
async def run_analysis(
    report_no: str,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """推进分析任务，并派生一条候选事件。

    真实系统里这一步是异步流水线；演示环境下同步跑完，
    但状态流转仍按 §5.2 的「上传中 → 排队中 → 分析中 → 证据生成中 → 待复核」逐级推进。
    """
    report = await _get(session, report_no)
    if report.status not in ("submitted",):
        raise report_status_locked(f"当前状态（{report.status}）不能启动分析")

    task = (
        await session.execute(select(AnalysisTask).where(AnalysisTask.report_no == report_no))
    ).scalar_one_or_none()

    # 逐级流转，保证状态机形态真实
    for target in ("queued", "analyzing", "generating"):
        if task is None:
            break
        _assert_task(task.status, target)
        task.status = target
        task.progress = {"queued": 20, "analyzing": 60, "generating": 85}[target]
        task.stage_detail = {
            "queued": "已进入分析队列",
            "analyzing": "正在定位持烟 / 抛掷 / 落地阶段",
            "generating": "正在生成三段式证据帧",
        }[target]

    report.status = "analyzing"
    report.accepted_at = None

    # 派生候选事件（市民素材来源）
    ensure_pool()
    cameras = list((await session.execute(select(Camera).order_by(Camera.id))).scalars())
    event = None
    if cameras:
        cam = cameras[hash(report_no) % len(cameras)]
        from ..generator import build_event

        import random as _random

        event = build_event(
            cam,
            at=now_cn(),
            rng=_random.Random(report_no),
            source="citizen",
            report_no=report_no,
        )
        session.add(event)
        await session.flush()
        report.event_id = event.event_id

    if task is not None:
        _assert_task(task.status, "pending_review")
        task.status = "pending_review"
        task.progress = 95
        task.stage_detail = "证据已生成，等待人工复核"
        task.event_id = report.event_id
        task.finished_at = iso_ms(now_cn())

    _assert_report(report.status, "pending_review")
    report.status = "pending_review"

    await write_audit(
        session,
        "REPORT_ANALYZE",
        actor=user,
        target=f"report:{report_no}",
        detail=f"分析完成，派生候选事件 {report.event_id}",
        ip=client_ip(request),
    )
    await session.commit()
    return {"report": report_dict(report), "task_id": task.task_id if task else "", "event_id": report.event_id}


@admin_router.post("/{report_no}/accept")
async def accept_report(
    report_no: str,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """受理：确认候选事件并自动建单（黄金路径的关键一跳）。"""
    report = await _get(session, report_no)
    _assert_report(report.status, "accepted")

    event = None
    order = None
    if report.event_id:
        event = (
            await session.execute(select(Event).where(Event.event_id == report.event_id))
        ).scalar_one_or_none()
    if event is not None:
        if event.status in ("candidate", "pending_review"):
            event.status = "confirmed"
            event.reviewed_by = user.real_name or user.username
            event.review_note = f"受理市民上报 {report_no}"
        cam = (await session.execute(select(Camera).where(Camera.camera_id == event.camera_id))).scalar_one_or_none()
        order = await create_workorder(session, event, cam)

    report.status = "accepted"
    report.accepted_at = iso_ms(now_cn())

    await write_audit(
        session,
        "REPORT_ACCEPT",
        actor=user,
        target=f"report:{report_no}",
        detail=f"受理上报，生成工单 {order.order_no if order else '（无）'}",
        ip=client_ip(request),
    )
    await session.commit()

    if order is not None:
        await manager.broadcast(
            CHANNEL_WORKORDERS, {"type": "workorder.created", "order_no": order.order_no}
        )
    return {"report": report_dict(report), "order_no": order.order_no if order else None}


@admin_router.post("/{report_no}/reject")
async def reject_report(
    report_no: str,
    payload: ReportReject,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    _assert_report(report.status, "rejected")

    report.status = "rejected"
    report.rejected_at = iso_ms(now_cn())
    report.reject_reason = payload.reason

    if report.event_id:
        event = (
            await session.execute(select(Event).where(Event.event_id == report.event_id))
        ).scalar_one_or_none()
        if event is not None and event.status in ("candidate", "pending_review"):
            event.status = "false_alarm"
            event.review_note = f"上报 {report_no} 不予受理：{payload.reason}"

    await write_audit(
        session,
        "REPORT_REJECT",
        actor=user,
        target=f"report:{report_no}",
        detail=f"不予受理：{payload.reason}",
        ip=client_ip(request),
    )
    await session.commit()
    return {"report": report_dict(report)}


@admin_router.post("/{report_no}/finish")
async def finish_report(
    report_no: str,
    payload: ReportReply,
    request: Request,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    if report.status == "accepted":
        _assert_report("accepted", "processing")
        report.status = "processing"
        report.started_at = report.started_at or iso_ms(now_cn())
    _assert_report(report.status, "finished")

    report.status = "finished"
    report.finished_at = iso_ms(now_cn())
    report.public_reply = payload.public_reply

    await write_audit(
        session,
        "REPORT_FINISH",
        actor=user,
        target=f"report:{report_no}",
        detail="办理完成并公开回复",
        ip=client_ip(request),
    )
    await session.commit()
    return {"report": report_dict(report)}


@admin_router.post("/{report_no}/start")
async def start_report(
    report_no: str,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    _assert_report(report.status, "processing")
    report.status = "processing"
    report.started_at = iso_ms(now_cn())
    await session.commit()
    return {"report": report_dict(report)}


@admin_router.post("/{report_no}/reopen-appeal")
async def resolve_appeal(
    report_no: str,
    payload: ReportReply,
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get(session, report_no)
    if report.status != "appealing":
        raise report_status_locked("该上报不在申诉状态")
    _assert_report(report.status, "finished")
    report.status = "finished"
    report.finished_at = iso_ms(now_cn())
    report.public_reply = payload.public_reply
    await session.commit()
    return {"report": report_dict(report)}


# 让 plus_ms / 未用到的导入保持显式（供后续扩展时间线推演）
_ = plus_ms

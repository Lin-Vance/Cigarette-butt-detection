"""审计日志：只读查询。审计表不提供任何修改/删除接口（对齐页面 18）。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_roles
from ..models import AuditLog, User
from ..services import audit_dict, paged

router = APIRouter(prefix="/audit", tags=["audit"])

ACTION_LABELS = {
    "AUTH_LOGIN": "登录",
    "AUTH_LOGOUT": "退出登录",
    "USER_CREATE": "新建账号",
    "USER_UPDATE": "修改账号",
    "USER_RESET_PASSWORD": "重置密码",
    "CAMERA_CREATE": "新增摄像头",
    "CAMERA_UPDATE": "修改摄像头",
    "AI_CONFIG_UPDATE": "修改 AI 阈值",
    "AI_PREPROCESS_TOGGLE": "切换图像预处理",
    "EVENT_SIMULATE": "一键演示违规",
    "EVENT_CONFIRM": "事件确认",
    "EVENT_REJECT": "事件驳回",
    "EVENT_REFER": "事件移送",
    "EVENT_CLOSE": "事件闭环",
    "WORKORDER_ACCEPT": "工单接单",
    "WORKORDER_START": "工单开始处理",
    "WORKORDER_COMPLETE": "提交闭环材料",
    "WORKORDER_VERIFY": "工单验收",
    "REPORT_SUBMIT": "市民提交上报",
    "REPORT_AI_CANDIDATE": "AI 预检判定候选线索",
    "REPORT_AI_FEEDBACK": "市民反馈 AI 判断",
    "REPORT_WITHDRAW": "市民撤回上报",
    "REPORT_ANALYZE": "上报分析",
    "REPORT_ACCEPT": "受理上报",
    "REPORT_REJECT": "上报不予受理",
    "REPORT_FINISH": "上报办结",
    "SUGGESTION_FEEDBACK": "建议反馈",
    "SUGGESTION_RECOMPUTE": "建议重算",
}


@router.get("/logs")
async def list_logs(
    page: int = 1,
    size: int = 20,
    user_id: int | None = None,
    action: str | None = None,
    result: str | None = None,
    keyword: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    _: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(AuditLog)
    if user_id:
        stmt = stmt.where(AuditLog.actor_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if result:
        stmt = stmt.where(AuditLog.result == result)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((AuditLog.actor.like(like)) | (AuditLog.target.like(like)) | (AuditLog.detail.like(like)))
    if start_date:
        stmt = stmt.where(AuditLog.ts >= f"{start_date}T00:00:00")
    if end_date:
        stmt = stmt.where(AuditLog.ts <= f"{end_date}T23:59:59.999+08:00")

    rows = list((await session.execute(stmt.order_by(AuditLog.id.desc()))).scalars())
    total = len(rows)
    page = max(1, page)
    size = min(200, max(1, size))

    items = []
    for log in rows[(page - 1) * size : page * size]:
        item = audit_dict(log)
        item["action_label"] = ACTION_LABELS.get(log.action, log.action)
        items.append(item)
    return paged(items, total, page, size)


@router.get("/actions")
async def list_actions(_: User = Depends(require_roles("admin", "manager"))) -> dict:
    return {"items": [{"key": k, "label": v} for k, v in ACTION_LABELS.items()]}

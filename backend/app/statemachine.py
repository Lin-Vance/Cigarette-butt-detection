"""共享状态机定义与校验。

三条主状态链对齐《竞赛风险逐项解决规划》§5.2「共享状态模型」。
三端读同一份后端数据，任何流转都必须经过这里的白名单校验，
不允许前端直接改状态。
"""

from .errors import invalid_state_transition

# ---------------- 事件 ----------------
# 候选 → 待复核 → 已确认 / 已驳回 → （满足条件）已移送 → 已闭环
EVENT_FLOW: dict[str, set[str]] = {
    "candidate": {"pending_review", "confirmed", "false_alarm"},
    "pending_review": {"confirmed", "false_alarm", "referred"},
    "confirmed": {"closed", "referred"},
    "referred": {"closed"},
    "closed": set(),
    "false_alarm": set(),
}

EVENT_LABELS: dict[str, str] = {
    "candidate": "候选",
    "pending_review": "待复核",
    "confirmed": "已确认",
    "false_alarm": "已驳回",
    "referred": "已移送",
    "closed": "已闭环",
}

# ---------------- 工单 ----------------
WORKORDER_FLOW: dict[str, set[str]] = {
    "pending": {"accepted", "timeout"},
    "accepted": {"processing", "timeout"},
    "processing": {"verifying", "completed", "timeout"},
    "verifying": {"closed", "processing"},  # 验收不通过打回处理中
    "completed": {"closed"},
    "timeout": {"accepted"},
    "closed": set(),
}

WORKORDER_LABELS: dict[str, str] = {
    "pending": "待派发",
    "accepted": "待接单",
    "processing": "处理中",
    "verifying": "待验收",
    "completed": "已完成",
    "closed": "已闭环",
    "timeout": "超时",
}

# 视为「已闭环」的工单状态（用于未闭环统计）
WORKORDER_CLOSED = {"closed", "completed"}

# ---------------- 市民上报 ----------------
REPORT_FLOW: dict[str, set[str]] = {
    "submitted": {"analyzing", "withdrawn"},
    "analyzing": {"pending_review", "withdrawn", "rejected", "failed"},
    "pending_review": {"accepted", "rejected"},
    "accepted": {"processing", "rejected"},
    "processing": {"finished", "rejected"},
    "finished": {"appealing"},
    "appealing": {"finished", "rejected"},
    "rejected": {"appealing"},
    "withdrawn": set(),
    "failed": {"analyzing", "withdrawn"},
}

REPORT_LABELS: dict[str, str] = {
    "submitted": "已提交",
    "analyzing": "分析中",
    "pending_review": "待复核",
    "accepted": "已受理",
    "processing": "处理中",
    "finished": "已完成",
    "rejected": "不予受理",
    "withdrawn": "已撤回",
    "appealing": "申诉中",
    "failed": "分析失败",
}

# 不予受理必须给出原因（三端架构 §5.6）
REJECT_REASONS: list[str] = [
    "素材经核查无法还原抛掷动作，仅可见地面烟头",
    "素材来源无法确认合法授权",
    "画面中无可识别的公共区域，超出受理范围",
    "同一地点同一问题已在处理中，避免重复受理",
    "时段与地点信息不足以派发任务",
]

# ---------------- 分析任务 ----------------
TASK_FLOW: dict[str, set[str]] = {
    "uploading": {"queued", "failed"},
    "queued": {"analyzing", "failed"},
    "analyzing": {"generating", "failed"},
    "generating": {"pending_review", "failed"},
    "pending_review": {"finished", "failed"},
    "finished": set(),
    "failed": {"queued"},
}

TASK_LABELS: dict[str, str] = {
    "uploading": "上传中",
    "queued": "排队中",
    "analyzing": "分析中",
    "generating": "证据生成中",
    "pending_review": "待复核",
    "finished": "完成",
    "failed": "失败",
}


def can(flow: dict[str, set[str]], current: str, target: str) -> bool:
    return target in flow.get(current, set())


def assert_transition(flow: dict[str, set[str]], current: str, target: str, code: str = "EVT_INVALID_STATE") -> None:
    """非法流转一律 409。code 按模块区分（EVT/WO/RPT/TASK），便于前端定位。"""
    if not can(flow, current, target):
        raise invalid_state_transition(current, target, code)

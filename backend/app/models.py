"""ORM 模型。

约定（对齐修订说明 C3）：
所有时间字段一律存 **ISO 8601 带 +08:00 时区** 的字符串，例如
`2026-09-27T19:42:16.123+08:00`。存字符串而非 DateTime 的原因：
1. 时区口径在序列化层就无法被悄悄改成本地时间（原缺陷就是无时区本地时间）；
2. SQLite / PostgreSQL 双库行为一致；
3. ISO 8601 同偏移量的字符串字典序等于时间序，范围查询可直接比较。
"""

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(64))
    real_name: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(16), default="worker")  # admin/manager/worker/ai_dev
    phone: Mapped[str] = mapped_column(String(32), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(40))


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    location_name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="online")  # online/offline/degraded
    fps: Mapped[float] = mapped_column(Float, default=25.0)
    preprocess_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    preprocess_algorithm: Mapped[str] = mapped_column(String(32), default="retinex")
    online_rate: Mapped[float] = mapped_column(Float, default=99.0)
    # 以下三项是 FDD §9.2 的字段，前端列表不展示，但接口要能返回
    rtsp_url: Mapped[str] = mapped_column(String(255), default="")
    roi_polygon: Mapped[list | None] = mapped_column(JSON, default=None)
    created_at: Mapped[str] = mapped_column(String(40))


class Event(Base):
    """违规事件（行为候选）。

    status 状态机（风险规划 §5.2）：
      候选 candidate → 待复核 pending_review → 已确认 confirmed / 已驳回 false_alarm → 已移送 referred
    另保留 closed（已闭环）以便与前端 mock/types.ts 的 EventStatus 对齐。
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    camera_id: Mapped[str] = mapped_column(String(32), index=True)
    camera_name: Mapped[str] = mapped_column(String(128), default="")
    track_id: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(24), default="THROW_CONFIRMED")
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[list] = mapped_column(JSON, default=list)
    trajectory: Mapped[list] = mapped_column(JSON, default=list)
    event_timestamp: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(24), default="candidate", index=True)
    has_workorder: Mapped[bool] = mapped_column(Boolean, default=False)
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(64), default="")
    video_clip_path: Mapped[str] = mapped_column(String(255), default="")
    # 来源：camera（固定摄像头）/ citizen（市民上报派生）
    source: Mapped[str] = mapped_column(String(16), default="camera")
    report_no: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[str] = mapped_column(String(40))

    frames: Mapped[list["EvidenceFrame"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", lazy="selectin"
    )


class EvidenceFrame(Base):
    __tablename__ = "evidence_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.event_id", ondelete="CASCADE"), index=True)
    frame_ts: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(16))  # holding / throwing / landed
    path: Mapped[str] = mapped_column(String(255))  # 必须非空（对应缺陷 A4）
    frame_no: Mapped[int] = mapped_column(Integer, default=0)  # 100fps 帧号

    event: Mapped[Event] = relationship(back_populates="frames")


class WorkOrder(Base):
    """工单状态机（风险规划 §5.2）：
    待派发 pending → 待接单 accepted → 处理中 processing → 待验收 verifying → 已闭环 closed
    异常分支：timeout（超 30 分钟未接收，PRD §5.2.3）
    """

    __tablename__ = "workorders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    event_id: Mapped[str] = mapped_column(String(48), index=True)
    camera_id: Mapped[str] = mapped_column(String(32), default="")
    location_name: Mapped[str] = mapped_column(String(128), default="")
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    assigned_to: Mapped[str] = mapped_column(String(64), default="待派发")
    assigned_to_id: Mapped[int | None] = mapped_column(Integer, default=None)
    priority: Mapped[str] = mapped_column(String(8), default="normal")
    created_at: Mapped[str] = mapped_column(String(40))
    accepted_at: Mapped[str | None] = mapped_column(String(40), default=None)
    started_at: Mapped[str | None] = mapped_column(String(40), default=None)
    verified_at: Mapped[str | None] = mapped_column(String(40), default=None)
    completed_at: Mapped[str | None] = mapped_column(String(40), default=None)
    response_time_sec: Mapped[int | None] = mapped_column(Integer, default=None)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    closure_photo_path: Mapped[str] = mapped_column(String(255), default="")
    completion_note: Mapped[str] = mapped_column(Text, default="")
    # 同一工单只允许一次闭环提交（对应「重复提交」验收项）
    completion_submitted: Mapped[bool] = mapped_column(Boolean, default=False)


class CitizenReport(Base):
    """市民上报状态机（三端架构 §5.6）：
    已提交 submitted → 分析中 analyzing → 待复核 pending_review → 已受理 accepted
    → 处理中 processing → 已完成 finished / 不予受理 rejected
    受理前可撤回 withdrawn；已完成/不予受理后可申诉 appealing
    """

    __tablename__ = "citizen_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="video")  # video / photo
    media_name: Mapped[str] = mapped_column(String(255), default="")
    media_path: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="submitted", index=True)
    submitted_at: Mapped[str] = mapped_column(String(40))
    accepted_at: Mapped[str | None] = mapped_column(String(40), default=None)
    started_at: Mapped[str | None] = mapped_column(String(40), default=None)
    finished_at: Mapped[str | None] = mapped_column(String(40), default=None)
    rejected_at: Mapped[str | None] = mapped_column(String(40), default=None)
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    public_reply: Mapped[str] = mapped_column(Text, default="")
    result_photo_path: Mapped[str] = mapped_column(String(255), default="")
    event_id: Mapped[str] = mapped_column(String(48), default="")
    task_id: Mapped[str] = mapped_column(String(48), default="")
    appeal_note: Mapped[str] = mapped_column(Text, default="")
    risk_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    # 市民上传素材时当场产出的 AI 报告快照（JSON 字符串）。
    # 存快照而不是只存一个结论：管理端复核时能看到当时的置信度、检出框与证据链口径。
    ai_report: Mapped[str] = mapped_column(Text, default="")
    # 市民对 AI 判断的异议反馈（JSON 字符串）：{ agree: bool, reason: str, expect: str }
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    ai_feedback_at: Mapped[str] = mapped_column(String(40), default="")


class AnalysisTask(Base):
    """分析任务状态机（风险规划 §5.2）：
    上传中 uploading → 排队中 queued → 分析中 analyzing → 证据生成中 generating
    → 待复核 pending_review → 完成 finished / 失败 failed
    """

    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    report_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    status: Mapped[str] = mapped_column(String(24), default="uploading")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage_detail: Mapped[str] = mapped_column(String(160), default="")
    failed_reason: Mapped[str] = mapped_column(Text, default="")
    event_id: Mapped[str] = mapped_column(String(48), default="")
    created_at: Mapped[str] = mapped_column(String(40))
    finished_at: Mapped[str | None] = mapped_column(String(40), default=None)


class Suggestion(Base):
    """调度建议（decision 模块）。"""

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32))  # add_facility / adjust_schedule / treatment_effective / warning
    area_name: Mapped[str] = mapped_column(String(128))
    time_range: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text)
    frequency_data: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[str] = mapped_column(String(40))
    feedback_note: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[str | None] = mapped_column(String(40), default=None)


class AuditLog(Base):
    """审计日志：登录审计 + 敏感操作审计（只增不改不删）。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, default=None)
    actor: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(16), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(16), default="success")  # success / denied / failed
    ip: Mapped[str] = mapped_column(String(64), default="")

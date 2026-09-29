"""请求体模型。响应统一走 services.py 的字典序列化（保持与前端的宽松契约）。"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------- auth ----------------


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class CitizenLoginRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)
    code: str = Field(default="", max_length=8)
    password: str = Field(default="", max_length=128)
    method: Literal["code", "password"] = "code"
    mode: Literal["login", "register"] = "login"


class LoginCodeRequest(BaseModel):
    target: str = Field(min_length=1, max_length=64)
    role: Literal["citizen", "worker", "admin"]


class CodeLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=6, max_length=6)
    role: Literal["worker", "admin"]


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = ""
    role: Literal["admin", "manager", "worker", "ai_dev"] = "worker"
    phone: str = ""


class UserUpdate(BaseModel):
    real_name: str | None = None
    role: Literal["admin", "manager", "worker", "ai_dev"] | None = None
    phone: str | None = None
    enabled: bool | None = None


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


# ---------------- camera ----------------


class CameraCreate(BaseModel):
    camera_id: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    rtsp_url: str = ""
    location_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    roi_polygon: list[list[float]] | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    location_name: str | None = None
    rtsp_url: str | None = None
    status: Literal["online", "offline", "degraded"] | None = None
    fps: float | None = None
    preprocess_enabled: bool | None = None
    preprocess_algorithm: Literal["retinex", "histogram_eq"] | None = None
    roi_polygon: list[list[float]] | None = None


class PreprocessToggle(BaseModel):
    camera_id: str
    enabled: bool
    algorithm: Literal["retinex", "histogram_eq"] = "retinex"
    auto_mode: bool = False


class AiConfigRequest(BaseModel):
    camera_id: str
    confidence_threshold: float = Field(ge=0.0, le=1.0, default=0.8)
    state_machine_params: dict[str, Any] = Field(default_factory=dict)
    roi: dict[str, Any] = Field(default_factory=dict)


# ---------------- event ----------------


class EventReview(BaseModel):
    action: Literal["confirm", "reject", "refer", "close"]
    note: str = ""


class SimulateRequest(BaseModel):
    camera_id: str | None = None
    # 是否顺带建单（一键演示默认建单，进入调度任务池）
    create_workorder: bool = True


# ---------------- workorder ----------------


class WorkOrderAction(BaseModel):
    note: str = ""


class WorkOrderVerify(BaseModel):
    passed: bool = True
    note: str = ""


# ---------------- citizen report ----------------


class ReportSubmit(BaseModel):
    kind: Literal["video", "photo"] = "video"
    media_name: str = ""
    location: str = ""
    description: str = ""
    safe_confirmed: bool = False
    has_risk: bool = False
    # 上传时当场产出的 AI 报告快照（市民端把 /public/ai/inspect 的结果原样回传）。
    # 存快照而不是只存结论：管理端复核时能看到当时的置信度、检出框与证据链口径。
    ai_report: dict[str, Any] | None = None


class AiFeedback(BaseModel):
    """市民对 AI 判断的反馈（同意 / 不同意 + 理由）。"""

    agree: bool = False
    reason: str = Field(default="", max_length=300)
    expect: str = Field(default="", max_length=200)


class ReportSupplement(BaseModel):
    description: str = ""
    media_name: str = ""


class ReportReject(BaseModel):
    reason: str = Field(min_length=4, max_length=200)


class ReportReply(BaseModel):
    public_reply: str = Field(min_length=2, max_length=500)


# ---------------- decision ----------------


class SuggestionFeedback(BaseModel):
    action: Literal["accepted", "rejected"]
    note: str = ""

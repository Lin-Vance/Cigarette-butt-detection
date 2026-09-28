"""统一错误码。格式 MODULE_ERROR_TYPE，对齐 FDD §10。"""

from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, code: str, message: str, http_status: int, extra: dict[str, Any] | None = None):
        body: dict[str, Any] = {"error_code": code, "message": message}
        if extra:
            body.update(extra)
        super().__init__(status_code=http_status, detail=body)
        self.error_code = code
        self.error_message = message


# ---- AUTH ----
def invalid_credentials() -> ApiError:
    return ApiError("AUTH_INVALID_CREDENTIALS", "用户名或密码错误", 401)


def token_expired() -> ApiError:
    return ApiError("AUTH_TOKEN_EXPIRED", "Token 已过期", 401)


def token_invalid() -> ApiError:
    return ApiError("AUTH_TOKEN_INVALID", "Token 无效", 401)


def account_disabled() -> ApiError:
    return ApiError("AUTH_ACCOUNT_DISABLED", "账户已禁用", 403)


def permission_denied(need: str = "") -> ApiError:
    msg = "无权限执行此操作" + (f"（需要 {need}）" if need else "")
    return ApiError("AUTH_PERMISSION_DENIED", msg, 403)


# ---- CAM ----
def camera_not_found(camera_id: str = "") -> ApiError:
    return ApiError("CAM_NOT_FOUND", f"摄像头 {camera_id} 不存在", 404)


def camera_duplicate(camera_id: str) -> ApiError:
    return ApiError("CAM_DUPLICATE", f"摄像头 {camera_id} 已存在", 409)


def camera_offline(camera_id: str) -> ApiError:
    return ApiError("CAM_OFFLINE", f"摄像头 {camera_id} 离线", 503)


# ---- EVT ----
def event_not_found(event_id: str = "") -> ApiError:
    return ApiError("EVT_NOT_FOUND", f"事件 {event_id} 不存在", 404)


def evidence_chain_invalid(reason: str) -> ApiError:
    return ApiError("EVT_EVIDENCE_CHAIN_INVALID", f"证据链校验未通过：{reason}", 422)


def invalid_state_transition(current: str, target: str, code: str = "EVT_INVALID_STATE") -> ApiError:
    return ApiError(code, f"状态不允许从 {current} 流转到 {target}", 409)


# ---- WO ----
def workorder_not_found(order_id: int | str = "") -> ApiError:
    return ApiError("WO_NOT_FOUND", f"工单 {order_id} 不存在", 404)


def workorder_conflict(reason: str) -> ApiError:
    return ApiError("WO_CONFLICT", reason, 409)


def duplicate_submission(reason: str = "该操作已提交，请勿重复提交") -> ApiError:
    return ApiError("WO_DUPLICATE_SUBMISSION", reason, 409)


def upload_invalid(reason: str) -> ApiError:
    return ApiError("WO_UPLOAD_INVALID", reason, 422)


# ---- RPT（市民上报） ----
def report_not_found(report_no: str = "") -> ApiError:
    return ApiError("RPT_NOT_FOUND", f"上报 {report_no} 不存在", 404)


def report_status_locked(reason: str) -> ApiError:
    return ApiError("RPT_STATUS_LOCKED", reason, 409)


# ---- SYS ----
def not_found(what: str = "资源") -> ApiError:
    return ApiError("SYS_NOT_FOUND", f"{what}不存在", 404)

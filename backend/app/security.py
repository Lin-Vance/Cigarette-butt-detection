"""认证与授权：口令散列、JWT 签发/校验、RBAC 页面矩阵。

RBAC 矩阵与前端 frontend/src/stores/auth.ts 的 allowedPageNames 完全一致，
保证「三个角色登录后看到不同菜单与数据范围」（风险规划 §5.4）。
"""

import base64
import hashlib
import hmac
import os
from datetime import timedelta
from typing import Any

import jwt

from .config import get_settings
from .errors import account_disabled, permission_denied, token_expired, token_invalid
from .timeutil import now_cn

PBKDF2_ITERATIONS = 120_000

# ---- 角色 -> 页面权限（与前端一一对应） ----

ALL_PAGES: list[str] = [
    "overview",
    "governance",
    "device-status",
    "workboard",
    "alerts",
    "report",
    "dispatch-pool",
    "dispatch-records",
    "gis",
    "device-archive",
    "sanitation",
    "ai-model",
    "ai-config",
    "analysis",
    "users",
    "platform-config",
    "audit",
]

ROLE_PAGES: dict[str, list[str]] = {
    "admin": ALL_PAGES,
    "manager": [
        "overview",
        "governance",
        "device-status",
        "workboard",
        "alerts",
        "report",
        "dispatch-pool",
        "dispatch-records",
        "gis",
        "analysis",
    ],
    "worker": ["dispatch-pool", "dispatch-records"],
    "ai_dev": ["overview", "alerts", "ai-model", "ai-config", "analysis"],
}

ROLE_LABELS: dict[str, str] = {
    "admin": "超级管理员",
    "manager": "后勤管理员",
    "worker": "环卫工人",
    "ai_dev": "AI 开发人员",
}


def allowed_pages(role: str) -> list[str]:
    return ROLE_PAGES.get(role, [])


# ---- 口令 ----


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """返回 (password_hash, salt)。用标准库 PBKDF2-SHA256，避免 bcrypt 的原生编译依赖。"""
    salt = salt or base64.b16encode(os.urandom(16)).decode()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return base64.b16encode(dk).decode(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


# ---- JWT ----


def _token(payload: dict[str, Any], ttl_sec: int) -> str:
    settings = get_settings()
    claims = {
        **payload,
        "iat": int(now_cn().timestamp()),
        "exp": int((now_cn() + timedelta(seconds=ttl_sec)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _token(
        {"sub": str(user_id), "username": username, "role": role, "typ": "access"},
        settings.access_token_ttl_sec,
    )


def create_refresh_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _token(
        {"sub": str(user_id), "username": username, "role": role, "typ": "refresh"},
        settings.refresh_token_ttl_sec,
    )


def create_citizen_token(phone: str) -> str:
    """市民端令牌（手机号为主体）。与管理员令牌用 typ 区分，互不可用。"""
    settings = get_settings()
    return _token({"sub": phone, "phone": phone, "typ": "citizen"}, settings.access_token_ttl_sec)


def decode_token(token: str, expect_type: str = "access") -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise token_expired() from exc
    except jwt.PyJWTError as exc:
        raise token_invalid() from exc

    if payload.get("typ") != expect_type:
        raise token_invalid()
    return payload


def require_pages(user_role: str, needed: list[str]) -> None:
    """缺少任一 required 页面权限就拒绝。"""
    allowed = set(allowed_pages(user_role))
    missing = [p for p in needed if p not in allowed]
    if missing:
        raise permission_denied("/".join(missing))


def ensure_enabled(enabled: bool) -> None:
    if not enabled:
        raise account_disabled()

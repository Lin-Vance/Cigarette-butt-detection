"""认证与账号管理：口令/动态验证码登录、市民注册登录与账号管理。"""

import hmac
import secrets
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import CurrentUser, require_roles
from ..errors import invalid_credentials, not_found, token_invalid
from ..models import User
from ..config import get_settings
from ..schemas import (
    CitizenLoginRequest,
    CodeLoginRequest,
    LoginCodeRequest,
    LoginRequest,
    PasswordReset,
    RefreshRequest,
    UserCreate,
    UserUpdate,
)
from ..security import (
    ROLE_LABELS,
    ROLE_PAGES,
    allowed_pages,
    create_access_token,
    create_citizen_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from ..services import audit_dict, client_ip, paged, write_audit
from ..timeutil import iso, now_cn

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

CODE_TTL_SECONDS = 300
CODE_COOLDOWN_SECONDS = 60
_login_codes: dict[str, tuple[str, float, float]] = {}
_login_failures: dict[str, list[float]] = {}


def _code_key(target: str, role: str) -> str:
    return f"{role}:{target.strip()}"


def _consume_code(target: str, role: str, supplied: str) -> bool:
    item = _login_codes.pop(_code_key(target, role), None)
    if item is None:
        return False
    code, expires_at, _ = item
    return time.time() <= expires_at and hmac.compare_digest(code, supplied)


def _login_result(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.username, user.role),
        "refresh_token": create_refresh_token(user.id, user.username, user.role),
        "token_type": "bearer",
        "expires_in": 7200,
        "user": user_dict(user),
    }


def user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "phone": user.phone,
        "enabled": user.enabled,
        "allowed_pages": allowed_pages(user.role),
        "created_at": user.created_at,
    }


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    ip = client_ip(request)
    failure_key = f"{ip}:{payload.username.strip()}"
    now_ts = time.time()
    recent = [stamp for stamp in _login_failures.get(failure_key, []) if now_ts - stamp < 300]
    if len(recent) >= 5:
        from ..errors import ApiError

        raise ApiError("AUTH_RATE_LIMITED", "登录失败次数过多，请 5 分钟后重试", 429)
    user = (
        await session.execute(select(User).where(User.username == payload.username.strip()))
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash, user.password_salt):
        recent.append(now_ts)
        _login_failures[failure_key] = recent
        await write_audit(
            session,
            "AUTH_LOGIN",
            actor_name=payload.username,
            target=f"user:{payload.username}",
            detail="账号或密码错误",
            result="failed",
            ip=ip,
        )
        await session.commit()
        raise invalid_credentials()

    if not user.enabled:
        await write_audit(
            session,
            "AUTH_LOGIN",
            actor=user,
            target=f"user:{user.username}",
            detail="账号已禁用",
            result="denied",
            ip=ip,
        )
        await session.commit()
        raise invalid_credentials()

    _login_failures.pop(failure_key, None)

    await write_audit(
        session,
        "AUTH_LOGIN",
        actor=user,
        target=f"user:{user.username}",
        detail=f"角色 {ROLE_LABELS.get(user.role, user.role)} 登录成功",
        ip=ip,
    )
    await session.commit()

    return _login_result(user)


@router.post("/code/send")
async def send_login_code(
    payload: LoginCodeRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    target = payload.target.strip()
    phone = target
    if payload.role == "citizen":
        if not (target.isdigit() and len(target) == 11):
            raise invalid_credentials()
    else:
        user = (
            await session.execute(select(User).where(User.username == target, User.enabled.is_(True)))
        ).scalar_one_or_none()
        if user is None or (payload.role == "worker" and user.role != "worker") or (
            payload.role == "admin" and user.role == "worker"
        ):
            raise invalid_credentials()
        phone = user.phone
        if not (phone.isdigit() and len(phone) == 11):
            raise invalid_credentials()

    key = _code_key(target, payload.role)
    now = time.time()
    previous = _login_codes.get(key)
    if previous and now - previous[2] < CODE_COOLDOWN_SECONDS:
        from ..errors import ApiError

        raise ApiError("AUTH_CODE_TOO_FREQUENT", "验证码发送过于频繁，请稍后再试", 429)
    code = f"{secrets.randbelow(1_000_000):06d}"
    _login_codes[key] = (code, now + CODE_TTL_SECONDS, now)
    result = {
        "status": "sent",
        "expires_in": CODE_TTL_SECONDS,
        "masked_target": f"{phone[:3]}****{phone[-4:]}",
    }
    if get_settings().expose_demo_codes:
        result["demo_code"] = code
    return result


@router.post("/code/login")
async def login_by_code(
    payload: CodeLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not _consume_code(payload.username, payload.role, payload.code):
        raise invalid_credentials()
    user = (
        await session.execute(select(User).where(User.username == payload.username, User.enabled.is_(True)))
    ).scalar_one_or_none()
    if user is None or (payload.role == "worker" and user.role != "worker") or (
        payload.role == "admin" and user.role == "worker"
    ):
        raise invalid_credentials()
    return _login_result(user)


@router.post("/refresh")
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> dict:
    claims = decode_token(payload.refresh_token, "refresh")
    user = await session.get(User, int(claims.get("sub", 0)))
    if user is None or not user.enabled:
        raise token_invalid()
    return {
        "access_token": create_access_token(user.id, user.username, user.role),
        "refresh_token": create_refresh_token(user.id, user.username, user.role),
        "token_type": "bearer",
        "expires_in": 7200,
        "user": user_dict(user),
    }


@router.get("/me")
async def me(request: Request, user: CurrentUser) -> dict:
    return {"user": user_dict(user), "ip": client_ip(request)}


@router.post("/logout")
async def logout(request: Request, user: CurrentUser, session: AsyncSession = Depends(get_session)) -> dict:
    await write_audit(
        session,
        "AUTH_LOGOUT",
        actor=user,
        target=f"user:{user.username}",
        detail="退出登录",
        ip=client_ip(request),
    )
    await session.commit()
    return {"status": "ok"}


# ---------------- 市民端登录 ----------------


@router.post("/citizen/login")
async def citizen_login(
    payload: CitizenLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not (payload.phone.isdigit() and len(payload.phone) == 11):
        raise invalid_credentials()
    user = (
        await session.execute(
            select(User).where(User.username == payload.phone, User.role == "citizen")
        )
    ).scalar_one_or_none()
    if payload.method == "password":
        if payload.mode == "register":
            if len(payload.password) < 6 or not _consume_code(payload.phone, "citizen", payload.code):
                raise invalid_credentials()
            password_hash, salt = hash_password(payload.password)
            if user is None:
                user = User(
                    username=payload.phone,
                    password_hash=password_hash,
                    password_salt=salt,
                    real_name=f"市民 {payload.phone[-4:]}",
                    role="citizen",
                    phone=payload.phone,
                    enabled=True,
                    created_at=iso(now_cn()),
                )
                session.add(user)
            else:
                user.password_hash, user.password_salt, user.enabled = password_hash, salt, True
            await session.commit()
        elif user is None or not verify_password(payload.password, user.password_hash, user.password_salt):
            raise invalid_credentials()
    else:
        if not _consume_code(payload.phone, "citizen", payload.code):
            raise invalid_credentials()
        if user is None:
            password_hash, salt = hash_password(secrets.token_urlsafe(18))
            user = User(
                username=payload.phone,
                password_hash=password_hash,
                password_salt=salt,
                real_name=f"市民 {payload.phone[-4:]}",
                role="citizen",
                phone=payload.phone,
                enabled=True,
                created_at=iso(now_cn()),
            )
            session.add(user)
            await session.commit()
    return {
        "access_token": create_citizen_token(payload.phone),
        "token_type": "bearer",
        "expires_in": 7200,
        "profile": {
            "phone": payload.phone,
            "displayName": f"市民 {payload.phone[-4:]}",
            "district": "浉河区",
            "contribution": 36,
        },
    }


# ---------------- 账号与角色（页面 16） ----------------


@users_router.get("")
async def list_users(
    page: int = 1,
    size: int = 20,
    role: str | None = None,
    keyword: str = "",
    user: User = Depends(require_roles("admin", "manager")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    page = max(1, page)
    size = min(100, max(1, size))

    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((User.username.like(like)) | (User.real_name.like(like)))
    rows = list((await session.execute(stmt.order_by(User.id))).scalars())
    total = len(rows)
    return paged([user_dict(u) for u in rows[(page - 1) * size : page * size]], total, page, size)


@users_router.post("", status_code=201)
async def create_user(
    payload: UserCreate,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    exists = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if exists is not None:
        from ..errors import ApiError

        raise ApiError("SYS_DUPLICATE", f"账号 {payload.username} 已存在", 409)

    password_hash, salt = hash_password(payload.password)
    user = User(
        username=payload.username,
        password_hash=password_hash,
        password_salt=salt,
        real_name=payload.real_name or payload.username,
        role=payload.role,
        phone=payload.phone,
        enabled=True,
        created_at=iso(now_cn()),
    )
    session.add(user)
    await session.flush()
    await write_audit(
        session,
        "USER_CREATE",
        actor=admin,
        target=f"user:{user.username}",
        detail=f"新建账号，角色 {ROLE_LABELS.get(user.role, user.role)}",
        ip=client_ip(request),
    )
    await session.commit()
    return user_dict(user)


@users_router.patch("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    target = await session.get(User, user_id)
    if target is None:
        raise not_found("账号")

    before = {"role": target.role, "enabled": target.enabled}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(target, field, value)

    await write_audit(
        session,
        "USER_UPDATE",
        actor=admin,
        target=f"user:{target.username}",
        detail=f"修改账号：{before} → 角色 {target.role} / 启用 {target.enabled}",
        ip=client_ip(request),
    )
    await session.commit()
    return user_dict(target)


@users_router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    payload: PasswordReset,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    target = await session.get(User, user_id)
    if target is None:
        raise not_found("账号")
    target.password_hash, target.password_salt = hash_password(payload.new_password)
    await write_audit(
        session,
        "USER_RESET_PASSWORD",
        actor=admin,
        target=f"user:{target.username}",
        detail="重置账号密码（不记录明文）",
        ip=client_ip(request),
    )
    await session.commit()
    return {"status": "ok", "id": target.id}


@users_router.get("/roles")
async def list_roles(user: User = Depends(require_roles("admin", "manager"))) -> dict:
    """角色与权限矩阵（页面 16 的「角色配置」面板）。"""
    descs = {
        "admin": "全平台配置与账号管理权限",
        "manager": "治理作业与调度权限，不含账号与平台配置",
        "worker": "仅移动工作台：接单与闭环提交",
        "ai_dev": "模型、数据集与识别阈值相关权限",
    }
    return {
        "items": [
            {
                "id": i + 1,
                "name": ROLE_LABELS[role],
                "key": role,
                "desc": descs[role],
                "perms": pages,
                "perm_count": len(pages),
            }
            for i, (role, pages) in enumerate(ROLE_PAGES.items())
        ]
    }


@users_router.get("/audit-summary")
async def audit_summary(
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    enabled = (
        await session.execute(select(func.count()).select_from(User).where(User.enabled.is_(True)))
    ).scalar_one()
    return {"total": total, "enabled": enabled, "disabled": total - enabled}

"""FastAPI 依赖：当前用户、角色校验、可选市民身份。"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .errors import permission_denied, token_invalid
from .models import User
from .security import allowed_pages, decode_token, ensure_enabled, verify_password

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if creds is None or not creds.credentials:
        raise token_invalid()
    payload = decode_token(creds.credentials, "access")
    try:
        user_id = int(payload.get("sub", "0"))
    except (TypeError, ValueError) as exc:
        raise token_invalid() from exc

    user = await session.get(User, user_id)
    if user is None:
        raise token_invalid()
    ensure_enabled(user.enabled)
    request.state.actor = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """角色白名单依赖工厂。"""

    async def _dep(user: CurrentUser) -> User:
        if roles and user.role not in roles:
            raise permission_denied("/".join(roles))
        return user

    return _dep


def require_pages(*pages: str):
    """页面权限依赖工厂：命中**任意一个**所列页面权限即放行（any-of）。

    ⚠️ 2026-09-28 修正（缺陷复核新发现 D-18）。

    原实现是 all-of（「缺少任一所列页面权限就拒绝」），但调用方几乎都是
    `require_pages("a", "b", "c")` 这种「该接口的数据被这几个页面共用」的写法，
    语义应当是本依赖函数的 any-of。all-of 相当于把接口锁给**唯一同时拥有全部页面**
    的角色（实际上只有 admin）。

    典型受害者：`/workorders` 要求 `dispatch-pool + dispatch-records + workboard`，
    而环卫角色（worker）的页面权限只有前两个 → 环卫端在 API 模式下
    `GET /workorders` 恒为 403、工单池恒为空，「接单 → 到场 → 提交验收」整条闭环
    在答辩现场直接演示不出来（qa-ends 的「环卫端：登录后出现工单」「环卫端：可接单」
    两条用例即为该问题的外部症状）。

    对单页调用（绝大多数）语义完全不变；只有原本被 all-of 误伤的多页调用会恢复可达。
    """

    async def _dep(user: CurrentUser) -> User:
        allowed = set(allowed_pages(user.role))
        if pages and allowed.isdisjoint(pages):
            raise permission_denied("/".join(pages))
        return user

    return _dep


async def check_password(user: User, password: str) -> bool:
    return verify_password(password, user.password_hash, user.password_salt)


async def get_current_citizen(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """市民身份：返回手机号。与管理员令牌互不通用（typ 校验）。"""
    if creds is None or not creds.credentials:
        raise token_invalid()
    payload = decode_token(creds.credentials, "citizen")
    phone = str(payload.get("sub") or "")
    if len(phone) != 11:
        raise token_invalid()
    request.state.citizen_phone = phone
    return phone


CurrentCitizen = Annotated[str, Depends(get_current_citizen)]

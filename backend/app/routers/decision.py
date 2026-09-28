"""决策接口：调度建议查询与反馈。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import CurrentUser, require_pages
from ..errors import not_found
from ..models import Suggestion
from ..rules import compute_heatmap, recompute_suggestions
from ..schemas import SuggestionFeedback
from ..services import client_ip, suggestion_dict, write_audit
from ..timeutil import iso, now_cn

router = APIRouter(tags=["decision"])


@router.get("/suggestions")
async def list_suggestions(
    status: str | None = None,
    _: object = Depends(require_pages("overview", "governance", "analysis")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(Suggestion)
    if status:
        stmt = stmt.where(Suggestion.status == status)
    rows = list((await session.execute(stmt.order_by(Suggestion.id))).scalars())
    return {"items": [suggestion_dict(s) for s in rows]}


@router.post("/suggestions/recompute")
async def recompute(
    request: Request,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = await recompute_suggestions(session)
    await write_audit(
        session,
        "SUGGESTION_RECOMPUTE",
        actor=user,
        target="suggestions",
        detail=f"重算调度建议，当前 {len(rows)} 条",
        ip=client_ip(request),
    )
    await session.commit()
    return {"items": [suggestion_dict(s) for s in rows]}


@router.post("/suggestions/{suggestion_id}/feedback")
async def feedback(
    suggestion_id: int,
    payload: SuggestionFeedback,
    request: Request,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    row = await session.get(Suggestion, suggestion_id)
    if row is None:
        raise not_found("建议")

    row.status = payload.action
    row.feedback_note = payload.note or ("已采纳" if payload.action == "accepted" else "已驳回")
    row.resolved_at = iso(now_cn())

    await write_audit(
        session,
        "SUGGESTION_FEEDBACK",
        actor=user,
        target=f"suggestion:{suggestion_id}",
        detail=f"{row.status} · {row.feedback_note}",
        ip=client_ip(request),
    )
    await session.commit()
    return suggestion_dict(row)


@router.get("/heatmap")
async def heatmap(
    days: int = 7,
    _: object = Depends(require_pages("governance", "gis", "overview")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await compute_heatmap(session, days)

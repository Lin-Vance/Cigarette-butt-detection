"""统计接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_pages
from ..stats import (
    area_metrics,
    daily_trend,
    health_snapshot,
    hourly_distribution,
    overview_metrics,
    type_distribution,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def overview(
    _: object = Depends(require_pages("overview")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {
        "metrics": await overview_metrics(session),
        "health": await health_snapshot(session),
        "demo": True,
    }


@router.get("/trend")
async def trend(
    days: int = 7,
    _: object = Depends(require_pages("overview", "analysis", "governance")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await daily_trend(session, days), "days": days}


@router.get("/hourly")
async def hourly(
    days: int = 7,
    _: object = Depends(require_pages("governance", "analysis")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await hourly_distribution(session, days), "days": days}


@router.get("/areas")
async def areas(
    days: int = 30,
    _: object = Depends(require_pages("governance", "workboard", "analysis")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await area_metrics(session, days), "days": days}


@router.get("/types")
async def types(
    days: int = 30,
    _: object = Depends(require_pages("governance", "analysis")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await type_distribution(session, days), "days": days}


@router.get("/health")
async def health(
    _: object = Depends(require_pages("overview")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await health_snapshot(session)

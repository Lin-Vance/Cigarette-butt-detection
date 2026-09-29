"""跨端活动摘要。

供前端 `AppTopbar.vue` 的顶栏使用：
  · 「三端同步 N」计数
  · 「三端协同动态」最近若干条

**为什么会有这个文件**（2026-09-28 缺陷复核新增）：
该接口为总览页提供统一的活动摘要。
前端代理收敛到 8000 之后，管理端 20 个页面全部出现
`404 /api/v1/admin/activity/summary` —— 页面本身不白屏（调用处有 try/catch），
但资源巡检会把每条 404 记为失败，属于真实缺口，故在此按 Java 侧同一响应结构补齐。

响应结构（与 Java 版保持一致，前端按字段名取值）：
    {
      "total": 128,
      "sources": {"admin": 90, "worker": 30, "citizen": 8},
      "latest": [
        {"source": "worker", "actor": "张建国", "detail": "环卫人员已接单", "created_at": "2026-09-28T19:20:11+08:00"}
      ]
    }

数据源复用**只增不改不删**的 `audit_logs`，因此本模块只提供只读查询。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_roles
from ..models import AuditLog, User

router = APIRouter(prefix="/admin/activity", tags=["activity"])

CITIZEN_ACTIONS = ("REPORT_",)


def _source(role: str, action: str) -> str:
    """把审计条目归到「市 / 环 / 管」三端之一。前端按 citizen|worker|其它 渲染角标。"""
    if role == "citizen" or action.startswith(CITIZEN_ACTIONS):
        return "citizen"
    if role == "worker" or action.startswith("WORKORDER_"):
        return "worker"
    return "admin"


@router.get("/summary")
async def activity_summary(
    limit: int = Query(5, ge=1, le=50),
    _: User = Depends(require_roles("admin", "manager", "worker", "ai_dev")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """最近活动摘要。四个角色都放行：这是共享顶栏的只读聚合，不含敏感字段。"""
    rows = list((await session.execute(select(AuditLog).order_by(AuditLog.id.desc()))).scalars())

    sources: dict[str, int] = {}
    for row in rows:
        key = _source(row.role, row.action)
        sources[key] = sources.get(key, 0) + 1

    latest = [
        {
            "source": _source(row.role, row.action),
            "actor": row.actor,
            "detail": row.detail,
            "created_at": row.ts,
        }
        for row in rows[:limit]
    ]
    return {"total": len(rows), "sources": sources, "latest": latest}

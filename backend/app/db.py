"""数据库连接与会话。"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每请求一个会话。"""
    async with get_session_factory()() as session:
        yield session


async def init_db() -> None:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)

    if settings.database_url.startswith("sqlite"):
        (settings.storage_dir.parent / "data").mkdir(parents=True, exist_ok=True)

    # 模型需先被导入才会注册到 Base.metadata
    from . import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)


# SQLite 下 `create_all` 只建新表，**不会给已存在的表补列**。
# 演示项目不引入 Alembic，这里做一次幂等补列：新增字段在旧库上也能直接生效，
# 不必删库重建（删库会连带丢掉已经演示出来的工单与上报数据）。
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "citizen_reports": [
        ("ai_report", "TEXT DEFAULT ''"),
        ("ai_feedback", "TEXT DEFAULT ''"),
        ("ai_feedback_at", "VARCHAR(40) DEFAULT ''"),
    ],
}


async def _ensure_columns(conn) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        try:
            rows = (await conn.exec_driver_sql(f"PRAGMA table_info({table})")).fetchall()
        except Exception:
            continue  # 非 SQLite 或表不存在：交给 create_all / 正式迁移处理
        have = {row[1] for row in rows}
        for name, ddl in columns:
            if name in have:
                continue
            await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


async def drop_all() -> None:
    from . import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

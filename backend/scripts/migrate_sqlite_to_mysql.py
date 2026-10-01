"""把历史 SQLite 数据一次性迁移到 DATABASE_URL 指向的 MySQL。"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import BACKEND_DIR, get_settings
from app.db import Base
from app import models  # noqa: F401  注册全部模型


async def migrate(source_path: Path, replace: bool) -> dict[str, int]:
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite 文件不存在：{source_path}")

    target_url = get_settings().database_url
    if not target_url.startswith("mysql+aiomysql://"):
        raise RuntimeError("DATABASE_URL 必须指向 mysql+aiomysql://")

    source = create_async_engine(f"sqlite+aiosqlite:///{source_path.as_posix()}")
    target = create_async_engine(target_url, pool_pre_ping=True)
    counts: dict[str, int] = {}
    try:
        async with target.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if replace:
                await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(delete(table))
                await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

        for table in Base.metadata.sorted_tables:
            async with source.connect() as source_conn:
                rows = (await source_conn.execute(select(table))).mappings().all()
            if rows:
                async with target.begin() as target_conn:
                    for offset in range(0, len(rows), 500):
                        await target_conn.execute(insert(table), [dict(row) for row in rows[offset:offset + 500]])
            async with target.connect() as target_conn:
                counts[table.name] = int(
                    (await target_conn.execute(select(func.count()).select_from(table))).scalar_one()
                )
        return counts
    finally:
        await source.dispose()
        await target.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_DIR / "backups" / "legacy-sqlite-before-mysql.db",
        help="历史 SQLite 文件路径",
    )
    parser.add_argument("--replace", action="store_true", help="清空 MySQL 现有业务表后再迁移")
    args = parser.parse_args()
    result = asyncio.run(migrate(args.source.resolve(), args.replace))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

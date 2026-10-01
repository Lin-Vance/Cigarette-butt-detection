"""Redis 连接与带命名空间的键生成。"""

from redis.asyncio import Redis

from .config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=5,
            health_check_interval=30,
        )
    return _client


def redis_key(*parts: str) -> str:
    prefix = get_settings().redis_key_prefix.strip(":")
    safe = [str(part).strip().replace(" ", "_") for part in parts]
    return ":".join([prefix, *safe])


async def init_redis() -> None:
    if not await get_redis().ping():
        raise RuntimeError("Redis PING 未返回成功")


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

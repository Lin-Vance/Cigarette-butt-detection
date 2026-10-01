"""Redis Pub/Sub 驱动的 WebSocket 广播。"""

import asyncio
import json
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from .redis_client import get_redis, redis_key

CHANNEL_ALERTS = "alerts"
CHANNEL_WORKORDERS = "workorders"
CHANNELS = (CHANNEL_ALERTS, CHANNEL_WORKORDERS)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {channel: set() for channel in CHANNELS}
        self._lock = asyncio.Lock()
        self._listener: asyncio.Task | None = None
        self._pubsub = None

    def _redis_channel(self, channel: str) -> str:
        return redis_key("ws", channel)

    async def start(self) -> None:
        if self._listener is not None:
            return
        self._pubsub = get_redis().pubsub()
        await self._pubsub.subscribe(*(self._redis_channel(channel) for channel in CHANNELS))
        self._listener = asyncio.create_task(self._listen(), name="redis-websocket-listener")

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener
            self._listener = None
        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None

    async def _listen(self) -> None:
        assert self._pubsub is not None
        while True:
            message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                redis_channel = str(message.get("channel", ""))
                channel = redis_channel.rsplit(":", 1)[-1]
                await self._send_local(channel, str(message.get("data", "{}")))
            await asyncio.sleep(0.01)

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(channel, set()).add(ws)

    async def disconnect(self, channel: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.get(channel, set()).discard(ws)

    async def _send_local(self, channel: str, text: str) -> int:
        async with self._lock:
            targets = list(self._rooms.get(channel, set()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms.get(channel, set()).discard(ws)
        return len(targets) - len(dead)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> int:
        """发布到 Redis，使所有后端实例上的 WebSocket 客户端都能收到消息。"""
        return int(
            await get_redis().publish(
                self._redis_channel(channel),
                json.dumps(payload, ensure_ascii=False),
            )
        )

    def counts(self) -> dict[str, int]:
        return {channel: len(connections) for channel, connections in self._rooms.items()}


manager = ConnectionManager()

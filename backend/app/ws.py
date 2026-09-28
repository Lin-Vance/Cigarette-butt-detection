"""WebSocket 广播（修订基线：2 个频道 /ws/alerts、/ws/workorders）。

无 Redis / 无消息队列，进程内 dict + asyncio。单进程 uvicorn 下足够。
"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket

CHANNEL_ALERTS = "alerts"
CHANNEL_WORKORDERS = "workorders"
CHANNELS = (CHANNEL_ALERTS, CHANNEL_WORKORDERS)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {c: set() for c in CHANNELS}
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(channel, set()).add(ws)

    async def disconnect(self, channel: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.get(channel, set()).discard(ws)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> int:
        """向频道内所有连接推送。断开的连接会被顺手清掉。"""
        async with self._lock:
            targets = list(self._rooms.get(channel, set()))
        if not targets:
            return 0

        text = json.dumps(payload, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001 - 连接已断开
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms.get(channel, set()).discard(ws)
        return len(targets) - len(dead)

    def counts(self) -> dict[str, int]:
        return {c: len(v) for c, v in self._rooms.items()}


manager = ConnectionManager()

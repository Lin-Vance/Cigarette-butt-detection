"""WebSocket 路由（修订基线：2 个频道）。"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..deps import require_roles
from ..security import decode_token
from ..ws import CHANNEL_ALERTS, CHANNEL_WORKORDERS, manager

router = APIRouter(tags=["ws"])


async def _serve(channel: str, ws: WebSocket) -> None:
    token = ws.query_params.get("token", "")
    try:
        decode_token(token, "access")
    except Exception:  # 无效或过期令牌一律拒绝，不向匿名访问者泄露实时事件
        await ws.close(code=1008, reason="authentication required")
        return
    await manager.connect(channel, ws)
    try:
        await ws.send_json({"type": "connected", "channel": channel})
        while True:
            # 客户端心跳；忽略内容
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        await manager.disconnect(channel, ws)


@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket) -> None:
    await _serve(CHANNEL_ALERTS, ws)


@router.websocket("/ws/workorders")
async def ws_workorders(ws: WebSocket) -> None:
    await _serve(CHANNEL_WORKORDERS, ws)


@router.get("/ws/stats")
async def ws_stats(_: object = Depends(require_roles("admin"))) -> dict:
    return {"connections": manager.counts()}

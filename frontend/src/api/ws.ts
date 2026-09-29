/**
 * WebSocket 订阅（后端两个频道：/ws/alerts、/ws/workorders）。
 *
 * 自动重连 + 心跳；页面卸载时务必调用返回的 close()。
 */
export type Channel = 'alerts' | 'workorders'

export interface ChannelMessage {
  type: string
  [key: string]: unknown
}

export interface ChannelHandle {
  close: () => void
  readonly readyState: number
}

export function openChannel(
  channel: Channel,
  accessToken: string,
  onMessage: (msg: ChannelMessage) => void,
  onStatus?: (connected: boolean) => void,
): ChannelHandle {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${proto}://${location.host}/ws/${channel}?token=${encodeURIComponent(accessToken)}`

  let ws: WebSocket | null = null
  let heartbeat: number | undefined
  let retry: number | undefined
  let closed = false

  const connect = () => {
    if (closed) return
    ws = new WebSocket(url)

    ws.onopen = () => {
      onStatus?.(true)
      heartbeat = window.setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 25000)
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data)) as ChannelMessage
        if (msg.type !== 'connected') onMessage(msg)
      } catch {
        /* 忽略非 JSON 帧 */
      }
    }

    ws.onclose = () => {
      if (heartbeat) window.clearInterval(heartbeat)
      onStatus?.(false)
      if (!closed) retry = window.setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      /* onclose 会兜住重连 */
    }
  }

  connect()

  return {
    get readyState() {
      return ws?.readyState ?? WebSocket.CLOSED
    },
    close() {
      closed = true
      if (heartbeat) window.clearInterval(heartbeat)
      if (retry) window.clearTimeout(retry)
      ws?.close()
    },
  }
}

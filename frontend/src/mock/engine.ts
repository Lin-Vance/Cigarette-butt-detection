/**
 * 模拟数据引擎 · 生成器
 *
 * 纯函数，不持有状态；状态由 stores/demo.ts 持有。
 * AI 算法管道尚未实现（用户 2026-09-23 确认），因此本文件承担
 * 「合规事件生成器」职责 —— 生成的事件必须能通过修订后的证据链校验
 * （三帧齐全且 path 非空、时间戳递增、轨迹点 >= 5）。
 */
import type {
  Camera,
  EvidenceFrame,
  Suggestion,
  TrendPoint,
  ViolationEvent,
  WorkOrder
} from './types'
import { getScale, type ScaleMode } from './config'

/** 可复现的伪随机数（mulberry32），保证刷新后演示数据稳定 */
function makeRng(seed: number) {
  let a = seed >>> 0
  return function rng() {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const EVIDENCE_POOL = {
  holding: [
    '/media/cameras/pedestrian-smoking.png',
    '/media/cameras/sidewalk-pedestrian.png'
  ],
  throwing: [
    '/media/evidence/event-detection.png',
    '/media/cameras/roadside-pedestrian.png'
  ],
  landed: [
    '/media/evidence/incident-cigarette.png',
    '/media/cameras/urban-vehicle.png'
  ]
}

const CLIP_POOL = [
  '/media/cameras/pedestrian-crosswalk.png',
  '/media/cameras/roadside-vehicle.png'
]

const STAFF_POOL = ['张建国', '李红梅', '王立新', '赵晓峰', '陈志远', '刘敏', '孙德海']

/** 摄像头点位（信阳学院校园，WGS84） */
export function buildCameras(mode: ScaleMode): Camera[] {
  const rng = makeRng(20260923)
  const base = { lat: 32.148, lon: 114.07 }
  const defs = [
    { id: 'cam_001', name: '图书馆北门枪机', loc: '图书馆北门' },
    { id: 'cam_002', name: '教学楼 A 座出口球机', loc: '教学楼 A 座出口' },
    { id: 'cam_003', name: '学生食堂东侧枪机', loc: '学生食堂东侧' },
    { id: 'cam_004', name: '体育馆西广场球机', loc: '体育馆西广场' }
  ]
  return defs.map((d, i) => {
    const degraded = i === 3
    return {
      camera_id: d.id,
      name: d.name,
      location_name: d.loc,
      latitude: +(base.lat + (rng() - 0.5) * 0.004).toFixed(6),
      longitude: +(base.lon + (rng() - 0.5) * 0.005).toFixed(6),
      status: degraded ? 'degraded' : 'online',
      fps: degraded ? 15 : 25,
      preprocess_enabled: degraded,
      preprocess_algorithm: degraded ? 'retinex' : 'histogram_eq',
      online_rate: mode === 'pilot' ? 100 : +(97.5 + rng() * 2).toFixed(1)
    }
  })
}

function pad(n: number) {
  return n < 10 ? `0${n}` : `${n}`
}

function toIso(d: Date) {
  const tz = '+08:00'
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
    `.${String(d.getMilliseconds()).padStart(3, '0')}${tz}`
  )
}

let seq = 0
/** 生成一个 UUID v4 形态的 event_id（PRD §7.3） */
function uuid() {
  const hex = '0123456789abcdef'
  let out = ''
  for (let i = 0; i < 36; i++) {
    if (i === 8 || i === 13 || i === 18 || i === 23) out += '-'
    else if (i === 14) out += '4'
    else if (i === 19) out += hex[(Math.floor(Math.random() * 4) + 8) & 0xf]
    else out += hex[Math.floor(Math.random() * 16)]
  }
  return out
}

function pick<T>(arr: T[], rng: () => number): T {
  return arr[Math.floor(rng() * arr.length) % arr.length]
}

/**
 * 生成一条「合规」违规事件：三段式时间戳递增、三帧证据 path 非空、轨迹点 >= 5。
 * 这正是 AI 管道未实现时所需的替代实现，也用于「一键演示一次违规」。
 */
export function buildEvent(
  cameras: Camera[],
  opts: { at?: Date; cameraIndex?: number; idOffset?: number } = {}
): ViolationEvent {
  const rng = makeRng(Math.floor(Math.random() * 1e9))
  const cam = cameras[(opts.cameraIndex ?? Math.floor(rng() * cameras.length)) % cameras.length]
  const end = opts.at ?? new Date()
  const start = new Date(end.getTime() - 6400)

  const holdingAt = new Date(start.getTime())
  const throwingAt = new Date(start.getTime() + 5200)
  const landedAt = new Date(start.getTime() + 6300)

  const evidence: EvidenceFrame[] = [
    { frame_ts: toIso(holdingAt), type: 'holding', path: pick(EVIDENCE_POOL.holding, rng) },
    { frame_ts: toIso(throwingAt), type: 'throwing', path: pick(EVIDENCE_POOL.throwing, rng) },
    { frame_ts: toIso(landedAt), type: 'landed', path: pick(EVIDENCE_POOL.landed, rng) }
  ]

  // 轨迹点：>= 5 个，时间戳递增（对应 PRD §5.2.1 轨迹完整性校验）
  const trajectory = Array.from({ length: 12 }, (_, i) => {
    const t = new Date(start.getTime() + i * 520)
    const p = i / 11
    return {
      x: Math.round(940 + p * 190 + (rng() - 0.5) * 12),
      y: Math.round(300 + p * p * 420 + (rng() - 0.5) * 8),
      ts: toIso(t)
    }
  })

  seq += 1

  return {
    id: (opts.idOffset ?? 0) + seq,
    event_id: uuid(),
    camera_id: cam.camera_id,
    camera_name: cam.name,
    track_id: 1000 + Math.floor(rng() * 8000),
    stage: 'THROW_CONFIRMED',
    confidence: +(0.78 + rng() * 0.2).toFixed(3),
    bbox: [930, 690, 26, 19],
    trajectory,
    event_timestamp: toIso(end),
    status: 'confirmed',
    evidence_frames: evidence,
    video_clip_path: pick(CLIP_POOL, rng),
    has_workorder: true
  }
}

export function buildEvents(cameras: Camera[], count: number): ViolationEvent[] {
  const rng = makeRng(777001)
  const now = Date.now()
  const list: ViolationEvent[] = []
  for (let i = 0; i < count; i++) {
    // 越靠前越新
    const at = new Date(now - i * (18 * 60 * 1000 + rng() * 900 * 1000))
    list.push(buildEvent(cameras, { at, idOffset: 100000 }))
  }
  return list.sort(
    (a, b) => new Date(b.event_timestamp).getTime() - new Date(a.event_timestamp).getTime()
  )
}

export function buildWorkOrders(
  events: ViolationEvent[],
  cameras: Camera[],
  mode: ScaleMode
): WorkOrder[] {
  const rng = makeRng(424242)
  const camMap = new Map(cameras.map((c) => [c.camera_id, c]))
  return events.slice(0, getScale(mode).eventCount).map((ev, i) => {
    const cam = camMap.get(ev.camera_id)!
    const created = new Date(ev.event_timestamp)
    const roll = rng()
    // 状态分布要保证「环卫工人端」有活可干：待接单 / 处理中 / 待验收 三个活跃态都必须有量，
    // 否则任务池和经验收流程演示不起来。
    let status: WorkOrder['status'] = 'pending'
    if (i < 3) {
      status = i === 0 ? 'pending' : i === 1 ? 'processing' : 'verifying'
    } else if (roll < 0.14) status = 'pending'
    else if (roll < 0.3) status = 'accepted'
    else if (roll < 0.4) status = 'verifying'
    else if (roll < 0.5) status = 'timeout'
    else if (roll < 0.94) status = 'completed'
    else status = 'closed'

    const acceptedOffset = status === 'pending' ? null : Math.floor(60 + rng() * 900)
    const accepted = acceptedOffset ? new Date(created.getTime() + acceptedOffset * 1000) : null
    const completed =
      status === 'completed' || status === 'closed'
        ? new Date(created.getTime() + (acceptedOffset! + 300 + rng() * 1200) * 1000)
        : null

    return {
      id: 200001 + i,
      order_no: `GD${new Date(created).getFullYear()}${pad(new Date(created).getMonth() + 1)}${pad(
        new Date(created).getDate()
      )}${String(i + 1).padStart(4, '0')}`,
      event_id: ev.event_id,
      camera_id: ev.camera_id,
      location_name: cam.location_name,
      latitude: cam.latitude,
      longitude: cam.longitude,
      status,
      assigned_to: pick(STAFF_POOL, rng),
      created_at: ev.event_timestamp,
      accepted_at: accepted ? toIso(accepted) : null,
      completed_at: completed ? toIso(completed) : null,
      response_time_sec: acceptedOffset,
      escalated: status === 'timeout'
    }
  })
}

export function buildTrend(mode: ScaleMode): TrendPoint[] {
  const { trendDetected, trendHandled } = getScale(mode)
  const out: TrendPoint[] = []
  const now = new Date()
  const n = trendDetected.length
  for (let i = 0; i < n; i++) {
    const d = new Date(now.getTime() - (n - 1 - i) * 86400000)
    out.push({
      date: `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
      detected: trendDetected[i],
      handled: trendHandled[i]
    })
  }
  return out
}

export function buildSuggestions(cameras: Camera[], mode: ScaleMode): Suggestion[] {
  const recent = getScale(mode).recentCount
  const baseline = getScale(mode).baselineDaily
  const over = Math.round(((recent / 7 - baseline) / (baseline || 1)) * 100)
  return [
    {
      id: 300001,
      type: 'add_facility',
      area_name: '教学楼 A 座出口',
      time_range: '',
      content: `建议在 教学楼 A 座出口 附近增设烟蒂收集器。该区域近 7 天日均违规 ${(
        recent / 7
      ).toFixed(1)} 次，高于近 30 天日均基线 ${baseline.toFixed(1)} 次（超出 ${over}%）。`,
      frequency_data: {
        area: '教学楼 A 座出口',
        recent_daily: +(recent / 7).toFixed(2),
        baseline_daily: baseline
      },
      status: 'pending',
      created_at: toIso(new Date(Date.now() - 3600 * 1000))
    },
    {
      id: 300002,
      type: 'adjust_schedule',
      area_name: '',
      time_range: '12:00-13:00',
      content:
        '建议在 12:00-13:00 增派巡查人员。该时段近 7 天日均违规 3.4 次，占全天违规的 28%，为全天峰值时段。',
      frequency_data: { hour: 12, recent_daily: 3.4, share_pct: 28 },
      status: 'pending',
      created_at: toIso(new Date(Date.now() - 5400 * 1000))
    },
    {
      id: 300003,
      type: 'treatment_effective',
      area_name: '学生食堂东侧',
      time_range: '',
      content:
        '学生食堂东侧 治理措施生效：违规频次近 7 天较前 7 天下降 34%，建议保持当前保洁与巡查方案。',
      frequency_data: { area: '学生食堂东侧', drop_pct: 34 },
      status: 'accepted',
      created_at: toIso(new Date(Date.now() - 26 * 3600 * 1000)),
      feedback_note: '已确认，继续保持'
    },
    {
      id: 300004,
      type: 'warning',
      area_name: '体育馆西广场',
      time_range: '',
      content:
        '体育馆西广场 违规频次连续上升 3 天（累计 +41%），且该点位摄像头当前处于降频状态，建议核查设备或加强巡查。',
      frequency_data: { area: '体育馆西广场', rise_pct: 41 },
      status: 'pending',
      created_at: toIso(new Date(Date.now() - 7200 * 1000))
    }
  ]
}

export function makeEventId() {
  return uuid()
}

export { toIso, pad }

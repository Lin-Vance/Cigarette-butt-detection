/**
 * 后台页面数据层
 *
 * 全部为模拟数据，由 stores/demo 的基础数据集（cameras / events / workOrders）派生。
 * 页面组件只消费这里的数据，不自己造数 —— 将来接后端时替换点集中在本文件。
 */

import type { Camera, ViolationEvent, WorkOrder, WorkOrderStatus } from './types'

export const AREAS = ['浉河区', '平桥区', '羊山新区', '高新区', '罗山县', '光山县']

/** 确定性伪随机：保证每次渲染结果一致，截图与答辩演示时数据不会跳动 */
export function rand(seed: number) {
  let s = seed % 2147483647
  if (s <= 0) s += 2147483646
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

const p2 = (n: number) => String(n).padStart(2, '0')

export function fmtDateTime(d: Date | string): string {
  const t = typeof d === 'string' ? new Date(d) : d
  return `${t.getFullYear()}-${p2(t.getMonth() + 1)}-${p2(t.getDate())} ${p2(t.getHours())}:${p2(
    t.getMinutes()
  )}:${p2(t.getSeconds())}`
}

export function fmtDate(d: Date | string): string {
  const t = typeof d === 'string' ? new Date(d) : d
  return `${t.getFullYear()}-${p2(t.getMonth() + 1)}-${p2(t.getDate())}`
}

export function fmtTime(d: Date | string): string {
  const t = typeof d === 'string' ? new Date(d) : d
  return `${p2(t.getHours())}:${p2(t.getMinutes())}:${p2(t.getSeconds())}`
}

/** 事件编号：EVT + 日期 + 序号 */
export function eventNo(ev: { id: number; event_timestamp: string }): string {
  const d = new Date(ev.event_timestamp)
  return `EVT${d.getFullYear()}${p2(d.getMonth() + 1)}${p2(d.getDate())}${String(ev.id % 1000).padStart(3, '0')}`
}

/** 置信度 → 风险等级 */
export function levelOf(confidence: number): { key: 'high' | 'mid' | 'low'; text: string; tone: string } {
  if (confidence >= 0.9) return { key: 'high', text: '高风险', tone: 'danger' }
  if (confidence >= 0.82) return { key: 'mid', text: '中风险', tone: 'warning' }
  return { key: 'low', text: '低风险', tone: 'muted' }
}

export const WORKORDER_STATUS: Record<WorkOrderStatus, { text: string; tone: string }> = {
  pending: { text: '待派发', tone: 'info' },
  accepted: { text: '已接单', tone: 'info' },
  processing: { text: '执行中', tone: 'success' },
  verifying: { text: '待验收', tone: 'warning' },
  completed: { text: '已完成', tone: 'success' },
  closed: { text: '已闭环', tone: 'success' },
  timeout: { text: '已超时', tone: 'warning' }
}

/* ============================================================
   地图投影工具
   ============================================================ */

/**
 * 把带经纬度的对象投影到地图 viewBox 坐标（默认 1600 × 720）。
 * 只做等比拉伸到可用区域，不做真实地理投影 —— 底图本身是示意图。
 */
export function projectToMap<T extends { latitude: number; longitude: number }>(
  items: T[],
  W = 1600,
  H = 720,
  pad = 96
) {
  if (!items.length) return [] as { item: T; x: number; y: number }[]
  const lats = items.map((i) => i.latitude)
  const lons = items.map((i) => i.longitude)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const spanLat = Math.max(1e-9, maxLat - minLat)
  const spanLon = Math.max(1e-9, maxLon - minLon)
  return items.map((item) => ({
    item,
    x: +(pad + ((item.longitude - minLon) / spanLon) * (W - pad * 2)).toFixed(1),
    y: +(pad + ((maxLat - item.latitude) / spanLat) * (H - pad * 2)).toFixed(1)
  }))
}

/* ============================================================
   页面 3 · 治理态势
   ============================================================ */

export interface AreaMetric {
  area: string
  total: number
  handled: number
  closed: number
  timeout: number
  rate: number
  avgMin: number
  trend: number
}

export function buildAreaMetrics(seed = 17): AreaMetric[] {
  const r = rand(seed)
  return AREAS.map((area, i) => {
    const total = 68 + Math.round(r() * 210) + i * 16
    const handled = Math.round(total * (0.87 + r() * 0.11))
    const closed = Math.round(handled * (0.91 + r() * 0.08))
    return {
      area,
      total,
      handled,
      closed,
      timeout: Math.round(total * r() * 0.045),
      rate: +((closed / total) * 100).toFixed(1),
      avgMin: +(20 + r() * 36).toFixed(0),
      trend: +((r() * 16 - 8).toFixed(1))
    }
  })
}

/** 24 小时时段分布（双峰：午间与傍晚） */
export function buildHourly(seed = 23): { hour: string; total: number; high: number }[] {
  const r = rand(seed)
  return Array.from({ length: 24 }, (_, h) => {
    const mid = Math.exp(-((h - 12) ** 2) / 12)
    const eve = Math.exp(-((h - 18.5) ** 2) / 8)
    const base = 18 + 168 * mid + 196 * eve + r() * 14
    const total = Math.round(base)
    return { hour: `${p2(h)}:00`, total, high: Math.round(total * (0.12 + r() * 0.16)) }
  })
}

export const VIOLATION_TYPES = [
  { name: '乱扔烟头', value: 46.8 },
  { name: '违规吸烟', value: 28.4 },
  { name: '烟头落地', value: 15.6 },
  { name: '疑似抛掷', value: 9.2 }
]

export const FAULT_TYPES = [
  { name: '网络中断', value: 38.3 },
  { name: '供电异常', value: 26.7 },
  { name: '画面异常', value: 20.8 },
  { name: '存储故障', value: 14.2 }
]

/* ============================================================
   页面 4 · 设备运行地图
   ============================================================ */

/** 近 7 日设备在线率 */
export function buildDeviceTrend(seed = 31): { date: string; online: number; health: number }[] {
  const r = rand(seed)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    return {
      date: `${p2(d.getMonth() + 1)}-${p2(d.getDate())}`,
      online: +(95.2 + r() * 3.4).toFixed(1),
      health: +(93.4 + r() * 4.2).toFixed(1)
    }
  })
}

export interface DeviceAlarmRow {
  id: string
  cameraId: string
  location: string
  status: 'online' | 'offline' | 'alarm'
  alarmType: string
  ts: string
}

export function buildDeviceAlarms(cameras: Camera[]): DeviceAlarmRow[] {
  const r = rand(41)
  const types = ['网络中断', '供电异常', '画面异常', '存储故障', '离线超 3 天']
  return cameras.slice(0, 12).map((c, i) => ({
    id: `DA${String(i + 1).padStart(4, '0')}`,
    cameraId: c.camera_id,
    location: c.location_name,
    status: i % 5 === 0 ? 'offline' : i % 3 === 0 ? 'alarm' : 'online',
    alarmType: i % 4 === 0 ? types[i % types.length] : '运行正常',
    ts: new Date(Date.now() - Math.round(r() * 8 * 3600e3)).toISOString()
  }))
}

/* ============================================================
   页面 5 · 工作看板
   ============================================================ */

export function buildTaskTrend(seed = 53): { date: string; created: number; done: number }[] {
  const r = rand(seed)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    const created = 120 + Math.round(r() * 96)
    return {
      date: `${p2(d.getMonth() + 1)}-${p2(d.getDate())}`,
      created,
      done: Math.round(created * (0.7 + r() * 0.24))
    }
  })
}

/* ============================================================
   页面 6 · 告警数据列表
   ============================================================ */

export interface AlertRow {
  id: string
  eventId: string
  ts: string
  area: string
  cameraId: string
  cameraName: string
  levelKey: 'high' | 'mid' | 'low'
  levelText: string
  levelTone: string
  thumb: string
  confidence: number
  read: boolean
}

export function buildAlertRows(events: ViolationEvent[], cameras: Camera[]): AlertRow[] {
  const r = rand(67)
  return events.map((ev, i) => {
    const cam = cameras.find((c) => c.camera_id === ev.camera_id)
    const lv = levelOf(ev.confidence)
    return {
      id: `AL${String(i + 1).padStart(4, '0')}`,
      eventId: eventNo(ev),
      ts: ev.event_timestamp,
      area: cam ? AREAS[cameras.indexOf(cam) % AREAS.length] : AREAS[0],
      cameraId: ev.camera_id,
      cameraName: ev.camera_name,
      levelKey: lv.key,
      levelText: lv.text,
      levelTone: lv.tone,
      thumb: ev.evidence_frames[0]?.path ?? '',
      confidence: ev.confidence,
      read: r() > 0.55
    }
  })
}

/* ============================================================
   页面 8 · 调度中心任务池
   ============================================================ */

export interface TaskRow {
  id: string
  orderNo: string
  createdAt: string
  road: string
  area: string
  type: string
  content: string
  owner: string
  status: WorkOrderStatus
  remainMin: number
  urgent: 'high' | 'mid' | 'low'
}

const TASK_TYPES = ['烟头清理', '文明劝导', '设施补充', '重点巡查']
const TASK_CONTENT = [
  '清理人行道烟头并冲洗地面',
  '现场劝导并补充烟蒂收集袋',
  '增设临时烟蒂收集设施',
  '该点位加密巡查一次'
]

export function buildTaskRows(orders: WorkOrder[]): TaskRow[] {
  const r = rand(83)
  return orders.map((o, i) => {
    const remain = o.response_time_sec ? 0 : Math.round(r() * 60)
    return {
      id: String(o.id),
      orderNo: o.order_no,
      createdAt: o.created_at,
      road: o.location_name,
      area: AREAS[i % AREAS.length],
      type: TASK_TYPES[i % TASK_TYPES.length],
      content: TASK_CONTENT[i % TASK_CONTENT.length],
      owner: o.assigned_to,
      status: o.escalated && o.status === 'pending' ? 'timeout' : o.status,
      remainMin: remain,
      urgent: remain < 10 ? 'high' : remain < 30 ? 'mid' : 'low'
    }
  })
}

/* ============================================================
   页面 9 · 调度记录
   ============================================================ */

export interface DispatchRow {
  id: string
  orderNo: string
  staff: string
  ts: string
  result: 'done' | 'fail' | 'cancel'
  resultText: string
  resultTone: string
  note: string
}

export function buildDispatchRows(orders: WorkOrder[]): DispatchRow[] {
  const r = rand(97)
  const staff = ['王建国', '李慧敏', '张海涛', '陈文静', '刘志远', '赵明月']
  const notes = ['现场清理完成，已拍照留证', '点位受阻，转下次巡查', '重复派单，已取消', '已完成并回填处置结果']
  const done = orders.filter((o) => o.status === 'completed' || o.status === 'closed')
  const list = done.length ? done : orders
  return list.slice(0, 24).map((o, i) => {
    const roll = r()
    const result: DispatchRow['result'] = roll > 0.18 ? 'done' : roll > 0.08 ? 'fail' : 'cancel'
    return {
      id: `DR${String(i + 1).padStart(5, '0')}`,
      orderNo: o.order_no,
      staff: staff[i % staff.length],
      ts: o.completed_at ?? o.created_at,
      result,
      resultText: result === 'done' ? '已完成' : result === 'fail' ? '处置失败' : '已取消',
      resultTone: result === 'done' ? 'success' : result === 'fail' ? 'danger' : 'muted',
      note: notes[i % notes.length]
    }
  })
}

/* ============================================================
   页面 10 · GIS 地图
   ============================================================ */

export const GIS_LABELS = [
  { x: 200, y: 130, text: '浉河区' },
  { x: 520, y: 96, text: '平桥区' },
  { x: 860, y: 250, text: '羊山新区' },
  { x: 1180, y: 130, text: '高新区' },
  { x: 300, y: 560, text: '罗山县' },
  { x: 900, y: 640, text: '光山县' }
]

/* ============================================================
   页面 11 · 设备档案
   ============================================================ */

export interface DeviceRow {
  id: string
  name: string
  address: string
  gis: string
  rtsp: string
  status: 'online' | 'offline' | 'alarm'
  statusText: string
  statusTone: string
  statusNote: string
  area: string
}

export function buildDeviceRows(cameras: Camera[]): DeviceRow[] {
  const r = rand(101)
  const notes = ['网络断开', '停电', '信号异常', '离线超 3 天', '运行正常']
  return cameras.map((c, i) => {
    const status: DeviceRow['status'] = i % 7 === 0 ? 'alarm' : i % 5 === 0 ? 'offline' : 'online'
    return {
      id: c.camera_id,
      name: c.name,
      address: c.location_name,
      gis: `${c.longitude.toFixed(5)}, ${c.latitude.toFixed(5)}`,
      rtsp: `rtsp://10.24.${(i % 6) + 1}.${(i % 200) + 10}:554/stream1`,
      status,
      statusText: status === 'online' ? '在线' : status === 'offline' ? '离线' : '告警设备',
      statusTone: status === 'online' ? 'success' : status === 'offline' ? 'muted' : 'danger',
      statusNote: status === 'online' ? notes[4] : notes[Math.floor(r() * 4)],
      area: AREAS[i % AREAS.length]
    }
  })
}

/* ============================================================
   页面 12 · 环卫资源
   ============================================================ */

export interface SanitationRow {
  id: string
  areaCode: string
  area: string
  road: string
  location: string
  team: string
}

export function buildSanitationRows(cameras: Camera[]): SanitationRow[] {
  const r = rand(113)
  const teams = ['一班', '二班', '三班', '四班', '五班']
  const base = cameras.length ? cameras : []
  const rows: SanitationRow[] = []
  const n = Math.max(12, base.length)
  for (let i = 0; i < n; i++) {
    const cam = base[i % Math.max(1, base.length)]
    const area = AREAS[i % AREAS.length]
    rows.push({
      id: String(i + 1),
      areaCode: `QY${p2(i + 1)}${String(Math.round(r() * 90) + 10)}`,
      area,
      road: cam ? cam.location_name : `${area}主干道`,
      location: `${area} · 第 ${(i % 12) + 1} 网格`,
      team: `${area}${teams[i % teams.length]}`
    })
  }
  return rows
}

/* ============================================================
   页面 13 · 模型与数据集
   ============================================================ */

export interface ModelRow {
  id: string
  name: string
  version: string
  ts: string
  enabled: boolean
  desc: string
}

export const MODEL_ROWS: ModelRow[] = [
  { id: 'MD-0001', name: '烟头行为三段式识别模型', version: 'v2.4', ts: '2026-08-12 10:24:31', enabled: true, desc: '当前线上启用版本，含持烟 / 抛掷 / 落地三阶段' },
  { id: 'MD-0002', name: '烟头行为三段式识别模型', version: 'v2.3', ts: '2026-06-28 16:02:07', enabled: false, desc: '上一版，落地阶段误报偏高' },
  { id: 'MD-0003', name: '手部关键点检测模型', version: 'v1.8', ts: '2026-05-19 09:41:52', enabled: true, desc: '提供手部与香烟的空间关联判断' },
  { id: 'MD-0004', name: '行人跟踪模型（ByteTrack）', version: 'v1.2', ts: '2026-04-03 14:18:20', enabled: true, desc: '目标跟踪与轨迹生成' },
  { id: 'MD-0005', name: '抛物线轨迹拟合模型', version: 'v0.9', ts: '2026-03-11 11:07:44', enabled: false, desc: '实验版本，遮挡场景下稳定性不足' }
]

export interface DatasetRow {
  id: string
  name: string
  samples: number
  ts: string
  status: 'ready' | 'training' | 'pending'
  statusText: string
  statusTone: string
}

export const DATASET_ROWS: DatasetRow[] = [
  { id: 'DS-0001', name: '校园公共场所吸烟行为数据集', samples: 4380, ts: '2026-08-10 09:12:00', status: 'ready', statusText: '可用', statusTone: 'success' },
  { id: 'DS-0002', name: '烟头落地点位标注集', samples: 2160, ts: '2026-07-22 15:36:11', status: 'ready', statusText: '可用', statusTone: 'success' },
  { id: 'DS-0003', name: '夜间低照度增强样本集', samples: 980, ts: '2026-07-05 20:41:37', status: 'training', statusText: '训练中', statusTone: 'info' },
  { id: 'DS-0004', name: '遮挡场景负样本集', samples: 1240, ts: '2026-06-18 13:22:09', status: 'pending', statusText: '待校验', statusTone: 'warning' },
  { id: 'DS-0005', name: '误报回溯样本集', samples: 640, ts: '2026-05-30 08:55:26', status: 'ready', statusText: '可用', statusTone: 'success' }
]

/* ============================================================
   页面 14 · AI 识别配置
   ============================================================ */

export interface AiThreshold {
  key: string
  label: string
  desc: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  /** 滑块型 or 数值框型 */
  control: 'range' | 'number'
}

export const AI_THRESHOLDS: AiThreshold[] = [
  { key: 'confidence', label: '检测置信度', desc: '低于该值的检测结果直接丢弃', value: 0.72, min: 0, max: 1, step: 0.01, unit: '', control: 'range' },
  { key: 'iou', label: 'IOU 阈值', desc: '目标框重叠度阈值，用于跟踪关联', value: 0.5, min: 0, max: 1, step: 0.01, unit: '', control: 'range' },
  { key: 'flow', label: '光流速度阈值', desc: '手部快速位移的判定下限', value: 18.5, min: 0, max: 50, step: 0.5, unit: 'px/s', control: 'range' },
  { key: 'frames', label: '行为判定帧数', desc: '连续满足条件的帧数达到该值才生成候选事件', value: 12, min: 3, max: 60, step: 1, unit: '帧', control: 'number' }
]

export const AI_ALERT_RULES = [
  { key: 'instant', label: '高风险事件立即告警', on: true },
  { key: 'streak', label: '连续识别 3 帧后触发', on: true },
  { key: 'night', label: '夜间重点区域加权', on: false }
]

export const CAMERA_WHITELIST = ['CAM-037', 'CAM-052', 'CAM-018']
export const CAMERA_BLACKLIST = ['CAM-061', 'CAM-086']

/* ============================================================
   页面 16 · 账号与角色
   ============================================================ */

export interface AccountRow {
  id: string
  account: string
  name: string
  role: string
  roleTone: string
  phone: string
  enabled: boolean
  ts: string
}

export const ACCOUNT_ROWS: AccountRow[] = [
  { id: 'U-001', account: 'admin', name: '系统管理员', role: '超级管理员', roleTone: 'info', phone: '138****0001', enabled: true, ts: '2026-09-20 10:12:04' },
  { id: 'U-002', account: 'manager_xh', name: '浉河区管理员', role: '区域管理员', roleTone: 'purple', phone: '139****2210', enabled: true, ts: '2026-09-18 16:35:41' },
  { id: 'U-003', account: 'manager_pq', name: '平桥区管理员', role: '区域管理员', roleTone: 'purple', phone: '137****5583', enabled: true, ts: '2026-09-15 09:02:17' },
  { id: 'U-004', account: 'worker_012', name: '王建国', role: '工作人员', roleTone: 'warning', phone: '150****7742', enabled: true, ts: '2026-09-12 14:48:55' },
  { id: 'U-005', account: 'worker_028', name: '李慧敏', role: '工作人员', roleTone: 'warning', phone: '186****3390', enabled: false, ts: '2026-09-08 11:20:33' },
  { id: 'U-006', account: 'ai_dev', name: '算法维护', role: '超级管理员', roleTone: 'info', phone: '135****1187', enabled: true, ts: '2026-09-05 17:09:28' }
]

export interface RoleRow {
  id: string
  name: string
  desc: string
  perms: string[]
  count: number
  ts: string
}

export const ROLE_ROWS: RoleRow[] = [
  { id: 'R-01', name: '超级管理员', desc: '全部模块与系统配置权限', perms: ['态势总览', '事件中心', '调度中心', '全域地图', '资源管理', 'AI治理', '系统管理'], count: 2, ts: '2026-08-01 09:00:00' },
  { id: 'R-02', name: '区域管理员', desc: '本辖区事件研判与调度', perms: ['态势总览', '事件中心', '调度中心', '全域地图'], count: 8, ts: '2026-08-01 09:00:00' },
  { id: 'R-03', name: '工作人员', desc: '移动工单执行与回填', perms: ['调度中心'], count: 118, ts: '2026-08-01 09:00:00' }
]

export const PERMISSION_TREE = [
  { key: 'situation', label: '态势总览', children: ['事件总览', '治理态势', '设备状态', '工作看板'] },
  { key: 'events', label: '事件中心', children: ['告警中心', '事件报表'] },
  { key: 'dispatch', label: '调度中心', children: ['任务池', '调度记录'] },
  { key: 'map', label: '全域地图', children: ['GIS 地图'] },
  { key: 'resource', label: '资源管理', children: ['设备资源', '环卫资源'] },
  { key: 'ai', label: 'AI治理', children: ['模型与数据集', 'AI识别配置', '数据分析'] },
  { key: 'system', label: '系统管理', children: ['权限与账号', '系统配置', '审计日志'] }
]

/* ============================================================
   页面 17 · 全平台配置
   ============================================================ */

export interface FeedbackRow {
  id: string
  ts: string
  author: string
  content: string
  area: string
  handled: boolean
}

export const FEEDBACK_ROWS: FeedbackRow[] = [
  { id: 'FB-001', ts: '2026-09-24 09:12:31', author: '市民 138****2246', content: '学校东门天桥下烟头比较多，建议增加收集设施。', area: '浉河区', handled: false },
  { id: 'FB-002', ts: '2026-09-23 18:40:07', author: '市民 150****8890', content: '公交站台旁边缺少吸烟区指引，希望补充标识。', area: '平桥区', handled: false },
  { id: 'FB-003', ts: '2026-09-22 14:05:52', author: '市民 186****3311', content: '广场草坪里发现不少烟头，清理过一次又有了。', area: '羊山新区', handled: true },
  { id: 'FB-004', ts: '2026-09-21 08:33:19', author: '市民 137****6604', content: '希望公开各点位清理的完成情况。', area: '高新区', handled: true }
]

export const PUBLIC_CONTENTS = {
  adminTip: '本平台数据为试点运行数据，处置结论以人工复核为准。',
  citizenTip: '感谢您共同维护环境卫生，提交线索后可在「我的上报」查看进度。',
  reportTemplate: '统计区间：{date_range}；所属单位：{organization}；导出人：{operator}。'
}

/* ============================================================
   页面 18 · 审计日志
   ============================================================ */

export interface AuditRow {
  id: string
  account: string
  action: 'login' | 'data' | 'perm' | 'config'
  actionText: string
  actionTone: string
  content: string
  ip: string
  ts: string
}

export function buildAuditRows(seed = 127, count = 20): AuditRow[] {
  const r = rand(seed)
  const acts: { a: AuditRow['action']; t: string; tone: string; items: string[] }[] = [
    { a: 'login', t: '登录', tone: 'info', items: ['管理员登录系统', '通过统一身份认证登录', '登录失败，密码错误'] },
    { a: 'data', t: '数据操作', tone: 'success', items: ['导出告警列表 Excel', '标记告警为已阅', '批量完成调度工单'] },
    { a: 'perm', t: '权限变更', tone: 'warning', items: ['新增账号 worker_031', '调整角色权限：区域管理员', '禁用账号 worker_028'] },
    { a: 'config', t: '系统配置', tone: 'danger', items: ['修改检测置信度阈值', '切换三段式证据链开关', '更新全平台基础配置'] }
  ]
  const accounts = ['admin', 'manager_xh', 'manager_pq', 'ai_dev', 'worker_012']
  return Array.from({ length: count }, (_, i) => {
    const g = acts[Math.floor(r() * acts.length)]
    return {
      id: `LG${String(36528 - i).padStart(6, '0')}`,
      account: accounts[Math.floor(r() * accounts.length)],
      action: g.a,
      actionText: g.t,
      actionTone: g.tone,
      content: g.items[Math.floor(r() * g.items.length)],
      ip: `10.24.${Math.floor(r() * 6) + 1}.${Math.floor(r() * 240) + 8}`,
      ts: new Date(Date.now() - Math.round(r() * 72 * 3600e3)).toISOString()
    }
  }).sort((a, b) => (a.ts < b.ts ? 1 : -1))
}

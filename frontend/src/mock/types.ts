/**
 * 模拟数据引擎 · 类型定义
 *
 * 字段命名严格对齐 PRD §7.1「AI → 全栈 事件输出协议」与 §8.3 数据字典，
 * 以便后端接入时零改动替换（见 docs/烟踪智治-文档缺陷与修订说明.md 第三节）。
 */

export type EventStage = 'HOLDING' | 'THROWING' | 'LANDED' | 'THROW_CONFIRMED'
export type EvidenceFrameType = 'holding' | 'throwing' | 'landed'
/**
 * 事件状态。
 *
 * 前端本地模拟只用到 confirmed / false_alarm / pending_review / closed；
 * candidate 与 referred 是后端状态机（backend/app/statemachine.py）里
 * 「候选 → 待复核 → 已确认 / 已驳回 → 已移送 → 已闭环」的另外两态。
 * 打开 VITE_USE_API 后后端会返回它们，所以一并声明。
 */
export type EventStatus =
  | 'candidate'
  | 'confirmed'
  | 'false_alarm'
  | 'pending_review'
  | 'referred'
  | 'closed'
export type CameraStatus = 'online' | 'offline' | 'degraded'
export type WorkOrderStatus =
  | 'pending'
  | 'accepted'
  | 'processing'
  /** 已提交闭环材料、等待管理端验收（后端比前端多这一态） */
  | 'verifying'
  | 'completed'
  | 'closed'
  | 'timeout'
export type SuggestionType =
  | 'add_facility'
  | 'adjust_schedule'
  | 'treatment_effective'
  | 'warning'
export type SuggestionStatus = 'pending' | 'accepted' | 'rejected' | 'expired'

export interface Camera {
  camera_id: string
  name: string
  location_name: string
  latitude: number
  longitude: number
  status: CameraStatus
  fps: number
  preprocess_enabled: boolean
  preprocess_algorithm: 'retinex' | 'histogram_eq'
  online_rate: number
}

export interface EvidenceFrame {
  frame_ts: string
  type: EvidenceFrameType
  path: string
}

export interface TrajectoryPoint {
  x: number
  y: number
  ts: string
}

export interface ViolationEvent {
  id: number
  event_id: string
  camera_id: string
  camera_name: string
  track_id: number
  stage: EventStage
  confidence: number
  bbox: [number, number, number, number]
  trajectory: TrajectoryPoint[]
  event_timestamp: string
  status: EventStatus
  evidence_frames: EvidenceFrame[]
  video_clip_path: string
  /** 是否已生成工单（决定是否计入"未闭环"） */
  has_workorder: boolean
  review_note?: string
}

export interface WorkOrder {
  id: number
  order_no: string
  event_id: string
  camera_id: string
  location_name: string
  latitude: number
  longitude: number
  status: WorkOrderStatus
  assigned_to: string
  created_at: string
  accepted_at: string | null
  completed_at: string | null
  response_time_sec: number | null
  /** 超时告警（超过 30 分钟未接收，PRD §5.2.3） */
  escalated: boolean
  /** 以下三项仅后端 API 模式会返回（作业端提交闭环材料后产生） */
  closure_photo?: string
  completion_note?: string
  completion_submitted?: boolean
  priority?: string
}

export interface Suggestion {
  id: number
  type: SuggestionType
  area_name: string
  time_range: string
  content: string
  frequency_data: Record<string, number | string>
  status: SuggestionStatus
  created_at: string
  feedback_note?: string
}

export interface TrendPoint {
  date: string
  /** 识别事件数 */
  detected: number
  /** 已处置事件数 */
  handled: number
}

export interface HeatmapPoint {
  lat: number
  lon: number
  weight: number
}

export interface DashboardMetrics {
  todayViolations: number
  processingEvents: number
  onlineDevices: number
  onlineStaff: number
  /** 同比 */
  todayViolationsDelta: number
  processingEventsDelta: number
  onlineDevicesDelta: number
  onlineStaffDelta: number
  /** 闭环相关 */
  workorderTotal: number
  workorderCompleted: number
  workorderCompletionRate: number
  avgResponseMin: number
  unclosedCount: number
}

/** 后端接口封装。返回值即后端 data，错误由调用方用 toFailure() 统一处理。 */

import type {
  Camera,
  DashboardMetrics,
  Suggestion,
  TrendPoint,
  ViolationEvent,
  WorkOrder
} from '@/mock/types'
import { apiForm, apiGet, apiPatch, apiPost } from './client'

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface BackendUser {
  id: number
  username: string
  real_name: string
  role: 'admin' | 'manager' | 'worker' | 'ai_dev'
  role_label: string
  phone: string
  enabled: boolean
  allowed_pages: string[]
  created_at: string
}

export interface LoginResult {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in: number
  user: BackendUser
}

export interface CitizenProfile {
  phone: string
  displayName: string
  district: string
  contribution: number
}

export interface CitizenReport {
  id: number
  report_no: string
  phone: string
  kind: 'video' | 'photo'
  kind_label: string
  media_name: string
  media_path: string
  location: string
  description: string
  status: string
  status_label: string
  submitted_at: string
  accepted_at: string | null
  started_at: string | null
  finished_at: string | null
  rejected_at: string | null
  reject_reason: string
  public_reply: string
  result_photo: string
  event_id: string
  task_id: string
  appeal_note: string
  risk_flag: boolean
  /** AI 报告快照（后端存的是 JSON 字符串，序列化后还原成对象） */
  ai_report?: {
    engine?: string
    detected?: boolean
    confidence?: number
    count?: number
    verdict?: string
    verdict_label?: string
    verdict_tone?: string
    summary?: string
    notice?: string
  } | null
  /** 市民对 AI 判断的反馈：{ agree, reason, expect } */
  ai_feedback?: { agree?: boolean; reason?: string; expect?: string } | null
  ai_feedback_at?: string
  timeline: { key: string; label: string; ts: string }[]
}

export interface AuditLog {
  id: number
  ts: string
  actor: string
  role: string
  action: string
  action_label: string
  target: string
  detail: string
  result: string
  ip: string
}

export interface WorkOrderStats {
  total: number
  by_status: Record<string, number>
  closed: number
  completion_rate: number
  avg_response_min: number
  overdue: number
}

export interface OverviewPayload {
  metrics: DashboardMetrics
  health: {
    deviceOnlineRate: number
    serviceAvailability: number
    storageHealth: number
    cameraTotal: number
    cameraOnline: number
  }
  demo: boolean
}

export interface ReportSubmitPayload {
  kind: 'video' | 'photo'
  media_name: string
  location: string
  description: string
  safe_confirmed: boolean
  has_risk?: boolean
  /** 上传时当场产出的 AI 报告快照（`/public/ai/inspect` 的原样结果） */
  ai_report?: unknown
}

/* ---------------- 认证 ---------------- */

export const login = (username: string, password: string) =>
  apiPost<LoginResult>('/auth/login', { username, password })

export const currentUser = () => apiGet<{ user: BackendUser }>('/auth/me')

export const logout = () => apiPost<{ status: string }>('/auth/logout')

export const citizenLogin = (phone: string, code: string) =>
  apiPost<{ access_token: string; profile: CitizenProfile }>('/auth/citizen/login', { phone, code })

/* ---------------- 摄像头 ---------------- */

export const listCameras = (params?: { page?: number; size?: number; status?: string }) =>
  apiGet<PageResult<Camera>>('/cameras', params)

export const createCamera = (body: Record<string, unknown>) => apiPost<Camera>('/cameras', body)

export const updateCamera = (cameraId: string, body: Record<string, unknown>) =>
  apiPatch<Camera>(`/cameras/${cameraId}`, body)

/* ---------------- 事件 ---------------- */

export const listEvents = (params?: {
  page?: number
  size?: number
  status?: string
  camera_id?: string
  min_confidence?: number
  start_date?: string
  end_date?: string
  source?: string
}) => apiGet<PageResult<ViolationEvent>>('/events', params)

export const getEvent = (eventId: string) => apiGet<ViolationEvent>(`/events/${eventId}`)

export const eventSummary = () => apiGet<Record<string, unknown>>('/events/summary')

export const reviewEvent = (eventId: string, action: 'confirm' | 'reject' | 'refer' | 'close', note = '') =>
  apiPost<{ event: ViolationEvent; order_no: string | null }>(`/events/${eventId}/review`, { action, note })

export const simulateEvent = (cameraId?: string, createWorkorder = true) =>
  apiPost<{ event: ViolationEvent; order_no: string | null; message: string }>('/events/simulate', {
    camera_id: cameraId ?? null,
    create_workorder: createWorkorder
  })

export const eventHeatmap = (days = 7) => apiGet<{ grid: unknown[]; bbox: number[] }>('/events/heatmap', { days })

/* ---------------- 工单 ---------------- */

export const listWorkorders = (params?: {
  page?: number
  size?: number
  status?: string
  assigned_to?: number
  location?: string
}) => apiGet<PageResult<WorkOrder>>('/workorders', params)

export const workorderStats = () => apiGet<WorkOrderStats>('/workorders/stats')

export const acceptWorkorder = (id: number) => apiPost<WorkOrder>(`/workorders/${id}/accept`)

export const startWorkorder = (id: number) => apiPost<WorkOrder>(`/workorders/${id}/start`)

export const completeWorkorder = (id: number, note: string, photo?: File | null) => {
  const form = new FormData()
  form.append('note', note)
  if (photo) form.append('photo', photo)
  return apiForm<WorkOrder>(`/workorders/${id}/complete`, form)
}

export const verifyWorkorder = (id: number, passed: boolean, note = '') => {
  const form = new FormData()
  form.append('passed', String(passed))
  form.append('note', note)
  return apiForm<WorkOrder>(`/workorders/${id}/verify`, form)
}

/* ---------------- 统计 ---------------- */

export const statsOverview = () => apiGet<OverviewPayload>('/stats/overview')

export const statsTrend = (days = 7) => apiGet<{ items: TrendPoint[] }>('/stats/trend', { days })

export const statsHourly = (days = 7) =>
  apiGet<{ items: { hour: string; total: number; high: number }[] }>('/stats/hourly', { days })

export const statsAreas = (days = 30) =>
  apiGet<{ items: { area: string; total: number; closed: number; rate: number; recent7: number }[] }>(
    '/stats/areas',
    { days }
  )

export const statsTypes = (days = 30) =>
  apiGet<{ items: { name: string; value: number; count: number }[] }>('/stats/types', { days })

export const statsHealth = () => apiGet<Record<string, unknown>>('/stats/health')

/* ---------------- 决策建议 ---------------- */

export const listSuggestions = () => apiGet<{ items: Suggestion[] }>('/suggestions')

export const recomputeSuggestions = () => apiPost<{ items: Suggestion[] }>('/suggestions/recompute')

export const feedbackSuggestion = (id: number, action: 'accepted' | 'rejected', note = '') =>
  apiPost<Suggestion>(`/suggestions/${id}/feedback`, { action, note })

/* ---------------- 市民上报 ---------------- */

export const submitCitizenReport = (payload: ReportSubmitPayload) =>
  apiPost<CitizenReport>('/citizen/reports', payload)

export const myReports = () => apiGet<PageResult<CitizenReport>>('/citizen/reports')

export const myReport = (reportNo: string) => apiGet<CitizenReport>(`/citizen/reports/${reportNo}`)

export const withdrawReport = (reportNo: string) =>
  apiPost<CitizenReport>(`/citizen/reports/${reportNo}/withdraw`)

export const appealReport = (reportNo: string, description: string) =>
  apiPost<CitizenReport>(`/citizen/reports/${reportNo}/appeal`, { description })

export const publicCase = (reportNo: string) => apiGet<CitizenReport>(`/public/cases/${reportNo}`)

/* ---------------- 上报受理（管理端） ---------------- */

export const listReports = (params?: { page?: number; size?: number; status?: string; keyword?: string }) =>
  apiGet<PageResult<CitizenReport>>('/reports', params)

export const analyzeReport = (reportNo: string) =>
  apiPost<{ report: CitizenReport; task_id: string; event_id: string }>(`/reports/${reportNo}/analyze`)

export const acceptReport = (reportNo: string) =>
  apiPost<{ report: CitizenReport; order_no: string | null }>(`/reports/${reportNo}/accept`)

export const rejectReport = (reportNo: string, reason: string) =>
  apiPost<{ report: CitizenReport }>(`/reports/${reportNo}/reject`, { reason })

export const finishReport = (reportNo: string, publicReply: string) =>
  apiPost<{ report: CitizenReport }>(`/reports/${reportNo}/finish`, { public_reply: publicReply })

/* ---------------- 审计 ---------------- */

export const listAuditLogs = (params?: {
  page?: number
  size?: number
  action?: string
  result?: string
  keyword?: string
}) => apiGet<PageResult<AuditLog>>('/audit/logs', params)

/* ---------------- 演示数据重置 ---------------- */

export const reseed = (force = true) =>
  apiPost<{ status: string; result: Record<string, number> }>(`/admin/reseed?force=${force}`)

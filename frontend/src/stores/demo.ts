import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  buildCameras,
  buildEvent,
  buildEvents,
  buildSuggestions,
  buildTrend,
  buildWorkOrders
} from '@/mock/engine'
import { SCALE_PRESETS, type ScaleMode } from '@/mock/config'
import { USE_API, backendReachable, hasAdminToken, toFailure } from '@/api/client'
import * as api from '@/api/endpoints'
import type {
  Camera,
  DashboardMetrics,
  Suggestion,
  TrendPoint,
  ViolationEvent,
  WorkOrder
} from '@/mock/types'

export interface AlertPopup {
  event_id: string
  camera_id: string
  camera_name: string
  location_name: string
  timestamp: string
  confidence: number
  thumbnail_url: string
  read: boolean
}

const SCALE_KEY = 'yz.demo.scale'

export const useDemoStore = defineStore('demo', () => {
  const scaleMode = ref<ScaleMode>(
    (localStorage.getItem(SCALE_KEY) as ScaleMode) === 'design' ? 'design' : 'pilot'
  )

  const cameras = ref<Camera[]>([])
  const events = ref<ViolationEvent[]>([])
  const workOrders = ref<WorkOrder[]>([])
  const suggestions = ref<Suggestion[]>([])
  const trend = ref<TrendPoint[]>([])
  const alerts = ref<AlertPopup[]>([])
  const initialized = ref(false)

  /** API 模式：后端是否可达 + 最近一次错误 */
  const backendOnline = ref(false)
  const lastError = ref('')
  /** 后端算出的指标与健康快照（API 模式下覆盖本地推算） */
  const apiMetrics = ref<DashboardMetrics | null>(null)
  const apiHealth = ref<{ deviceOnlineRate: number; serviceAvailability: number; storageHealth: number } | null>(
    null
  )
  const loading = ref(false)

  const scale = computed(() => SCALE_PRESETS[scaleMode.value])
  const apiMode = computed(() => USE_API)

  function rebuild() {
    cameras.value = buildCameras(scaleMode.value)
    events.value = buildEvents(cameras.value, scale.value.eventCount)
    workOrders.value = buildWorkOrders(events.value, cameras.value, scaleMode.value)
    suggestions.value = buildSuggestions(cameras.value, scaleMode.value)
    trend.value = buildTrend(scaleMode.value)
    alerts.value = events.value.slice(0, 3).map((ev) => toAlert(ev))
    initialized.value = true
  }

  function toAlert(ev: ViolationEvent): AlertPopup {
    const cam = cameras.value.find((c) => c.camera_id === ev.camera_id)
    return {
      event_id: ev.event_id,
      camera_id: ev.camera_id,
      camera_name: ev.camera_name,
      location_name: cam?.location_name ?? ev.camera_name,
      timestamp: ev.event_timestamp,
      confidence: ev.confidence,
      thumbnail_url: ev.evidence_frames?.[0]?.path ?? '',
      read: false
    }
  }

  /** 从后端拉取全部业务数据。后端不可用时**回退到本地模拟**，页面不会白屏。 */
  async function refresh(): Promise<void> {
    // 未登录 / 后端不可达时不打受保护接口：
    //  · 入口页也会调 init()，匿名请求只会得到 401（D-20）；
    //  · 后端没起时代理会挂起，直接改走本地模拟，避免长时间空白（D-22）。
    const canUseApi = USE_API && hasAdminToken() && (await backendReachable())
    if (!canUseApi) {
      rebuild()
      backendOnline.value = false
      return
    }
    loading.value = true
    try {
      const [cams, evs, orders, sugg, tr, ov] = await Promise.all([
        api.listCameras({ size: 200 }),
        api.listEvents({ size: 200 }),
        api.listWorkorders({ size: 200 }),
        api.listSuggestions(),
        api.statsTrend(7),
        api.statsOverview()
      ])
      cameras.value = cams.items
      events.value = evs.items
      workOrders.value = orders.items
      suggestions.value = sugg.items
      trend.value = tr.items
      apiMetrics.value = ov.metrics
      apiHealth.value = ov.health
      alerts.value = evs.items.slice(0, 3).map((ev) => toAlert(ev))
      backendOnline.value = true
      lastError.value = ''
    } catch (err) {
      const failure = toFailure(err)
      backendOnline.value = false
      lastError.value = failure.message
      // 关键：后端掉线时仍要能演示，退回本地模拟数据
      rebuild()
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  async function init(): Promise<void> {
    if (initialized.value) return
    await refresh()
  }

  /** 重新加载（后端不可用时自动回退本地模拟） */
  async function reload(): Promise<void> {
    await refresh()
  }

  function setScaleMode(mode: ScaleMode) {
    scaleMode.value = mode
    localStorage.setItem(SCALE_KEY, mode)
    // API 模式下数据量级由后端数据决定，这里只切换本地展示预设
    if (!USE_API) rebuild()
  }

  /** 未闭环事件：已确认但工单尚未完成/关闭 */
  const unclosedEvents = computed(() => {
    const closedOrderEventIds = new Set(
      workOrders.value
        .filter((o) => o.status === 'completed' || o.status === 'closed')
        .map((o) => o.event_id)
    )
    return events.value.filter(
      (ev) => ev.status !== 'false_alarm' && !closedOrderEventIds.has(ev.event_id)
    )
  })

  const metrics = computed<DashboardMetrics>(() => {
    if (USE_API && apiMetrics.value) return apiMetrics.value

    const s = scale.value
    const total = workOrders.value.length
    const done = workOrders.value.filter(
      (o) => o.status === 'completed' || o.status === 'closed'
    ).length
    const responses = workOrders.value
      .map((o) => o.response_time_sec)
      .filter((v): v is number => typeof v === 'number')
    const avgSec = responses.length
      ? responses.reduce((a, b) => a + b, 0) / responses.length
      : 0
    return {
      todayViolations: s.todayViolations,
      processingEvents: s.processingEvents,
      onlineDevices: s.onlineDevices,
      onlineStaff: s.onlineStaff,
      todayViolationsDelta: s.todayViolationsDelta,
      processingEventsDelta: s.processingEventsDelta,
      onlineDevicesDelta: s.onlineDevicesDelta,
      onlineStaffDelta: s.onlineStaffDelta,
      workorderTotal: total,
      workorderCompleted: done,
      workorderCompletionRate: total ? +((done / total) * 100).toFixed(1) : 0,
      avgResponseMin: avgSec ? +(avgSec / 60).toFixed(1) : s.avgResponseMin,
      unclosedCount: unclosedEvents.value.length
    }
  })

  /** 系统健康监测（设计稿的三个环） */
  const health = computed(() => {
    if (USE_API && apiHealth.value) {
      return {
        deviceOnlineRate: apiHealth.value.deviceOnlineRate,
        serviceAvailability: apiHealth.value.serviceAvailability,
        storageHealth: apiHealth.value.storageHealth
      }
    }
    const onlineCameras = cameras.value.filter((c) => c.status === 'online').length
    const deviceRate = cameras.value.length
      ? +((onlineCameras / cameras.value.length) * 100).toFixed(1)
      : 0
    return {
      deviceOnlineRate: scaleMode.value === 'pilot' ? deviceRate : 98.6,
      serviceAvailability: 99.9,
      storageHealth: scaleMode.value === 'pilot' ? 62.4 : 95.3
    }
  })

  /**
   * 一键演示一次违规（答辩核心操作）。
   * API 模式走后端 /events/simulate：事件生成 → 自动建单 → WebSocket 推送，
   * 数据落库，刷新页面不会消失。
   */
  async function simulateViolation(cameraIndex?: number): Promise<ViolationEvent | null> {
    if (USE_API) {
      try {
        const res = await api.simulateEvent(undefined, true)
        events.value.unshift(res.event)
        alerts.value.unshift(toAlert(res.event))
        if (alerts.value.length > 8) alerts.value.pop()
        const orders = await api.listWorkorders({ size: 200 })
        workOrders.value = orders.items
        backendOnline.value = true
        return res.event
      } catch (err) {
        lastError.value = toFailure(err).message
        backendOnline.value = false
        return null
      }
    }

    const ev = buildEvent(cameras.value, {
      at: new Date(),
      cameraIndex,
      idOffset: 900000 + events.value.length
    })
    events.value.unshift(ev)

    const cam = cameras.value.find((c) => c.camera_id === ev.camera_id)!
    workOrders.value.unshift({
      id: 900000 + workOrders.value.length,
      order_no: `GD${new Date().getFullYear()}${String(Date.now()).slice(-8)}`,
      event_id: ev.event_id,
      camera_id: ev.camera_id,
      location_name: cam.location_name,
      latitude: cam.latitude,
      longitude: cam.longitude,
      status: 'pending',
      assigned_to: '待派发',
      created_at: ev.event_timestamp,
      accepted_at: null,
      completed_at: null,
      response_time_sec: null,
      escalated: false
    })

    alerts.value.unshift(toAlert(ev))
    if (alerts.value.length > 8) alerts.value.pop()

    return ev
  }

  async function acceptOrder(orderId: number, staff: string): Promise<void> {
    if (USE_API) {
      try {
        const updated = await api.acceptWorkorder(orderId)
        patchOrder(updated)
      } catch (err) {
        lastError.value = toFailure(err).message
      }
      return
    }
    const o = workOrders.value.find((x) => x.id === orderId)
    if (!o) return
    o.status = 'accepted'
    o.assigned_to = staff
    o.accepted_at = new Date().toISOString()
    o.response_time_sec = Math.floor((Date.now() - new Date(o.created_at).getTime()) / 1000)
  }

  async function startOrder(orderId: number): Promise<void> {
    if (USE_API) {
      try {
        patchOrder(await api.startWorkorder(orderId))
      } catch (err) {
        lastError.value = toFailure(err).message
      }
      return
    }
    const o = workOrders.value.find((x) => x.id === orderId)
    if (o) o.status = 'processing'
  }

  /** 提交闭环材料（可附清理后照片）。API 模式下会真正上传到后端 storage/。 */
  async function submitClosure(orderId: number, note: string, photo?: File | null): Promise<boolean> {
    if (USE_API) {
      try {
        patchOrder(await api.completeWorkorder(orderId, note, photo))
        return true
      } catch (err) {
        lastError.value = toFailure(err).message
        return false
      }
    }
    const o = workOrders.value.find((x) => x.id === orderId)
    if (!o) return false
    o.status = 'verifying'
    o.completion_note = note
    return true
  }

  /** 管理端验收：通过 → 已闭环；不通过 → 打回处理中 */
  async function verifyOrder(orderId: number, passed: boolean, note = ''): Promise<boolean> {
    if (USE_API) {
      try {
        patchOrder(await api.verifyWorkorder(orderId, passed, note))
        return true
      } catch (err) {
        lastError.value = toFailure(err).message
        return false
      }
    }
    const o = workOrders.value.find((x) => x.id === orderId)
    if (!o) return false
    o.status = passed ? 'closed' : 'processing'
    return true
  }

  async function completeOrder(orderId: number): Promise<void> {
    await submitClosure(orderId, '已完成清理')
  }

  function patchOrder(updated: WorkOrder) {
    const idx = workOrders.value.findIndex((o) => o.id === updated.id)
    if (idx >= 0) workOrders.value.splice(idx, 1, updated)
    else workOrders.value.unshift(updated)
  }

  async function feedbackSuggestion(id: number, accepted: boolean, note = ''): Promise<void> {
    if (USE_API) {
      try {
        const updated = await api.feedbackSuggestion(id, accepted ? 'accepted' : 'rejected', note)
        const idx = suggestions.value.findIndex((s) => s.id === id)
        if (idx >= 0) suggestions.value.splice(idx, 1, updated)
      } catch (err) {
        lastError.value = toFailure(err).message
      }
      return
    }
    const s = suggestions.value.find((x) => x.id === id)
    if (!s) return
    s.status = accepted ? 'accepted' : 'rejected'
    s.feedback_note = note || (accepted ? '已采纳' : '已驳回')
  }

  function markAlertsRead() {
    alerts.value.forEach((a) => (a.read = true))
  }

  return {
    scaleMode,
    scale,
    apiMode,
    backendOnline,
    lastError,
    loading,
    cameras,
    events,
    workOrders,
    suggestions,
    trend,
    alerts,
    initialized,
    unclosedEvents,
    metrics,
    health,
    init,
    rebuild,
    reload,
    setScaleMode,
    simulateViolation,
    acceptOrder,
    startOrder,
    submitClosure,
    verifyOrder,
    completeOrder,
    feedbackSuggestion,
    markAlertsRead
  }
})

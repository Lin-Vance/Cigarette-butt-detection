/**
 * 执法协同（原「交警端」）线索状态。
 *
 * 交警端已并入管理端，成为「执法协同」模块下的两个页面，
 * 所以这份状态放在管理端工程里，由 law-cases / law-trail 两个页面共享。
 *
 * 职责边界（对齐《三端架构》与隐私要求）：
 * - 只处理**已复核**的行为线索，不做算法定性；
 * - 不展示举报人实名，也不展示被举报对象的可识别画面；
 * - 三个处置动作（需补充 / 不予处理 / 已处理）都必须留痕。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { ViolationEvent } from '@/mock/types'

export type CaseStatus = 'to_check' | 'need_more' | 'handling' | 'done' | 'rejected'

export const CASE_STATUS_TEXT: Record<CaseStatus, string> = {
  to_check: '待核查',
  need_more: '需补充',
  handling: '处理中',
  done: '已处理',
  rejected: '不予处理'
}

export const CASE_TONE: Record<CaseStatus, string> = {
  to_check: 'warning',
  need_more: 'info',
  handling: 'info',
  done: 'success',
  rejected: 'danger'
}

export interface LawCase {
  key: string
  no: string
  area: string
  ts: string
  confidence: number
  frames: number
  status: CaseStatus
  note: string
  operator: string
  updatedAt: string
}

export interface LawTrailItem {
  no: string
  action: string
  note: string
  operator: string
  at: string
  result: 'success' | 'returned' | 'rejected'
}

/** 处置动作 -> 目标状态与留痕结果的映射 */
export const DISPOSE: Record<
  'done' | 'need_more' | 'rejected',
  { status: CaseStatus; action: string; result: LawTrailItem['result'] }
> = {
  done: { status: 'done', action: '处理完成', result: 'success' },
  need_more: { status: 'need_more', action: '退回补充材料', result: 'returned' },
  rejected: { status: 'rejected', action: '不予处理', result: 'rejected' }
}

/** 演示用状态分布：固定顺序，保证每次演示看到的数量一致 */
const DEMO_DIST: CaseStatus[] = [
  'to_check',
  'to_check',
  'to_check',
  'handling',
  'need_more',
  'done',
  'done',
  'rejected'
]

export const useLawStore = defineStore('law', () => {
  const cases = ref<LawCase[]>([])
  const trail = ref<LawTrailItem[]>([])
  const initialized = ref(false)

  /** 从已复核的事件派生线索。幂等：已初始化则不重建，避免刷新页面丢状态。 */
  function seed(events: ViolationEvent[], operator = '演示执法人员') {
    if (initialized.value) return
    const pool = events.filter((e) => e.status === 'confirmed' || e.status === 'referred')
    cases.value = pool.slice(0, 12).map((e, i) => {
      const status = DEMO_DIST[i % DEMO_DIST.length]
      return {
        key: e.event_id,
        no: `JF${new Date(e.event_timestamp).getFullYear()}${String(i + 1).padStart(4, '0')}`,
        area: e.camera_name || '未标注区域',
        ts: e.event_timestamp,
        confidence: e.confidence,
        frames: e.evidence_frames?.length ?? 0,
        status,
        note: status === 'rejected' ? '现场核查未发现遗留烟蒂，不予处理' : '',
        operator: status === 'to_check' ? '' : operator,
        updatedAt: e.event_timestamp
      }
    })
    // 已完成的线索补一条历史留痕，让「处置留痕」页一进来就有内容
    trail.value = cases.value
      .filter((c) => c.status === 'done' || c.status === 'rejected')
      .slice(0, 6)
      .map((c) => ({
        no: c.no,
        action: c.status === 'done' ? '处理完成' : '不予处理',
        note: c.note || '已完成现场处置并回复',
        operator,
        at: c.updatedAt,
        result: c.status === 'done' ? ('success' as const) : ('rejected' as const)
      }))
    initialized.value = true
  }

  const byStatus = computed(() => {
    const m: Record<CaseStatus, LawCase[]> = {
      to_check: [],
      need_more: [],
      handling: [],
      done: [],
      rejected: []
    }
    cases.value.forEach((c) => m[c.status].push(c))
    return m
  })

  const stats = computed(() => ({
    toCheck: byStatus.value.to_check.length,
    needMore: byStatus.value.need_more.length,
    handling: byStatus.value.handling.length,
    done: byStatus.value.done.length,
    rejected: byStatus.value.rejected.length,
    returnRate:
      cases.value.length > 0
        ? +((byStatus.value.need_more.length / cases.value.length) * 100).toFixed(1)
        : 0
  }))

  function claim(key: string, operator: string) {
    const c = cases.value.find((x) => x.key === key)
    if (!c || c.status !== 'to_check') return false
    c.status = 'handling'
    c.operator = operator
    c.updatedAt = new Date().toISOString()
    trail.value.unshift({
      no: c.no,
      action: '认领核查',
      note: '已认领，准备现场核查',
      operator,
      at: c.updatedAt,
      result: 'success'
    })
    return true
  }

  function dispose(key: string, kind: 'done' | 'need_more' | 'rejected', note: string, operator: string) {
    const c = cases.value.find((x) => x.key === key)
    if (!c) return false
    const cfg = DISPOSE[kind]
    c.status = cfg.status
    c.note = note.trim()
    c.operator = operator
    c.updatedAt = new Date().toISOString()
    trail.value.unshift({
      no: c.no,
      action: cfg.action,
      note: c.note || '—',
      operator,
      at: c.updatedAt,
      result: cfg.result
    })
    return true
  }

  /** 证据完整度：三帧齐全视为完整（与后端校验同口径） */
  function integrity(c: LawCase) {
    return c.frames >= 3 ? '完整' : c.frames > 0 ? '不完整' : '缺失'
  }

  const RESULT_TEXT: Record<LawTrailItem['result'], string> = {
    success: '已回传',
    returned: '已退回',
    rejected: '已驳回'
  }

  return { cases, trail, initialized, seed, byStatus, stats, claim, dispose, integrity, RESULT_TEXT }
})

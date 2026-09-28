/**
 * 演示数据量级配置
 *
 * 对应 docs/烟踪智治-文档缺陷与修订说明.md 的缺陷 C2：
 * 设计稿写「在线设备 3,842 / 今日违规 1,286」，与 PRD 声明的
 * 「校园试点（2-4 路摄像头）」严重不符，评审现场极易被质疑。
 *
 * 因此这里把量级抽成可切换的两档：
 *   - design : 完全沿用设计稿数值，保证视觉与已验收设计稿一致（默认）
 *   - pilot  : 与 2-4 路摄像头试点规模匹配，答辩讲解时切换，数据可信
 *
 * 切换入口见「系统管理 → 全平台基础配置（页面 17）」。
 */

export type ScaleMode = 'design' | 'pilot'

export interface ScalePreset {
  key: ScaleMode
  label: string
  desc: string
  /** 四个指标卡数值 */
  todayViolations: number
  processingEvents: number
  onlineDevices: number
  onlineStaff: number
  /** 同比变化（百分数，正数为上升） */
  todayViolationsDelta: number
  processingEventsDelta: number
  onlineDevicesDelta: number
  onlineStaffDelta: number
  /** 近 7 日趋势的两条曲线（识别事件 / 已处置事件），取值对齐设计稿图形 */
  trendDetected: number[]
  trendHandled: number[]
  trendMax: number
  /** 生成的事件条数（列表用） */
  eventCount: number
  /** 近 7 天违规总次数（用于决策规则的分子） */
  recentCount: number
  /** 近 30 天日均基线（用于决策规则的分母） */
  baselineDaily: number
  /** 工单相关 */
  workorderTotal: number
  workorderCompletionRate: number
  avgResponseMin: number
}

export const SCALE_PRESETS: Record<ScaleMode, ScalePreset> = {
  design: {
    key: 'design',
    label: '设计稿量级',
    desc: '沿用现有设计稿数值，视觉与已验收页面一致',
    todayViolations: 1286,
    processingEvents: 118,
    onlineDevices: 3842,
    onlineStaff: 684,
    todayViolationsDelta: -12.5,
    processingEventsDelta: -8.3,
    onlineDevicesDelta: 6.7,
    onlineStaffDelta: 4.1,
    trendDetected: [400, 470, 500, 640, 570, 630, 590],
    trendHandled: [210, 255, 300, 410, 330, 390, 340],
    trendMax: 800,
    eventCount: 48,
    recentCount: 1240,
    baselineDaily: 152.0,
    workorderTotal: 1186,
    workorderCompletionRate: 92.4,
    avgResponseMin: 18.6
  },
  pilot: {
    key: 'pilot',
    label: '试点实测量级',
    desc: '与 2-4 路摄像头校园试点规模匹配，答辩讲解用',
    todayViolations: 27,
    processingEvents: 3,
    onlineDevices: 4,
    onlineStaff: 6,
    todayViolationsDelta: -11.2,
    processingEventsDelta: -25.0,
    onlineDevicesDelta: 0,
    onlineStaffDelta: 0,
    trendDetected: [8, 10, 11, 13, 12, 13, 12],
    trendHandled: [4, 5, 6, 8, 7, 8, 7],
    trendMax: 16,
    eventCount: 28,
    recentCount: 31,
    baselineDaily: 3.4,
    workorderTotal: 27,
    workorderCompletionRate: 88.9,
    avgResponseMin: 14.2
  }
}

export function getScale(mode: ScaleMode): ScalePreset {
  return SCALE_PRESETS[mode] ?? SCALE_PRESETS.design
}

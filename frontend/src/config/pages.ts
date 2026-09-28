/**
 * 页面与导航注册表
 *
 * 全站唯一的数据源：路由、顶栏下拉、二级菜单、侧边栏均从此处生成。
 * `no` 字段对应 smoke-admin/ 下设计稿的页号（1..18），用于与设计稿对照。
 * `icon` 为 @element-plus/icons-vue 的组件名（已在 main.ts 全局注册）。
 *
 * 模块结构沿用 smoke-admin/README.md「三、导航体系」的 7 模块划分。
 */

export interface PageDef {
  /** 设计稿页号 1..18 */
  no: number
  /** 路由名（唯一） */
  name: string
  /** 路由路径（不含前导斜杠，login 除外） */
  path: string
  /** 页面标题 */
  title: string
  /** 下拉菜单中的短标题 */
  short: string
  /** Element Plus 图标组件名 */
  icon: string
  /** 是否已迁移到 Vue3（false 的走占位页） */
  migrated: boolean
  /** 说明（占位页展示） */
  note?: string
}

export interface ModuleDef {
  key: string
  label: string
  icon: string
  pages: PageDef[]
}

export const MODULES: ModuleDef[] = [
  {
    key: 'situation',
    label: '态势总览',
    icon: 'Odometer',
    pages: [
      {
        no: 2,
        name: 'overview',
        path: 'overview',
        title: '项目总览首页',
        short: '事件总览',
        icon: 'Odometer',
        migrated: true
      },
      {
        no: 3,
        name: 'governance',
        path: 'governance',
        title: '治理态势 · 未闭环预警',
        short: '治理态势',
        icon: 'Warning',
        migrated: true,
        note: '未闭环事件列表 + 超时升级链路'
      },
      {
        no: 4,
        name: 'device-status',
        path: 'device-status',
        title: '设备运行地图',
        short: '设备状态',
        icon: 'VideoCamera',
        migrated: true,
        note: '摄像头点位层 + 在线率；预留 MCP 地图挂载点'
      },
      {
        no: 5,
        name: 'workboard',
        path: 'workboard',
        title: '区域任务分布地图',
        short: '工作看板',
        icon: 'Grid',
        migrated: true,
        note: '区域任务分布 + 执行路线；预留 MCP 地图挂载点'
      }
    ]
  },
  {
    key: 'events',
    label: '事件中心',
    icon: 'Bell',
    pages: [
      {
        no: 6,
        name: 'alerts',
        path: 'alerts',
        title: '告警数据列表',
        short: '告警中心',
        icon: 'Bell',
        migrated: true,
        note: '违规事件分页表 + 三帧证据缩略图 + 轨迹回放'
      },
      {
        no: 7,
        name: 'report',
        path: 'report',
        title: '事件报表',
        short: '事件报表',
        icon: 'Histogram',
        migrated: true,
        note: '区域事件对比 + 违规类型分布（设计稿为贴图，需换成可交互图表）'
      }
    ]
  },
  {
    key: 'dispatch',
    label: '调度中心',
    icon: 'Tickets',
    pages: [
      {
        no: 8,
        name: 'dispatch-pool',
        path: 'dispatch-pool',
        title: '调度中心任务池',
        short: '任务池',
        icon: 'Tickets',
        migrated: true,
        note: '工单池 + 派发/改派 + 超时升级'
      },
      {
        no: 9,
        name: 'dispatch-records',
        path: 'dispatch-records',
        title: '调度记录管理',
        short: '调度记录',
        icon: 'List',
        migrated: true,
        note: '历史工单 + 响应时长统计'
      }
    ]
  },
  {
    /**
     * 执法协同：原「交警端」并入管理端后的模块。
     * 这两页没有对应的设计稿页号（设计稿只到 18 页），`no` 从 19 起排，
     * 仅用于菜单排序，不与 smoke-admin/ 的页号对照。
     */
    key: 'law',
    label: '执法协同',
    icon: 'Stamp',
    pages: [
      {
        no: 19,
        name: 'law-cases',
        path: 'law-cases',
        title: '执法线索核查',
        short: '线索核查',
        icon: 'Stamp',
        migrated: true,
        note: '已复核线索的核查、认领与处置；不展示举报人实名'
      },
      {
        no: 20,
        name: 'law-trail',
        path: 'law-trail',
        title: '处置结果与留痕',
        short: '处置留痕',
        icon: 'Finished',
        migrated: true,
        note: '只读留痕：执法协同侧的认领 / 退回 / 驳回 / 处置完成'
      }
    ]
  },
  {
    key: 'map',
    label: '全域地图',
    icon: 'MapLocation',
    pages: [
      {
        no: 10,
        name: 'gis',
        path: 'gis',
        title: '全域治理 GIS 地图',
        short: 'GIS 地图',
        icon: 'MapLocation',
        migrated: true,
        note: '热力图层挂载点 .map-art；预留 MCP 地图接入'
      }
    ]
  },
  {
    key: 'resource',
    label: '资源管理',
    icon: 'Box',
    pages: [
      {
        no: 11,
        name: 'device-archive',
        path: 'device-archive',
        title: '设备档案管理',
        short: '设备资源',
        icon: 'Monitor',
        migrated: true,
        note: '摄像头 CRUD + RTSP 配置 + ROI 绘制'
      },
      {
        no: 12,
        name: 'sanitation',
        path: 'sanitation',
        title: '环卫资源管理',
        short: '环卫资源',
        icon: 'Van',
        migrated: true,
        note: '人员/车辆档案 + 排班'
      }
    ]
  },
  {
    key: 'ai',
    label: 'AI治理',
    icon: 'Cpu',
    pages: [
      {
        no: 13,
        name: 'ai-model',
        path: 'ai-model',
        title: '模型与数据集管理',
        short: '模型与数据集',
        icon: 'Cpu',
        migrated: true,
        note: '模型版本 + 数据集 + 指标看板；预留 Agent 问答位'
      },
      {
        no: 14,
        name: 'ai-config',
        path: 'ai-config',
        title: 'AI 阈值配置',
        short: 'AI 识别配置',
        icon: 'Operation',
        migrated: true,
        note: '状态机阈值 / ROI / 图像增强开关；对应修订后的 /api/ai/config'
      },
      {
        no: 15,
        name: 'analysis',
        path: 'analysis',
        title: '数据分析',
        short: '数据分析',
        icon: 'DataAnalysis',
        migrated: true,
        note: '时段潮汐 + 治理效果对比 + 调度建议卡片'
      }
    ]
  },
  {
    key: 'system',
    label: '系统管理',
    icon: 'Setting',
    pages: [
      {
        no: 16,
        name: 'users',
        path: 'users',
        title: '用户账号管理',
        short: '权限与账号',
        icon: 'User',
        migrated: true,
        note: 'RBAC 角色矩阵（admin / manager / worker / ai_dev）'
      },
      {
        no: 17,
        name: 'platform-config',
        path: 'platform-config',
        title: '全平台基础配置',
        short: '系统配置',
        icon: 'Setting',
        migrated: true,
        note: '演示数据量级开关（对应修订说明 C2）+ 阈值与倍数参数'
      },
      {
        no: 18,
        name: 'audit',
        path: 'audit',
        title: '审计日志',
        short: '审计日志',
        icon: 'Document',
        migrated: true,
        note: '写操作审计追溯'
      }
    ]
  }
]

/** 扁平化的页面列表项（在 PageDef 基础上带出所属模块） */
export interface PageRouteDef extends PageDef {
  moduleKey: string
  moduleLabel: string
}

/** 扁平化的页面列表，按设计稿页号升序 */
export const ALL_PAGES: PageRouteDef[] = (
  MODULES.flatMap((m) =>
    m.pages.map((p) => ({ ...p, moduleKey: m.key, moduleLabel: m.label }))
  ) as PageRouteDef[]
).sort((a, b) => a.no - b.no)

/** 根据设计稿页号取所在模块 */
export function findModuleByPageNo(no: number): ModuleDef | undefined {
  return MODULES.find((m) => m.pages.some((p) => p.no === no))
}

/** 根据路由名取页面定义 */
export function findPageByName(name: string): PageDef | undefined {
  return ALL_PAGES.find((p) => p.name === name)
}

/** 系统名称 */
export const APP_NAME = '烟踪智治'
export const APP_SUBTITLE = 'AI 烟头乱扔智能识别与环卫调度平台'

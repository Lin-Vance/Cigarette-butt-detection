import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import type { Component } from 'vue'
import { ALL_PAGES } from '@/config/pages'
import { useAuthStore } from '@/stores/auth'
import { useCitizenStore } from '@/stores/citizen'

import AdminLayout from '@/layouts/AdminLayout.vue'
import PortalView from '@/views/PortalView.vue'
import AuthView from '@/views/AuthView.vue'
import CitizenLoginView from '@/views/CitizenLoginView.vue'
import CitizenAppView from '@/views/CitizenAppView.vue'
import WorkerAppView from '@/views/WorkerAppView.vue'
import PagePlaceholder from '@/views/PagePlaceholder.vue'

/** 已迁移到 Vue3 的页面（18 页全部迁移完成） */
const MIGRATED_VIEWS: Record<string, () => Promise<{ default: Component }>> = {
  overview: () => import('@/views/OverviewView.vue'),
  'monitor-wall': () => import('@/views/MonitorWallView.vue'),
  governance: () => import('@/views/GovernanceView.vue'),
  'device-status': () => import('@/views/DeviceStatusView.vue'),
  workboard: () => import('@/views/WorkboardView.vue'),
  alerts: () => import('@/views/AlertsView.vue'),
  report: () => import('@/views/ReportView.vue'),
  'dispatch-pool': () => import('@/views/DispatchPoolView.vue'),
  'dispatch-records': () => import('@/views/DispatchRecordsView.vue'),
  gis: () => import('@/views/GisView.vue'),
  'device-archive': () => import('@/views/DeviceArchiveView.vue'),
  sanitation: () => import('@/views/SanitationView.vue'),
  'ai-model': () => import('@/views/AiModelView.vue'),
  'ai-config': () => import('@/views/AiConfigView.vue'),
  analysis: () => import('@/views/AnalysisView.vue'),
  users: () => import('@/views/UsersView.vue'),
  'law-cases': () => import('@/views/LawCasesView.vue'),
  'law-trail': () => import('@/views/LawTrailView.vue'),
  'platform-config': () => import('@/views/PlatformConfigView.vue'),
  audit: () => import('@/views/AuditView.vue')
}

/** 路由名 → 路由路径。越权兜底时靠它找「该角色真正可达的第一个页面」。 */
const PAGE_PATH_BY_NAME: Record<string, string> = Object.fromEntries(
  ALL_PAGES.map((page) => [page.name, `/platform/${page.path}`])
)

/**
 * 端首页。五个 HTML 共用同一份路由代码，靠 `<html data-end="…">` 分辨当前在哪一端，
 * 这样未知路由（catch-all）会回落到**本端**的默认页，而不是一律跳官网首页（缺陷 D-12）。
 */
const END_HOME: Record<string, string> = {
  index: '/',
  auth: '/auth',
  citizen: '/citizen',
  worker: '/worker',
  admin: '/platform/overview'
}

/** 角色 → 该角色自己的端页面。用于「兜底也兜不住」时的真实换端。 */
const END_BY_ROLE: Record<string, string> = {
  admin: './admin.html',
  manager: './admin.html',
  ai_dev: './admin.html',
  worker: './worker.html'
}

const CURRENT_END =
  (typeof document !== 'undefined' && document.documentElement.dataset.end) || 'index'

// CSP 禁止 HTML 内联脚本；因此由受构建管线管理的模块代码设置各端默认路由。
// 这也保证直接访问 auth.html / citizen.html / worker.html / admin.html 时不会误落到官网首页。
if (typeof window !== 'undefined' && !window.location.hash) {
  window.location.hash = `#${END_HOME[CURRENT_END] ?? '/'}`
}

const childRoutes: RouteRecordRaw[] = ALL_PAGES.map((page) => {
  const loader = MIGRATED_VIEWS[page.name]
  return {
    path: page.path,
    name: page.name,
    component: loader ?? PagePlaceholder,
    meta: {
      pageNo: page.no,
      title: page.title,
      short: page.short,
      icon: page.icon,
      module: page.moduleLabel,
      note: page.note ?? ''
    }
  } as RouteRecordRaw
})

const routes: RouteRecordRaw[] = [
  {
    // 入口页（index.html）：5 屏长滚动叙事，含各端真实页面跳转
    path: '/',
    name: 'portal',
    component: PortalView,
    meta: { public: true, title: '烟踪智治' }
  },
  {
    // 登录 / 注册页（auth.html）
    path: '/auth',
    name: 'auth',
    component: AuthView,
    meta: { public: true, title: '登录 · 注册' }
  },
  {
    // 环卫工人端（worker.html），登录在这一端内部完成
    path: '/worker',
    name: 'worker',
    component: WorkerAppView,
    meta: { public: true, title: '环卫工人端' }
  },
  {
    path: '/citizen-login',
    name: 'citizen-login',
    component: CitizenLoginView,
    meta: { public: true, title: '市民登录' }
  },
  {
    path: '/citizen',
    name: 'citizen',
    component: CitizenAppView,
    meta: { citizenAuth: true, title: '市民用户端' }
  },
  {
    // 旧版管理员专用登录页已取消。历史链接统一换到三端共用登录页，
    // 自动选中“管理端”，并保留原本想访问的管理页面。
    path: '/login',
    name: 'login',
    component: AuthView,
    beforeEnter: (to) => {
      const target = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/platform/')
        ? to.query.redirect
        : '/platform/overview'
      window.location.replace(`./auth.html#/auth?role=admin&redirect=${encodeURIComponent(target)}`)
      return false
    },
    meta: { public: true, title: '管理员登录' }
  },
  {
    path: '/platform',
    component: AdminLayout,
    redirect: '/platform/overview',
    children: childRoutes
  },
  {
    // 未知路由回落到**当前端**的默认页（缺陷 D-12）：
    // 以前固定 redirect '/'，导致在 admin.html 里访问 #/not-exist 会渲染出官网入口页。
    path: '/:pathMatch(.*)*',
    redirect: () => END_HOME[CURRENT_END] ?? '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const citizen = useCitizenStore()

  // 开发期直达：任意页面带 ?autologin=1 即以管理员身份进入，
  // 便于本地截图、录制与答辩演示时一键跳到指定页面。生产构建不生效。
  if (import.meta.env.DEV && to.query.autologin === '1' && !auth.isLoggedIn) {
    // 环卫端用工号身份，其余端用管理员，避免演示时角色错位
    await auth.login(to.name === 'worker' ? 'worker01' : 'admin', '123456')
  }
  if (import.meta.env.DEV && to.query.autologin === 'citizen' && !citizen.isLoggedIn) {
    // 本地回归直达使用演示账户密码；短信验证码是动态、一次性的，不能写死在代码中。
    await citizen.login('13800000000', '123456', 'password')
  }

  if (to.meta.citizenAuth) {
    // App 模式允许先浏览首页/地图/科普，真正提交或查看个人数据时再弹登录。
    if (!citizen.isLoggedIn && to.query.app !== '1') return { name: 'citizen-login', query: { redirect: to.fullPath } }
    return true
  }

  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') return { path: '/platform/overview' }
    if (citizen.isLoggedIn && to.name === 'citizen-login') return { path: '/citizen' }
    return true
  }

  if (!auth.isLoggedIn) {
    // 管理端不再保留第二套登录页，失效/未登录一律进入统一登录注册页面。
    const target = to.fullPath.startsWith('/platform/') ? to.fullPath : '/platform/overview'
    window.location.replace(`./auth.html#/auth?role=admin&redirect=${encodeURIComponent(target)}`)
    return false
  }

  const name = String(to.name ?? '')
  if (name && !auth.allowedPageNames.includes(name)) {
    // 越权兜底必须落到**该角色真正可达**的页面。
    // 以前固定返回 { path: '/platform/overview' }，而 worker 角色的允许列表只有
    // ['dispatch-pool','dispatch-records'] —— 兜底目标同样越权，于是形成无限重定向，
    // 整页白屏并抛 "Infinite redirect in navigation guard"（缺陷 D-02）。
    const allowed = auth.allowedPageNames
    const fallbackPath = allowed.length ? PAGE_PATH_BY_NAME[allowed[0]] : ''
    if (fallbackPath && fallbackPath !== to.path) return { path: fallbackPath }

    // 兜底也兜不住（该角色在管理端一个页面都没有）：换端回自己的端。
    // 注意**不能**返回 { name: 'login' }——已登录时 login 会被上面的 public 分支
    // 立刻反弹回 /platform/overview，仍是死循环。
    window.location.replace(END_BY_ROLE[auth.user?.role ?? ''] ?? './index.html')
    return false
  }

  return true
})

/**
 * 守卫/组件加载异常时的可见兜底：绝不留白屏（缺陷 D-02 的连带诉求）。
 * 只在自己没渲染出任何内容时才接管，避免覆盖正常页面。
 */
router.onError((err) => {
  console.error('[router] 导航异常：', err)
  const mount = document.getElementById('app')
  if (!mount || mount.innerHTML.trim().length > 0) return
  mount.innerHTML =
    '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;' +
    'gap:12px;height:100%;font-family:\'Microsoft YaHei\',sans-serif;color:#31414f;text-align:center">' +
    '<h2 style="margin:0;font-size:18px">页面加载未完成</h2>' +
    '<p style="margin:0;font-size:13px;color:#7d8999">可能是资源未加载完整，请刷新重试；' +
    '若持续出现请检查前端服务是否正常。</p>' +
    '<a href="./index.html" style="font-size:13px;color:#216eff">返回入口页</a>' +
    '</div>'
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || ''
  document.title = title ? `${title} · 烟踪智治` : '烟踪智治'
})

export default router

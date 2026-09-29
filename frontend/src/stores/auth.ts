import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ALL_PAGES } from '@/config/pages'
import { USE_API, backendReachable, setAdminToken, toFailure } from '@/api/client'
import * as api from '@/api/endpoints'

export type Role = 'admin' | 'manager' | 'worker' | 'ai_dev'

export interface CurrentUser {
  username: string
  realName: string
  role: Role
  avatar: string
}

const STORAGE_KEY = 'yz.auth'
const AVATAR = '/media/avatars/supervisor.png'

/**
 * 登录态有效期，与后端 `expires_in = 7200`（2 小时）对齐（缺陷 D-17）。
 * 以前 `restore()` 从不校验 `loginAt`，token 过期后界面依旧当作已登录。
 */
const SESSION_TTL_MS = 2 * 60 * 60 * 1000

/**
 * 演示账号。与后端 backend/app/seed.py 的 SEED_USERS 保持同一套账号，
 * 这样「本地模拟」与「已连接后端」两种模式下都能演示多角色权限差异。
 */
const DEMO_ACCOUNTS: Record<string, { password: string; user: CurrentUser }> = {
  admin: {
    password: '123456',
    user: { username: 'admin', realName: '超级管理员', role: 'admin', avatar: AVATAR }
  },
  manager: {
    password: '123456',
    user: { username: 'manager', realName: '后勤管理员', role: 'manager', avatar: AVATAR }
  },
  worker01: {
    password: '123456',
    user: { username: 'worker01', realName: '张建国', role: 'worker', avatar: AVATAR }
  },
  aidev: {
    password: '123456',
    user: { username: 'aidev', realName: 'AI 开发人员', role: 'ai_dev', avatar: AVATAR }
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const user = ref<CurrentUser | null>(null)
  const loginAt = ref<number>(0)
  /** 后端下发的页面权限；仅在 API 模式下非空 */
  const apiPages = ref<string[]>([])

  const isLoggedIn = computed(() => !!token.value)
  const roleLabel = computed(() => {
    const map: Record<Role, string> = {
      admin: '超级管理员',
      manager: '管理人员',
      worker: '环卫工人',
      ai_dev: 'AI 开发人员'
    }
    return user.value ? map[user.value.role] : ''
  })

  /**
   * 执法协同是本轮由「交警端」并入的前端模块，后端 RBAC 矩阵尚未同步这两个页面名。
   * 这里显式并入，避免开启 VITE_USE_API 后管理员被路由守卫挡在门外。
   */
  const LAW_PAGES = ['law-cases', 'law-trail']

  /** 可用页面。API 模式下以**后端下发**为准（真正的 RBAC），否则用本地矩阵。 */
  const allowedPageNames = computed<string[]>(() => {
    if (USE_API && apiPages.value.length) {
      if (apiPages.value.includes('*')) return ALL_PAGES.map((p) => p.name)
      return Array.from(new Set([...apiPages.value, ...LAW_PAGES]))
    }

    const r = user.value?.role ?? 'admin'
    if (r === 'admin') return ALL_PAGES.map((p) => p.name)
    if (r === 'manager') {
      return ALL_PAGES.filter((p) =>
        [
          'overview',
          'governance',
          'device-status',
          'workboard',
          'alerts',
          'report',
          'dispatch-pool',
          'dispatch-records',
          'gis',
          'analysis',
          ...LAW_PAGES
        ].includes(p.name)
      ).map((p) => p.name)
    }
    if (r === 'worker') return ['dispatch-pool', 'dispatch-records']
    return ALL_PAGES.filter((p) =>
      ['overview', 'alerts', 'ai-model', 'ai-config', 'analysis'].includes(p.name)
    ).map((p) => p.name)
  })

  function restore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      // 时效校验（缺陷 D-17）：过期即当作未登录，避免拿一个早就失效的 token 去请求。
      const at = Number(parsed.loginAt) || 0
      if (at && Date.now() - at > SESSION_TTL_MS) {
        localStorage.removeItem(STORAGE_KEY)
        return
      }
      token.value = parsed.token ?? ''
      user.value = parsed.user ?? null
      loginAt.value = at
      apiPages.value = parsed.apiPages ?? []
      setAdminToken(token.value)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function persist() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        token: token.value,
        user: user.value,
        loginAt: loginAt.value,
        apiPages: apiPages.value
      })
    )
  }

  /**
   * 本地演示账号校验。与 `DEMO_ACCOUNTS` 同一套账号，供两种场景使用：
   * 未开启 API 模式、以及 API 模式下后端不可达时的降级。
   */
  function localLogin(username: string, password: string): { ok: boolean; message: string } {
    const account = DEMO_ACCOUNTS[username.trim()]
    if (!account) return { ok: false, message: '账号不存在' }
    if (account.password !== password) return { ok: false, message: '密码错误' }
    token.value = `demo-token-${Date.now()}`
    user.value = { ...account.user }
    apiPages.value = []
    loginAt.value = Date.now()
    persist()
    return { ok: true, message: '登录成功' }
  }

  /**
   * 登录。
   * - `VITE_USE_API=1`：POST /api/v1/auth/login，权限以后端下发为准
   * - 否则：本地模拟校验（无后端也能演示）
   */
  async function login(username: string, password: string): Promise<{ ok: boolean; message: string }> {
    if (USE_API) {
      // 先探一次后端（≤1.2s）。不可达就直接走本地演示账号，
      // 不能让它挂到 axios 的 15 秒超时——那会让深链页面空白十几秒（D-22）。
      if (!(await backendReachable())) {
        const fb = localLogin(username, password)
        return fb.ok
          ? { ok: true, message: '登录成功（后端未连接 · 本地模拟）' }
          : { ok: false, message: `${fb.message}（后端未连接，本地演示账号校验未通过）` }
      }
      try {
        const res = await api.login(username.trim(), password)
        token.value = res.access_token
        user.value = {
          username: res.user.username,
          realName: res.user.real_name || res.user.username,
          role: res.user.role,
          avatar: AVATAR
        }
        apiPages.value = res.user.allowed_pages
        loginAt.value = Date.now()
        setAdminToken(res.access_token)
        persist()
        return { ok: true, message: '登录成功' }
      } catch (err) {
        const f = toFailure(err)
        // 兜底：请求过程中后端掉线（status 0）时同样降级到本地演示账号；
        // 后端在线但明确拒绝（401/403/5xx）一律如实报错，不掩盖问题。
        if (f.status === 0) {
          const fb = localLogin(username, password)
          if (fb.ok) return { ok: true, message: '登录成功（后端未连接 · 本地模拟）' }
          return { ok: false, message: `${f.message}；本地演示账号校验也未通过（${fb.message}）` }
        }
        return { ok: false, message: f.message }
      }
    }

    return localLogin(username, password)
  }

  async function loginByCode(username: string, code: string, role: 'worker' | 'admin'): Promise<{ ok: boolean; message: string }> {
    if (!USE_API) return { ok: false, message: '验证码登录需要连接后端服务' }
    try {
      const res = await api.loginByCode(username.trim(), code, role)
      token.value = res.access_token
      user.value = { username: res.user.username, realName: res.user.real_name || res.user.username, role: res.user.role, avatar: AVATAR }
      apiPages.value = res.user.allowed_pages
      loginAt.value = Date.now()
      setAdminToken(res.access_token)
      persist()
      return { ok: true, message: '验证码登录成功' }
    } catch (err) {
      return { ok: false, message: toFailure(err).message }
    }
  }

  function logout() {
    if (USE_API && token.value) {
      // 让后端留下退出审计；失败不阻塞前端登出
      void api.logout().catch(() => undefined)
    }
    token.value = ''
    user.value = null
    apiPages.value = []
    loginAt.value = 0
    setAdminToken('')
    localStorage.removeItem(STORAGE_KEY)
  }

  restore()

  return { token, user, loginAt, apiPages, isLoggedIn, roleLabel, allowedPageNames, login, loginByCode, logout, restore }
})

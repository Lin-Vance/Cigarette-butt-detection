/**
 * 后端 API 客户端。
 *
 * **默认关闭**（`VITE_USE_API` 未设为 1 时，全部业务仍走本地模拟数据），
 * 这样交付物在没有后端的环境里也能完整演示；打开开关后，
 * 登录、事件、工单、上报等状态改由后端提供，三端读同一份数据。
 *
 * 接口契约与运行方式见 backend/README.md。
 */
import axios, { AxiosError } from 'axios'

export const USE_API = import.meta.env.VITE_USE_API === '1'
export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export interface ApiFailure {
  code: string
  message: string
  status: number
}

/** 令牌由 store 写入。管理员令牌与市民令牌分开存放，避免混用。 */
let adminToken = ''
let citizenToken = ''

export function setAdminToken(token: string): void {
  adminToken = token
}

export function setCitizenToken(token: string): void {
  citizenToken = token
}

/**
 * 是否已持有管理员令牌。
 *
 * 用途：数据仓库在**未登录**时不要去打受保护的业务接口。
 * 入口页（`PortalView`）是纯叙事页，同样会调 `demo.init()`，
 * 以前会在匿名状态下打出 6 个 401（`/cameras`、`/events`…），
 * 既是无效请求，也会污染资源巡检结果。
 */
export function hasAdminToken(): boolean {
  return Boolean(adminToken)
}

/**
 * 后端可达性探测（短超时 + 结果缓存）。
 *
 * **为什么需要它**（2026-09-28 复核新发现 D-22）：
 * `VITE_USE_API=1` 但后端没启动时，Vite 代理会**挂起或回 5xx**，
 * 于是 `auth.login()` 要一路等到 axios 的 15 秒超时；
 * 而 `#/platform/overview?autologin=1` 这类深链会在路由守卫里 `await` 这次登录，
 * 结果是**整页空白最多 15 秒**；同时 `toFailure` 拿到的是 5xx（不是 status 0），
 * 导致"后端连不上就回退本地演示"的降级逻辑根本不触发。
 *
 * 做法：探测后端自己的 `/healthz`（已在 `vite.config.ts` 里代理），
 * 1.2 秒超时；**并校验响应确实是 JSON**（防止被 SPA fallback 的 HTML 骗过）；
 * 结果缓存 5 秒，避免每次请求都探一遍。
 */
let reachable: boolean | null = null
let reachableAt = 0
const REACHABLE_TTL_MS = 5000

export async function backendReachable(force = false): Promise<boolean> {
  if (!USE_API) return false
  if (!force && reachable !== null && Date.now() - reachableAt < REACHABLE_TTL_MS) {
    return reachable
  }
  try {
    const res = await axios.get('/healthz', { timeout: 1200 })
    const ct = String(res.headers?.['content-type'] ?? '')
    reachable = res.status === 200 && ct.includes('json')
  } catch {
    reachable = false
  }
  reachableAt = Date.now()
  return reachable
}

export const http = axios.create({ baseURL: API_BASE, timeout: 15000 })

http.interceptors.request.use((config) => {
  const url = config.url || ''
  // 市民端接口固定挂在 /citizen/* 下，其余用管理员令牌；/public/* 不需要令牌
  const token = url.startsWith('/citizen') ? citizenToken : adminToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * HTTP 状态码 → 中文字案。
 *
 * 缺陷 D-10：后端在 CORS 拦截、网关异常等场景返回的是**纯文本**
 * （例如 `Invalid CORS request`），没有 `error_code` 字段，
 * 于是旧实现落到 `SYS_HTTP_ERROR` 直接把 axios 的英文 message 抛到界面上，
 * 登录页会显示 `Request failed with status code 403`。
 * 这里按状态码给中文兜底，原始英文只进 console。
 */
const STATUS_TEXT: Record<number, string> = {
  400: '请求参数有误，请检查后重试',
  401: '账号或密码错误，或登录状态已失效',
  403: '无权限或被服务端拒绝（开发环境常见于后端 CORS 白名单未放行当前端口）',
  404: '接口不存在，请确认后端版本与前端一致',
  405: '请求方式不被允许',
  409: '数据状态冲突，请刷新后重试',
  422: '提交的数据未通过校验',
  429: '操作过于频繁，请稍后再试',
  500: '服务端异常，请查看后端日志',
  502: '网关异常，后端可能未启动',
  503: '服务暂不可用，请稍后重试',
  504: '后端响应超时'
}

/** 把 axios 错误统一成 { code, message, status }，页面只认这一种形态。 */
export function toFailure(err: unknown): ApiFailure {
  if (err instanceof AxiosError) {
    const status = err.response?.status ?? 0
    const data = err.response?.data as { error_code?: string; message?: string } | undefined
    if (data?.error_code) {
      return { code: data.error_code, message: data.message || '请求失败', status }
    }
    if (err.code === 'ECONNABORTED') {
      return { code: 'NETWORK_TIMEOUT', message: '请求超时，请检查后端服务是否已启动', status }
    }
    if (status === 0) {
      return {
        code: 'NETWORK_UNREACHABLE',
        message: '无法连接后端服务（请确认 Spring Boot 已在 127.0.0.1:8080 启动）',
        status
      }
    }
    // 原始英文只留给开发者看，界面上一律中文
    console.warn(`[api] HTTP ${status} ${err.config?.url ?? ''}：${err.message}`)
    return {
      code: 'SYS_HTTP_ERROR',
      message: STATUS_TEXT[status] ?? `请求失败（HTTP ${status}）`,
      status
    }
  }
  return { code: 'SYS_UNKNOWN', message: String(err), status: 0 }
}

export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await http.get<T>(url, { params })
  return data
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await http.post<T>(url, body ?? {})
  return data
}

export async function apiForm<T>(url: string, form: FormData): Promise<T> {
  const { data } = await http.post<T>(url, form)
  return data
}

export async function apiPatch<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await http.patch<T>(url, body ?? {})
  return data
}

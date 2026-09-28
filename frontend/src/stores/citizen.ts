import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { USE_API, backendReachable, setCitizenToken, toFailure } from '@/api/client'
import * as api from '@/api/endpoints'
import type { CitizenReport, ReportSubmitPayload } from '@/api/endpoints'

const STORAGE_KEY = 'yz.citizen.auth'

export interface CitizenProfile {
  phone: string
  displayName: string
  district: string
  contribution: number
}

export const useCitizenStore = defineStore('citizen', () => {
  const token = ref('')
  const profile = ref<CitizenProfile | null>(null)

  /** 我的上报（API 模式下来自后端；本地模式下为空，页面用静态演示数据） */
  const reports = ref<CitizenReport[]>([])
  const backendOnline = ref(false)
  const lastError = ref('')
  const loadingReports = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value && profile.value))
  const apiMode = computed(() => USE_API)

  function restore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const data = JSON.parse(raw)
      token.value = data.token || ''
      profile.value = data.profile || null
      setCitizenToken(token.value)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: token.value, profile: profile.value }))
  }

  function localLogin(phone: string, code: string) {
    if (!/^1\d{10}$/.test(phone)) return { ok: false, message: '请输入正确的11位手机号' }
    if (code !== '123456') return { ok: false, message: '演示验证码为 123456' }
    token.value = `citizen-demo-${Date.now()}`
    profile.value = {
      phone,
      displayName: `市民 ${phone.slice(-4)}`,
      district: '浉河区',
      contribution: 36
    }
    setCitizenToken('')
    persist()
    return { ok: true, message: '登录成功' }
  }

  /**
   * 市民登录。
   * - `VITE_USE_API=1`：POST /auth/citizen/login，拿真实令牌
   * - 后端不可达时**回退本地演示登录**，保证断网也能演示
   */
  async function login(phone: string, code: string): Promise<{ ok: boolean; message: string }> {
    if (USE_API) {
      // 后端不可达时不要等 axios 超时，直接回退本地演示登录（D-22）
      if (!(await backendReachable())) {
        backendOnline.value = false
        return localLogin(phone, code)
      }
      try {
        const res = await api.citizenLogin(phone, code)
        token.value = res.access_token
        profile.value = res.profile
        setCitizenToken(res.access_token)
        backendOnline.value = true
        persist()
        return { ok: true, message: '登录成功' }
      } catch (err) {
        const failure = toFailure(err)
        if (failure.status !== 0) {
          return { ok: false, message: failure.message }
        }
        // 网络不可达 → 回退本地演示
        backendOnline.value = false
        lastError.value = failure.message
        return localLogin(phone, code)
      }
    }
    return localLogin(phone, code)
  }

  function logout() {
    token.value = ''
    profile.value = null
    reports.value = []
    setCitizenToken('')
    localStorage.removeItem(STORAGE_KEY)
  }

  /** 拉取「我的上报」。后端不可达时置空并记录错误，不抛异常。 */
  async function loadReports(): Promise<void> {
    if (!USE_API || !token.value) return
    loadingReports.value = true
    try {
      const res = await api.myReports()
      reports.value = res.items
      backendOnline.value = true
      lastError.value = ''
    } catch (err) {
      backendOnline.value = false
      lastError.value = toFailure(err).message
    } finally {
      loadingReports.value = false
    }
  }

  /** 提交线索。返回 { ok, report } —— report_no 用于成功页展示。 */
  async function submitReport(
    payload: ReportSubmitPayload
  ): Promise<{ ok: boolean; message: string; report?: CitizenReport }> {
    if (!USE_API) {
      return { ok: true, message: '本地演示模式：未真实上传', report: undefined }
    }
    try {
      const report = await api.submitCitizenReport(payload)
      reports.value.unshift(report)
      backendOnline.value = true
      return { ok: true, message: '提交成功', report }
    } catch (err) {
      const failure = toFailure(err)
      lastError.value = failure.message
      return { ok: false, message: failure.message }
    }
  }

  async function withdraw(reportNo: string): Promise<{ ok: boolean; message: string }> {
    if (!USE_API) return { ok: true, message: '本地演示模式' }
    try {
      const updated = await api.withdrawReport(reportNo)
      patch(updated)
      return { ok: true, message: '已撤回' }
    } catch (err) {
      const failure = toFailure(err)
      return { ok: false, message: failure.message }
    }
  }

  async function appeal(reportNo: string, description: string): Promise<{ ok: boolean; message: string }> {
    if (!USE_API) return { ok: true, message: '本地演示模式' }
    try {
      patch(await api.appealReport(reportNo, description))
      return { ok: true, message: '已提交申诉' }
    } catch (err) {
      const failure = toFailure(err)
      return { ok: false, message: failure.message }
    }
  }

  function patch(updated: CitizenReport) {
    const idx = reports.value.findIndex((r) => r.report_no === updated.report_no)
    if (idx >= 0) reports.value.splice(idx, 1, updated)
  }

  restore()

  return {
    token,
    profile,
    reports,
    backendOnline,
    apiMode,
    loadingReports,
    lastError,
    isLoggedIn,
    login,
    logout,
    restore,
    loadReports,
    submitReport,
    withdraw,
    appeal
  }
})

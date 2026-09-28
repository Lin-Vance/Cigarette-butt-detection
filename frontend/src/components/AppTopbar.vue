<script setup lang="ts">
/**
 * 全站顶栏
 *
 * 结构沿用 smoke-admin/README.md 的「yz-dd v4 悬浮卡片菜单」规范：
 * 点击钉住展开 / 悬停临时预览 / 当前页带「当前」徽标 / 内容区点击收起。
 * 坐标与尺寸取自 smoke-admin/2.png-html/styles.css 的 .topbar 系列规则。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MODULES } from '@/config/pages'
import { useAuthStore } from '@/stores/auth'
import { useDemoStore } from '@/stores/demo'
import { http, USE_API } from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const demo = useDemoStore()
const crossTotal = ref(0)
const crossFeed = ref<{ source: string; actor: string; detail: string; created_at: string }[]>([])
let syncTimer: number | undefined

async function refreshCrossEnd() {
  if (!USE_API) return
  try {
    const { data } = await http.get<{ total: number; latest: typeof crossFeed.value }>('/admin/activity/summary')
    const changed = crossTotal.value > 0 && data.total !== crossTotal.value
    crossTotal.value = data.total
    crossFeed.value = data.latest || []
    if (changed) await demo.reload()
  } catch {
    // 顶栏同步提示失败不阻断主页面，数据仓库仍会执行既有离线回退。
  }
}

onMounted(() => {
  void refreshCrossEnd()
  syncTimer = window.setInterval(refreshCrossEnd, 8000)
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (syncTimer) window.clearInterval(syncTimer)
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})

const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`)
/* ---------- 导航下拉 ---------- */
const navRef = ref<HTMLElement | null>(null)
const openKey = ref<string>('')
const pinned = ref(false)

const activeModuleKey = computed(() => {
  const cur = String(route.name ?? '')
  const hit = MODULES.find((m) => m.pages.some((p) => p.name === cur))
  return hit?.key ?? ''
})

function openPreview(key: string) {
  if (pinned.value) return
  openKey.value = key
}

function closePreview() {
  if (pinned.value) return
  openKey.value = ''
}

function togglePin(key: string) {
  if (openKey.value === key && pinned.value) {
    openKey.value = ''
    pinned.value = false
    return
  }
  openKey.value = key
  pinned.value = true
}

function closeNav() {
  openKey.value = ''
  pinned.value = false
}

function onDocClick(e: MouseEvent) {
  if (!openKey.value) return
  const nav = navRef.value
  if (nav && !nav.contains(e.target as Node)) closeNav()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closeNav()
    alertOpen.value = false
  }
}

/* ---------- 报警铃铛 ---------- */
const alertOpen = ref(false)
const unreadCount = computed(() => demo.alerts.filter((a) => !a.read).length)

function toggleAlerts() {
  alertOpen.value = !alertOpen.value
  if (alertOpen.value) {
    closeNav()
    demo.markAlertsRead()
  }
}

/* ---------- 演示控制 ---------- */
const simulating = ref(false)

async function onSimulate() {
  if (simulating.value) return
  simulating.value = true
  try {
    const ev = await demo.simulateViolation()
    if (!ev) {
      ElMessage({
        type: 'error',
        duration: 3200,
        message: demo.lastError ? `生成失败：${demo.lastError}` : '生成失败，请检查后端服务'
      })
      return
    }
    ElMessage({
      type: 'success',
      duration: 2600,
      message: `已模拟一次违规：${ev.camera_name} · 置信度 ${(ev.confidence * 100).toFixed(
        1
      )}% · 已自动生成清理工单`
    })
  } finally {
    simulating.value = false
  }
}

function onLogout() {
  auth.logout()
  location.href = './auth.html#/auth?role=admin'
}

function formatTime(ts: string) {
  const d = new Date(ts)
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}:${pad(d.getSeconds())}`
}
</script>

<template>
  <header class="topbar">
    <img class="brand-logo" src="/logo-horizontal.png" alt="烟踪智治" />

    <nav ref="navRef" class="main-nav" aria-label="主导航">
      <div
        v-for="m in MODULES"
        :key="m.key"
        class="nav-slot"
        @mouseenter="openPreview(m.key)"
        @mouseleave="closePreview"
      >
        <button
          class="nav-item"
          :class="{ active: activeModuleKey === m.key, opened: openKey === m.key }"
          type="button"
          @click="togglePin(m.key)"
        >
          {{ m.label }}
        </button>

        <transition name="yz-dd">
          <div v-if="openKey === m.key" class="dd-panel">
            <span class="dd-arrow" />
            <div class="dd-head">
              <i class="dd-dot" />
              <span>{{ m.label }}</span>
            </div>
            <ul class="dd-list">
              <li
                v-for="p in m.pages"
                :key="p.name"
                class="dd-item"
                :class="{ current: String(route.name) === p.name }"
                @click="
                  () => {
                    router.push({ name: p.name })
                    closeNav()
                  }
                "
              >
                <span class="dd-icon"><component :is="p.icon" /></span>
                <span class="dd-label">{{ p.short }}</span>
                <span v-if="String(route.name) === p.name" class="dd-badge">当前</span>
              </li>
            </ul>
          </div>
        </transition>
      </div>
    </nav>

    <div class="top-actions">
      <span class="sync-pill" :class="{ live: USE_API && demo.backendOnline }">
        <i />{{ USE_API ? `三端同步 ${crossTotal}` : '三端演示' }}
      </span>
      <button class="demo-btn" type="button" title="生成一条合规违规事件，驱动完整闭环" @click="onSimulate">
        <span class="demo-dot" />模拟一次违规
      </button>

      <div class="bell-wrap">
      <button class="bell" type="button" aria-label="实时报警" @click.stop="toggleAlerts">
        <svg viewBox="0 0 26 28" width="26" height="28" fill="none" stroke="#15243b" stroke-width="1.8">
          <path d="M6 20h14M7 18V11a6 6 0 0 1 12 0v7l2 2H5l2-2Z"></path>
          <path d="M11 24c.7 1 1.4 1.4 2 1.4s1.3-.4 2-1.4"></path>
        </svg>
        <i v-if="unreadCount" class="bell-dot"></i>
      </button>

      <transition name="yz-dd">
        <div v-if="alertOpen" class="alert-panel" @click.stop>
          <div class="dd-head">
            <i class="dd-dot" />
            <span>实时违规报警</span>
            <span class="alert-count">{{ demo.alerts.length }}</span>
          </div>
          <p class="mode-note" :class="{ live: demo.apiMode && demo.backendOnline }">
            {{
              demo.apiMode
                ? demo.backendOnline
                  ? '数据源：后端服务（状态已落库，刷新不丢失）'
                  : '数据源：本地模拟（已开启 API 模式但后端不可达，已自动回退）'
                : '数据源：本地模拟（未开启 VITE_USE_API）'
            }}
          </p>
          <div v-if="crossFeed.length" class="cross-feed">
            <strong>三端协同动态</strong>
            <p v-for="item in crossFeed.slice(0, 4)" :key="item.created_at + item.detail">
              <i>{{ item.source === 'citizen' ? '市' : item.source === 'worker' ? '环' : '管' }}</i>
              <span><b>{{ item.actor }}</b>{{ item.detail }}</span>
            </p>
          </div>
          <ul class="alert-list">
            <li v-for="a in demo.alerts.slice(0, 6)" :key="a.event_id" class="alert-item">
              <img class="alert-thumb" :src="a.thumbnail_url" alt="证据缩略图" />
              <div class="alert-body">
                <div class="alert-loc">{{ a.location_name }}</div>
                <div class="alert-meta">
                  {{ formatTime(a.timestamp) }} · 置信度 {{ (a.confidence * 100).toFixed(1) }}%
                </div>
              </div>
            </li>
            <li v-if="!demo.alerts.length" class="alert-empty">暂无报警</li>
          </ul>
          <button class="alert-more" type="button" @click="router.push({ name: 'alerts' }); alertOpen = false">
            查看全部告警数据 →
          </button>
        </div>
      </transition>
      </div>

      <img class="profile-avatar" :src="auth.user?.avatar" alt="用户头像" />
      <div class="profile-name">{{ auth.user?.realName ?? '未登录' }}</div>
      <button class="logout" type="button" @click="onLogout">退出</button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: absolute;
  left: 0;
  top: 0;
  width: 1672px;
  height: var(--yz-topbar-h);
  background: var(--yz-topbar-bg);
  border-bottom: 1px solid var(--yz-topbar-border);
  box-shadow: var(--yz-topbar-shadow);
  z-index: 20;
}

.brand-logo {
  position: absolute;
  left: 16px;
  top: 5px;
  width: 160px;
  height: 47px;
  object-fit: contain;
}

/* ---- 主导航 ---- */
.main-nav {
  position: absolute;
  left: 222px;
  top: 9px;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.nav-slot {
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
}
.nav-item {
  position: relative;
  height: 38px;
  min-width: 80px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #152039;
  font-size: 15px;
  background: transparent;
  border: 0;
  border-radius: var(--yz-radius-btn);
  white-space: nowrap;
  transition: color 0.15s, background 0.15s;
}
.nav-item:hover {
  color: var(--yz-primary);
}
.nav-item.opened,
.nav-item.active {
  color: var(--yz-primary);
  font-weight: 700;
  background: var(--yz-primary-soft);
}

/* ---- 悬浮卡片菜单（yz-dd v4） ---- */
.dd-panel {
  position: absolute;
  left: 0;
  top: 44px;
  min-width: 226px;
  padding: 6px;
  background: #fff;
  border: 1px solid var(--yz-border-faint);
  border-radius: var(--yz-radius-card);
  box-shadow: var(--yz-shadow-pop);
  z-index: 40;
}
.dd-arrow {
  position: absolute;
  left: 30px;
  top: -6px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-left: 1px solid var(--yz-border-faint);
  border-top: 1px solid var(--yz-border-faint);
  transform: rotate(45deg);
}
.dd-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px 9px;
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.6px;
  color: #8395ab;
  border-bottom: 1px solid #eef3f8;
}
.dd-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--yz-accent-cyan);
}
.dd-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dd-item {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--yz-text-strong);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.dd-item:hover {
  background: #f2f8fe;
  color: var(--yz-primary);
}
.dd-item.current {
  background: linear-gradient(100deg, #e6f4ff 0%, #eafaf3 100%);
  color: var(--yz-primary);
  font-weight: 700;
}
.dd-icon {
  display: inline-flex;
  width: 15px;
  height: 15px;
  color: currentColor;
  opacity: 0.85;
}
.dd-icon :deep(svg) {
  width: 15px;
  height: 15px;
}
.dd-label {
  flex: 1;
  white-space: nowrap;
}
.dd-badge {
  padding: 1px 6px;
  border-radius: var(--yz-radius-tag);
  background: var(--yz-primary);
  color: #fff;
  font-size: 10px;
  line-height: 16px;
  font-weight: 400;
}

/* ---- 演示按钮 ---- */
.demo-btn {
  position: static;
  height: 32px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #fff;
  background: var(--yz-primary-grad);
  border: 0;
  border-radius: var(--yz-radius-btn);
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 3px 5px rgba(55, 151, 224, 0.18);
}
.demo-btn:active {
  filter: brightness(0.96);
}
.demo-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #fff;
  animation: yz-pulse 1.6s ease-in-out infinite;
}
@keyframes yz-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.35;
    transform: scale(0.75);
  }
}

/* ---- 右侧信息：统一由 flex 排列，避免时间与身份区域互相挤压 ---- */
.top-actions {
  position: absolute;
  right: 16px;
  top: 0;
  height: var(--yz-topbar-h);
  display: flex;
  align-items: center;
  gap: 14px;
}
.sync-pill { display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 11px;border:1px solid #cdddea;border-radius:999px;color:#587089;background:#fff;font-size:11px;white-space:nowrap; }
.sync-pill i { width:7px;height:7px;border-radius:50%;background:#aab8c5; }
.sync-pill.live { color:#167a5d;border-color:#b7e3d2;background:#eefaf6; }
.sync-pill.live i { background:#24b47e;box-shadow:0 0 0 3px rgba(36,180,126,.13); }
.cross-feed { margin:0 0 6px;padding:8px 10px;border-radius:8px;background:#f4f9fd; }
.cross-feed > strong { display:block;margin-bottom:5px;color:#24384e;font-size:11px; }
.cross-feed p { display:flex;align-items:flex-start;gap:7px;margin:5px 0;color:#6f8092;font-size:10px;line-height:1.45; }
.cross-feed p i { display:grid;place-items:center;flex:0 0 20px;width:20px;height:20px;border-radius:6px;color:#fff;background:linear-gradient(135deg,#2586ef,#27bda0);font-style:normal;font-weight:700; }
.cross-feed p span { min-width:0; }
.cross-feed p b { margin-right:5px;color:#2a425b; }

.bell-wrap {
  position: relative;
}
.bell {
  position: relative;
  width: 26px;
  height: 28px;
  padding: 0;
  background: none;
  border: 0;
}
.bell-dot {
  position: absolute;
  right: 1px;
  top: -1px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--yz-danger-soft);
}

.alert-panel {
  position: absolute;
  right: -12px;
  top: 38px;
  width: 340px;
  padding: 6px;
  background: #fff;
  border: 1px solid var(--yz-border-faint);
  border-radius: var(--yz-radius-card);
  box-shadow: var(--yz-shadow-pop);
  z-index: 40;
}
.alert-count {
  margin-left: auto;
  color: var(--yz-primary);
}
/* 数据源提示：明确当前是后端数据还是本地模拟数据，避免演示时说不清 */
.mode-note {
  margin: 0 0 6px;
  padding: 5px 10px 6px;
  font-size: 10px;
  letter-spacing: 0.4px;
  color: #936213;
  background: #fdf6e6;
  border-left: 2px solid #d9a441;
}
.mode-note.live {
  color: #277454;
  background: #edf5f0;
  border-left-color: var(--yz-success, #2e9e6b);
}
.alert-list {
  max-height: 280px;
  overflow-y: auto;
}
.alert-item {
  display: flex;
  gap: 10px;
  padding: 8px 6px;
  border-bottom: 1px solid #f2f6fa;
}
.alert-item:last-child {
  border-bottom: 0;
}
.alert-thumb {
  width: 66px;
  height: 44px;
  flex: none;
  object-fit: cover;
  border-radius: 6px;
  background: #eef2f6;
}
.alert-body {
  min-width: 0;
}
.alert-loc {
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.alert-meta {
  margin-top: 3px;
  font-size: 11px;
  color: var(--yz-text-muted);
}
.alert-empty {
  padding: 18px 0;
  text-align: center;
  font-size: 12px;
  color: var(--yz-text-muted);
}
.alert-more {
  width: 100%;
  height: 30px;
  margin-top: 4px;
  background: #f5f9fd;
  border: 0;
  border-radius: 8px;
  color: var(--yz-primary);
  font-size: 12px;
}

.profile-avatar {
  position: static;
  width: 43px;
  height: 46px;
  object-fit: contain;
  border-radius: 50%;
  background: #eef3f8;
}
.profile-name {
  position: static;
  font-size: 14px;
  color: var(--yz-text-strong);
  white-space: nowrap;
}
.logout {
  position: static;
  width: 61px;
  height: 32px;
  color: var(--yz-text-body);
  background: #fff;
  border: 1px solid var(--yz-border-soft);
  border-radius: 5px;
  font-size: 13px;
}
.logout:hover {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}

/* ---- 下拉动画：自锚点缩放淡入 200ms ---- */
.yz-dd-enter-active {
  transition: opacity 0.2s cubic-bezier(0.22, 1, 0.36, 1), transform 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}
.yz-dd-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}
.yz-dd-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}
.yz-dd-leave-to {
  opacity: 0;
  transform: scale(0.98) translateY(-2px);
}
</style>

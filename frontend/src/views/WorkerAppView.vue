<script setup lang="ts">
/**
 * 环卫工人端（worker.html）。
 *
 * 外观与**管理端同一套**：EndShell 顶栏 + `.ad-*` 原子类 + YzStat / YzPanel / YzTable。
 * 职责单一：把派到手上的工单做完 —— 接单 → 现场处置 → 上传清理后照片 → 提交验收。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import EndShell from '@/layouts/EndShell.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzStat from '@/components/ui/YzStat.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import { useAuthStore } from '@/stores/auth'
import { useDemoStore } from '@/stores/demo'
import type { WorkOrder } from '@/mock/types'

const auth = useAuthStore()
const demo = useDemoStore()

const account = ref('worker01')
const password = ref('123456')
const logging = ref(false)
const loginError = ref('')

const tab = ref<'pending' | 'active' | 'done'>('pending')
/** 主视图：工单列表 / 路线与班次 / 绩效激励 */
const view = ref<'orders' | 'route' | 'perf'>('orders')
const busyId = ref<number | null>(null)
const closureTarget = ref<WorkOrder | null>(null)
const closureNote = ref('已完成清理并拍照留档')
const closureFile = ref<File | null>(null)
const closurePreview = ref('')
const shiftOn = ref(true)
const routeStarted = ref(false)
const arrivedIds = ref<number[]>([])
const kit = ref({ gloves: true, tongs: true, bags: false })
const localOrders = ref([
  { id: -101, order_no: 'GD202609290018', location_name: '信阳学院北门', created_at: '2026-09-29T09:18:00', status: 'pending', priority: 'high' },
  { id: -102, order_no: 'GD202609290019', location_name: '学生食堂东侧', created_at: '2026-09-29T09:26:00', status: 'pending', priority: 'normal' },
  { id: -103, order_no: 'GD202609290020', location_name: '学院路公交站', created_at: '2026-09-29T09:34:00', status: 'pending', priority: 'high' },
  { id: -104, order_no: 'GD202609290021', location_name: '图书馆北广场', created_at: '2026-09-29T09:42:00', status: 'pending', priority: 'normal' },
  { id: -105, order_no: 'GD202609290022', location_name: '校园南门步道', created_at: '2026-09-29T09:51:00', status: 'pending', priority: 'normal' }
])

/** 每次进入页面生成一组不完全整齐的现场数据，避免演示卡片机械重复。 */
const sessionSeed = Math.floor(Math.random() * 997) + 31
const fieldSnapshot = {
  distanceKm: +(3.2 + ((sessionSeed * 7) % 39) / 10).toFixed(1),
  activeMinutes: 96 + ((sessionSeed * 13) % 87),
  delayed: 1 + (sessionSeed % 3),
  battery: 58 + ((sessionSeed * 11) % 35)
}
const areaLoad = [
  { name: '图书馆片区', value: 42 + ((sessionSeed * 5) % 43) },
  { name: '教学楼片区', value: 29 + ((sessionSeed * 7) % 48) },
  { name: '体育馆片区', value: 18 + ((sessionSeed * 11) % 51) }
]

const isWorker = computed(() => auth.isLoggedIn)
const userName = computed(() =>
  auth.user ? `${auth.user.realName} · ${auth.user.username}` : ''
)

const COLS: YzColumn[] = [
  { key: 'order_no', label: '工单号', width: '1.1fr' },
  { key: 'location', label: '点位', width: '1.2fr' },
  { key: 'created', label: '派单时间', width: '1.2fr' },
  { key: 'wait', label: '等待时长', width: '100px', align: 'right' },
  { key: 'priority', label: '优先级', width: '84px' },
  { key: 'statusText', label: '状态', width: '96px' },
  { key: 'op', label: '操作', width: '196px' }
]

const STATUS_TEXT: Record<string, string> = {
  pending: '待接单',
  accepted: '已接单',
  processing: '处理中',
  verifying: '待验收',
  completed: '已完成',
  closed: '已闭环',
  timeout: '已超时'
}

const TONE: Record<string, string> = {
  pending: 'warning',
  accepted: 'info',
  processing: 'info',
  verifying: 'warning',
  completed: 'success',
  closed: 'success',
  timeout: 'danger'
}

async function doLogin() {
  loginError.value = ''
  if (logging.value) return
  logging.value = true
  try {
    const res = await auth.login(account.value, password.value)
    if (!res.ok) {
      loginError.value = res.message
      return
    }
    await demo.reload()
  } finally {
    logging.value = false
  }
}

/** 演示直入：不填表单，直接用 demo 账号进 */
async function demoEnter() {
  account.value = 'worker01'
  password.value = '123456'
  await doLogin()
}

function logout() {
  auth.logout()
  location.href = './auth.html#/auth?role=worker'
}

const pending = computed(() => demo.workOrders.filter((o) => o.status === 'pending'))
const active = computed(() =>
  demo.workOrders.filter((o) => ['accepted', 'processing', 'verifying'].includes(o.status))
)
const done = computed(() =>
  demo.workOrders.filter((o) => ['completed', 'closed'].includes(o.status))
)
const list = computed(() =>
  tab.value === 'pending' ? pending.value : tab.value === 'active' ? active.value : done.value
)
const localList = computed(() => localOrders.value.filter((o) => tab.value === 'pending' ? o.status === 'pending' : tab.value === 'active' ? ['accepted', 'processing'].includes(o.status) : o.status === 'completed'))
const pendingCount = computed(() => pending.value.length + localOrders.value.filter((o) => o.status === 'pending').length)
const activeCount = computed(() => active.value.length + localOrders.value.filter((o) => ['accepted', 'processing'].includes(o.status)).length)
const doneCount = computed(() => done.value.length + localOrders.value.filter((o) => o.status === 'completed').length)

const statItems = computed(() => [
  { label: '待接单', value: pendingCount.value, hint: '可立即接单', tone: 'warning' as const },
  { label: '进行中', value: activeCount.value, hint: '含待验收', tone: 'primary' as const },
  { label: '今日完成', value: doneToday.value, hint: '已提交闭环材料', tone: 'success' as const },
  {
    label: '平均响应',
    value: `${demo.metrics.avgResponseMin}`,
    hint: '单位：分钟',
    tone: 'primary' as const
  }
])

function todayKey() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
const doneToday = computed(
  () => done.value.filter((o) => (o.completed_at ?? '').slice(0, 10) === todayKey()).length
)

function fmt(ts?: string | null) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 等待时长（分钟），超 30 分钟标红——对应 PRD §5.2.3 的超时告警 */
function waitMin(ts: string) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return 0
  return Math.max(0, Math.round((Date.now() - d.getTime()) / 60000))
}

const rows = computed(() =>
  [...list.value, ...localList.value].map((o: any) => ({
    id: o.id,
    order_no: o.order_no,
    location: o.location_name || '未标注点位',
    created: fmt(o.created_at),
    wait: `${waitMin(o.created_at)} 分`,
    over: o.status === 'pending' && waitMin(o.created_at) > 30,
    priority: (o.priority ?? (o.id % 5 === 0 || waitMin(o.created_at) > 45 ? 'high' : 'normal')) === 'high' ? '高' : '常规',
    statusText: STATUS_TEXT[o.status] ?? o.status,
    tone: TONE[o.status] ?? 'info',
    status: o.status,
    completedAt: o.completed_at,
    raw: o
  }))
)

const routeStops = computed(() =>
  [...pending.value, ...active.value].slice(0, 4).map((o, index) => ({
    id: o.id,
    no: index + 1,
    location: o.location_name,
    orderNo: o.order_no,
    eta: 7 + ((o.id * 13 + sessionSeed + index * 9) % 26),
    distance: +(0.3 + ((o.id * 7 + sessionSeed) % 19) / 10).toFixed(1),
    urgent: o.id % 5 === 0 || waitMin(o.created_at) > 45,
    arrived: arrivedIds.value.includes(o.id)
  }))
)

function toggleShift() {
  shiftOn.value = !shiftOn.value
  ElMessage.success(shiftOn.value ? '已开始本班次，正在接收任务' : '本班次已暂停接单')
}

function startRoute() {
  routeStarted.value = !routeStarted.value
  ElMessage.success(routeStarted.value ? '路线已开始，将按推荐顺序前往' : '路线已暂停')
}

function markArrived(id: number) {
  if (!arrivedIds.value.includes(id)) arrivedIds.value = [...arrivedIds.value, id]
  ElMessage.success('已记录到达时间')
}

async function onAccept(row: Record<string, any>) {
  if (row.id < 0) {
    const item = localOrders.value.find((o) => o.id === row.id)
    if (item) item.status = 'accepted'
    ElMessage.success(`已接单 ${row.order_no}，已转入“进行中”`)
    return
  }
  if (busyId.value) return
  busyId.value = row.id
  try {
    await demo.acceptOrder(row.id, auth.user?.realName ?? '当前作业人员')
    ElMessage.success(`已接单 ${row.order_no}`)
  } finally {
    busyId.value = null
  }
}

async function onStart(row: Record<string, any>) {
  if (row.id < 0) {
    const item = localOrders.value.find((o) => o.id === row.id)
    if (item) item.status = 'processing'
    ElMessage.success('已开始处理该模拟工单')
    return
  }
  if (busyId.value) return
  busyId.value = row.id
  try {
    await demo.startOrder(row.id)
    ElMessage.success('已开始处理')
  } finally {
    busyId.value = null
  }
}

function openClosure(row: Record<string, any>) {
  if (row.id < 0) {
    const item = localOrders.value.find((o) => o.id === row.id)
    if (item) item.status = 'completed'
    ElMessage.success('模拟工单已上传清理照片并提交验收')
    return
  }
  closureTarget.value = row.raw as WorkOrder
  closureNote.value = '已完成清理并拍照留档'
  closureFile.value = null
  closurePreview.value = ''
}

function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] ?? null
  closureFile.value = f
  closurePreview.value = f ? URL.createObjectURL(f) : ''
}

async function submitClosure() {
  const target = closureTarget.value
  if (!target) return
  busyId.value = target.id
  try {
    const ok = await demo.submitClosure(target.id, closureNote.value, closureFile.value)
    if (!ok) {
      ElMessage.error(demo.lastError || '提交失败，请重试')
      return
    }
    ElMessage.success('已提交闭环材料，等待管理端验收')
    closureTarget.value = null
  } finally {
    busyId.value = null
  }
}

onMounted(async () => {
  if (auth.isLoggedIn) await demo.reload()
})

/* ================= 绩效激励 ================= */
/** 积分：完成 5 分/单、进行中 2 分、待接单 1 分，加基础出勤分 */
const perfPoints = computed(() => done.value.length * 5 + active.value.length * 2 + pending.value.length + 20)
const PERF_LEVELS = [
  { name: '一星环卫', min: 0 },
  { name: '二星环卫', min: 60 },
  { name: '三星环卫', min: 120 },
  { name: '四星环卫', min: 200 },
  { name: '五星环卫', min: 300 }
]
const perfLevel = computed(() => {
  let cur = PERF_LEVELS[0]
  for (const l of PERF_LEVELS) if (perfPoints.value >= l.min) cur = l
  return cur
})
const nextLevel = computed(() => {
  const idx = PERF_LEVELS.indexOf(perfLevel.value)
  return PERF_LEVELS[idx + 1] ?? null
})
const levelProgress = computed(() => {
  if (!nextLevel.value) return 100
  const span = nextLevel.value.min - perfLevel.value.min
  return Math.min(100, Math.round(((perfPoints.value - perfLevel.value.min) / span) * 100))
})
/** 班组周排行（同事匿名化，仅演示） */
const perfRank = computed(() => {
  const me = { name: `${auth.user?.realName ?? '我'}（本人）`, score: 96 + perfPoints.value, me: true }
  const mates = [
    { name: '王师傅 13**', score: 262, me: false },
    { name: '李师傅 07**', score: 241, me: false },
    { name: '赵师傅 21**', score: 228, me: false },
    { name: '陈师傅 02**', score: 205, me: false },
    { name: '刘师傅 19**', score: 187, me: false },
    { name: '孙师傅 05**', score: 166, me: false }
  ]
  return [...mates, me].sort((a, b) => b.score - a.score)
})
const myPerfRank = computed(() => perfRank.value.findIndex((r) => r.me) + 1)
const PERF_RULES = [
  { act: '完成一单清理并提交闭环材料', pts: '+5' },
  { act: '接单后 30 分钟内完成处置', pts: '+3' },
  { act: '管理端验收通过（一次通过）', pts: '+2' },
  { act: '获得市民/巡查好评', pts: '+5' },
  { act: '每日出勤打卡', pts: '+1' }
]
</script>

<template>
  <!-- 未登录：只挡这一个端，样式与管理端登录同源 -->
  <EndShell v-if="!isWorker" end="worker" title="环卫工人端" subtitle="烟踪智治 · 作业工作台" width="460">
    <div class="ad-head">
      <div>
        <h1 class="ad-title">作业人员登录</h1>
        <p class="ad-sub">用工号登录后查看派到本人的清理工单</p>
      </div>
    </div>

    <YzPanel title="登录">
      <label class="f-field"><span>工号</span><input v-model="account" class="ad-ctrl" autocomplete="username" /></label>
      <label class="f-field">
        <span>口令</span>
        <input v-model="password" class="ad-ctrl" type="password" autocomplete="current-password" />
      </label>
      <p v-if="loginError" class="f-err" role="alert">{{ loginError }}</p>
      <div class="f-acts">
        <button class="ad-btn" type="button" @click="demoEnter">演示直入</button>
        <button class="ad-btn ad-btn--primary" type="button" :disabled="logging" @click="doLogin">
          {{ logging ? '登录中…' : '登录' }}
        </button>
      </div>
      <p class="f-tip">演示账号 <code>worker01 / 123456</code></p>
    </YzPanel>
  </EndShell>

  <EndShell
    v-else
    class="worker-app"
    end="worker"
    title="环卫工人端"
    subtitle="烟踪智治 · 作业工作台"
    :user="userName"
    width="100%"
  >
    <template #nav>
      <button
        class="ad-btn"
        :class="{ 'ad-btn--primary': view === 'orders' && tab === 'pending' }"
        type="button"
        @click="view = 'orders'; tab = 'pending'"
      >
        待接单 {{ pendingCount }}
      </button>
      <button
        class="ad-btn"
        :class="{ 'ad-btn--primary': view === 'orders' && tab === 'active' }"
        type="button"
        @click="view = 'orders'; tab = 'active'"
      >
        进行中 {{ activeCount }}
      </button>
      <button
        class="ad-btn"
        :class="{ 'ad-btn--primary': view === 'orders' && tab === 'done' }"
        type="button"
        @click="view = 'orders'; tab = 'done'"
      >
        已完成 {{ doneCount }}
      </button>
      <button
        class="ad-btn"
        :class="{ 'ad-btn--primary': view === 'route' }"
        type="button"
        @click="view = 'route'"
      >
        路线与班次
      </button>
      <button
        class="ad-btn"
        :class="{ 'ad-btn--primary': view === 'perf' }"
        type="button"
        @click="view = 'perf'"
      >
        ★ 绩效激励
      </button>
    </template>
    <template #actions>
      <button class="ad-btn" type="button" @click="logout">退出</button>
    </template>

    <section v-if="view === 'orders'" class="orders-hero">
      <img src="/media/worker-operations-hero.png" alt="环卫人员在滨水步道协同作业" />
      <div><span>FIELD OPERATIONS · 今日作业</span><h1>清洁有路线，处置有回音</h1><p>根据待办优先级规划清扫顺序，处置照片与验收结果实时同步至管理端。</p></div>
    </section>

    <div v-if="view === 'orders'" class="ad-head">
      <div>
        <h1 class="ad-title">我的清理工单</h1>
        <p class="ad-sub">
          接单 → 现场处置 → 上传清理后照片 → 提交验收 · 等待时长超过 30 分钟会标红提示
        </p>
      </div>
      <div class="ad-actions">
        <span class="ad-badge">当前分组 {{ rows.length }} 条</span>
      </div>
    </div>

    <YzStat v-if="view === 'orders'" :items="statItems" compact />

    <section v-if="view === 'orders'" class="worker-overview" aria-label="今日现场概况">
      <article class="overview-card shift-card">
        <div class="overview-title">
          <span class="overview-icon">班</span>
          <div><small>当前班次</small><strong>{{ shiftOn ? '作业中' : '已暂停' }}</strong></div>
          <i :class="{ on: shiftOn }"></i>
        </div>
        <p>已在线 {{ fieldSnapshot.activeMinutes }} 分钟 · 设备电量 {{ fieldSnapshot.battery }}%</p>
        <button class="overview-action" type="button" @click="toggleShift">
          {{ shiftOn ? '暂停接单' : '开始班次' }}
        </button>
      </article>

      <article class="overview-card route-card">
        <div class="overview-title">
          <span class="overview-icon">线</span>
          <div><small>推荐路线</small><strong>{{ fieldSnapshot.distanceKm }} 公里</strong></div>
        </div>
        <p>{{ routeStops.length }} 个待到达点位，其中 {{ fieldSnapshot.delayed }} 处建议优先处理</p>
        <button class="overview-action" type="button" @click="view = 'route'">查看路线安排</button>
      </article>

      <article class="overview-card load-card">
        <div class="overview-title">
          <span class="overview-icon">区</span>
          <div><small>片区任务负载</small><strong>实时分布</strong></div>
        </div>
        <div class="load-list">
          <div v-for="area in areaLoad" :key="area.name">
            <span>{{ area.name }}</span><b>{{ area.value }}%</b>
            <i><em :style="{ width: area.value + '%' }"></em></i>
          </div>
        </div>
      </article>
    </section>

    <YzPanel v-if="view === 'orders'" :title="tab === 'pending' ? '待接单' : tab === 'active' ? '进行中' : '已完成'" :count="rows.length" grow>
      <div class="worker-table">
        <YzTable :columns="COLS" :rows="rows" row-key="id" dense empty="当前分组没有工单">
        <template #cell-wait="{ row }">
          <span :class="{ 'warn-num': row.over }">{{ row.wait }}</span>
        </template>
        <template #cell-statusText="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.tone}`">{{ row.statusText }}</span>
        </template>
        <template #cell-op="{ row }">
          <button
            v-if="row.status === 'pending'"
            class="ad-link"
            type="button"
            :disabled="busyId === row.id"
            @click="onAccept(row)"
          >
            接单
          </button>
          <button
            v-else-if="row.status === 'accepted'"
            class="ad-link"
            type="button"
            :disabled="busyId === row.id"
            @click="onStart(row)"
          >
            开始处理
          </button>
          <button
            v-else-if="row.status === 'processing' || row.status === 'timeout'"
            class="ad-link"
            type="button"
            @click="openClosure(row)"
          >
            上传清理后照片
          </button>
          <span v-else-if="row.status === 'verifying'" class="ad-sub">等待管理端验收</span>
          <span v-else class="ad-sub">完成于 {{ fmt(row.completedAt) }}</span>
        </template>
        </YzTable>
      </div>

      <div class="worker-cards" aria-label="移动端工单列表">
        <article v-for="row in rows" :key="row.id" class="worker-card">
          <header>
            <span class="yz-tag" :class="`yz-tag--${row.tone}`">{{ row.statusText }}</span>
            <span :class="['worker-wait', { over: row.over }]">等待 {{ row.wait }}</span>
          </header>
          <h3>{{ row.location }}</h3>
          <p class="worker-no">{{ row.order_no }}</p>
          <dl>
            <div><dt>派单时间</dt><dd>{{ row.created }}</dd></div>
            <div><dt>优先级</dt><dd>{{ row.priority }}</dd></div>
          </dl>
          <button
            v-if="row.status === 'pending'"
            class="worker-action"
            type="button"
            :disabled="busyId === row.id"
            @click="onAccept(row)"
          >
            接单并查看位置
          </button>
          <button
            v-else-if="row.status === 'accepted'"
            class="worker-action"
            type="button"
            :disabled="busyId === row.id"
            @click="onStart(row)"
          >
            开始现场处置
          </button>
          <button
            v-else-if="row.status === 'processing' || row.status === 'timeout'"
            class="worker-action"
            type="button"
            @click="openClosure(row)"
          >
            上传清理后照片
          </button>
          <p v-else-if="row.status === 'verifying'" class="worker-result">已提交，等待管理端验收</p>
          <p v-else class="worker-result">完成于 {{ fmt(row.completedAt) }}</p>
        </article>
        <p v-if="!rows.length" class="worker-empty">当前分组没有工单</p>
      </div>
    </YzPanel>

    <p v-if="view === 'orders'" class="foot-note">
      闭环需两步：作业端提交清理后照片 → 管理端验收通过才计为「已闭环」。
      照片仅用于核验处置结果，不对外公开。
    </p>

    <!-- ================= 路线与班次 ================= -->
    <template v-else-if="view === 'route'">
      <div class="ad-head route-head">
        <div>
          <div class="route-kicker">现场辅助 · 模拟路线</div>
          <h1 class="ad-title">今日路线与班次</h1>
          <p class="ad-sub">根据工单等待时间和距离给出建议顺序，实际作业以现场安全与调度通知为准。</p>
        </div>
        <div class="route-head-actions">
          <span :class="['shift-pill', { off: !shiftOn }]">{{ shiftOn ? '班次进行中' : '班次已暂停' }}</span>
          <button class="ad-btn" type="button" @click="toggleShift">{{ shiftOn ? '暂停班次' : '恢复班次' }}</button>
          <button class="ad-btn ad-btn--primary" type="button" @click="startRoute">
            {{ routeStarted ? '暂停路线' : '开始路线' }}
          </button>
        </div>
      </div>

      <section class="route-summary">
        <article><small>预计里程</small><strong>{{ fieldSnapshot.distanceKm }}<em> km</em></strong><span>按建议顺序估算</span></article>
        <article><small>待到达点位</small><strong>{{ routeStops.filter(s => !s.arrived).length }}<em> 处</em></strong><span>到达后手动确认</span></article>
        <article><small>设备状态</small><strong>{{ fieldSnapshot.battery }}<em>%</em></strong><span>{{ fieldSnapshot.battery < 70 ? '建议途中补电' : '电量正常' }}</span></article>
      </section>

      <div class="route-layout">
        <YzPanel title="建议到访顺序" :count="routeStops.length">
          <ol class="stop-list">
            <li v-for="stop in routeStops" :key="stop.id" :class="{ arrived: stop.arrived }">
              <span class="stop-no">{{ stop.arrived ? '✓' : stop.no }}</span>
              <div class="stop-line"></div>
              <div class="stop-main">
                <div><strong>{{ stop.location || '未标注点位' }}</strong><span v-if="stop.urgent">优先</span></div>
                <p>{{ stop.orderNo }} · 距离约 {{ stop.distance }} km · 预计 {{ stop.eta }} 分钟</p>
              </div>
              <button v-if="!stop.arrived" class="ad-btn" type="button" @click="markArrived(stop.id)">记录到达</button>
              <span v-else class="arrived-text">已到达</span>
            </li>
            <li v-if="!routeStops.length" class="route-empty">当前没有需要规划的点位</li>
          </ol>
        </YzPanel>

        <aside class="route-side">
          <section class="kit-card">
            <div class="side-heading"><span>出发前检查</span><small>{{ Object.values(kit).filter(Boolean).length }}/3</small></div>
            <label><input v-model="kit.gloves" type="checkbox" /><span>防护手套</span><em>接触废弃物前佩戴</em></label>
            <label><input v-model="kit.tongs" type="checkbox" /><span>拾取夹</span><em>避免徒手接触烟头</em></label>
            <label><input v-model="kit.bags" type="checkbox" /><span>密封收集袋</span><em>分类封装后统一清运</em></label>
          </section>
          <section class="safety-card">
            <span>安全提醒</span>
            <p>处理未熄灭烟头时先确认无明火；靠近车道作业需穿反光服并避开车辆盲区。</p>
          </section>
        </aside>
      </div>
    </template>

    <!-- ================= 绩效激励 ================= -->
    <template v-else>
      <div class="perf-hero">
        <img class="perf-hero-img" src="/media/worker-team.png" alt="班组绩效示意插画" />
        <div class="perf-hero-copy">
          <span>PERFORMANCE</span>
          <h1>绩效激励</h1>
          <p>多劳多得、好劳优得。积分与等级每月汇总，作为绩效奖金与评优依据（演示规则）。</p>
        </div>
      </div>

      <div class="perf-grid">
        <section class="perf-card perf-me">
          <img class="perf-medal" src="/media/medal.png" alt="等级勋章" />
          <div class="perf-me-main">
            <small>我的积分</small>
            <strong>{{ perfPoints }}</strong>
            <span class="perf-level">{{ perfLevel.name }}</span>
            <div class="perf-progress">
              <i :style="{ width: levelProgress + '%' }"></i>
            </div>
            <em v-if="nextLevel">
              距 {{ nextLevel.name }} 还需 {{ nextLevel.min - perfPoints }} 分
            </em>
            <em v-else>已是最高等级，保持！</em>
          </div>
          <div class="perf-milestones">
            <div><strong>{{ doneToday }}</strong><span>今日闭环</span></div>
            <div><strong>{{ fieldSnapshot.activeMinutes }}</strong><span>在线分钟</span></div>
            <div><strong>{{ fieldSnapshot.delayed }}</strong><span>优先任务</span></div>
          </div>
          <div class="perf-week-tip">
            <b>本周提升建议</b>
            <p>优先完成等待时间较长的任务，提交清晰的清理后照片，可减少返工并提升一次验收率。</p>
          </div>
        </section>

        <section class="perf-card">
          <h2>班组周排行</h2>
          <ol class="perf-rank">
            <li v-for="(r, i) in perfRank" :key="r.name" :class="{ me: r.me, top: i < 3 }">
              <span class="pr-no">{{ i + 1 }}</span>
              <span class="pr-name">{{ r.name }}</span>
              <em>{{ r.score }} 分</em>
            </li>
          </ol>
          <p class="perf-note">你本周暂列第 {{ myPerfRank }} 名 · 完成手上的工单即可提升排名</p>
        </section>

        <section class="perf-card">
          <h2>积分规则</h2>
          <ul class="perf-rules">
            <li v-for="r in PERF_RULES" :key="r.act">
              <span>{{ r.act }}</span><em>{{ r.pts }}</em>
            </li>
          </ul>
          <div class="perf-quality">
            <div><span>按时响应率</span><b>92%</b><i><em style="width:92%"></em></i></div>
            <div><span>一次验收率</span><b>87%</b><i><em style="width:87%"></em></i></div>
            <div><span>安全检查完成</span><b>3/3</b><i><em style="width:100%"></em></i></div>
          </div>
          <p class="perf-note">积分按自然月汇总；异常申诉可在管理端「处置留痕」中核对。</p>
        </section>
      </div>
    </template>
  </EndShell>

  <!-- 上传闭环材料 -->
  <div v-if="closureTarget" class="mask" @click.self="closureTarget = null">
    <div class="sheet">
      <h2 class="s-title">提交闭环材料</h2>
      <p class="s-sub">{{ closureTarget.order_no }} · {{ closureTarget.location_name }}</p>
      <label class="upload">
        <input type="file" accept="image/*" @change="onPickFile" />
        <img v-if="closurePreview" :src="closurePreview" alt="清理后照片预览" />
        <span v-else>＋ 选择清理后照片</span>
      </label>
      <label class="f-field">
        <span>处置说明</span>
        <textarea v-model="closureNote" rows="3"></textarea>
      </label>
      <p class="s-tip">提交后进入「待验收」，由管理端确认闭环。</p>
      <div class="s-acts">
        <button class="ad-btn" type="button" @click="closureTarget = null">取消</button>
        <button
          class="ad-btn ad-btn--primary"
          type="button"
          :disabled="busyId === closureTarget.id"
          @click="submitClosure"
        >
          提交验收
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.worker-app :deep(.es-main) { padding:16px 20px 28px;scrollbar-gutter:stable; }
.worker-app :deep(.es-inner) { min-height:100%; }
.worker-app :deep(.es-nav .ad-btn) { min-width:82px;height:34px;padding:0 12px;justify-content:center;font-size:13px;line-height:1;white-space:nowrap; }
.worker-app :deep(.es-nav .ad-btn:nth-child(4)) { min-width:104px; }
.worker-app :deep(.es-nav .ad-btn:nth-child(5)) { min-width:104px; }
.worker-app .ad-head { min-height:48px;margin:0;align-items:center; }
.worker-app .ad-title { margin:0;line-height:1.25; }
.worker-app .ad-sub { margin-top:3px;line-height:1.4; }
.f-field {
  display: grid;
  gap: 7px;
  margin-top: 14px;
}
.f-field > span {
  font-size: 12px;
  color: var(--yz-text-muted);
}
.f-field .ad-ctrl {
  width: 100%;
}
.f-field textarea {
  padding: 9px 11px;
  border: 1px solid var(--yz-border-soft);
  border-radius: var(--yz-radius-input);
  font-family: inherit;
  font-size: 13px;
  color: var(--yz-text-2);
  resize: vertical;
  outline: none;
}
.f-field textarea:focus {
  border-color: var(--yz-primary);
  box-shadow: 0 0 0 2px var(--yz-primary-soft);
}
.f-err {
  margin-top: 12px;
  font-size: 13px;
  color: var(--yz-danger);
}
.f-acts {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}
.f-tip {
  margin-top: 12px;
  font-size: 12px;
  color: var(--yz-text-muted);
}
.f-tip code {
  font-family: Consolas, monospace;
  color: var(--yz-text-strong);
}

.warn-num {
  color: var(--yz-danger);
  font-weight: 700;
}

.worker-cards {
  display: none;
}

.foot-note {
  flex: none;
  padding: 9px 12px;
  border-left: 3px solid var(--yz-primary);
  background: var(--yz-primary-soft);
  font-size: 12px;
  line-height: 1.8;
  color: var(--yz-text-muted);
}

/* ============ 现场概况 ============ */
.worker-overview {
  display: grid;
  grid-template-columns: 0.9fr 1fr 1.25fr;
  gap: 14px;
}
.overview-card {
  min-width: 0;
  padding: 16px 18px;
  border: 1px solid var(--yz-border-soft);
  border-radius: var(--yz-radius-card);
  background: #fff;
  box-shadow: var(--yz-shadow-card);
}
.overview-title { display: flex; align-items: center; gap: 11px; }
.overview-title > div { flex: 1; min-width: 0; }
.overview-title small,
.overview-title strong { display: block; }
.overview-title small { margin-bottom: 3px; color: var(--yz-text-muted); font-size: 11px; }
.overview-title strong { color: var(--yz-text-strong); font-size: 15px; }
.overview-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 11px;
  color: var(--yz-primary);
  background: var(--yz-primary-soft);
  font-size: 13px;
  font-weight: 800;
}
.overview-title > i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #aab5c0;
  box-shadow: 0 0 0 4px rgba(170, 181, 192, 0.15);
}
.overview-title > i.on { background: #29a36a; box-shadow: 0 0 0 4px rgba(41, 163, 106, 0.14); }
.overview-card > p { min-height: 34px; margin: 13px 0 10px; color: var(--yz-text-muted); font-size: 12px; line-height: 1.55; }
.overview-action {
  padding: 0;
  border: 0;
  color: var(--yz-primary);
  background: transparent;
  font: 700 12px var(--yz-font);
  cursor: pointer;
}
.load-list { display: grid; gap: 7px; margin-top: 12px; }
.load-list > div { display: grid; grid-template-columns: 1fr auto; gap: 4px 10px; align-items: center; }
.load-list span, .load-list b { color: var(--yz-text-muted); font-size: 10.5px; }
.load-list b { font-family: Consolas, monospace; font-weight: 600; }
.load-list i { grid-column: 1 / -1; overflow: hidden; height: 4px; border-radius: 99px; background: #edf2f5; }
.load-list em { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #4ba5cf, #3bc08b); }

/* ============ 路线与班次 ============ */
.route-head { align-items: flex-end; }
.route-kicker { margin-bottom: 5px; color: var(--yz-primary); font-size: 10px; font-weight: 800; letter-spacing: .13em; }
.route-head-actions { display: flex; align-items: center; gap: 9px; }
.shift-pill { padding: 6px 10px; border-radius: 99px; color: #18754b; background: #e8f7ef; font-size: 11px; font-weight: 700; }
.shift-pill.off { color: #7b8790; background: #edf1f4; }
.route-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.route-summary article { padding: 17px 18px; border: 1px solid var(--yz-border-soft); border-radius: var(--yz-radius-card); background: linear-gradient(145deg, #fff, #f7fbfd); box-shadow: var(--yz-shadow-card); }
.route-summary small, .route-summary span { display: block; color: var(--yz-text-muted); font-size: 11px; }
.route-summary strong { display: block; margin: 7px 0 4px; color: var(--yz-text-strong); font: 700 27px Consolas, monospace; }
.route-summary strong em { color: var(--yz-text-muted); font: 500 11px var(--yz-font); }
.route-layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(260px, .72fr); gap: 14px; align-items: start; }
.stop-list { display: grid; margin: 0; padding: 0; list-style: none; }
.stop-list li { position: relative; display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 13px; align-items: center; min-height: 72px; padding: 10px 0; border-bottom: 1px solid var(--yz-border-faint); }
.stop-list li:last-child { border-bottom: 0; }
.stop-no { z-index: 1; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: #fff; background: var(--yz-primary); font: 700 12px Consolas, monospace; }
.stop-line { position: absolute; top: 47px; bottom: -25px; left: 14px; width: 1px; border-left: 1px dashed #b9d5e3; }
.stop-list li:nth-last-child(1) .stop-line { display: none; }
.stop-main { min-width: 0; }
.stop-main > div { display: flex; align-items: center; gap: 8px; }
.stop-main strong { overflow: hidden; color: var(--yz-text-strong); font-size: 13.5px; text-overflow: ellipsis; white-space: nowrap; }
.stop-main span { flex: none; padding: 2px 6px; border-radius: 4px; color: #b66513; background: #fff0df; font-size: 9px; font-weight: 700; }
.stop-main p { margin: 5px 0 0; color: var(--yz-text-muted); font-size: 11px; }
.stop-list li.arrived .stop-no { background: #29a36a; }
.stop-list li.arrived .stop-main { opacity: .65; }
.arrived-text { color: #21865a; font-size: 11px; font-weight: 700; }
.route-empty { display: block !important; color: var(--yz-text-muted); text-align: center; }
.route-side { display: grid; gap: 14px; }
.kit-card, .safety-card { padding: 18px; border: 1px solid var(--yz-border-soft); border-radius: var(--yz-radius-card); background: #fff; box-shadow: var(--yz-shadow-card); }
.side-heading { display: flex; justify-content: space-between; margin-bottom: 8px; color: var(--yz-text-strong); font-size: 14px; font-weight: 700; }
.side-heading small { color: var(--yz-primary); font: 700 12px Consolas, monospace; }
.kit-card label { display: grid; grid-template-columns: auto 1fr; gap: 3px 9px; padding: 11px 0; border-bottom: 1px dashed var(--yz-border-soft); cursor: pointer; }
.kit-card label:last-child { border-bottom: 0; }
.kit-card input { grid-row: 1 / 3; align-self: center; accent-color: var(--yz-primary); }
.kit-card label span { color: var(--yz-text-2); font-size: 12.5px; }
.kit-card label em { color: var(--yz-text-muted); font-size: 10.5px; font-style: normal; }
.safety-card { border-color: #f0d8b5; background: #fffaf2; }
.safety-card span { color: #9a5d12; font-size: 12px; font-weight: 800; }
.safety-card p { margin: 8px 0 0; color: #8b6d49; font-size: 11.5px; line-height: 1.75; }

.orders-hero { position:relative;flex:none;height:152px;overflow:hidden;border-radius:var(--yz-radius-card);box-shadow:var(--yz-shadow-card); }
.orders-hero > img { width:100%;height:100%;object-fit:cover;object-position:center 48%; }
.orders-hero > div { position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 34px;color:#fff;background:linear-gradient(90deg,rgba(6,31,47,.92),rgba(8,54,71,.58) 42%,transparent 72%); }
.orders-hero span { color:#82ead5;font:700 10px Consolas,monospace;letter-spacing:.16em; }
.orders-hero h1 { margin:8px 0 5px;font-size:27px; }
.orders-hero p { max-width:570px;margin:0;color:rgba(255,255,255,.86);font-size:12px;line-height:1.7; }
.orders-hero > b { position:absolute;right:18px;top:14px;padding:5px 10px;border-radius:999px;color:#fff;background:rgba(7,35,48,.62);font-size:10px;font-weight:600;backdrop-filter:blur(8px); }

/* ============ 绩效激励 ============ */
.perf-hero {
  position: relative;
  flex: none;
  overflow: hidden;
  border-radius: var(--yz-radius-card);
  box-shadow: var(--yz-shadow-card);
}
.perf-hero-img {
  display: block;
  width: 100%;
  height: 190px;
  object-fit: cover;
  object-position: center 38%;
}

.worker-app :deep(.stats .stat) {
  display: flex;
  min-height: 76px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.perf-hero-copy {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 34px;
  background: linear-gradient(92deg, rgba(9, 40, 60, 0.78) 0%, rgba(10, 60, 85, 0.42) 52%, rgba(10, 60, 85, 0) 82%);
  color: #fff;
}
.perf-hero-copy span {
  color: #ffd98a;
  font: 10px Consolas, monospace;
  letter-spacing: 0.16em;
}
.perf-hero-copy h1 {
  margin: 8px 0 8px;
  font-size: 30px;
  letter-spacing: 0.02em;
}
.perf-hero-copy p {
  max-width: 520px;
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.88);
}
.perf-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.95fr 1fr;
  gap: 14px;
  margin-top: 14px;
  align-items: stretch;
}
.perf-card {
  height: 100%;
  padding: 18px;
  border: 1px solid var(--yz-border-soft);
  border-radius: var(--yz-radius-card);
  background: #fff;
  box-shadow: var(--yz-shadow-card);
}
.perf-card h2 {
  margin: 0 0 14px;
  color: var(--yz-text-strong);
  font-size: 15px;
}
.perf-me {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.perf-medal {
  flex: none;
  width: 108px;
  height: 108px;
  object-fit: cover;
  border-radius: 16px;
}
.perf-me-main {
  flex: 1;
  min-width: 0;
}
.perf-me-main small {
  color: var(--yz-text-muted);
  font-size: 11px;
}
.perf-me-main strong {
  display: block;
  margin: 2px 0 6px;
  color: #d98a1e;
  font: 700 34px Consolas, monospace;
}
.perf-level {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 999px;
  color: #8a5a00;
  background: linear-gradient(100deg, #ffe9b8, #ffd98a);
  font-size: 12px;
  font-weight: 700;
}
.perf-progress {
  overflow: hidden;
  height: 7px;
  margin-top: 12px;
  border-radius: 999px;
  background: #eef1f4;
}
.perf-progress i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #f0a92e, #f7c65b);
  transition: width 0.4s;
}
.perf-me-main em {
  display: block;
  margin-top: 8px;
  color: var(--yz-text-muted);
  font-size: 11.5px;
  font-style: normal;
}
.perf-milestones { display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:100%; }
.perf-milestones div { padding:11px 8px;border-radius:10px;background:#f5f8fb;text-align:center; }
.perf-milestones strong { display:block;color:var(--yz-text-strong);font:700 18px Consolas,monospace; }
.perf-milestones span { display:block;margin-top:3px;color:var(--yz-text-muted);font-size:10.5px; }
.perf-week-tip { width:100%;padding:12px 14px;border-radius:10px;background:linear-gradient(115deg,#eef6ff,#edf9f4); }
.perf-week-tip b { color:var(--yz-text-strong);font-size:12px; }
.perf-week-tip p { margin:5px 0 0;color:var(--yz-text-muted);font-size:11px;line-height:1.65; }
.perf-rank {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.perf-rank li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background: var(--yz-canvas-bg);
}
.perf-rank li.me {
  background: #fff6e6;
  outline: 1.5px solid #f7c65b;
}
.perf-rank li.top .pr-no {
  color: #fff;
  background: linear-gradient(135deg, #f0a92e, #f7c65b);
}
.pr-no {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: var(--yz-text-muted);
  background: #e4eaf0;
  font-size: 11px;
  font-weight: 700;
}
.pr-name {
  flex: 1;
  color: var(--yz-text-2);
  font-size: 13px;
}
.perf-rank li.me .pr-name {
  color: #b06f00;
  font-weight: 700;
}
.perf-rank li em {
  color: #d98a1e;
  font-size: 12.5px;
  font-style: normal;
  font-weight: 700;
}
.perf-note {
  margin: 12px 0 0;
  color: var(--yz-text-muted);
  font-size: 11.5px;
  line-height: 1.7;
}
.perf-rules {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.perf-rules li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--yz-border-soft);
  font-size: 12.5px;
  color: var(--yz-text-2);
}
.perf-rules li:last-child {
  border-bottom: 0;
}
.perf-rules li span {
  flex: 1;
}
.perf-rules li em {
  color: #1d8a52;
  font-style: normal;
  font-weight: 700;
}
.perf-quality { display:grid;gap:9px;margin-top:14px;padding-top:13px;border-top:1px solid var(--yz-border-faint); }
.perf-quality > div { display:grid;grid-template-columns:1fr auto;gap:5px 10px;align-items:center; }
.perf-quality span,.perf-quality b { color:var(--yz-text-muted);font-size:10.5px; }
.perf-quality b { color:#1d8a52;font-family:Consolas,monospace; }
.perf-quality i { grid-column:1/-1;overflow:hidden;height:5px;border-radius:99px;background:#edf1f4; }
.perf-quality i em { display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#258cf3,#31b980); }
@media (max-width: 900px) {
  .worker-overview { grid-template-columns: 1fr 1fr; }
  .load-card { grid-column: 1 / -1; }
  .route-head { align-items: flex-start; }
  .route-head-actions { flex-wrap: wrap; }
  .route-layout { grid-template-columns: 1fr; }
  .perf-grid {
    grid-template-columns: 1fr;
  }
  .perf-hero-img {
    height: 150px;
  }
}

@media (max-width: 700px) {
  .worker-overview,
  .route-summary { grid-template-columns: 1fr; }
  .load-card { grid-column: auto; }
  .route-head-actions { width: 100%; }
  .route-head-actions .ad-btn { flex: 1; }
  .route-summary article { padding: 14px 16px; }
  .stop-list li { grid-template-columns: 32px minmax(0, 1fr); }
  .stop-list li > .ad-btn,
  .stop-list li > .arrived-text { grid-column: 2; justify-self: start; }
  .worker-table {
    display: none;
  }
  .worker-cards {
    display: grid;
    gap: 12px;
  }
  .worker-card {
    padding: 16px;
    border: 1px solid var(--yz-border-faint);
    border-radius: var(--yz-radius-card);
    background: #fff;
    box-shadow: var(--yz-shadow-card);
  }
  .worker-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .worker-card h3 {
    margin: 14px 0 4px;
    color: var(--yz-text-strong);
    font-size: 17px;
  }
  .worker-no {
    margin: 0;
    color: var(--yz-text-muted);
    font: 12px Consolas, monospace;
  }
  .worker-wait {
    color: var(--yz-text-muted);
    font-size: 13px;
  }
  .worker-wait.over {
    color: var(--yz-danger);
    font-weight: 700;
  }
  .worker-card dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 16px 0;
  }
  .worker-card dl div {
    padding: 10px 12px;
    border-radius: var(--yz-radius-btn);
    background: #f4f9fd;
  }
  .worker-card dt {
    margin-bottom: 4px;
    color: var(--yz-text-muted);
    font-size: 12px;
  }
  .worker-card dd {
    margin: 0;
    color: var(--yz-text-2);
    font-size: 14px;
    font-weight: 700;
  }
  .worker-action {
    width: 100%;
    min-height: 48px;
    border: 0;
    border-radius: var(--yz-radius-btn);
    background: var(--yz-primary-grad);
    color: #fff;
    font: 700 15px var(--yz-font);
    cursor: pointer;
  }
  .worker-action:disabled {
    opacity: 0.55;
    cursor: wait;
  }
  .worker-result {
    margin: 16px 0 0;
    padding: 12px;
    border-radius: var(--yz-radius-btn);
    background: var(--yz-primary-soft);
    color: var(--yz-text-muted);
    font-size: 13px;
    text-align: center;
  }
  .worker-empty {
    margin: 0;
    padding: 28px 0;
    color: var(--yz-text-muted);
    font-size: 14px;
    text-align: center;
  }
}

.mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(23, 39, 67, 0.42);
}
.sheet {
  width: min(460px, 100%);
  padding: 22px 22px 18px;
  border-radius: var(--yz-radius-card);
  background: #fff;
  box-shadow: var(--yz-shadow-pop);
}
.s-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.s-sub {
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--yz-text-muted);
}
.upload {
  display: grid;
  place-items: center;
  min-height: 160px;
  margin-top: 14px;
  border: 1px dashed var(--yz-border);
  border-radius: var(--yz-radius-btn);
  background: #fafcfe;
  cursor: pointer;
  overflow: hidden;
}
.upload input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.upload img {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
}
.upload span {
  font-size: 13px;
  color: var(--yz-text-muted);
}
.s-tip {
  margin-top: 12px;
  font-size: 11.5px;
  line-height: 1.8;
  color: var(--yz-text-muted);
}
.s-acts {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
</style>

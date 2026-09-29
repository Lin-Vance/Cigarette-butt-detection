<script setup lang="ts">
/**
 * 页面 2 · 项目总览首页（事件总览）
 *
 * 管理端总览页面。
 * 与设计稿的唯一差异：原稿的「风险热力图」与「近 7 日趋势」是 PNG 贴图 / 硬编码 SVG，
 * 这里全部替换为可交互的 ECharts，数据来自模拟数据引擎。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/EChart.vue'
import { useDemoStore } from '@/stores/demo'
import type { ViolationEvent } from '@/mock/types'

const router = useRouter()
const demo = useDemoStore()
demo.init()

/* ---------------- 首屏轮播 ---------------- */
const HERO_SLIDES = [
  {
    image: '/media/admin-carousel-ai.png',
    title: 'AI候选识别\n让治理线索更清晰',
    sub: '设备感知 · 片段提取 · 人工复核 · 全程留痕'
  },
  {
    image: '/media/admin-carousel-facility.png',
    title: '公共设施升级\n服务与秩序同步改善',
    sub: '设施档案 · 状态巡检 · 维护提醒 · 使用评估'
  },
  {
    image: '/media/admin-carousel-closure.png',
    title: '环卫协同处置\n从派单到验收形成闭环',
    sub: '智能调度 · 到场记录 · 清理取证 · 结果复核'
  }
]
const heroIndex = ref(0)
const currentHero = computed(() => HERO_SLIDES[heroIndex.value])
let heroTimer: ReturnType<typeof setInterval> | null = null

function changeHero(step: number) {
  heroIndex.value = (heroIndex.value + step + HERO_SLIDES.length) % HERO_SLIDES.length
}
function setHero(index: number) {
  heroIndex.value = index
}
onMounted(() => {
  heroTimer = setInterval(() => changeHero(1), 5200)
})
onBeforeUnmount(() => {
  if (heroTimer) clearInterval(heroTimer)
})

/* ---------------- 指标卡 ---------------- */
const METRIC_ICONS = [
  '/media/icons/today-incident.png',
  '/media/icons/processing-hourglass.png',
  '/media/icons/online-camera.png',
  '/media/icons/online-person.png'
]

const metricCards = computed(() => {
  const m = demo.metrics
  return [
    { label: '今日违规事件', value: m.todayViolations, delta: m.todayViolationsDelta, first: true },
    { label: '处置中事件', value: m.processingEvents, delta: m.processingEventsDelta },
    { label: '在线设备', value: m.onlineDevices, delta: m.onlineDevicesDelta },
    { label: '在线人员', value: m.onlineStaff, delta: m.onlineStaffDelta }
  ]
})

const fmt = (n: number) => n.toLocaleString('zh-CN')

/* ---------------- 健康环 ---------------- */
const rings = computed(() => {
  const h = demo.health
  return [
    { label: '设备在线率', value: h.deviceOnlineRate, c1: '#05a9cb', c2: '#137de4' },
    { label: '服务可用率', value: h.serviceAvailability, c1: '#00a970', c2: '#0faec0' },
    { label: '存储健康度', value: h.storageHealth, c1: '#43b77a', c2: '#43b77a' }
  ]
})

function ringStyle(r: { value: number; c1: string; c2: string }) {
  const v = Math.max(0, Math.min(100, r.value))
  const mid = +(v * 0.73).toFixed(1)
  return {
    background: `conic-gradient(${r.c1} 0 ${mid}%, ${r.c2} ${mid}% ${v}%, #dce7ed ${v}% 100%)`
  }
}

/* ---------------- 风险热力图（ECharts 替换 PNG 贴图） ---------------- */
const heatmapOption = computed(() => {
  const cams = demo.cameras
  const events = demo.events
  if (!cams.length) return {} as EChartsOption

  const weightByCam = new Map<string, number>()
  events.forEach((e) => weightByCam.set(e.camera_id, (weightByCam.get(e.camera_id) ?? 0) + 1))

  const lats = cams.map((c) => c.latitude)
  const lons = cams.map((c) => c.longitude)
  let minLat = Math.min(...lats)
  let maxLat = Math.max(...lats)
  let minLon = Math.min(...lons)
  let maxLon = Math.max(...lons)

  // 点位包围盒近似方形（校园约 450m × 470m），而绘图区是 2.25:1。
  // 若直接映射，数据坐标会被非等比拉伸，圆形热斑会被拉成横椭圆。
  // 这里按「地面真实距离之比 = 绘图区像素之比」反推需要补足的边长。
  const PLOT_W = 428
  const PLOT_H = 190
  const midLat = (minLat + maxLat) / 2
  const kx = Math.cos((midLat * Math.PI) / 180)
  const mPerLon = kx * 111320
  const mPerLat = 110540
  const groundX = (maxLon - minLon) * mPerLon
  const groundY = (maxLat - minLat) * mPerLat
  const targetAspect = PLOT_W / PLOT_H
  if (groundX / Math.max(groundY, 1) < targetAspect) {
    const need = (groundY * targetAspect - groundX) / 2
    minLon -= need / mPerLon
    maxLon += need / mPerLon
  } else {
    const need = (groundX / targetAspect - groundY) / 2
    minLat -= need / mPerLat
    maxLat += need / mPerLat
  }
  // 再按「地面距离」外扩边距，保证高斯晕圈完整落在卡内（按百分比给会裁掉边缘热点）
  const padMeters = 180
  minLon -= padMeters / mPerLon
  maxLon += padMeters / mPerLon
  minLat -= padMeters / mPerLat
  maxLat += padMeters / mPerLat

  const NX = 36
  const NY = 22
  const data: [number, number, number][] = []
  let peak = 0

  for (let i = 0; i < NX; i++) {
    for (let j = 0; j < NY; j++) {
      const lon = minLon + ((maxLon - minLon) * i) / (NX - 1)
      const lat = minLat + ((maxLat - minLat) * j) / (NY - 1)
      let w = 0
      cams.forEach((c, cameraIndex) => {
        // 经度投影修正：1° 经度的地面距离 ≈ cos(lat) × 1° 纬度（对应修订说明缺陷 B10）
        const kx = Math.cos((lat * Math.PI) / 180)
        const dx = (lon - c.longitude) * kx * 111320
        const dy = (lat - c.latitude) * 110540
        const sigma = 130
        // 演示数据较少时仍给每个在线点位一个稳定基线，避免热力图只剩一个像素块。
        const cw = weightByCam.get(c.camera_id) ?? (4 + (cameraIndex * 3) % 8)
        w += cw * Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
      })
      peak = Math.max(peak, w)
      data.push([i, j, w])
    }
  }

  // 归一化后做幂次强调：让低值迅速落到浅色区，热区收敛成局部热点。
  // （核带宽必须显著小于点位包围盒，否则四点高斯叠加会铺满整张卡片。）
  data.forEach((d) => (d[2] = +(peak ? Math.pow(d[2] / peak, 1.25) : 0).toFixed(3)))

  return {
    animation: false,
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'category', data: Array.from({ length: NX }, (_, i) => i), show: false },
    yAxis: { type: 'category', data: Array.from({ length: NY }, (_, i) => i), show: false },
    visualMap: {
      show: false,
      min: 0,
      max: 1,
      inRange: {
        color: [
          '#f6fafd',
          '#e3f2fa',
          '#c3e4f4',
          '#8fcfe8',
          '#7fd6b4',
          '#f2d06b',
          '#f0944a',
          '#e24b4a'
        ]
      }
    },
    series: [
      {
        type: 'heatmap',
        data,
        // pointSize 必须显式大于「单元格最小边长」，否则 ECharts 会取两轴最小值，
        // 横向单元格之间留出缝隙，呈现出规则白点阵。blurSize 用于抹平块状边界。
        pointSize: 14,
        blurSize: 12,
        emphasis: { disabled: true },
        itemStyle: { borderRadius: 0 }
      }
    ]
  } as EChartsOption
})

/* ---------------- 近 7 日趋势 ---------------- */
const trendOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 40, right: 16, top: 36, bottom: 26 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: demo.trend.map((t) => t.date),
        axisLine: { lineStyle: { color: '#dbe6ee' } },
        axisTick: { show: false },
        axisLabel: { fontSize: 10, color: '#41516b', fontFamily: 'Microsoft YaHei' }
      },
      yAxis: {
        type: 'value',
        max: demo.scale.trendMax,
        splitLine: { lineStyle: { color: '#dbe6ee' } },
        axisLabel: { fontSize: 10, color: '#41516b', fontFamily: 'Microsoft YaHei' }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,.96)',
        borderColor: '#d7e5f0',
        textStyle: { color: '#172743', fontSize: 12 }
      },
      series: [
        {
          name: '识别事件',
          type: 'line',
          symbol: 'circle',
          symbolSize: 6,
          data: demo.trend.map((t) => t.detected),
          lineStyle: { width: 2, color: '#137de4' },
          itemStyle: { color: '#137de4', borderColor: '#fff', borderWidth: 1 }
        },
        {
          name: '已处置事件',
          type: 'line',
          symbol: 'circle',
          symbolSize: 6,
          data: demo.trend.map((t) => t.handled),
          lineStyle: { width: 2, color: '#25a47b' },
          itemStyle: { color: '#25a47b', borderColor: '#fff', borderWidth: 1 }
        }
      ]
    }) as EChartsOption
)

/* ---------------- 区域事件排名 ---------------- */
interface RankRow {
  area: string
  total: number
  share: number
  progress: number
}

const ranking = computed<RankRow[]>(() => {
  const counter = new Map<string, number>()
  demo.events.forEach((e) => {
    const area = areaOf(e)
    counter.set(area, (counter.get(area) ?? 0) + 1)
  })
  const seedAreas = [
    ['信阳学院北门', 18], ['学生食堂东侧', 15], ['体育馆西广场', 12],
    ['学院路公交站', 10], ['图书馆东侧', 8], ['校园南门步道', 6]
  ] as const
  seedAreas.forEach(([area, total]) => {
    if (!counter.has(area)) counter.set(area, total)
  })
  const rows = [...counter.entries()].map(([area, total]) => ({ area, total }))
  const sum = rows.reduce((a, b) => a + b.total, 0) || 1

  const byArea = new Map<string, { done: number; all: number }>()
  demo.workOrders.forEach((o) => {
    const cur = byArea.get(o.location_name) ?? { done: 0, all: 0 }
    cur.all += 1
    if (o.status === 'completed' || o.status === 'closed') cur.done += 1
    byArea.set(o.location_name, cur)
  })

  return rows
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
    .map((r) => {
      const d = byArea.get(r.area)
      return {
        area: r.area,
        total: r.total,
        share: +((r.total / sum) * 100).toFixed(1),
        progress: d && d.all ? Math.round((d.done / d.all) * 100) : 58 + ((r.total * 7) % 38)
      }
    })
})

/* ---------------- 事件等级 / 编号 / 状态 ---------------- */
function areaOf(ev: ViolationEvent) {
  return demo.cameras.find((c) => c.camera_id === ev.camera_id)?.location_name ?? ev.camera_name
}

function levelOf(ev: ViolationEvent) {
  if (ev.confidence >= 0.9) return { text: '高风险', cls: 'tag red' }
  if (ev.confidence >= 0.82) return { text: '中风险', cls: 'tag orange' }
  return { text: '低风险', cls: 'tag green' }
}

function eventNo(ev: ViolationEvent) {
  const d = new Date(ev.event_timestamp)
  const p = (n: number) => (n < 10 ? `0${n}` : `${n}`)
  const seq = String(ev.id % 1000 || 1).padStart(3, '0')
  return `EVT${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${seq}`
}

function statusOf(ev: ViolationEvent) {
  const order = demo.workOrders.find((o) => o.event_id === ev.event_id)
  if (!order || order.status === 'pending' || order.status === 'timeout') {
    return { text: '待复核', cls: 'tag blue' }
  }
  if (order.status === 'completed' || order.status === 'closed') {
    return { text: '已闭环', cls: 'tag green' }
  }
  return { text: '处置中', cls: 'tag orange' }
}

/* ---------------- 事件详情 ---------------- */
const selected = ref<ViolationEvent | null>(null)
const currentEvent = computed(() => selected.value ?? demo.events[0] ?? null)

function selectEvent(ev: ViolationEvent) {
  selected.value = ev
}

function fmtTs(ts: string) {
  const d = new Date(ts)
  const p = (n: number) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes()
  )}:${p(d.getSeconds())}`
}

function watchTrack() {
  ElMessage.info('轨迹回放面板将在「告警数据列表」页实现')
  router.push({ name: 'alerts' })
}

function handleNow() {
  ElMessage.success('已派发清理工单，可在「调度中心 · 任务池」查看')
  router.push({ name: 'dispatch-pool' })
}
</script>

<template>
  <div class="overview">
    <!-- ============ Hero ============ -->
    <section class="hero">
      <img
        :key="currentHero.image"
        class="hero-art composite"
        :src="currentHero.image"
        alt=""
      />
      <div class="hero-copy">
        <h1>{{ currentHero.title }}</h1>
        <p>{{ currentHero.sub }}</p>
        <button class="hero-button" type="button" @click="router.push({ name: 'governance' })">
          查看项目态势
        </button>
      </div>
      <button class="hero-arrow left" type="button" aria-label="上一张" @click="changeHero(-1)">
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#1f344d" stroke-width="1.7">
          <path d="m10 3-5 5 5 5" />
        </svg>
      </button>
      <button class="hero-arrow right" type="button" aria-label="下一张" @click="changeHero(1)">
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#1f344d" stroke-width="1.7">
          <path d="m6 3 5 5-5 5" />
        </svg>
      </button>
      <div class="hero-dots">
        <button v-for="(_, i) in HERO_SLIDES" :key="i" type="button" :class="{ on: i === heroIndex }" :aria-label="`第 ${i + 1} 张`" @click="setHero(i)" />
      </div>
      <span class="demo-flag">演示数据 · {{ demo.scale.label }}</span>
    </section>

    <!-- ============ 指标卡 ============ -->
    <section class="metrics">
      <article v-for="(m, i) in metricCards" :key="m.label" class="metric-card">
        <img class="metric-icon" :src="METRIC_ICONS[i]" alt="" />
        <div class="metric-label">{{ m.label }}</div>
        <div class="metric-value yz-num" :class="{ first: m.first }">{{ fmt(m.value) }}</div>
        <div class="metric-change">
          同比
          <span :class="m.delta <= 0 ? 'down' : 'up'">
            {{ m.delta > 0 ? '+' : '' }}{{ m.delta }}%
            <b>{{ m.delta <= 0 ? '↓' : '↑' }}</b>
          </span>
        </div>
      </article>
    </section>

    <!-- ============ 事件详情 ============ -->
    <section class="card detail-card">
      <h2 class="detail-title">事件详情</h2>
      <button class="close-button" type="button" aria-label="收起" @click="selected = null">
        <svg viewBox="0 0 14 14" width="13" height="13" fill="none" stroke="#41516b" stroke-width="1.6">
          <path d="M3 3l8 8M11 3l-8 8" />
        </svg>
      </button>

      <div v-if="currentEvent" class="detail-meta">
        <div><b>事件编号</b>{{ eventNo(currentEvent) }}</div>
        <div>
          <b>事件等级</b>
          <span :class="levelOf(currentEvent).cls">{{ levelOf(currentEvent).text }}</span>
        </div>
        <div><b>所属区域</b>{{ areaOf(currentEvent) }}</div>
        <div><b>发生时间</b>{{ fmtTs(currentEvent.event_timestamp) }}</div>
        <div><b>事件类型</b>乱扔烟头</div>
      </div>

      <div class="analysis-box">
        <div class="box-title">AI分析结论</div>
        <div class="analysis-text">
          检测到目标人员完成持烟、抛掷及烟头落地动作，<br />三段式证据链校验通过，判定为违规乱扔烟头。
        </div>
        <div class="confidence" />
        <div class="confidence-label">{{ ((currentEvent?.confidence ?? 0) * 100).toFixed(1) }}%</div>
      </div>

      <div class="evidence-box">
        <div class="box-title">事件截图</div>
        <img
          class="evidence-photo"
          :src="currentEvent?.evidence_frames[0]?.path"
          alt="证据关键帧"
        />
      </div>

      <div class="suggest-box">
        <div class="box-title">处理建议</div>
        <div class="suggest-text">
          建议立即调派环卫任务，清理点位并加强巡查，<br />对当事人进行文明吸烟宣传教育。
        </div>
      </div>

      <div class="detail-actions">
        <button class="watch-button" type="button" @click="watchTrack">查看录像</button>
        <button class="handle-button" type="button" @click="handleNow">事件处置</button>
      </div>
    </section>

    <!-- ============ 风险热力图 ============ -->
    <section class="card heatmap-card">
      <h2 class="section-title">风险热力图</h2>
      <div class="heatmap-chart"><EChart :option="heatmapOption" /></div>
      <span class="heat-place hp1">学院北门</span><span class="heat-place hp2">学生食堂</span><span class="heat-place hp3">体育馆</span><span class="heat-place hp4">学院路口</span>
      <div class="heatmap-legend"><span>低</span><i></i><span>高</span></div>
      <div class="heatmap-note">学院路口 · 食堂东侧 · 体育馆广场等模拟热点</div>
    </section>

    <!-- ============ 系统健康监测 ============ -->
    <section class="card health-card">
      <h2 class="section-title">系统健康监测</h2>
      <div class="rings">
        <div v-for="r in rings" :key="r.label" class="ring" :style="ringStyle(r)">
          <div class="ring-content">
            {{ r.label }}
            <strong>{{ r.value }}%</strong>
          </div>
        </div>
      </div>
      <div class="health-links">
        <button class="health-link" type="button" @click="router.push({ name: 'device-archive' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke-width="1.4">
            <path d="M3 5h10v8H3zM5 5V3h6v2M6 8h4M6 10h3" />
          </svg>
          设备管理
        </button>
        <button class="health-link" type="button" @click="router.push({ name: 'ai-config' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke-width="1.4">
            <rect x="2" y="3" width="12" height="8" rx="1" />
            <path d="M6 14h4M8 11v3M5 7l2 2 4-4" />
          </svg>
          系统监控
        </button>
        <button class="health-link" type="button" @click="router.push({ name: 'audit' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke-width="1.4">
            <path d="M4 2h7l2 2v10H4zM6 7h5M6 9h5M6 11h3" />
          </svg>
          日志审计
        </button>
      </div>
    </section>

    <!-- ============ 近 7 日趋势 ============ -->
    <section class="card trend-card">
      <h2 class="section-title">近7日事件趋势</h2>
      <div class="trend-legend">
        <span><i style="background: #137de4" />识别事件</span>
        <span><i style="background: #25a47b" />已处置事件</span>
      </div>
      <div class="trend-chart"><EChart :option="trendOption" /></div>
    </section>

    <!-- ============ 区域事件排名 ============ -->
    <section class="card ranking-card">
      <h2 class="section-title">区域事件排名</h2>
      <div class="table ranking-table">
        <div class="table-row table-head">
          <span class="table-cell">排名</span>
          <span class="table-cell">区域</span>
          <span class="table-cell">事件数量</span>
          <span class="table-cell">占比</span>
          <span class="table-cell">处置进度</span>
        </div>
        <div v-for="(r, i) in ranking" :key="r.area" class="table-row">
          <span class="table-cell">{{ i + 1 }}</span>
          <span class="table-cell strong">{{ r.area }}</span>
          <span class="table-cell">{{ r.total }}</span>
          <span class="table-cell">{{ r.share }}%</span>
          <span class="table-cell">
            <span class="progress-cell">
              <span class="progress"><i :style="{ width: r.progress + '%' }" /></span>
              <span class="percent">{{ r.progress }}%</span>
            </span>
          </span>
        </div>
      </div>
    </section>

    <!-- ============ 实时事件 ============ -->
    <section class="card events-card">
      <h2 class="section-title">实时事件</h2>
      <div class="table events-table">
        <div class="table-row table-head">
          <span class="table-cell">事件编号</span>
          <span class="table-cell">事件等级</span>
          <span class="table-cell">所属区域</span>
          <span class="table-cell">处理状态</span>
          <span class="table-cell">操作</span>
        </div>
        <div
          v-for="ev in demo.events.slice(0, 5)"
          :key="ev.event_id"
          class="table-row clickable"
          :class="{ on: currentEvent?.event_id === ev.event_id }"
          @click="selectEvent(ev)"
        >
          <span class="table-cell">{{ eventNo(ev) }}</span>
          <span class="table-cell">
            <span :class="levelOf(ev).cls">{{ levelOf(ev).text }}</span>
          </span>
          <span class="table-cell strong">{{ areaOf(ev) }}</span>
          <span class="table-cell">
            <span :class="statusOf(ev).cls">{{ statusOf(ev).text }}</span>
          </span>
          <span class="table-cell">
            <button class="mini-action" type="button" @click.stop="selectEvent(ev)">查看</button>
            <button class="mini-action" type="button" @click.stop="handleNow">处置</button>
          </span>
        </div>
      </div>
    </section>

    <!-- 偏高视口的补充信息带：16:9 答辩屏隐藏，较高窗口用于填充额外纵向空间 -->
    <section class="overview-extra" aria-label="平台实时运行摘要">
      <span><i class="live"></i><b>识别服务正常</b><small>最近心跳 8 秒前</small></span>
      <span><i></i><b>今日闭环率 84.6%</b><small>较昨日提升 3.2%</small></span>
      <span><i></i><b>平均响应 18 分钟</b><small>6 个班组在线</small></span>
      <span><i></i><b>证据留痕完整</b><small>操作日志持续写入</small></span>
    </section>
  </div>
</template>

<style scoped>
.overview {
  position: absolute;
  inset: 0;
}
.overview-extra {
  display: none;
  position: absolute;
  left: 13px;
  right: 11px;
  top: 860px;
  bottom: 12px;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.overview-extra span {
  display: grid;
  grid-template-columns: 10px 1fr;
  align-content: center;
  column-gap: 8px;
  padding: 8px 14px;
  border: 1px solid #dbe8f2;
  border-radius: 10px;
  background: rgba(255,255,255,.72);
}
.overview-extra i { grid-row:1/3;width:7px;height:7px;margin-top:4px;border-radius:50%;background:#2f86ed; }
.overview-extra i.live { background:#24aa78;box-shadow:0 0 0 4px rgba(36,170,120,.12); }
.overview-extra b { color:#31445d;font-size:12px; }
.overview-extra small { margin-top:2px;color:#8b98a7;font-size:10px; }
@media (max-aspect-ratio: 7/4) {
  .overview-extra { display:grid; }
}

/* ---------------- Hero ---------------- */
.hero {
  position: absolute;
  left: 13px;
  top: 15px;
  width: 1648px;
  height: 235px;
  border-radius: var(--yz-radius-card);
  overflow: hidden;
  background: #176b9b;
}
.hero-art {
  position: absolute;
  left: 0;
  top: 0;
  width: 1648px;
  height: 235px;
  object-fit: cover;
  object-position: center;
  z-index: 0;
  animation: hero-in .45s ease both;
}
@keyframes hero-in { from { opacity:.4;transform:scale(1.015); } to { opacity:1;transform:scale(1); } }
.hero-copy {
  position: absolute;
  left: 49px;
  top: 44px;
  z-index: 4;
  width: 360px;
  color: #fff;
}
.hero-copy h1 {
  font-size: 21px;
  line-height: 1.55;
  font-weight: 700;
  letter-spacing: 0.2px;
  white-space: pre-line;
}
.hero-copy p {
  margin-top: 8px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.hero-button {
  margin-top: 25px;
  width: 115px;
  height: 30px;
  color: #fff;
  background: rgba(4, 126, 190, 0.42);
  border: 1px solid #fff;
  border-radius: 17px;
  font-size: 12px;
}
.hero-arrow {
  position: absolute;
  z-index: 5;
  top: 94px;
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(30, 100, 150, 0.18);
  display: grid;
  place-items: center;
}
.hero-arrow.left {
  left: 7px;
}
.hero-arrow.right {
  right: 8px;
}
.hero-dots {
  position: absolute;
  z-index: 5;
  left: 774px;
  bottom: 13px;
  display: flex;
  gap: 15px;
}
.hero-dots button {
  display: block;
  width: 14px;
  height: 14px;
  padding: 0;
  border-radius: 50%;
  background: #f7fafc;
  border: 1px solid #b8c6ce;
}
.hero-dots button.on {
  background: #fff;
  box-shadow: 0 0 0 2px rgba(255,255,255,.28);
}
.demo-flag {
  position: absolute;
  right: 16px;
  top: 14px;
  z-index: 5;
  padding: 4px 12px;
  border-radius: var(--yz-radius-pill);
  background: rgba(255, 255, 255, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.55);
  color: #fff;
  font-size: 11px;
  letter-spacing: 0.4px;
}

/* ---------------- 通用卡片 ---------------- */
.card {
  position: absolute;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid #dbe8f2;
  border-radius: 11px;
  box-shadow: 0 2px 7px rgba(61, 112, 150, 0.06);
}
.section-title {
  position: absolute;
  left: 18px;
  top: 9px;
  font-size: 14px;
  font-weight: 700;
  color: var(--yz-text-strong);
  white-space: nowrap;
}

/* ---------------- 指标卡 ---------------- */
.metrics {
  position: absolute;
  left: 13px;
  top: 261px;
  width: 1240px;
  height: 110px;
  display: flex;
  gap: 11px;
}
.metric-card {
  position: relative;
  width: 298px;
  height: 110px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid #dbe8f2;
  border-radius: 11px;
  box-shadow: 0 2px 7px rgba(61, 112, 150, 0.06);
}
.metric-icon {
  position: absolute;
  object-fit: contain;
}
.metric-card:nth-child(1) .metric-icon {
  left: 27px;
  top: 19px;
  width: 52px;
  height: 62px;
}
.metric-card:nth-child(2) .metric-icon {
  left: 29px;
  top: 20px;
  width: 45px;
  height: 61px;
}
.metric-card:nth-child(3) .metric-icon {
  left: 18px;
  top: 18px;
  width: 60px;
  height: 62px;
}
.metric-card:nth-child(4) .metric-icon {
  left: 26px;
  top: 16px;
  width: 61px;
  height: 65px;
}
.metric-label {
  position: absolute;
  left: 101px;
  top: 17px;
  font-size: 13px;
  color: #35465e;
  white-space: nowrap;
}
.metric-value {
  position: absolute;
  left: 101px;
  top: 39px;
  font-size: 29px;
  line-height: 34px;
  font-weight: 700;
  color: #117fba;
  white-space: nowrap;
}
.metric-value.first {
  color: #1478e5;
}
.metric-change {
  position: absolute;
  left: 101px;
  top: 80px;
  font-size: 12px;
  color: #40506a;
  white-space: nowrap;
}
.metric-change .down,
.metric-change .up {
  font-size: 14px;
  font-weight: 700;
}
.down {
  color: #00a971;
}
.up {
  color: #fb5b4b;
}
.down b,
.up b {
  font-size: 17px;
}

/* ---------------- 事件详情 ---------------- */
.detail-card {
  left: 1264px;
  top: 261px;
  width: 396px;
  height: 589px;
}
.detail-title {
  position: absolute;
  left: 19px;
  top: 17px;
  font-size: 15px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.close-button {
  position: absolute;
  right: 17px;
  top: 13px;
  width: 31px;
  height: 31px;
  padding: 0;
  border: 1px solid #d2e1ed;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
}
.detail-meta {
  position: absolute;
  left: 19px;
  top: 44px;
  width: 356px;
  font-size: 11px;
  line-height: 23px;
  color: #41516a;
}
.detail-meta b {
  display: inline-block;
  width: 87px;
  color: #58677b;
  font-weight: 400;
}
.risk {
  color: #f55d51;
  background: #fff0ee;
  border: 1px solid #ffc5bd;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 6px;
}
.analysis-box,
.evidence-box,
.suggest-box {
  position: absolute;
  left: 10px;
  width: 376px;
  border: 1px solid #dce8f1;
  border-radius: var(--yz-radius-input);
  background: rgba(248, 251, 253, 0.72);
}
.analysis-box {
  top: 157px;
  height: 99px;
}
.evidence-box {
  top: 263px;
  height: 179px;
}
.suggest-box {
  top: 449px;
  height: 64px;
}
.box-title {
  position: absolute;
  left: 10px;
  top: 9px;
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.analysis-text {
  position: absolute;
  left: 10px;
  top: 33px;
  width: 348px;
  color: #4e5e72;
  font-size: 11px;
  line-height: 17px;
}
.confidence {
  position: absolute;
  left: 10px;
  top: 70px;
  width: 345px;
  height: 6px;
  background: #dce5eb;
  border-radius: 6px;
}
.confidence::before {
  content: "";
  display: block;
  width: 92%;
  height: 6px;
  border-radius: 6px;
  background: linear-gradient(90deg, #16a8dd, #2ab36c);
}
.confidence-label {
  position: absolute;
  right: 9px;
  top: 60px;
  font-size: 11px;
  color: #41516a;
}
.evidence-photo {
  position: absolute;
  left: 7px;
  top: 35px;
  width: 359px;
  height: 142px;
  object-fit: cover;
  border-radius: 7px;
  background: #e9eff4;
}
.suggest-text {
  position: absolute;
  left: 10px;
  top: 31px;
  color: #526174;
  font-size: 11px;
  line-height: 17px;
}
.detail-actions {
  position: absolute;
  left: 10px;
  bottom: 18px;
  width: 376px;
  display: flex;
  gap: 18px;
}
.detail-actions button {
  height: 44px;
  border-radius: var(--yz-radius-input);
  font-size: 14px;
  font-weight: 700;
}
.watch-button {
  width: 150px;
  color: #087fc2;
  border: 1px solid #0b9cdb;
  background: #fff;
}
.handle-button {
  width: 207px;
  color: #fff;
  border: 0;
  background: linear-gradient(100deg, #087cf0, #05bd8d);
}

/* ---------------- 中部三卡 ---------------- */
.heatmap-card {
  left: 13px;
  top: 381px;
  width: 444px;
  height: 229px;
}
.heatmap-chart {
  position: absolute;
  left: 8px;
  top: 30px;
  width: 428px;
  height: 190px;
  border-radius: var(--yz-radius-input);
  overflow: hidden;
  background:linear-gradient(rgba(44,115,155,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(44,115,155,.07) 1px,transparent 1px),linear-gradient(145deg,#eef7fb,#f7fbfd);background-size:34px 34px,34px 34px,auto;
}
.heat-place{position:absolute;z-index:2;padding:2px 5px;border-radius:4px;background:rgba(255,255,255,.78);color:#536b80;font-size:8px}.hp1{left:64px;top:80px}.hp2{left:205px;top:92px}.hp3{left:302px;top:143px}.hp4{left:116px;top:171px}
.heatmap-legend{position:absolute;left:22px;right:22px;bottom:13px;z-index:3;display:flex;align-items:center;gap:7px;color:#63778c;font-size:10px}.heatmap-legend i{width:92px;height:7px;border-radius:999px;background:linear-gradient(90deg,#c3e4f4,#7fd6b4,#f2d06b,#e24b4a)}.heatmap-note{position:absolute;right:17px;bottom:12px;z-index:3;color:#607489;font-size:9px}
.health-card {
  left: 466px;
  top: 381px;
  width: 359px;
  height: 229px;
}
.rings {
  position: absolute;
  left: 15px;
  top: 41px;
  display: flex;
  gap: 17px;
}
.ring {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
}
.ring::after {
  content: "";
  position: absolute;
  inset: 8px;
  background: #f8fbfd;
  border-radius: 50%;
}
.ring-content {
  position: relative;
  z-index: 1;
  text-align: center;
  font-size: 10px;
  color: #526176;
  white-space: nowrap;
}
.ring-content strong {
  display: block;
  margin-top: 4px;
  color: var(--yz-text-strong);
  font-size: 18px;
}
.health-links {
  position: absolute;
  left: 15px;
  top: 172px;
  display: flex;
  gap: 15px;
}
.health-link {
  width: 96px;
  height: 37px;
  padding: 0;
  border: 1px solid #dbe8f1;
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #41516b;
  font-size: 11px;
  white-space: nowrap;
}
.health-link:hover {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}
.health-link svg {
  stroke: #00a2b9;
}
.trend-card {
  left: 835px;
  top: 381px;
  width: 418px;
  height: 229px;
}
.trend-legend {
  position: absolute;
  left: 0;
  right: 0;
  top: 32px;
  display: flex;
  justify-content: center;
  gap: 34px;
  font-size: 11px;
  color: #41516b;
}
.trend-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.trend-legend i {
  display: block;
  width: 14px;
  height: 3px;
  border-radius: 2px;
}
.trend-chart {
  position: absolute;
  left: 8px;
  top: 34px;
  width: 402px;
  height: 186px;
}

/* ---------------- 底部两表 ---------------- */
.ranking-card {
  left: 13px;
  top: 620px;
  width: 542px;
  height: 230px;
}
.events-card {
  left: 565px;
  top: 620px;
  width: 688px;
  height: 230px;
}
.table {
  position: absolute;
  left: 8px;
  top: 28px;
  width: calc(100% - 16px);
  border: 1px solid #dce8f1;
  border-radius: 7px;
  overflow: hidden;
  font-size: 11px;
}
.table-row {
  height: 36px;
  display: grid;
  align-items: center;
  border-bottom: 1px solid #e1ebf2;
  color: #42536d;
}
.table-row:last-child {
  border-bottom: 0;
}
.ranking-table .table-row {
  grid-template-columns: 74px 111px 100px 75px 1fr;
  height: 31px;
}
.ranking-table .table-row.table-head {
  height: 30px;
}
.events-table .table-row {
  grid-template-columns: 190px 127px 127px 125px 1fr;
}
/* 实时事件表格必须**装得进**这张 230px 高的卡片。
   原先行高 36px：表头 31 + 5 行 ×36 = 211，加上 28px 的表格上边距共 239 > 230，
   最后一行溢出卡片 12px，正好压到下方 `.overview-extra` 信息带上（实测重叠 2px），
   看上去就像"文字框重合"。这里把行高压到 33 / 表头 30，总高 195，留 7px 余量。 */
.events-table .table-row {
  height: 33px;
}
.events-table .table-row.table-head {
  height: 30px;
}
.table-head {
  height: 31px;
  background: #f5f9fc;
  color: #637189;
}
.table-cell {
  padding-left: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-cell.strong {
  color: var(--yz-text-strong);
  font-weight: 700;
}
.table-cell.mono {
  font-family: Consolas, Monaco, monospace;
  letter-spacing: 0.3px;
}
.clickable {
  cursor: pointer;
}
.clickable:hover {
  background: #f2f8fe;
}
.clickable.on {
  background: #e9f4ff;
}
/* ---- 状态 / 等级标签（对应设计稿 .tag 系列） ---- */
.tag {
  display: inline-block;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 10px;
  line-height: 13px;
}
.tag.red {
  color: #f05a4e;
  background: #fff0ee;
  border: 1px solid #ffc6be;
}
.tag.orange {
  color: #e99222;
  background: #fff7e8;
  border: 1px solid #ffd79b;
}
.tag.green {
  color: #25a47b;
  background: #ebfaf4;
  border: 1px solid #bdebd9;
}
.tag.blue {
  color: #2789d0;
  background: #eef8ff;
  border: 1px solid #bbdef4;
}

/* ---- 处置进度条（对应设计稿 .progress / .percent） ---- */
.progress-cell {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
}
.progress {
  display: block;
  flex: 0 0 82px;
  width: 82px;
  height: 7px;
  border-radius: 7px;
  background: #e4ebf0;
}
.progress i {
  display: block;
  height: 7px;
  border-radius: 7px;
  background: linear-gradient(90deg, #238aff, #32be88);
}
.percent {
  min-width: 34px;
  color: #526176;
}

/* ---- 表格行内迷你操作（对应设计稿 .mini-action） ---- */
.mini-action {
  color: #168dc2;
  border: 1px solid #b5dceb;
  background: #f5fbfe;
  border-radius: 4px;
  padding: 3px 7px;
  margin-right: 7px;
  font-size: 10px;
}
.mini-action:hover {
  background: #e9f6fc;
}
</style>

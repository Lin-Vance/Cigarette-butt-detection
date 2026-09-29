<script setup lang="ts">
/** 页面 10 · 全域治理 GIS 地图
 *
 * 2026-09-28 细化：原先整张图只有 5 台设备 × 2 个图层 = 10 个点，几乎是一块空画布。
 * 现在补齐四层信息，让"全域"真的看得出细节：
 *   ① 行政区分区着色（3×2，数字＝该区近 7 天事件数，颜色按密度分级）
 *   ② 事件点位按摄像机扇出（同一台设备的多次事件不再叠成一个点）
 *   ③ 任务点（来自工单）与烟蒂投放设施点
 *   ④ 兴趣点（学校/医院/商圈/公园/公厕/站点）+ 千米网格 + 比例尺
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import GaodeTileMap, { type TileMarker } from '@/components/GaodeTileMap.vue'
import type {
  MapMarker,
  MapPoi,
  MapZone
} from '@/components/ui/YzMapStage.vue'
import { useDemoStore } from '@/stores/demo'
import { buildTaskRows, eventNo, fmtDateTime, levelOf, projectToMap } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const layers = ref({
  zones: true,
  devices: true,
  events: true,
  heat: true,
  tasks: true,
  facilities: true,
  pois: true
})
const picked = ref<{ kind: 'event' | 'camera'; id: string } | null>(null)
const boxed = ref(false)
const refreshedAt = ref(new Date())

const LAYER_DEFS = [
  { key: 'zones', label: '行政区分区' },
  { key: 'devices', label: '设备点位' },
  { key: 'events', label: '事件点位' },
  { key: 'heat', label: '风险热力' },
  { key: 'tasks', label: '任务点' },
  { key: 'facilities', label: '烟蒂设施' },
  { key: 'pois', label: '兴趣点' }
] as const

const projectedCams = computed(() => projectToMap(demo.cameras.map((c) => ({ ...c }))))

/** 稳定的伪随机：同一个 id 永远得到同一个偏移，避免每次刷新点位乱跳 */
function jitter(seed: string, span: number): [number, number] {
  let h = 2166136261
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  const a = ((h >>> 0) % 1000) / 1000
  const b = (((h >>> 10) >>> 0) % 1000) / 1000
  return [(a - 0.5) * span, (b - 0.5) * span]
}

/* ---------------- 分区：3×2 六区，数字＝区内事件数 ---------------- */
const ZONE_DEFS = [
  { id: 'shihe', name: '浉河区', x: 0, y: 0 },
  { id: 'pingqiao', name: '平桥区', x: 533, y: 0 },
  { id: 'gaoxin', name: '高新区', x: 1067, y: 0 },
  { id: 'guangshan', name: '光山县', x: 0, y: 360 },
  { id: 'luoshan', name: '罗山县', x: 533, y: 360 },
  { id: 'yangshan', name: '羊山新区', x: 1067, y: 360 }
]
const ZONE_W = 533
const ZONE_H = 360

/** 事件点位：按摄像机位置扇开，同一台设备的多次事件不叠点 */
const eventPins = computed(() =>
  demo.events.slice(0, 40).map((ev, i) => {
    const hit = projectedCams.value.find(({ item }) => item.camera_id === ev.camera_id)
    const base = hit ? { x: hit.x, y: hit.y } : { x: 200 + (i % 6) * 200, y: 120 + (i % 4) * 160 }
    const [dx, dy] = jitter(ev.event_id || `ev${i}`, 74)
    const lv = levelOf(ev.confidence)
    return {
      id: `E-${ev.event_id || i}`,
      x: +(base.x + dx).toFixed(1),
      y: +(base.y + dy).toFixed(1),
      kind: (lv.key === 'high' ? 'high' : 'mid') as MapMarker['kind'],
      label: `${eventNo(ev)} · ${ev.camera_name ?? ev.camera_id} · 置信度 ${ev.confidence}%`
    }
  })
)

const zones = computed<MapZone[]>(() => {
  const zoneOf = (x: number, y: number) =>
    ZONE_DEFS.findIndex((z) => x >= z.x && x < z.x + ZONE_W && y >= z.y && y < z.y + ZONE_H)
  const events = ZONE_DEFS.map(() => 0)
  const devices = ZONE_DEFS.map(() => 0)
  eventPins.value.forEach((p) => {
    const i = zoneOf(p.x, p.y)
    if (i >= 0) events[i] += 1
  })
  projectedCams.value.forEach((p) => {
    const i = zoneOf(p.x, p.y)
    if (i >= 0) devices[i] += 1
  })
  const max = Math.max(1, ...events)
  // 区名后面带上该区摄像机路数：事件为 0 的区也不至于看起来"空白"
  return ZONE_DEFS.map((z, i) => ({
    ...z,
    name: `${z.name} · ${devices[i]} 路设备`,
    w: ZONE_W,
    h: ZONE_H,
    value: events[i],
    max
  }))
})

/** 设备点位 */
const deviceMarkers = computed<MapMarker[]>(() =>
  projectedCams.value.map(({ item, x, y }) => ({
    id: `D-${item.camera_id}`,
    x,
    y,
    kind: item.status === 'online' ? 'online' : 'offline',
    label: `${item.camera_id} ${item.location_name} · ${item.status === 'online' ? '在线' : '离线'} · ${item.fps}fps`
  }))
)

/** 任务点：取未闭环工单，落在所属摄像机附近 */
const taskMarkers = computed<MapMarker[]>(() => {
  const open = demo.workOrders.filter((o) => o.status !== 'closed').slice(0, 10)
  return open.map((o, i) => {
    const hit = projectedCams.value.find(({ item }) => item.camera_id === o.camera_id)
    const base = hit ? { x: hit.x, y: hit.y } : { x: 260 + (i % 5) * 260, y: 200 + (i % 3) * 200 }
    const [dx, dy] = jitter(o.order_no || String(o.id), 52)
    return {
      id: `T-${o.order_no || o.id}`,
      x: +(base.x + dx).toFixed(1),
      y: +(base.y + dy).toFixed(1),
      kind: 'task' as const,
      label: `工单 ${o.order_no} · ${o.location_name} · ${o.status}`
    }
  })
})

/** 烟蒂投放设施：位置取自演示点位表（与市民端同一批设施，便于对照） */
const FACILITIES = [
  { id: 'F1', name: '城市书房烟蒂投放设施', x: 232, y: 148 },
  { id: 'F2', name: '步行街示范点收集设施', x: 604, y: 262 },
  { id: 'F3', name: '交通枢纽站前设施', x: 986, y: 176 },
  { id: 'F4', name: '社区公园收集设施', x: 418, y: 512 },
  { id: 'F5', name: '滨河步道收集设施', x: 786, y: 604 },
  { id: 'F6', name: '政务中心广场设施', x: 1240, y: 470 },
  { id: 'F7', name: '体育场西门设施', x: 1082, y: 610 },
  { id: 'F8', name: '老街口投放点', x: 158, y: 300 }
]
const facilityMarkers = computed<MapMarker[]>(() =>
  FACILITIES.map((f) => ({ id: f.id, x: f.x, y: f.y, kind: 'done' as const, label: `${f.name} · 运行正常` }))
)

/** 兴趣点：让底图有城市纹理 */
const POIS: MapPoi[] = [
  { id: 'P1', x: 120, y: 74, name: '第三小学', kind: 'school' },
  { id: 'P2', x: 468, y: 96, name: '市人民医院', kind: 'hospital' },
  { id: 'P3', x: 742, y: 62, name: '万达商圈', kind: 'mall' },
  { id: 'P4', x: 1032, y: 104, name: '羊山公园', kind: 'park' },
  { id: 'P5', x: 1380, y: 76, name: '高新客运站', kind: 'station' },
  { id: 'P6', x: 220, y: 224, name: '胜利路公厕', kind: 'toilet' },
  { id: 'P7', x: 560, y: 206, name: '实验中学', kind: 'school' },
  { id: 'P8', x: 878, y: 238, name: '中医院', kind: 'hospital' },
  { id: 'P9', x: 1188, y: 268, name: '会展中心商圈', kind: 'mall' },
  { id: 'P10', x: 1436, y: 214, name: '滨河公园', kind: 'park' },
  { id: 'P11', x: 306, y: 430, name: '和平路公厕', kind: 'toilet' },
  { id: 'P12', x: 640, y: 470, name: '第五小学', kind: 'school' },
  { id: 'P13', x: 946, y: 424, name: '罗山客运站', kind: 'station' },
  { id: 'P14', x: 1306, y: 508, name: '人民公园', kind: 'park' },
  { id: 'P15', x: 486, y: 626, name: '光山医院', kind: 'hospital' },
  { id: 'P16', x: 1132, y: 656, name: '南湾商圈', kind: 'mall' }
]

const markers = computed<MapMarker[]>(() => {
  const out: MapMarker[] = []
  if (layers.value.devices) out.push(...deviceMarkers.value)
  if (layers.value.events) out.push(...eventPins.value)
  if (layers.value.tasks) out.push(...taskMarkers.value)
  if (layers.value.facilities) out.push(...facilityMarkers.value)
  return out
})

const heat = computed(() =>
  layers.value.heat
    ? eventPins.value.filter((m) => m.kind === 'high').map((m) => ({ x: m.x, y: m.y, r: 96 }))
    : []
)

/** 框选区域：固定一块示意矩形 */
const BOX = { x: 520, y: 240, w: 420, h: 260 }

const pickedEvent = computed(() => {
  if (picked.value?.kind !== 'event') return null
  const id = picked.value.id.replace('E-', '')
  return demo.events.find((e) => e.event_id === id) ?? demo.events[0] ?? null
})
const pickedCam = computed(() =>
  picked.value?.kind === 'camera'
    ? demo.cameras.find((c) => c.camera_id === picked.value?.id.replace('D-', '')) ?? null
    : null
)

const boxStats = computed(() => {
  const tasks = buildTaskRows(demo.workOrders)
  const inside = eventPins.value.filter(
    (p) => p.x >= BOX.x && p.x <= BOX.x + BOX.w && p.y >= BOX.y && p.y <= BOX.y + BOX.h
  )
  return [
    { label: '框选事件', value: inside.length },
    { label: '待处置工单', value: tasks.filter((t) => t.status === 'pending').length },
    { label: '在线设备', value: demo.cameras.filter((c) => c.status === 'online').length },
    { label: '按时闭环率', value: `${demo.metrics.workorderCompletionRate}%` }
  ]
})

/** 顶栏概览：让"详细"体现在数字上，而不只是点变多了 */
const overview = computed(() => [
  { label: '在线设备', value: `${demo.cameras.filter((c) => c.status === 'online').length}/${demo.cameras.length}` },
  { label: '近 7 天事件', value: demo.events.length },
  { label: '未闭环工单', value: buildTaskRows(demo.workOrders).filter((t) => t.status !== 'closed').length },
  { label: '烟蒂设施', value: FACILITIES.length }
])

const LEGEND = computed(() => {
  const out = [] as { kind: MapMarker['kind']; label: string }[]
  if (layers.value.devices) out.push({ kind: 'online', label: '在线设备' }, { kind: 'offline', label: '离线设备' })
  if (layers.value.events) out.push({ kind: 'high', label: '高风险事件' }, { kind: 'mid', label: '中风险事件' })
  if (layers.value.tasks) out.push({ kind: 'task', label: '处置任务点' })
  if (layers.value.facilities) out.push({ kind: 'done', label: '烟蒂投放设施' })
  return out
})

/** 信阳学院浉河校区周边演示点位（GCJ-02 近似坐标，不作为官方测绘数据）。 */
const CAMPUS_CENTER: [number, number] = [114.0418, 32.1462]
const campusMarkers = computed<TileMarker[]>(() => {
  const base: TileMarker[] = [{ lng: 114.0418, lat: 32.1462, label: '你所在位置 · 信阳学院浉河校区', kind: 'self' }]
  if (layers.value.devices) base.push(
    { lng: 114.0399, lat: 32.1475, label: '设备 · 图书馆北门 CAM-061', kind: 'spot' },
    { lng: 114.0403, lat: 32.1446, label: '设备 · 教学楼 A 座 CAM-018', kind: 'spot' },
    { lng: 114.0448, lat: 32.1480, label: '设备 · 北区宿舍入口 CAM-037', kind: 'spot' },
    { lng: 114.0377, lat: 32.1468, label: '设备 · 校园西门 CAM-052', kind: 'spot' }
  )
  if (layers.value.events) base.push(
    { lng: 114.0441, lat: 32.1470, label: '事件 · 学生食堂东侧待复核（模拟）', kind: 'spot' },
    { lng: 114.0392, lat: 32.1452, label: '事件 · 一教南侧烟蒂散落（模拟）', kind: 'spot' },
    { lng: 114.0437, lat: 32.1439, label: '事件 · 南门步道环境线索（模拟）', kind: 'spot' }
  )
  if (layers.value.tasks) base.push(
    { lng: 114.0432, lat: 32.1447, label: '任务 · 体育馆西广场处理中（模拟）', kind: 'spot' },
    { lng: 114.0450, lat: 32.1460, label: '任务 · 实验楼东侧待接单（模拟）', kind: 'spot' }
  )
  if (layers.value.facilities) base.push(
    { lng: 114.0385, lat: 32.1455, label: '设施 · 校园西门烟蒂投放点', kind: 'facility' },
    { lng: 114.0453, lat: 32.1456, label: '设施 · 实验楼连廊投放点', kind: 'facility' },
    { lng: 114.0421, lat: 32.1484, label: '设施 · 北区生活广场投放点', kind: 'facility' }
  )
  if (layers.value.pois) base.push(
    { lng: 114.0412, lat: 32.1474, label: '兴趣点 · 图书馆', kind: 'facility' },
    { lng: 114.0428, lat: 32.1468, label: '兴趣点 · 学生食堂', kind: 'facility' },
    { lng: 114.0408, lat: 32.1437, label: '兴趣点 · 南门公交站', kind: 'facility' }
  )
  if (layers.value.heat) base.push(
    { lng: 114.0440, lat: 32.1469, label: '热力高值 · 食堂东侧 86', kind: 'spot' },
    { lng: 114.0393, lat: 32.1453, label: '热力中值 · 一教南侧 62', kind: 'spot' }
  )
  return base
})

function refreshMap() {
  refreshedAt.value = new Date()
  ElMessage.success(`地图点位已刷新 · ${refreshedAt.value.toLocaleTimeString('zh-CN', { hour12: false })}`)
}
</script>

<template>
  <div class="ad-page">
    <YzPanel title="地图图层">
      <div class="layer-bar">
        <label v-for="l in LAYER_DEFS" :key="l.key" class="sw">
          <input v-model="layers[l.key]" type="checkbox" />
          <span class="sw-track"><i /></span>
          <span class="sw-label">{{ l.label }}</span>
        </label>

        <div class="acts">
          <button class="ad-btn ad-btn--sm" type="button" @click="boxed = !boxed">
            {{ boxed ? '清除选择' : '框选统计' }}
          </button>
          <button class="ad-btn ad-btn--sm" type="button" @click="refreshMap">刷新地图</button>
        </div>
      </div>
      <p class="layer-help">开关会立即显示或隐藏地图上的对应点位；关闭后该类标记会从下方地图消失。行政分区用于统计口径，风险热力以“热力高值/中值”标记呈现。</p>
    </YzPanel>

    <YzPanel title="全域治理 GIS 地图" grow>
      <template #tools>
        <span class="ov-item" v-for="o in overview" :key="o.label">
          <b class="yz-num">{{ o.value }}</b>{{ o.label }}
        </span>
      </template>

      <div class="map-box">
        <GaodeTileMap :center="CAMPUS_CENTER" :zoom="16" :markers="campusMarkers" height="100%" />
        <div class="campus-map-badge"><b>当前位置：信阳学院浉河校区</b><span>校园道路与治理点位示意 · 当前显示 {{ campusMarkers.length }} 个标记</span></div>
        <div v-if="layers.zones" class="zone-ribbon">校内治理分区：北区生活区 · 中心教学区 · 南区运动区</div>
        <div v-if="boxed" class="box-card">
          <p class="bc-title">当前校区统计</p>
          <ul class="bc-list"><li v-for="s in boxStats" :key="s.label"><span>{{ s.label }}</span><b class="yz-num">{{ s.value }}</b></li></ul>
          <button class="ad-btn ad-btn--sm ad-btn--primary" type="button">查看区域详情</button>
        </div>
      </div>
    </YzPanel>
  </div>
</template>

<style scoped>
.layer-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 22px;
}

.sw {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.sw input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.sw-track {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: #cfdce8;
  transition: background 0.18s;
}

.sw-track i {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s;
}

.sw input:checked + .sw-track {
  background: var(--yz-primary);
}

.sw input:checked + .sw-track i {
  transform: translateX(16px);
}

.sw input:focus-visible + .sw-track {
  outline: 2px solid var(--yz-primary);
  outline-offset: 2px;
}

.sw-label {
  font-size: 13px;
  color: var(--yz-text-2);
}

.acts {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.layer-help { margin: 10px 0 0; color: var(--yz-text-muted); font-size: 12px; font-weight: 500; }

/* 顶栏概览 */
.ov-item {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  margin-left: 16px;
  color: var(--yz-text-muted);
  font-size: 11px;
}
.ov-item b {
  color: var(--yz-text-strong);
  font-size: 14px;
}

.map-box {
  position: relative;
  height: 100%;
  min-height: 520px;
}
.map-box :deep(.gd-map) { border-radius: 10px; }
.campus-map-badge { position:absolute;left:14px;top:14px;z-index:5;padding:10px 14px;border:1px solid #d9e7f2;border-radius:10px;background:rgba(255,255,255,.94);box-shadow:0 5px 16px rgba(41,83,116,.14); }
.campus-map-badge b,.campus-map-badge span { display:block; }
.campus-map-badge b { color:var(--yz-text-strong);font-size:13px; }
.campus-map-badge span { margin-top:3px;color:var(--yz-text-muted);font-size:10px; }
.zone-ribbon { position:absolute;left:14px;bottom:16px;z-index:5;padding:8px 12px;border-radius:8px;background:rgba(16,50,75,.86);color:#fff;font-size:12px;font-weight:600; }

.box-sel {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.box-sel rect {
  fill: rgba(8, 124, 224, 0.08);
  stroke: #087ce0;
  stroke-width: 2;
  stroke-dasharray: 10 8;
}

.box-card,
.ev-card {
  position: absolute;
  width: 230px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid #dbe8f2;
  box-shadow: 0 6px 18px rgba(61, 112, 150, 0.16);
}

.box-card {
  right: 12px;
  bottom: 62px;
}

.ev-card {
  left: 12px;
  top: 12px;
}

.bc-title,
.ec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}

.bc-list {
  margin: 8px 0 10px;
}

.bc-list li {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  line-height: 20px;
  color: var(--yz-text-muted);
}

.bc-list b {
  color: var(--yz-text-strong);
}

.ec-line {
  margin-top: 3px;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.ec-note {
  margin: 6px 0 8px;
  font-size: 11px;
  line-height: 17px;
  color: var(--yz-text-body);
}

.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}
</style>

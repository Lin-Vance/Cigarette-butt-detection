<script setup lang="ts">
import { computed, ref } from 'vue'

export interface MapMarker {
  id: string
  x: number
  y: number
  /** online 在线设备 / offline 离线设备 / high 高风险事件 / mid 中风险事件 / task 任务点 / done 已完成点位 */
  kind: 'online' | 'offline' | 'high' | 'mid' | 'task' | 'done'
  label?: string
}

export interface MapHeat {
  x: number
  y: number
  r: number
}

export interface MapLabel {
  x: number
  y: number
  text: string
}

/** 行政区分区：按事件密度做分级着色，并直接标注区名与数量 */
export interface MapZone {
  id: string
  x: number
  y: number
  w: number
  h: number
  name: string
  value: number
  /** 用于计算着色强度（一般取各区最大值） */
  max: number
}

/** 兴趣点：学校 / 医院 / 商圈 / 公园 / 公厕 / 站点 */
export interface MapPoi {
  id: string
  x: number
  y: number
  name: string
  kind: 'school' | 'hospital' | 'mall' | 'park' | 'toilet' | 'station'
}

const props = withDefaults(
  defineProps<{
    markers?: MapMarker[]
    heat?: MapHeat[]
    /** 执行路线（虚线） */
    route?: string
    labels?: MapLabel[]
    /** 分区（分级着色 + 区名 + 数量） */
    zones?: MapZone[]
    /** 兴趣点（小方块，hover 显示名称） */
    pois?: MapPoi[]
    legend?: { kind: MapMarker['kind']; label: string }[]
    /** 是否显示缩放控件 */
    zoomable?: boolean
  }>(),
  {
    markers: () => [],
    heat: () => [],
    labels: () => [],
    zones: () => [],
    pois: () => [],
    legend: () => [],
    zoomable: true
  }
)

const emit = defineEmits<{ (e: 'pick', id: string): void }>()

const W = 1600
const H = 720

const scale = ref(1)
const viewBox = computed(() => {
  const w = W / scale.value
  const h = H / scale.value
  return `${(W - w) / 2} ${(H - h) / 2} ${w} ${h}`
})

function zoom(step: number) {
  scale.value = Math.min(2.4, Math.max(1, +(scale.value + step).toFixed(2)))
}

/** 道路网（主干 + 支路） */
const ROADS = [
  { d: `M0 176H${W}`, w: 26 },
  { d: `M0 424H${W}`, w: 26 },
  { d: `M0 592H${W}`, w: 18 },
  { d: 'M268 0V720', w: 26 },
  { d: 'M672 0V720', w: 26 },
  { d: 'M1116 0V720', w: 18 },
  { d: 'M1382 0V720', w: 18 },
  { d: `M0 300H${W}`, w: 12 },
  { d: `M0 508H${W}`, w: 12 },
  { d: 'M464 0V720', w: 12 },
  { d: 'M922 0V720', w: 12 },
  { d: 'M1280 0V720', w: 12 }
]

/** 街区地块：由道路切出，留出左下河道与右上绿地 */
const BLOCKS = (() => {
  const xs: [number, number][] = [
    [10, 258],
    [278, 454],
    [474, 662],
    [682, 912],
    [932, 1106],
    [1126, 1270],
    [1292, 1372],
    [1392, 1590]
  ]
  const ys: [number, number][] = [
    [10, 166],
    [186, 290],
    [310, 414],
    [434, 498],
    [518, 582],
    [602, 710]
  ]
  const out: { x: number; y: number; w: number; h: number }[] = []
  xs.forEach((xc, i) => {
    ys.forEach((yc, j) => {
      if (i <= 1 && j >= 5) return
      if (i >= 7 && j <= 1) return
      if (i === 2 && j === 5) return
      out.push({ x: xc[0], y: yc[0], w: xc[1] - xc[0], h: yc[1] - yc[0] })
    })
  })
  return out
})()

function pick(m: MapMarker) {
  emit('pick', m.id)
}

/** 分区着色：数量越多越偏红，保持低不透明度以免盖住路网 */
function zoneFill(z: MapZone): string {
  const r = z.max > 0 ? Math.min(1, z.value / z.max) : 0
  const alpha = 0.06 + r * 0.2
  const hue = 205 - r * 175 // 205 蓝 → 30 橙红
  return `hsla(${hue}, 78%, 58%, ${alpha.toFixed(3)})`
}
function zoneStroke(z: MapZone): string {
  const r = z.max > 0 ? Math.min(1, z.value / z.max) : 0
  return `hsla(${205 - r * 175}, 72%, 46%, ${(0.3 + r * 0.35).toFixed(2)})`
}

/** 细网格 + 标尺刻度：让底图"像一张真地图"而不是一块空画布 */
const GRID_X = Array.from({ length: 15 }, (_, i) => (i + 1) * 100)
const GRID_Y = Array.from({ length: 6 }, (_, i) => (i + 1) * 100)

const POI_GLYPH: Record<MapPoi['kind'], string> = {
  school: '校',
  hospital: '医',
  mall: '商',
  park: '园',
  toilet: '厕',
  station: '站'
}
</script>

<template>
  <div class="stage">
    <svg :viewBox="viewBox" class="map" role="img" aria-label="区域示意地图">
      <title>区域示意地图</title>
      <desc>抽象街网底图，叠加设备点位、事件点位与风险热力层。</desc>

      <defs>
        <radialGradient id="yzMapHeat">
          <stop offset="0%" stop-color="#e24b4a" stop-opacity="0.5" />
          <stop offset="60%" stop-color="#f0944a" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#f0944a" stop-opacity="0" />
        </radialGradient>
      </defs>

      <rect width="1600" height="720" fill="#f4f9fd" />

      <!-- 千米网格：给底图一个可读的尺度参照 -->
      <g class="grid">
        <path v-for="x in GRID_X" :key="`gx${x}`" :d="`M${x} 0V720`" />
        <path v-for="y in GRID_Y" :key="`gy${y}`" :d="`M0 ${y}H1600`" />
      </g>

      <!-- 河道 -->
      <path
        class="river"
        d="M-20 700C140 664 286 706 402 676C512 648 556 596 646 580V740H-20Z"
      />
      <!-- 绿地 -->
      <rect class="park" x="1392" y="10" width="198" height="156" />
      <rect class="park" x="1126" y="602" width="146" height="108" />

      <!-- 地块 -->
      <g class="blocks">
        <rect
          v-for="(b, i) in BLOCKS"
          :key="i"
          :x="b.x"
          :y="b.y"
          :width="b.w"
          :height="b.h"
        />
      </g>

      <!-- 分区色块：必须画在地块**之上**——地块是不透明的，画在下面会被整片盖住；
           但仍低于路网与点位，保证读图顺序是「分区 → 路网 → 点位」。 -->
      <g class="zones">
        <rect
          v-for="z in zones"
          :key="z.id"
          :x="z.x"
          :y="z.y"
          :width="z.w"
          :height="z.h"
          :fill="zoneFill(z)"
          :stroke="zoneStroke(z)"
        />
      </g>

      <!-- 道路：先铺路面，再画中线 -->
      <g class="road-bed">
        <path v-for="(r, i) in ROADS" :key="`b${i}`" :d="r.d" :stroke-width="r.w" />
      </g>
      <g class="road-line">
        <path v-for="(r, i) in ROADS" :key="`l${i}`" :d="r.d" />
      </g>

      <!-- 风险热力 -->
      <circle
        v-for="(h, i) in heat"
        :key="`h${i}`"
        :cx="h.x"
        :cy="h.y"
        :r="h.r"
        fill="url(#yzMapHeat)"
      />

      <!-- 执行路线 -->
      <path v-if="route" class="route" :d="route" />

      <!-- 区县标注 -->
      <text v-for="(l, i) in labels" :key="`t${i}`" class="area-label" :x="l.x" :y="l.y">
        {{ l.text }}
      </text>

      <!-- 兴趣点：小方块 + 单字图标，hover 显示全称 -->
      <g v-for="p in pois" :key="p.id" class="poi">
        <title>{{ p.name }}</title>
        <rect :x="p.x - 9" :y="p.y - 9" width="18" height="18" rx="4" :class="`p-${p.kind}`" />
        <text :x="p.x" :y="p.y + 4.5">{{ POI_GLYPH[p.kind] }}</text>
      </g>

      <!-- 点位 -->
      <g
        v-for="m in markers"
        :key="m.id"
        class="marker"
        role="button"
        tabindex="0"
        :aria-label="m.label ?? m.id"
        @click="pick(m)"
        @keydown.enter.prevent="pick(m)"
      >
        <title>{{ m.label ?? m.id }}</title>
        <circle v-if="m.kind === 'high' || m.kind === 'task'" class="halo" :cx="m.x" :cy="m.y" r="15" />
        <circle class="dot" :class="`k-${m.kind}`" :cx="m.x" :cy="m.y" r="7.5" />
        <rect class="hit" :x="m.x - 18" :y="m.y - 18" width="36" height="36" />
      </g>

      <!-- 分区标注：放在最上层，避免被地块 / 路网 / 热力盖住 -->
      <g class="zone-labels">
        <g v-for="z in zones" :key="`zl-${z.id}`">
          <text class="zone-name" :x="z.x + 12" :y="z.y + 26">{{ z.name }}</text>
          <text class="zone-value" :x="z.x + z.w - 14" :y="z.y + 30">{{ z.value }}</text>
        </g>
      </g>

      <!-- 比例尺 -->
      <g class="scalebar">
        <rect x="1216" y="676" width="120" height="9" />
        <rect x="1216" y="676" width="60" height="9" class="alt" />
        <text x="1216" y="670">0</text>
        <text x="1322" y="670">1 km</text>
      </g>
    </svg>

    <div v-if="zoomable" class="zoom">
      <button type="button" aria-label="放大" @click="zoom(0.3)">＋</button>
      <button type="button" aria-label="缩小" @click="zoom(-0.3)">－</button>
      <button type="button" aria-label="重置视图" @click="scale = 1">⌖</button>
    </div>

    <slot name="tools" />

    <div v-if="legend.length" class="legend">
      <span v-for="l in legend" :key="l.kind">
        <i :class="`k-${l.kind}`" />{{ l.label }}
      </span>
    </div>

    <slot name="overlay" />
  </div>
</template>

<style scoped>
.stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 200px;
  border: 1px solid #dbe8f2;
  border-radius: 10px;
  overflow: hidden;
  background: #f4f9fd;
}

.map {
  width: 100%;
  height: 100%;
  display: block;
}

.river {
  fill: #dceaf3;
  stroke: #c2dae9;
  stroke-width: 2;
}

.park {
  fill: #e3f2e8;
  stroke: #cbe4d5;
  stroke-width: 1.5;
}

/* ---- 千米网格 ---- */
.grid path {
  fill: none;
  stroke: rgba(23, 110, 155, 0.07);
  stroke-width: 1;
}

/* ---- 行政区分区（分级着色 + 区名 + 事件数） ---- */
.zones rect {
  transition: fill 0.25s;
}
.zone-name {
  fill: #3d5468;
  font-size: 15px;
  font-weight: 600;
  font-family: var(--yz-font);
  letter-spacing: 1px;
}
.zone-value {
  fill: #1f344a;
  font-size: 26px;
  font-weight: 700;
  font-family: Consolas, Monaco, monospace;
  text-anchor: end;
}

/* ---- 兴趣点 ---- */
.poi {
  pointer-events: none;
}
.poi rect {
  stroke: #fff;
  stroke-width: 1.6;
}
.poi text {
  fill: #fff;
  font-size: 11px;
  font-family: var(--yz-font);
  text-anchor: middle;
}
.poi .p-school { fill: #5b8def; }
.poi .p-hospital { fill: #e2574c; }
.poi .p-mall { fill: #ef9f27; }
.poi .p-park { fill: #3aa982; }
.poi .p-toilet { fill: #2aa7b8; }
.poi .p-station { fill: #7a6ff0; }

/* ---- 比例尺 ---- */
.scalebar rect {
  fill: #33475e;
}
.scalebar rect.alt {
  fill: #ffffff;
  stroke: #33475e;
  stroke-width: 1.5;
}
.scalebar text {
  fill: #4a5f76;
  font-size: 13px;
  font-family: Consolas, Monaco, monospace;
  text-anchor: middle;
}

.blocks rect {
  fill: #e9f1f7;
}

.road-bed path {
  fill: none;
  stroke: #ffffff;
  stroke-linecap: square;
}

.road-line path {
  fill: none;
  stroke: #c9dae6;
  stroke-width: 1.4;
  stroke-dasharray: 10 12;
}

.route {
  fill: none;
  stroke: #087ce0;
  stroke-width: 4;
  stroke-dasharray: 12 10;
  stroke-linecap: round;
  opacity: 0.85;
}

.area-label {
  fill: #7d90a6;
  font-size: 20px;
  font-family: var(--yz-font);
  letter-spacing: 2px;
}

/* ---- 点位 ---- */
.marker {
  cursor: pointer;
}

.dot {
  stroke: #fff;
  stroke-width: 2;
  transition: r 0.16s;
}

.dot.k-online {
  fill: #1d9e75;
}
.dot.k-offline {
  fill: #9aa8b8;
}
.dot.k-high {
  fill: #e24b4a;
}
.dot.k-mid {
  fill: #ef9f27;
}
.dot.k-task {
  fill: #087ce0;
}
.dot.k-done {
  fill: #25a47b;
}

.halo {
  fill: none;
  stroke: #e24b4a;
  stroke-width: 1.6;
  opacity: 0.6;
}
.k-task + .halo,
.halo {
  stroke-dasharray: 4 4;
}

.hit {
  fill: transparent;
}

.marker:hover .dot,
.marker:focus-visible .dot {
  r: 10;
}

.marker:focus-visible {
  outline: none;
}

.marker:focus-visible .dot {
  stroke: var(--yz-primary);
  stroke-width: 3;
}

/* ---- 控件 ---- */
.zoom {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zoom button {
  width: 30px;
  height: 30px;
  border: 1px solid var(--yz-border-soft);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.94);
  color: var(--yz-text-2);
  font-size: 14px;
  line-height: 1;
}

.zoom button:hover {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}

/* ---- 图例 ---- */
.legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  padding: 7px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #dbe8f2;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: block;
}

.legend i.k-online {
  background: #1d9e75;
}
.legend i.k-offline {
  background: #9aa8b8;
}
.legend i.k-high {
  background: #e24b4a;
}
.legend i.k-mid {
  background: #ef9f27;
}
.legend i.k-task {
  background: #087ce0;
}
.legend i.k-done {
  background: #25a47b;
}
</style>

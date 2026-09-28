<script setup lang="ts">
/**
 * 高德瓦片地图（合规：GCJ-02 坐标 + 高德栅格瓦片，无需 key）
 * - 轻量自绘网格，不依赖 Leaflet 等库
 * - 瓦片加载失败时自动回退「离线演示」抽象底图
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface TileMarker {
  lng: number
  lat: number
  label?: string
  kind?: 'self' | 'facility' | 'spot'
}

const props = withDefaults(
  defineProps<{
    center: [number, number]
    zoom?: number
    markers?: TileMarker[]
    height?: string
    interactive?: boolean
    /** 演示导航路线（GCJ-02 折线）。给值即渲染路线图层。 */
    route?: [number, number][]
    /** 行进进度 0~1：已走部分高亮，并在断点处画一个行进点 */
    routeProgress?: number
  }>(),
  { zoom: 15, markers: () => [], height: '200px', interactive: true, route: () => [], routeProgress: 0 }
)

const emit = defineEmits<{ (e: 'move', center: [number, number]): void }>()

const MIN_ZOOM = 12
const MAX_ZOOM = 17

const wrapEl = ref<HTMLDivElement | null>(null)
const size = ref({ w: 600, h: 200 })
const center = ref<[number, number]>([...props.center])
const zoom = ref(props.zoom)
const offline = ref(false)
let tileFail = 0
let tileTotal = 0
let ro: ResizeObserver | null = null

function project(lng: number, lat: number, z: number) {
  const s = 256 * Math.pow(2, z)
  const x = ((lng + 180) / 360) * s
  const latR = (lat * Math.PI) / 180
  const y = ((1 - Math.log(Math.tan(latR) + 1 / Math.cos(latR)) / Math.PI) / 2) * s
  return { x, y }
}

function unproject(x: number, y: number, z: number): [number, number] {
  const s = 256 * Math.pow(2, z)
  const lng = (x / s) * 360 - 180
  const n = Math.PI - (2 * Math.PI * y) / s
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)))
  return [lng, lat]
}

const centerPx = computed(() => project(center.value[0], center.value[1], zoom.value))

/** 当前视口需要渲染的瓦片列表 */
const tiles = computed(() => {
  const z = zoom.value
  const max = Math.pow(2, z)
  const originX = centerPx.value.x - size.value.w / 2
  const originY = centerPx.value.y - size.value.h / 2
  const list: { key: string; url: string; left: number; top: number }[] = []
  const x0 = Math.floor(originX / 256)
  const y0 = Math.floor(originY / 256)
  for (let ty = y0; ty * 256 < originY + size.value.h; ty++) {
    for (let tx = x0; tx * 256 < originX + size.value.w; tx++) {
      const wx = ((tx % max) + max) % max
      const sub = 1 + ((Math.abs(tx) + Math.abs(ty)) % 4)
      list.push({
        key: `${z}-${tx}-${ty}`,
        url: `https://webrd0${sub}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x=${wx}&y=${ty}&z=${z}`,
        left: Math.round(tx * 256 - originX),
        top: Math.round(ty * 256 - originY)
      })
    }
  }
  return list
})

/** 点位像素坐标（相对容器） */
const markerPos = computed(() =>
  props.markers.map((m, i) => {
    const p = project(m.lng, m.lat, zoom.value)
    return {
      i,
      left: p.x - centerPx.value.x + size.value.w / 2,
      top: p.y - centerPx.value.y + size.value.h / 2,
      m
    }
  })
)

/** 路线像素坐标（相对容器） */
const routePx = computed<[number, number][]>(() =>
  props.route.map(([lng, lat]) => {
    const p = project(lng, lat, zoom.value)
    return [p.x - centerPx.value.x + size.value.w / 2, p.y - centerPx.value.y + size.value.h / 2] as [number, number]
  })
)

/**
 * 按进度把路线切成「已走 / 未走」两段，并在断点处给出行进点。
 * 用折线累加长度做插值，这样进度是**按实际路程**推进的，
 * 不会因为某一段特别长而看起来忽快忽慢。
 */
const routeSplit = computed(() => {
  const pts = routePx.value
  if (pts.length < 2) return { traveled: '', remaining: '', walker: null as [number, number] | null }

  const segs: number[] = []
  let total = 0
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    segs.push(d)
    total += d
  }
  if (total <= 0) return { traveled: '', remaining: '', walker: null }

  const target = Math.min(1, Math.max(0, props.routeProgress)) * total
  const traveled: [number, number][] = [pts[0]]
  let acc = 0
  let walker: [number, number] = pts[pts.length - 1]
  let remainStart = pts.length - 1

  for (let i = 0; i < segs.length; i++) {
    if (acc + segs[i] <= target) {
      traveled.push(pts[i + 1])
      acc += segs[i]
      continue
    }
    const r = segs[i] === 0 ? 0 : (target - acc) / segs[i]
    const px = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r
    const py = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r
    walker = [px, py]
    traveled.push([px, py])
    remainStart = i
    break
  }

  const remaining: [number, number][] = [walker, ...pts.slice(remainStart + 1)]
  const fmt = (list: [number, number][]) =>
    list.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  return { traveled: fmt(traveled), remaining: fmt(remaining), walker }
})

function onTileError() {  tileFail++
  // 连续多张瓦片失败视为离线，切换抽象底图，避免半白半花的脏画面
  if (tileTotal > 0 && tileFail >= Math.min(4, tileTotal) && tileFail >= 3) offline.value = true
}
function onTileLoad() {
  tileTotal++
}

function zoomBy(d: number) {
  zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom.value + d))
}

/* ---- 拖动平移 ---- */
let dragging = false
let last = { x: 0, y: 0 }

function down(e: PointerEvent) {
  if (!props.interactive) return
  dragging = true
  last = { x: e.clientX, y: e.clientY }
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}
function move(e: PointerEvent) {
  if (!dragging) return
  const dx = e.clientX - last.x
  const dy = e.clientY - last.y
  last = { x: e.clientX, y: e.clientY }
  const c = centerPx.value
  center.value = unproject(c.x - dx, c.y - dy, zoom.value)
  emit('move', center.value)
}
function up() {
  dragging = false
}

onMounted(() => {
  const el = wrapEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  size.value = { w: rect.width || 600, h: rect.height || 200 }
  ro = new ResizeObserver(() => {
    const r = el.getBoundingClientRect()
    size.value = { w: r.width, h: r.height }
  })
  ro.observe(el)
  // 网络不可用时快速失败：发一张探测瓦片
  const probe = new Image()
  probe.onerror = () => (offline.value = true)
  probe.src = tiles.value[0]?.url ?? ''
})

onBeforeUnmount(() => ro?.disconnect())

defineExpose({
  recenter(c: [number, number]) {
    center.value = [...c]
  },
  /**
   * 一次性设置中心与缩放。
   * 导航场景需要它：两点在校区尺度上只差 ~250 米，z15 下只有约 60px，
   * 路线画出来几乎看不见；放大到 z17（约 1 米/像素）才有可读的路线长度。
   */
  setView(c: [number, number], z: number) {
    center.value = [...c]
    zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z))
    emit('move', center.value)
  }
})
</script>

<template>
  <div
    ref="wrapEl"
    class="gd-map"
    :style="{ height }"
    :class="{ offline, readonly: !interactive }"
    @pointerdown="down"
    @pointermove="move"
    @pointerup="up"
    @pointerleave="up"
  >
    <template v-if="!offline">
      <img
        v-for="t in tiles"
        :key="t.key"
        class="gd-tile"
        :src="t.url"
        alt=""
        draggable="false"
        :style="{ left: t.left + 'px', top: t.top + 'px' }"
        @error="onTileError"
        @load="onTileLoad"
      />
    </template>
    <div v-else class="gd-fallback" aria-hidden="true">
      <i v-for="n in 12" :key="n"></i>
      <span class="gd-fallback-note">离线演示模式 · 示意底图</span>
    </div>

    <!-- 演示导航路线：底层虚线表示待走路线，高亮实线表示已走，断点处是行进点 -->
    <svg
      v-if="routePx.length > 1"
      class="gd-route"
      :viewBox="`0 0 ${size.w} ${size.h}`"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <polyline class="rt-remain" :points="routeSplit.remaining" />
      <polyline class="rt-done" :points="routeSplit.traveled" />
      <circle v-if="routeSplit.walker" class="rt-walker" :cx="routeSplit.walker[0]" :cy="routeSplit.walker[1]" r="7" />
    </svg>

    <div
      v-for="p in markerPos"
      :key="p.i"
      class="gd-pin"
      :class="p.m.kind ?? 'spot'"
      :style="{ left: p.left + 'px', top: p.top + 'px' }"
    >
      <i></i>
      <span v-if="p.m.label">{{ p.m.label }}</span>
    </div>

    <div v-if="interactive" class="gd-ctrl">
      <button type="button" aria-label="放大" @click.stop="zoomBy(1)">＋</button>
      <button type="button" aria-label="缩小" @click.stop="zoomBy(-1)">－</button>
    </div>
    <span class="gd-credit">© 高德地图</span>
  </div>
</template>

<style scoped>
.gd-map {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 12px;
  background: #e9edf0;
  touch-action: none;
  user-select: none;
}
.gd-map:not(.readonly) {
  cursor: grab;
}
.gd-map:not(.readonly):active {
  cursor: grabbing;
}
.gd-tile {
  position: absolute;
  width: 256px;
  height: 256px;
  pointer-events: none;
}
.gd-fallback {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(23, 110, 155, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 110, 155, 0.06) 1px, transparent 1px),
    #eef3f6;
  background-size: 42px 42px;
}
.gd-fallback i {
  position: absolute;
  background: rgba(23, 110, 155, 0.12);
  border-radius: 6px;
}
.gd-fallback i:nth-child(1) { left: 8%; top: 18%; width: 34%; height: 10px; }
.gd-fallback i:nth-child(2) { left: 30%; top: 48%; width: 44%; height: 10px; }
.gd-fallback i:nth-child(3) { left: 12%; top: 72%; width: 28%; height: 10px; }
.gd-fallback i:nth-child(4) { left: 55%; top: 12%; width: 12px; height: 56%; }
.gd-fallback i:nth-child(5) { left: 20%; top: 8%; width: 12px; height: 76%; }
.gd-fallback-note {
  position: absolute;
  right: 10px;
  bottom: 24px;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.85);
  color: #6b7885;
  font-size: 10px;
}
.gd-pin {
  position: absolute;
  transform: translate(-50%, -100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  pointer-events: none;
}

/* ---------------- 演示导航路线 ---------------- */
.gd-route {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}
.rt-remain {
  fill: none;
  stroke: #1f6fd0;
  stroke-width: 6;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 12 9;
  opacity: 0.55;
}
.rt-done {
  fill: none;
  stroke: #0f8bff;
  stroke-width: 6;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 2px 4px rgba(15, 139, 255, 0.45));
}
.rt-walker {
  fill: #ff7a32;
  stroke: #fff;
  stroke-width: 3;
  filter: drop-shadow(0 2px 5px rgba(0, 0, 0, 0.3));
}
.gd-pin i {
  width: 14px;
  height: 14px;
  border: 2.5px solid #fff;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}
.gd-pin.facility i { background: #1f9d63; }
.gd-pin.spot i { background: #216eff; }
.gd-pin.self i {
  background: #ff7a32;
  border-radius: 50%;
  transform: none;
}
.gd-pin.self::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 4px;
  width: 44px;
  height: 44px;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(255, 122, 50, 0.4);
  border-radius: 50%;
  animation: gd-pulse 2.4s ease-out infinite;
}
@keyframes gd-pulse {
  0% { transform: translate(-50%, -50%) scale(0.4); opacity: 0.9; }
  100% { transform: translate(-50%, -50%) scale(1.4); opacity: 0; }
}
.gd-pin span {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(15, 35, 55, 0.78);
  color: #fff;
  font-size: 10px;
  white-space: nowrap;
}
.gd-pin.self span { background: #ff7a32; }
.gd-ctrl {
  position: absolute;
  right: 10px;
  top: 10px;
  display: grid;
  gap: 6px;
}
.gd-ctrl button {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #22364d;
  font-size: 15px;
  box-shadow: 0 2px 8px rgba(20, 50, 80, 0.18);
  cursor: pointer;
}
.gd-credit {
  position: absolute;
  left: 8px;
  bottom: 6px;
  color: rgba(60, 75, 90, 0.65);
  font-size: 9px;
}
</style>

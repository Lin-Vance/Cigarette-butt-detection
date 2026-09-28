<script setup lang="ts">
/**
 * 页面 3 · 治理态势（未闭环预警）
 * 顶部地图 + 两张对比图 + 类型占比 + 效能排行。
 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/EChart.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzMapStage, { type MapMarker } from '@/components/ui/YzMapStage.vue'
import { useDemoStore } from '@/stores/demo'
import {
  buildAreaMetrics,
  buildHourly,
  levelOf,
  projectToMap,
  VIOLATION_TYPES
} from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const areaMetrics = buildAreaMetrics()
const hourly = buildHourly()

const unclosed = computed(() => demo.unclosedEvents)
const escalated = computed(
  () => demo.workOrders.filter((o) => o.escalated && o.status === 'pending')
)

/* ---- 地图 ---- */
const projected = computed(() =>
  projectToMap(demo.cameras.map((c) => ({ ...c })))
)

const markers = computed<MapMarker[]>(() =>
  projected.value.map(({ item, x, y }) => {
    const ev = unclosed.value.find((e) => e.camera_id === item.camera_id)
    const lv = ev ? levelOf(ev.confidence) : null
    return {
      id: item.camera_id,
      x,
      y,
      kind: lv ? (lv.key === 'high' ? 'high' : lv.key === 'mid' ? 'mid' : 'online') : 'online',
      label: `${item.camera_id} ${item.location_name}`
    }
  })
)

const heat = computed(() =>
  markers.value
    .filter((m) => m.kind === 'high' || m.kind === 'mid')
    .map((m) => ({ x: m.x, y: m.y, r: m.kind === 'high' ? 88 : 62 }))
)

const LEGEND = [
  { kind: 'high' as const, label: '高风险' },
  { kind: 'mid' as const, label: '中风险' },
  { kind: 'online' as const, label: '低风险 / 正常' }
]

const floatStats = computed(() => [
  { label: '事件处置率', value: `${demo.metrics.workorderCompletionRate}%`, hint: '较上周 +3.2%' },
  { label: '平均处置时长', value: `${demo.metrics.avgResponseMin} 分钟`, hint: '较上周 -6.8%' },
  { label: '闭环完成率', value: '94.7%', hint: '较上周 +2.4%' },
  { label: '高发区域数量', value: '12 处', hint: '重点关注 4 处' }
])

/* ---- 图表 ---- */
const areaBar = computed(
  () =>
    ({
      animation: false,
      grid: { left: 44, right: 16, top: 34, bottom: 26 },
      legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      tooltip: { trigger: 'axis', textStyle: { fontSize: 12 } },
      xAxis: {
        type: 'category',
        data: areaMetrics.map((a) => a.area),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#dbe6ee' } },
        axisLabel: { fontSize: 10, color: '#41516b' }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#e8f0f6' } },
        axisLabel: { fontSize: 10, color: '#41516b' }
      },
      series: [
        { name: '事件总量', type: 'bar', barWidth: 14, data: areaMetrics.map((a) => a.total), itemStyle: { color: '#3f8fe6', borderRadius: [3, 3, 0, 0] } },
        { name: '已处置', type: 'bar', barWidth: 14, data: areaMetrics.map((a) => a.handled), itemStyle: { color: '#5cc0a0', borderRadius: [3, 3, 0, 0] } },
        { name: '已闭环', type: 'bar', barWidth: 14, data: areaMetrics.map((a) => a.closed), itemStyle: { color: '#8fd8b4', borderRadius: [3, 3, 0, 0] } }
      ]
    }) as EChartsOption
)

const hourLine = computed(
  () =>
    ({
      animation: false,
      grid: { left: 44, right: 16, top: 34, bottom: 26 },
      legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      tooltip: { trigger: 'axis', textStyle: { fontSize: 12 } },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: hourly.map((h) => h.hour),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#dbe6ee' } },
        axisLabel: { fontSize: 9, color: '#41516b', interval: 3 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#e8f0f6' } },
        axisLabel: { fontSize: 10, color: '#41516b' }
      },
      series: [
        { name: '识别事件', type: 'line', smooth: true, symbol: 'none', data: hourly.map((h) => h.total), lineStyle: { width: 2, color: '#137de4' } },
        { name: '高风险事件', type: 'line', smooth: true, symbol: 'none', data: hourly.map((h) => h.high), lineStyle: { width: 2, color: '#4baedb' } }
      ]
    }) as EChartsOption
)

const typeRing = computed(
  () =>
    ({
      animation: false,
      tooltip: { trigger: 'item', formatter: '{b}: {c}%', textStyle: { fontSize: 12 } },
      legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      color: ['#137de4', '#4baedb', '#53c1a4', '#9fb4c9'],
      series: [
        {
          type: 'pie',
          radius: ['42%', '66%'],
          center: ['50%', '44%'],
          label: { fontSize: 11, formatter: '{b}\n{c}%' },
          labelLine: { length: 6, length2: 6 },
          data: VIOLATION_TYPES
        }
      ]
    }) as EChartsOption
)

/* ---- 排行榜 ---- */
const RANK_COLS: YzColumn[] = [
  { key: 'idx', label: '排名', width: '66px', align: 'center' },
  { key: 'area', label: '区域', width: '110px' },
  { key: 'rate', label: '处置率', width: '1.4fr' },
  { key: 'avgMin', label: '平均时长', width: '96px' },
  { key: 'closedRate', label: '闭环率', width: '1.4fr' },
  { key: 'trend', label: '趋势', width: '80px', align: 'right' }
]

const rank = computed(() =>
  [...areaMetrics]
    .sort((a, b) => b.rate - a.rate)
    .map((a, i) => ({
      idx: i + 1,
      area: a.area,
      rate: `${a.rate}%`,
      rateVal: a.rate,
      avgMin: `${a.avgMin} 分钟`,
      closedRate: `${a.rate}%`,
      closedVal: a.rate,
      trend: a.trend
    }))
)
</script>

<template>
  <div class="ad-page">
    <YzPanel title="未闭环事件预警" class="map-panel">
      <template #tools>
        <span class="yz-tag yz-tag--danger">未闭环 {{ unclosed.length }}</span>
        <span class="yz-tag yz-tag--warning">超时 {{ escalated.length }}</span>
      </template>

      <YzMapStage :markers="markers" :heat="heat" :legend="LEGEND">
        <template #overlay>
          <div class="floats">
            <div v-for="s in floatStats" :key="s.label" class="float">
              <p class="f-label">{{ s.label }}</p>
              <p class="f-value yz-num">{{ s.value }}</p>
              <p class="f-hint">{{ s.hint }}</p>
            </div>
          </div>
        </template>
      </YzMapStage>
    </YzPanel>

    <div class="ad-row grow-row">
      <YzPanel title="各区域事件处置对比" class="ad-grow">
        <div class="chart"><EChart :option="areaBar" /></div>
      </YzPanel>
      <YzPanel title="24 小时违规行为时段分布" class="ad-grow">
        <div class="chart"><EChart :option="hourLine" /></div>
      </YzPanel>
    </div>

    <div class="ad-row grow-row">
      <YzPanel title="违规行为类型占比" class="type-panel">
        <div class="chart"><EChart :option="typeRing" /></div>
      </YzPanel>

      <div class="ad-col ad-grow">
        <YzPanel title="治理效能排行榜" :count="rank.length">
          <YzTable :columns="RANK_COLS" :rows="rank" row-key="area" dense>
            <template #cell-rate="{ row }">
              <span class="bar-cell">
                <span class="ad-bar"><i :style="{ width: `${row.rateVal}%` }" /></span>
                <b class="yz-num">{{ row.rate }}</b>
              </span>
            </template>
            <template #cell-closedRate="{ row }">
              <span class="bar-cell">
                <span class="ad-bar"><i :style="{ width: `${row.closedVal}%` }" /></span>
                <b class="yz-num">{{ row.closedRate }}</b>
              </span>
            </template>
            <template #cell-trend="{ row }">
              <span :class="row.trend > 0 ? 'up' : 'down'">
                {{ row.trend > 0 ? '↑' : '↓' }}{{ Math.abs(row.trend) }}%
              </span>
            </template>
          </YzTable>
        </YzPanel>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-panel {
  flex: none;
  height: 258px;
}

.grow-row {
  flex: 1;
  min-height: 0;
}

.grow-row > :deep(.panel) {
  min-height: 0;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 150px;
}

.type-panel {
  flex: none;
  width: 320px;
}

.floats {
  position: absolute;
  inset: 12px 12px auto 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  pointer-events: none;
}

.float {
  padding: 8px 12px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.93);
  border: 1px solid #dbe8f2;
  box-shadow: 0 3px 10px rgba(61, 112, 150, 0.1);
}

.f-label {
  font-size: 11px;
  color: var(--yz-text-muted);
}

.f-value {
  margin-top: 2px;
  font-size: 19px;
  font-weight: 700;
  color: #117fba;
}

.f-hint {
  margin-top: 1px;
  font-size: 10px;
  color: var(--yz-text-muted);
}

.bar-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.bar-cell b {
  font-size: 12px;
  color: var(--yz-text-strong);
}

.up {
  color: #fb5b4b;
}

.down {
  color: #00a971;
}
</style>

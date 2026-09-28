<script setup lang="ts">
/** 页面 4 · 设备运行地图 */
import { computed, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/EChart.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzMapStage, { type MapMarker } from '@/components/ui/YzMapStage.vue'
import { useDemoStore } from '@/stores/demo'
import { buildDeviceAlarms, buildDeviceTrend, FAULT_TYPES, fmtDateTime, projectToMap } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const picked = ref<string | null>(null)
const trend = buildDeviceTrend()
const alarms = computed(() => buildDeviceAlarms(demo.cameras))

const projected = computed(() => projectToMap(demo.cameras.map((c) => ({ ...c }))))

const markers = computed<MapMarker[]>(() =>
  projected.value.map(({ item, x, y }, i) => ({
    id: item.camera_id,
    x,
    y,
    kind: i % 6 === 0 ? 'high' : item.status === 'online' ? 'online' : 'offline',
    label: `${item.camera_id} ${item.location_name}`
  }))
)

const LEGEND = [
  { kind: 'online' as const, label: '在线设备' },
  { kind: 'offline' as const, label: '离线设备' },
  { kind: 'high' as const, label: '告警设备' }
]

const onlineRate = computed(() => {
  const on = demo.cameras.filter((c) => c.status === 'online').length
  return demo.cameras.length ? +((on / demo.cameras.length) * 100).toFixed(1) : 0
})

const floatStats = computed(() => [
  { label: '设备总数', value: demo.metrics.onlineDevices, hint: '较上周 ↑2.4%' },
  { label: '设备在线率', value: `${onlineRate.value}%`, hint: '较上周 ↑1.2%' },
  { label: '设备离线率', value: `${(100 - onlineRate.value).toFixed(1)}%`, hint: '较上周 ↓0.8%' },
  { label: '告警待处置', value: alarms.value.filter((a) => a.status !== 'online').length, hint: '较昨日 ↓6 台' }
])

const pickedCam = computed(
  () => demo.cameras.find((c) => c.camera_id === picked.value) ?? null
)

const trendOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 46, right: 18, top: 34, bottom: 26 },
      legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      tooltip: { trigger: 'axis', textStyle: { fontSize: 12 } },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trend.map((t) => t.date),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#dbe6ee' } },
        axisLabel: { fontSize: 10, color: '#41516b' }
      },
      yAxis: {
        type: 'value',
        min: 86,
        max: 100,
        splitLine: { lineStyle: { color: '#e8f0f6' } },
        axisLabel: { fontSize: 10, color: '#41516b', formatter: '{value}%' }
      },
      series: [
        {
          name: '在线率',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          data: trend.map((t) => t.online),
          lineStyle: { width: 2, color: '#137de4' },
          itemStyle: { color: '#137de4' }
        },
        {
          name: '设备健康度',
          type: 'line',
          smooth: true,
          symbolSize: 6,
          data: trend.map((t) => t.health),
          lineStyle: { width: 2, color: '#4baedb' },
          itemStyle: { color: '#4baedb' }
        }
      ]
    }) as EChartsOption
)

const faultOption = computed(
  () =>
    ({
      animation: false,
      tooltip: { trigger: 'item', formatter: '{b}: {c}%', textStyle: { fontSize: 12 } },
      legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      color: ['#e24b4a', '#ef9f27', '#4baedb', '#9fb4c9'],
      series: [
        {
          type: 'pie',
          radius: ['46%', '68%'],
          center: ['50%', '42%'],
          label: { formatter: '{b}\n{c}%', fontSize: 11 },
          labelLine: { length: 6, length2: 6 },
          data: FAULT_TYPES
        }
      ]
    }) as EChartsOption
)

const COLS: YzColumn[] = [
  { key: 'cameraId', label: '设备编号', width: '1fr' },
  { key: 'location', label: '安装点位', width: '1.6fr' },
  { key: 'status', label: '设备状态', width: '96px' },
  { key: 'alarmType', label: '告警类型', width: '1fr' },
  { key: 'ts', label: '发生时间', width: '1.3fr' },
  { key: 'op', label: '操作', width: '84px', align: 'right' }
]

const rows = computed(() =>
  alarms.value.map((a) => ({
    ...a,
    ts: fmtDateTime(a.ts),
    statusText: a.status === 'online' ? '在线' : a.status === 'offline' ? '离线' : '告警',
    statusTone: a.status === 'online' ? 'success' : a.status === 'offline' ? 'muted' : 'danger'
  }))
)
</script>

<template>
  <div class="ad-page">
    <YzPanel title="设备运行地图" class="map-panel">
      <template #tools>
        <span class="ad-badge">演示数据 · {{ demo.scale.label }}</span>
      </template>

      <YzMapStage
        :markers="markers"
        :legend="LEGEND"
        @pick="(id) => (picked = picked === id ? null : id)"
      >
        <template #overlay>
          <div class="floats">
            <div v-for="s in floatStats" :key="s.label" class="float">
              <p class="f-label">{{ s.label }}</p>
              <p class="f-value yz-num">{{ s.value }}</p>
              <p class="f-hint">{{ s.hint }}</p>
            </div>
          </div>

          <div v-if="pickedCam" class="cam-card">
            <div class="cc-head">
              <b>{{ pickedCam.camera_id }}</b>
              <span class="yz-tag" :class="pickedCam.status === 'online' ? 'yz-tag--success' : 'yz-tag--muted'">
                {{ pickedCam.status === 'online' ? '在线' : '离线' }}
              </span>
            </div>
            <p class="cc-name">{{ pickedCam.location_name }}</p>
            <dl class="cc-meta">
              <div><dt>设备类型</dt><dd>球机 · 1080P</dd></div>
              <div><dt>所属区域</dt><dd>浉河区</dd></div>
              <div><dt>帧率</dt><dd>{{ pickedCam.fps }} fps</dd></div>
            </dl>
            <button class="ad-btn ad-btn--sm ad-btn--primary" type="button" @click="picked = null">
              收起
            </button>
          </div>
        </template>
      </YzMapStage>
    </YzPanel>

    <div class="ad-row grow-row">
      <YzPanel title="设备在线率趋势" class="ad-grow">
        <div class="chart"><EChart :option="trendOption" /></div>
      </YzPanel>
      <YzPanel title="设备故障类型占比" class="ring-panel">
        <div class="chart"><EChart :option="faultOption" /></div>
      </YzPanel>
    </div>

    <YzPanel title="设备告警列表" :count="rows.length" class="ad-grow">
      <YzTable :columns="COLS" :rows="rows" row-key="id">
        <template #cell-status="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.statusTone}`">{{ row.statusText }}</span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">查看详情</button>
        </template>
      </YzTable>
    </YzPanel>
  </div>
</template>

<style scoped>
.map-panel {
  flex: none;
  height: 286px;
}

.grow-row {
  flex: 1;
  min-height: 0;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 150px;
}

.ring-panel {
  flex: none;
  width: 340px;
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

.cam-card {
  position: absolute;
  left: 12px;
  top: 96px;
  width: 216px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid #dbe8f2;
  box-shadow: 0 6px 18px rgba(61, 112, 150, 0.16);
}

.cc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--yz-text-strong);
}

.cc-name {
  margin-top: 4px;
  font-size: 12px;
  color: var(--yz-text-body);
}

.cc-meta {
  margin: 8px 0 10px;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.cc-meta div {
  display: flex;
  gap: 8px;
  line-height: 20px;
}

.cc-meta dt {
  width: 56px;
  flex: none;
}

.cc-meta dd {
  margin: 0;
  color: var(--yz-text-2);
}
</style>

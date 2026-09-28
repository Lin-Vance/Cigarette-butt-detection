<script setup lang="ts">
/** 页面 15 · 数据分析 */
import { computed, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import { ElMessage } from 'element-plus'
import EChart from '@/components/EChart.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzStat from '@/components/ui/YzStat.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { AREAS, buildAreaMetrics, buildHourly, fmtDate, rand } from '@/mock/pages'

const hourly = buildHourly()
const areaMetrics = buildAreaMetrics(29)

const filter = ref({ range: '', area: '' })
const FIELDS = [
  { key: 'range', label: '时间范围', type: 'date' as const, width: '150px' },
  { key: 'area', label: '选择区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })), width: '150px' }
]

const kpis = computed(() => {
  const total = areaMetrics.reduce((a, b) => a + b.total, 0)
  const high = Math.round(total * 0.243)
  return [
    { label: '总识别事件', value: total },
    { label: '高风险事件占比', value: '24.3%', hint: '环比 ↓3.2%', trend: 'down' as const },
    { label: '重复告警数量', value: 278, hint: '环比 ↓18.5%', trend: 'down' as const },
    { label: '平均 AI 识别耗时', value: '168 ms', hint: '环比 ↓12 ms', trend: 'down' as const }
  ]
})

const hourOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 46, right: 18, top: 34, bottom: 26 },
      legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      tooltip: { trigger: 'axis', textStyle: { fontSize: 12 } },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: hourly.map((h) => h.hour),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#dbe6ee' } },
        axisLabel: { fontSize: 10, color: '#41516b', interval: 2 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#e8f0f6' } },
        axisLabel: { fontSize: 10, color: '#41516b' }
      },
      series: [
        { name: '识别事件', type: 'line', smooth: true, symbol: 'none', data: hourly.map((h) => h.total), lineStyle: { width: 2, color: '#137de4' }, areaStyle: { color: 'rgba(19,125,228,.08)' } },
        { name: '高风险事件', type: 'line', smooth: true, symbol: 'none', data: hourly.map((h) => h.high), lineStyle: { width: 2, color: '#4baedb' } }
      ]
    }) as EChartsOption
)

const areaOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 46, right: 18, top: 34, bottom: 26 },
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
        { name: '事件总量', type: 'bar', barWidth: 16, data: areaMetrics.map((a) => a.total), itemStyle: { color: '#3f8fe6', borderRadius: [3, 3, 0, 0] } },
        { name: '高风险事件', type: 'bar', barWidth: 16, data: areaMetrics.map((a) => Math.round(a.total * 0.243)), itemStyle: { color: '#4baedb', borderRadius: [3, 3, 0, 0] } }
      ]
    }) as EChartsOption
)

const detail = computed(() => {
  const r = rand(307)
  return Array.from({ length: 36 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - Math.floor(i / AREAS.length))
    const area = AREAS[i % AREAS.length]
    const total = 60 + Math.round(r() * 210)
    const high = Math.round(total * (0.18 + r() * 0.14))
    const handled = Math.round(total * (0.85 + r() * 0.13))
    const closed = Math.round(handled * (0.9 + r() * 0.09))
    return {
      id: `${fmtDate(d)}-${area}`,
      date: fmtDate(d),
      area,
      total,
      high,
      handled,
      closed,
      avgMin: +(20 + r() * 30).toFixed(0),
      chain: +((r() * 10 - 6).toFixed(1))
    }
  })
})

const page = ref(1)
const size = ref(6)
watch(size, () => (page.value = 1))
const paged = computed(() => detail.value.slice((page.value - 1) * size.value, page.value * size.value))

const COLS: YzColumn[] = [
  { key: 'date', label: '统计日期', width: '1fr' },
  { key: 'area', label: '所属区域', width: '0.9fr' },
  { key: 'total', label: '违规事件总数', width: '1.1fr', align: 'right' },
  { key: 'high', label: '高风险事件', width: '1fr', align: 'right' },
  { key: 'handled', label: '已处置数量', width: '1fr', align: 'right' },
  { key: 'closed', label: '闭环数量', width: '0.9fr', align: 'right' },
  { key: 'avgMin', label: '平均处置时长', width: '1.1fr', align: 'right' },
  { key: 'chain', label: '治理环比', width: '0.9fr', align: 'right' },
  { key: 'op', label: '操作', width: '84px', align: 'right' }
]
</script>

<template>
  <div class="ad-page">
    <YzPanel title="分析筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.success('已导出分析数据（演示环境）')">
          导出分析数据
        </button>
      </template>
    </YzPanel>

    <div class="ad-row grow-row">
      <YzPanel title="违规行为时段分布" class="ad-grow">
        <div class="chart"><EChart :option="hourOption" /></div>
      </YzPanel>
      <YzPanel title="各区域违规频次" class="ad-grow">
        <div class="chart"><EChart :option="areaOption" /></div>
      </YzPanel>
    </div>

    <YzStat :items="kpis" compact />

    <YzPanel title="统计明细" :count="detail.length" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.success('已导出明细（演示环境）')">
          导出明细
        </button>
      </template>

      <YzTable :columns="COLS" :rows="paged" row-key="id" dense>
        <template #cell-avgMin="{ row }">{{ row.avgMin }} 分钟</template>
        <template #cell-chain="{ row }">
          <span :class="row.chain <= 0 ? 'down' : 'up'">
            {{ row.chain <= 0 ? '↓' : '↑' }}{{ Math.abs(row.chain) }}%
          </span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">查看详情</button>
        </template>
      </YzTable>

      <YzPager v-model:page="page" v-model:size="size" :total="detail.length" :size-options="[6, 10, 20]" />
    </YzPanel>
  </div>
</template>

<style scoped>
.grow-row {
  flex: 1;
  min-height: 0;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 150px;
}

.up {
  color: #fb5b4b;
}

.down {
  color: #00a971;
}
</style>

<script setup lang="ts">
/** 页面 7 · 事件报表 */
import { computed, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import { ElMessage } from 'element-plus'
import EChart from '@/components/EChart.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzStat from '@/components/ui/YzStat.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildAreaMetrics, fmtDate, rand, VIOLATION_TYPES } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const areaMetrics = buildAreaMetrics(17)

const filter = ref({ area: '' })
const FIELDS = [
  { key: 'area', label: '区域范围', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })), width: '150px' }
]

const stats = computed(() => [
  { label: '事件总量', value: areaMetrics.reduce((a, b) => a + b.total, 0), hint: '较上期 ↑12.6%', trend: 'up' as const },
  { label: '已处置数量', value: areaMetrics.reduce((a, b) => a + b.handled, 0), hint: '较上期 ↑9.8%', trend: 'up' as const },
  { label: '闭环数量', value: areaMetrics.reduce((a, b) => a + b.closed, 0), hint: '闭环率 87.3%', trend: 'flat' as const, tone: 'success' as const },
  { label: '平均处置时长', value: `${demo.metrics.avgResponseMin} 分钟`, hint: '较上期 ↓6.8%', trend: 'down' as const }
])

const barOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 44, right: 16, top: 20, bottom: 26 },
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
        {
          type: 'bar',
          barWidth: 20,
          data: areaMetrics.map((a) => a.total),
          itemStyle: { color: '#3f8fe6', borderRadius: [4, 4, 0, 0] }
        }
      ]
    }) as EChartsOption
)

const pieOption = computed(
  () =>
    ({
      animation: false,
      tooltip: { trigger: 'item', formatter: '{b}: {c}%', textStyle: { fontSize: 12 } },
      legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      color: ['#137de4', '#4baedb', '#53c1a4', '#9fb4c9'],
      series: [
        {
          type: 'pie',
          radius: ['40%', '64%'],
          center: ['50%', '42%'],
          label: { formatter: '{b}\n{c}%', fontSize: 11 },
          labelLine: { length: 6, length2: 6 },
          data: VIOLATION_TYPES
        }
      ]
    }) as EChartsOption
)

/* ---- 明细 ---- */
const detail = computed(() => {
  const r = rand(211)
  const out: Record<string, any>[] = []
  for (let i = 0; i < 36; i++) {
    const d = new Date()
    d.setDate(d.getDate() - Math.floor(i / AREAS.length))
    const area = AREAS[i % AREAS.length]
    const total = 60 + Math.round(r() * 220)
    const handled = Math.round(total * (0.86 + r() * 0.12))
    const closed = Math.round(handled * (0.9 + r() * 0.09))
    out.push({
      id: `${fmtDate(d)}-${area}`,
      date: fmtDate(d),
      area,
      total,
      handled,
      closed,
      pending: total - handled,
      rate: +((closed / total) * 100).toFixed(1),
      avgMin: +(20 + r() * 32).toFixed(0)
    })
  }
  return out
})

const page = ref(1)
const size = ref(6)
watch(size, () => (page.value = 1))
const paged = computed(() => detail.value.slice((page.value - 1) * size.value, page.value * size.value))

const COLS: YzColumn[] = [
  { key: 'date', label: '统计日期', width: '1.1fr' },
  { key: 'area', label: '所属区域', width: '1fr' },
  { key: 'total', label: '事件总量', width: '90px', align: 'right' },
  { key: 'handled', label: '已处置', width: '84px', align: 'right' },
  { key: 'closed', label: '已闭环', width: '84px', align: 'right' },
  { key: 'pending', label: '待处置', width: '84px', align: 'right' },
  { key: 'rate', label: '闭环率', width: '1.2fr' },
  { key: 'avgMin', label: '平均时长', width: '94px', align: 'right' }
]
</script>

<template>
  <div class="ad-page">
    <div class="bar">
      <button class="ad-btn" type="button" @click="ElMessage.info('报表预览（演示环境）')">报表预览</button>
      <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.success('已导出 Excel（演示环境，未生成真实文件）')">
        导出 Excel
      </button>
      <button class="ad-btn" type="button" @click="ElMessage.success('已导出 PDF（演示环境，未生成真实文件）')">
        导出 PDF
      </button>
      <span class="ad-badge" style="margin-left: auto">演示数据 · {{ demo.scale.label }}</span>
    </div>

    <YzPanel title="报表筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzStat :items="stats" compact />

    <div class="ad-row grow-row">
      <YzPanel title="各区域事件对比" class="ad-grow">
        <div class="chart"><EChart :option="barOption" /></div>
      </YzPanel>
      <YzPanel title="违规类型占比" class="pie-panel">
        <div class="chart"><EChart :option="pieOption" /></div>
      </YzPanel>
    </div>

    <YzPanel title="事件统计明细" :count="detail.length" grow>
      <YzTable :columns="COLS" :rows="paged" row-key="id" dense>
        <template #cell-rate="{ row }">
          <span class="bar-cell">
            <span class="ad-bar"><i :style="{ width: `${row.rate}%` }" /></span>
            <b class="yz-num">{{ row.rate }}%</b>
          </span>
        </template>
        <template #cell-avgMin="{ row }">{{ row.avgMin }} 分钟</template>
      </YzTable>
      <YzPager v-model:page="page" v-model:size="size" :total="detail.length" :size-options="[6, 10, 20]" />
    </YzPanel>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.grow-row {
  flex: 1;
  min-height: 0;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 140px;
}

.pie-panel {
  flex: none;
  width: 340px;
}

.bar-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.bar-cell b {
  font-size: 12px;
}
</style>

<script setup lang="ts">
/** 页面 5 · 区域任务分布地图（工作看板） */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { EChartsOption } from 'echarts'
import EChart from '@/components/EChart.vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzMapStage, { type MapMarker } from '@/components/ui/YzMapStage.vue'
import { useDemoStore } from '@/stores/demo'
import {
  AREAS,
  buildAreaMetrics,
  buildTaskRows,
  buildTaskTrend,
  fmtDateTime,
  projectToMap,
  WORKORDER_STATUS
} from '@/mock/pages'

const demo = useDemoStore()
const router = useRouter()
demo.init()

const pickedArea = ref<string | null>(null)
const areaMetrics = buildAreaMetrics(19)
const taskTrend = buildTaskTrend()
const tasks = computed(() => buildTaskRows(demo.workOrders))

const projected = computed(() => projectToMap(demo.cameras.map((c) => ({ ...c }))))

const markers = computed<MapMarker[]>(() =>
  projected.value.map(({ item, x, y }, i) => {
    const t = tasks.value[i % Math.max(1, tasks.value.length)]
    return {
      id: item.camera_id,
      x,
      y,
      kind: t && t.urgent === 'high' ? 'task' : i % 4 === 0 ? 'done' : 'online',
      label: `${item.location_name}`
    }
  })
)

/** 执行路线：取前几个点连成一条折线 */
const route = computed(() => {
  const pts = projected.value.slice(0, 6)
  if (pts.length < 2) return ''
  return 'M' + pts.map((p) => `${p.x} ${p.y}`).join('L')
})

const LEGEND = [
  { kind: 'task' as const, label: '紧急任务' },
  { kind: 'online' as const, label: '普通任务' },
  { kind: 'done' as const, label: '已完成点位' }
]

const floatStats = computed(() => [
  { label: '在岗人员数', value: demo.metrics.onlineStaff, hint: '较昨日 ↑3.2%' },
  { label: '正在执行任务', value: tasks.value.filter((t) => t.status === 'processing' || t.status === 'accepted').length, hint: '实时更新' },
  { label: '待派发任务', value: tasks.value.filter((t) => t.status === 'pending').length, hint: '需及时处理' },
  { label: '今日已完成', value: tasks.value.filter((t) => t.status === 'completed' || t.status === 'closed').length, hint: `完成率 ${demo.metrics.workorderCompletionRate}%` }
])

const pickedMetric = computed(
  () => areaMetrics.find((a) => a.area === pickedArea.value) ?? null
)

const trendOption = computed(
  () =>
    ({
      animation: false,
      grid: { left: 44, right: 16, top: 34, bottom: 26 },
      legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      tooltip: { trigger: 'axis', textStyle: { fontSize: 12 } },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: taskTrend.map((t) => t.date),
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
        { name: '新增任务', type: 'line', smooth: true, symbolSize: 6, data: taskTrend.map((t) => t.created), lineStyle: { width: 2, color: '#137de4' }, itemStyle: { color: '#137de4' } },
        { name: '已完成任务', type: 'line', smooth: true, symbolSize: 6, data: taskTrend.map((t) => t.done), lineStyle: { width: 2, color: '#25a47b' }, itemStyle: { color: '#25a47b' } }
      ]
    }) as EChartsOption
)

const AREA_COLS: YzColumn[] = [
  { key: 'area', label: '区域', width: '1fr' },
  { key: 'total', label: '任务总数', width: '90px', align: 'right' },
  { key: 'done', label: '已完成', width: '84px', align: 'right' },
  { key: 'pending', label: '待处理', width: '84px', align: 'right' },
  { key: 'timeout', label: '超时', width: '70px', align: 'right' },
  { key: 'rate', label: '完成率', width: '1.2fr' }
]

const areaRows = computed(() =>
  areaMetrics.map((a) => ({
    area: a.area,
    total: a.total,
    done: a.closed,
    pending: a.total - a.closed,
    timeout: a.timeout,
    rate: a.rate
  }))
)

const TASK_COLS: YzColumn[] = [
  { key: 'orderNo', label: '任务编号', width: '1.2fr' },
  { key: 'area', label: '所属区域', width: '1fr' },
  { key: 'status', label: '任务状态', width: '90px' },
  { key: 'remain', label: '剩余时长', width: '96px' },
  { key: 'op', label: '操作', width: '120px', align: 'right' }
]

const taskRows = computed(() => tasks.value.slice(0, 7))

function openTask(row: Record<string, any>) {
  router.push({ name: 'dispatch-records', query: { order: row.orderNo } })
}

function reassign(row: Record<string, any>) {
  ElMessage.info(`正在打开 ${row.orderNo} 的改派面板`)
  router.push({ name: 'dispatch-pool', query: { order: row.orderNo, action: 'reassign' } })
}

function quickAction(name: string) {
  const query = name === '快速派单' ? { action: 'create' } : name === '批量调度' ? { action: 'batch' } : { filter: 'pending' }
  router.push({ name: 'dispatch-pool', query })
}
</script>

<template>
  <div class="ad-page">
    <YzPanel title="区域任务分布地图" class="map-panel">
      <template #tools>
        <span class="ad-badge">{{ AREAS.length }} 个区域</span>
      </template>

      <YzMapStage :markers="markers" :route="route" :legend="LEGEND" @pick="pickedArea = '浉河区'">
        <template #overlay>
          <div class="floats">
            <div v-for="s in floatStats" :key="s.label" class="float">
              <p class="f-label">{{ s.label }}</p>
              <p class="f-value yz-num">{{ s.value }}</p>
              <p class="f-hint">{{ s.hint }}</p>
            </div>
          </div>

          <div v-if="pickedMetric" class="area-card">
            <p class="ac-title">{{ pickedMetric.area }}任务概况</p>
            <ul class="ac-list">
              <li><span>任务总数</span><b class="yz-num">{{ pickedMetric.total }}</b></li>
              <li><span>待处理</span><b class="yz-num warn">{{ pickedMetric.total - pickedMetric.closed }}</b></li>
              <li><span>超时</span><b class="yz-num warn">{{ pickedMetric.timeout }}</b></li>
              <li><span>完成率</span><b class="yz-num">{{ pickedMetric.rate }}%</b></li>
            </ul>
            <button class="ad-btn ad-btn--sm ad-btn--primary" type="button" @click="pickedArea = null">
              收起
            </button>
          </div>
        </template>
      </YzMapStage>
    </YzPanel>

    <div class="ad-row grow-row">
      <YzPanel title="任务完成量近 7 日趋势" class="ad-grow">
        <div class="chart"><EChart :option="trendOption" /></div>
      </YzPanel>
      <YzPanel title="区域工作状态" :count="areaRows.length" class="area-panel">
        <YzTable :columns="AREA_COLS" :rows="areaRows" row-key="area" dense>
          <template #cell-rate="{ row }">
            <span class="bar-cell">
              <span class="ad-bar"><i :style="{ width: `${row.rate}%` }" /></span>
              <b class="yz-num">{{ row.rate }}%</b>
            </span>
          </template>
        </YzTable>
      </YzPanel>
    </div>

    <div class="ad-row grow-row">
      <YzPanel title="任务执行监控" :count="tasks.length" class="ad-grow">
        <YzTable :columns="TASK_COLS" :rows="taskRows" row-key="id" dense>
          <template #cell-status="{ row }">
            <span class="yz-tag" :class="`yz-tag--${WORKORDER_STATUS[row.status as keyof typeof WORKORDER_STATUS].tone}`">
              {{ WORKORDER_STATUS[row.status as keyof typeof WORKORDER_STATUS].text }}
            </span>
          </template>
          <template #cell-remain="{ row }">
            <span :class="row.remainMin < 10 ? 'warn' : ''">
              {{ row.remainMin > 0 ? `${row.remainMin} 分钟` : '已完成' }}
            </span>
          </template>
          <template #cell-op="{ row }">
            <button class="ad-link" type="button" @click="openTask(row)">查看详情</button>
            <button class="ad-link" type="button" style="margin-left: 8px" @click="reassign(row)">改派</button>
          </template>
        </YzTable>
      </YzPanel>

      <YzPanel title="快捷操作" class="quick-panel">
        <div class="quick">
          <button v-for="q in ['快速派单', '待处理任务提醒', '批量调度']" :key="q" class="q-btn" type="button" @click="quickAction(q)">
            {{ q }}
          </button>
        </div>
        <p class="q-note">今日已生成 {{ tasks.length }} 条工单，其中 {{ tasks.filter((t) => t.status === 'pending').length }} 条待派发。最新一条：{{ fmtDateTime(tasks[0]?.createdAt ?? new Date()) }}</p>
      </YzPanel>
    </div>
  </div>
</template>

<style scoped>
.map-panel {
  flex: none;
  height: 244px;
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

.area-panel {
  flex: none;
  width: 560px;
}

.quick-panel {
  flex: none;
  width: 300px;
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

.area-card {
  position: absolute;
  left: 12px;
  top: 86px;
  width: 210px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid #dbe8f2;
  box-shadow: 0 6px 18px rgba(61, 112, 150, 0.16);
}

.ac-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}

.ac-list {
  margin: 8px 0 10px;
}

.ac-list li {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  line-height: 20px;
  color: var(--yz-text-muted);
}

.ac-list b {
  color: var(--yz-text-strong);
}

.ac-list b.warn {
  color: var(--yz-warning);
}

.bar-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.bar-cell b {
  font-size: 12px;
}

.warn {
  color: var(--yz-warning);
}

.quick {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.q-btn {
  height: 42px;
  border: 1px solid #dbe8f2;
  border-radius: 9px;
  background: #fff;
  color: var(--yz-text-2);
  font-size: 13px;
}

.q-btn:hover {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}

.q-note {
  margin-top: 12px;
  font-size: 11px;
  line-height: 18px;
  color: var(--yz-text-muted);
}

.grow-row:last-child :deep(.yz-panel__body) {
  min-height: 0;
  overflow: auto;
}
</style>

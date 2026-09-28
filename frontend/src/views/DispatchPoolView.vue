<script setup lang="ts">
/** 页面 8 · 调度中心任务池 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildTaskRows, fmtDateTime, WORKORDER_STATUS } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const all = computed(() => buildTaskRows(demo.workOrders))

const filter = ref({ area: '', status: '', urgent: '', kw: '' })

const STATUS_OPTIONS = [
  { label: '待派发', value: 'pending' },
  { label: '待处理(含超时)', value: 'timeout' },
  { label: '执行中', value: 'processing' },
  { label: '已完成', value: 'completed' }
]

const FIELDS = [
  { key: 'area', label: '所属区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })) },
  { key: 'status', label: '任务状态', type: 'select' as const, placeholder: '全部状态', options: STATUS_OPTIONS },
  { key: 'urgent', label: '紧急等级', type: 'select' as const, placeholder: '全部等级', options: [
    { label: '紧急', value: 'high' },
    { label: '一般', value: 'mid' },
    { label: '低', value: 'low' }
  ] },
  { key: 'kw', label: '关键词', type: 'text' as const, placeholder: '请输入任务编号或路段名称', width: '232px' }
]

const filtered = computed(() =>
  all.value.filter((t) => {
    const f = filter.value
    if (f.area && t.area !== f.area) return false
    if (f.status) {
      if (f.status === 'timeout' && t.status !== 'timeout' && t.status !== 'pending') return false
      if (f.status !== 'timeout' && t.status !== f.status) return false
    }
    if (f.urgent && t.urgent !== f.urgent) return false
    if (f.kw) {
      const kw = f.kw.trim().toLowerCase()
      if (!t.orderNo.toLowerCase().includes(kw) && !t.road.toLowerCase().includes(kw)) return false
    }
    return true
  })
)

const page = ref(1)
const size = ref(10)
watch([filtered, size], () => (page.value = 1))
const paged = computed(() =>
  filtered.value.slice((page.value - 1) * size.value, page.value * size.value).map((t) => ({
    ...t,
    createdAt: fmtDateTime(t.createdAt),
    statusText: WORKORDER_STATUS[t.status].text,
    statusTone: WORKORDER_STATUS[t.status].tone
  }))
)

const counts = computed(() => ({
  pending: all.value.filter((t) => t.status === 'pending').length,
  processing: all.value.filter((t) => t.status === 'accepted' || t.status === 'processing').length,
  timeout: all.value.filter((t) => t.status === 'timeout').length
}))

const COLS: YzColumn[] = [
  { key: 'orderNo', label: '任务编号', width: '1.2fr' },
  { key: 'createdAt', label: '生成时间', width: '1.4fr' },
  { key: 'road', label: '所属路段', width: '1.4fr' },
  { key: 'type', label: '任务类型', width: '0.9fr' },
  { key: 'content', label: '任务内容', width: '1.6fr' },
  { key: 'owner', label: '负责人', width: '0.9fr' },
  { key: 'status', label: '任务状态', width: '90px' },
  { key: 'remain', label: '剩余时效', width: '100px' },
  { key: 'op', label: '操作', width: '170px', align: 'right' }
]
</script>

<template>
  <div class="ad-page">
    <div class="overview">
      <span class="yz-tag yz-tag--info">待派发 {{ counts.pending }}</span>
      <span class="yz-tag yz-tag--success">执行中 {{ counts.processing }}</span>
      <span class="yz-tag yz-tag--warning">已超时 {{ counts.timeout }}</span>
      <button
        class="ad-btn ad-btn--primary"
        type="button"
        style="margin-left: auto"
        @click="ElMessage.success('已批量派发选中任务（演示环境）')"
      >
        批量派发任务
      </button>
    </div>

    <YzPanel title="任务筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="任务数据列表" :count="filtered.length" grow>
      <YzTable :columns="COLS" :rows="paged" selectable row-key="id">
        <template #cell-status="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.statusTone}`">{{ row.statusText }}</span>
        </template>
        <template #cell-remain="{ row }">
          <span
            class="yz-num"
            :class="row.remainMin < 10 ? 'danger' : row.remainMin < 30 ? 'warn' : 'ok'"
          >
            {{ row.remainMin > 0 ? `${row.remainMin} 分钟` : '已完成' }}
          </span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">查看详情</button>
          <button class="ad-link" type="button" style="margin-left: 8px">派发</button>
          <button class="ad-link" type="button" style="margin-left: 8px">改派</button>
        </template>
      </YzTable>

      <YzPager v-model:page="page" v-model:size="size" :total="filtered.length" />
    </YzPanel>
  </div>
</template>

<style scoped>
.overview {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.danger {
  color: var(--yz-danger);
}
.warn {
  color: var(--yz-warning);
}
.ok {
  color: var(--yz-success);
}
</style>

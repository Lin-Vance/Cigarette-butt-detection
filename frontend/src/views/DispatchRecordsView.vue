<script setup lang="ts">
/** 页面 9 · 调度记录管理 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildDispatchRows, fmtDateTime } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const all = computed(() => buildDispatchRows(demo.workOrders))

const filter = ref({ area: '', result: '', kw: '' })

const FIELDS = [
  { key: 'area', label: '所属区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })) },
  { key: 'result', label: '处置状态', type: 'select' as const, placeholder: '全部状态', options: [
    { label: '已完成', value: 'done' },
    { label: '处置失败', value: 'fail' },
    { label: '已取消', value: 'cancel' }
  ] },
  { key: 'kw', label: '关键词', type: 'text' as const, placeholder: '请输入记录编号或任务编号', width: '232px' }
]

const filtered = computed(() =>
  all.value.filter((r) => {
    const f = filter.value
    if (f.result && r.result !== f.result) return false
    if (f.kw) {
      const kw = f.kw.trim().toLowerCase()
      if (!r.id.toLowerCase().includes(kw) && !r.orderNo.toLowerCase().includes(kw)) return false
    }
    return true
  })
)

const page = ref(1)
const size = ref(10)
watch([filtered, size], () => (page.value = 1))
const paged = computed(() =>
  filtered.value
    .slice((page.value - 1) * size.value, page.value * size.value)
    .map((r) => ({ ...r, ts: fmtDateTime(r.ts) }))
)

const stats = computed(() => {
  const done = all.value.filter((r) => r.result === 'done').length
  return [
    { label: '历史记录', value: 12568, hint: '全部处置记录' },
    { label: '今日完成', value: done, hint: '含人工回填' },
    { label: '处置成功率', value: '96.8%', hint: '近 30 天均值', tone: 'success' as const }
  ]
})

const COLS: YzColumn[] = [
  { key: 'id', label: '记录编号', width: '1.1fr' },
  { key: 'orderNo', label: '关联任务编号', width: '1.3fr' },
  { key: 'staff', label: '处置人员', width: '0.9fr' },
  { key: 'ts', label: '处置时间', width: '1.4fr' },
  { key: 'result', label: '处置结果', width: '94px' },
  { key: 'note', label: '备注', width: '1.8fr' },
  { key: 'op', label: '操作', width: '84px', align: 'right' }
]
</script>

<template>
  <div class="ad-page">
    <div class="overview">
      <template v-for="s in stats" :key="s.label">
        <span class="mini">
          <b class="yz-num" :class="s.tone ?? ''">{{ typeof s.value === 'number' ? s.value.toLocaleString('zh-CN') : s.value }}</b>
          <i>{{ s.label }}</i>
        </span>
      </template>
      <button
        class="ad-btn ad-btn--primary"
        type="button"
        style="margin-left: auto"
        @click="ElMessage.success('已导出全部历史调度记录（演示环境，未生成真实文件）')"
      >
        导出全部历史调度记录
      </button>
    </div>

    <YzPanel title="调度记录筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="历史调度记录" :count="filtered.length" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.success('已导出当前结果（演示环境）')">
          导出记录
        </button>
      </template>

      <YzTable :columns="COLS" :rows="paged" selectable row-key="id">
        <template #cell-result="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.resultTone}`">{{ row.resultText }}</span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">查看详情</button>
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
  gap: 22px;
  flex: none;
  padding: 10px 16px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid #dbe8f2;
}

.mini {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.mini b {
  font-size: 20px;
  font-weight: 700;
  color: #117fba;
}

.mini b.success {
  color: var(--yz-success);
}

.mini i {
  font-style: normal;
  font-size: 12px;
  color: var(--yz-text-muted);
}
</style>

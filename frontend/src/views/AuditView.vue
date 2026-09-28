<script setup lang="ts">
/** 页面 18 · 审计日志（只读） */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { buildAuditRows, fmtDateTime } from '@/mock/pages'

const all = computed(() => buildAuditRows(127, 26))

const filter = ref({ account: '', action: '', range: '' })

const FIELDS = [
  { key: 'account', label: '操作账号', type: 'text' as const, placeholder: '请输入账号', width: '150px' },
  { key: 'range', label: '操作时间', type: 'datetime' as const, width: '200px' },
  { key: 'action', label: '操作类型', type: 'select' as const, placeholder: '全部类型', options: [
    { label: '登录', value: 'login' },
    { label: '数据操作', value: 'data' },
    { label: '权限变更', value: 'perm' },
    { label: '系统配置', value: 'config' }
  ] }
]

const filtered = computed(() =>
  all.value.filter((r) => {
    const f = filter.value
    if (f.account.trim() && !r.account.includes(f.account.trim())) return false
    if (f.action && r.action !== f.action) return false
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

const stats = computed(() => [
  { label: '今日日志', value: 1286, tone: '' },
  { label: '异常操作', value: 3, tone: 'danger' },
  { label: '登录记录', value: 326, tone: 'success' },
  { label: '权限变更', value: 18, tone: 'warning' }
])

const COLS: YzColumn[] = [
  { key: 'id', label: '日志编号', width: '1.1fr' },
  { key: 'account', label: '操作账号', width: '1fr' },
  { key: 'content', label: '操作内容', width: '2.4fr' },
  { key: 'ip', label: '操作 IP', width: '1.1fr' },
  { key: 'ts', label: '操作时间', width: '1.4fr' },
  { key: 'op', label: '查看', width: '56px', align: 'right' }
]
</script>

<template>
  <div class="ad-page">
    <div class="overview">
      <template v-for="s in stats" :key="s.label">
        <span class="mini">
          <b class="yz-num" :class="s.tone">{{ s.value.toLocaleString('zh-CN') }}</b>
          <i>{{ s.label }}</i>
        </span>
      </template>
      <span class="ad-badge" style="margin-left: 18px">日志只读 · 不可删除</span>
      <button
        class="ad-btn ad-btn--primary"
        type="button"
        style="margin-left: auto"
        @click="ElMessage.success('已导出审计日志（演示环境，未生成真实文件）')"
      >
        导出审计日志
      </button>
    </div>

    <YzPanel title="审计日志筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="审计日志列表" :count="filtered.length" grow>
      <template #tools>
        <span class="ro mono">共 36,528 条不可删除审计记录</span>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.success('已导出当前结果（演示环境）')">
          导出当前结果
        </button>
      </template>

      <YzTable :columns="COLS" :rows="paged" selectable row-key="id">
        <template #cell-content="{ row }">
          <span class="content">
            <span class="yz-tag" :class="`yz-tag--${row.actionTone}`">{{ row.actionText }}</span>
            <span class="c-text">{{ row.content }}</span>
          </span>
        </template>
        <template #cell-ip="{ row }">
          <span class="mono">{{ row.ip }}</span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button" aria-label="查看详情">›</button>
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
  gap: 24px;
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

.mini b.danger {
  color: var(--yz-danger);
}
.mini b.success {
  color: var(--yz-success);
}
.mini b.warning {
  color: var(--yz-warning);
}

.mini i {
  font-style: normal;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.ro {
  font-size: 11px;
  color: var(--yz-text-muted);
}

.content {
  display: inline-flex;
  align-items: center;
  gap: 9px;
}

.c-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
}
</style>

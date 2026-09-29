<script setup lang="ts">
/**
 * 执法协同 · 处置留痕（管理端模块，原交警端并入）。
 *
 * 只读页：执法协同的每一次动作都写在这里，不提供修改与删除。
 * 与页面 18「审计日志」的分工：审计日志记录平台侧操作，
 * 本页记录执法协同侧的线索处置与结果回传。
 */
import { computed, onMounted } from 'vue'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzStat from '@/components/ui/YzStat.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import { useDemoStore } from '@/stores/demo'
import { useLawStore } from '@/stores/law'

const demo = useDemoStore()
const law = useLawStore()

const COLS: YzColumn[] = [
  { key: 'at', label: '时间', width: '1.2fr' },
  { key: 'no', label: '线索编号', width: '1fr' },
  { key: 'location', label: '处置地点', width: '1.35fr' },
  { key: 'action', label: '动作', width: '1fr' },
  { key: 'note', label: '原因 / 结果', width: '2.4fr' },
  { key: 'operator', label: '操作人', width: '120px' },
  { key: 'resultText', label: '回传状态', width: '110px' }
]

function fmt(ts: string) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const rows = computed(() =>
  law.trail.map((t, i) => ({
    id: `${t.no}-${i}-${t.at}`,
    at: fmt(t.at),
    no: t.no,
    location: t.location || ['信阳学院北门', '学院路公交站', '城市书房广场'][i % 3],
    action: t.action,
    note: t.note,
    operator: t.operator,
    resultText: law.RESULT_TEXT[t.result],
    tone: t.result === 'success' ? 'success' : t.result === 'returned' ? 'warning' : 'danger'
  }))
)

const statItems = computed(() => {
  const total = law.trail.length
  const ok = law.trail.filter((t) => t.result === 'success').length
  const back = law.trail.filter((t) => t.result === 'returned').length
  const rej = law.trail.filter((t) => t.result === 'rejected').length
  return [
    { label: '留痕条目', value: total, hint: '只增不改不删', tone: 'primary' as const },
    { label: '已回传', value: ok, hint: '处置完成', tone: 'success' as const },
    { label: '已退回', value: back, hint: '要求补充材料', tone: 'warning' as const },
    { label: '已驳回', value: rej, hint: '不予处理', tone: 'danger' as const }
  ]
})

onMounted(async () => {
  await demo.init()
  law.seed(demo.events)
})
</script>

<template>
  <div class="ad-page">
    <div class="ad-head">
      <div>
        <h1 class="ad-title">处置结果与留痕</h1>
        <p class="ad-sub">执法协同侧的全部处置动作 · 只读 · 结果同步回管理员端与市民端</p>
      </div>
      <div class="ad-actions">
        <span class="ad-badge">只读页面 · 不可修改或删除</span>
        <router-link class="ad-btn" :to="{ name: 'law-cases' }">← 返回线索核查</router-link>
      </div>
    </div>

    <YzStat :items="statItems" compact />

    <YzPanel title="处置留痕" :count="rows.length" grow>
      <YzTable :columns="COLS" :rows="rows" row-key="id" dense empty="暂无处置记录" class="trail-table">
        <template #cell-resultText="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.tone}`">{{ row.resultText }}</span>
        </template>
        <template #cell-note="{ row }">
          <span class="note-cell">{{ row.note }}</span>
        </template>
      </YzTable>
    </YzPanel>

    <div class="foot-rows">
      <p class="foot-note">
        留痕不提供删除入口：执法协同的每次认领、退回、驳回与处置完成都会写入这里，
        供审计与复核追溯。
      </p>
      <p class="foot-note">
        与「审计日志（页面 18）」的分工：审计日志记录平台侧账号与配置操作，
        本页只记录执法协同侧的线索处置与结果回传。
      </p>
    </div>
  </div>
</template>

<style scoped>
.note-cell {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trail-table { min-width: 1050px; }
.foot-rows {
  display: grid;
  gap: 8px;
  flex: none;
}
.foot-note {
  padding: 9px 12px;
  border-left: 3px solid var(--yz-primary);
  background: var(--yz-primary-soft);
  font-size: 12px;
  line-height: 1.8;
  color: var(--yz-text-muted);
}
</style>

<script setup lang="ts">
/**
 * 执法协同 · 线索核查（管理端模块，原交警端并入）。
 *
 * 与其它管理端页面同一套外观：`.ad-*` 原子类 + YzStat / YzPanel / YzTable。
 * 职责边界：只处理已复核线索，不展示举报人实名与被举报对象可识别画面。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzStat from '@/components/ui/YzStat.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import { useDemoStore } from '@/stores/demo'
import { CASE_STATUS_TEXT, CASE_TONE, DISPOSE, useLawStore, type CaseStatus, type LawCase } from '@/stores/law'

const demo = useDemoStore()
const law = useLawStore()

const operator = '演示执法人员'
const statusFilter = ref<'all' | CaseStatus>('all')
const keyword = ref('')
const drawer = ref<{ open: boolean; kind: '' | 'done' | 'need_more' | 'rejected'; target: LawCase | null }>({
  open: false,
  kind: '',
  target: null
})
const drawerNote = ref('')

const COLS: YzColumn[] = [
  { key: 'no', label: '线索编号', width: '1.1fr' },
  { key: 'area', label: '区域', width: '1.1fr' },
  { key: 'ts', label: '事件时间', width: '1.3fr' },
  { key: 'confidence', label: '置信度', width: '90px', align: 'right' },
  { key: 'integrity', label: '证据完整度', width: '110px' },
  { key: 'operator', label: '处置人', width: '110px' },
  { key: 'statusText', label: '状态', width: '96px' },
  { key: 'op', label: '操作', width: '198px' }
]

const statItems = computed(() => [
  { label: '待核查', value: law.stats.toCheck, hint: '需现场核实', tone: 'warning' as const },
  { label: '处理中', value: law.stats.handling, hint: '已认领', tone: 'primary' as const },
  { label: '需补充', value: law.stats.needMore, hint: '退回补充材料', tone: 'primary' as const },
  { label: '已处理', value: law.stats.done, hint: '结果已回传', tone: 'success' as const },
  { label: '不予处理', value: law.stats.rejected, hint: '已注明原因', tone: 'danger' as const }
])

function fmt(ts: string) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const filtered = computed(() =>
  law.cases.filter((c) => {
    if (statusFilter.value !== 'all' && c.status !== statusFilter.value) return false
    const kw = keyword.value.trim()
    if (!kw) return true
    return c.no.includes(kw) || c.area.includes(kw)
  })
)

const rows = computed(() =>
  filtered.value.map((c) => ({
    key: c.key,
    no: c.no,
    area: c.area,
    ts: fmt(c.ts),
    confidence: `${(c.confidence * 100).toFixed(1)}%`,
    integrity: law.integrity(c),
    operator: c.operator || '—',
    statusText: CASE_STATUS_TEXT[c.status],
    tone: CASE_TONE[c.status],
    status: c.status,
    raw: c
  }))
)

function claim(row: Record<string, any>) {
  const c = row.raw as LawCase
  if (law.claim(c.key, operator)) {
    ElMessage.success(`${c.no} 已认领，进入处理中`)
  }
}

function openDrawer(row: Record<string, any>, kind: 'done' | 'need_more' | 'rejected') {
  drawer.value = { open: true, kind, target: row.raw as LawCase }
  drawerNote.value = kind === 'done' ? '已完成现场处置并回复' : ''
}

function closeDrawer() {
  drawer.value = { open: false, kind: '', target: null }
  drawerNote.value = ''
}

const DRAWER_TITLE: Record<string, string> = {
  done: '标记已处理',
  need_more: '退回补充材料',
  rejected: '不予处理'
}

function confirmDrawer() {
  const { kind, target } = drawer.value
  if (!target || !kind) return
  // 退回与不予处理必须写原因：不写清楚，管理员端和市民端都无法核对
  if (kind !== 'done' && drawerNote.value.trim().length < 4) {
    ElMessage.warning('请填写原因（至少 4 个字），该说明会写入留痕并回传')
    return
  }
  if (law.dispose(target.key, kind, drawerNote.value, operator)) {
    ElMessage.success(`${target.no} 已${DISPOSE[kind].action}，结果已回传`)
  }
  closeDrawer()
}

/** 便捷操作：把第一条待核查直接认领，方便演示连点 */
function claimFirst() {
  const first = law.byStatus.to_check[0]
  if (!first) {
    ElMessage.info('没有待核查线索')
    return
  }
  law.claim(first.key, operator)
  ElMessage.success(`${first.no} 已认领`)
}

onMounted(async () => {
  await demo.init()
  law.seed(demo.events, operator)
})
</script>

<template>
  <div class="ad-page">
    <div class="ad-head">
      <div>
        <h1 class="ad-title">执法线索核查</h1>
        <p class="ad-sub">
          只处理已复核线索 · 不展示举报人实名与被举报对象可识别画面 · 处置动作全程留痕
        </p>
      </div>
      <div class="ad-actions">
        <select v-model="statusFilter" class="ad-ctrl" aria-label="按状态筛选">
          <option value="all">全部状态</option>
          <option v-for="(text, key) in CASE_STATUS_TEXT" :key="key" :value="key">{{ text }}</option>
        </select>
        <input v-model="keyword" class="ad-ctrl" placeholder="线索编号 / 区域" />
        <button class="ad-btn" type="button" @click="claimFirst">认领首条待核查</button>
        <router-link class="ad-btn ad-btn--primary" :to="{ name: 'law-trail' }">处置留痕 →</router-link>
      </div>
    </div>

    <YzStat :items="statItems" compact />

    <YzPanel title="待办线索" :count="filtered.length" grow>
      <YzTable :columns="COLS" :rows="rows" row-key="key" dense>
        <template #cell-statusText="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.tone}`">{{ row.statusText }}</span>
        </template>
        <template #cell-integrity="{ row }">
          <span :class="{ 'ad-sub': row.integrity !== '完整' }">{{ row.integrity }}</span>
        </template>
        <template #cell-op="{ row }">
          <button
            v-if="row.status === 'to_check'"
            class="ad-link"
            type="button"
            @click="claim(row)"
          >
            认领核查
          </button>
          <template v-else-if="row.status === 'handling' || row.status === 'need_more'">
            <button class="ad-link" type="button" @click="openDrawer(row, 'done')">已处理</button>
            <button class="ad-link op-gap" type="button" @click="openDrawer(row, 'need_more')">
              需补充
            </button>
            <button class="ad-link op-gap danger" type="button" @click="openDrawer(row, 'rejected')">
              不予处理
            </button>
          </template>
          <span v-else class="ad-sub">已办结</span>
        </template>
      </YzTable>
    </YzPanel>

    <p class="foot-note">
      线索来自算法候选事件，经人工复核后进入本模块。AI 不自动定性、不自动处罚；
      本模块不展示被举报对象的可识别画面。
    </p>

    <div v-if="drawer.open" class="mask" @click.self="closeDrawer">
      <aside class="drawer">
        <header class="d-head">
          <div>
            <p class="d-title">{{ DRAWER_TITLE[drawer.kind] }}</p>
            <p class="d-sub">{{ drawer.target?.no }} · {{ drawer.target?.area }}</p>
          </div>
          <button class="d-close" type="button" aria-label="关闭" @click="closeDrawer">×</button>
        </header>

        <div class="d-body">
          <div class="d-meta">
            <span><small>事件时间</small>{{ fmt(drawer.target?.ts ?? '') }}</span>
            <span><small>置信度</small>{{ ((drawer.target?.confidence ?? 0) * 100).toFixed(1) }}%</span>
            <span><small>证据完整度</small>{{ drawer.target ? law.integrity(drawer.target) : '—' }}</span>
          </div>
          <label class="d-field">
            <span>{{ drawer.kind === 'done' ? '处置结果（回传管理员端）' : '原因（必填，至少 4 个字）' }}</span>
            <textarea v-model="drawerNote" rows="3"></textarea>
          </label>
          <p class="d-tip">
            该说明会写入处置留痕并同步到管理员端。不予受理必须给出原因，便于市民端与管理员端核对。
          </p>
        </div>

        <footer class="d-foot">
          <button class="ad-btn" type="button" @click="closeDrawer">取消</button>
          <button class="ad-btn ad-btn--primary" type="button" @click="confirmDrawer">确认提交</button>
        </footer>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.op-gap {
  margin-left: 8px;
}
.danger {
  color: var(--yz-danger);
}
.foot-note {
  flex: none;
  padding: 9px 12px;
  border-left: 3px solid var(--yz-primary);
  background: var(--yz-primary-soft);
  font-size: 12px;
  line-height: 1.8;
  color: var(--yz-text-muted);
}

/* ---- 处置抽屉（与页面 16 的抽屉同一套观感） ---- */
.mask {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgba(23, 39, 67, 0.28);
}
.drawer {
  display: flex;
  flex-direction: column;
  width: 420px;
  background: #fff;
  box-shadow: -8px 0 22px rgba(23, 63, 105, 0.16);
}
.d-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--yz-border-faint);
}
.d-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.d-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--yz-text-muted);
}
.d-close {
  border: 0;
  background: none;
  font-size: 20px;
  line-height: 1;
  color: var(--yz-text-muted);
  cursor: pointer;
}
.d-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
}
.d-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--yz-border-faint);
}
.d-meta small {
  display: block;
  margin-bottom: 4px;
  font-size: 11px;
  color: var(--yz-text-muted);
}
.d-meta span {
  font-size: 13px;
  color: var(--yz-text-2);
}
.d-field {
  display: grid;
  gap: 7px;
  margin-top: 16px;
}
.d-field span {
  font-size: 12px;
  color: var(--yz-text-muted);
}
.d-field textarea {
  padding: 9px 11px;
  border: 1px solid var(--yz-border-soft);
  border-radius: var(--yz-radius-input);
  font-family: inherit;
  font-size: 13px;
  color: var(--yz-text-2);
  resize: vertical;
  outline: none;
}
.d-field textarea:focus {
  border-color: var(--yz-primary);
  box-shadow: 0 0 0 2px var(--yz-primary-soft);
}
.d-tip {
  margin-top: 12px;
  font-size: 11.5px;
  line-height: 1.8;
  color: var(--yz-text-muted);
}
.d-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 18px;
  border-top: 1px solid var(--yz-border-faint);
}
</style>

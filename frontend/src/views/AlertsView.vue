<script setup lang="ts">
/** 页面 6 · 告警数据列表 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildAlertRows, fmtDateTime } from '@/mock/pages'
import type { ViolationEvent } from '@/mock/types'

const demo = useDemoStore()
demo.init()

const readIds = ref<string[]>([])
const pickedIds = ref<string[]>([])
const evidenceTarget = ref<ViolationEvent | null>(null)

const all = computed(() =>
  buildAlertRows(demo.events, demo.cameras).map((row) => ({
    ...row,
    read: row.read || readIds.value.includes(row.id),
    event: demo.events.find(
      (event) => event.camera_id === row.cameraId && event.event_timestamp === row.ts
    ) ?? null
  }))
)

const filter = ref({ level: '', area: '', status: '', kw: '' })

const FIELDS = [
  { key: 'level', label: '告警等级', type: 'select' as const, placeholder: '全部等级', options: [
    { label: '高风险', value: 'high' },
    { label: '中风险', value: 'mid' },
    { label: '低风险', value: 'low' }
  ] },
  { key: 'area', label: '所属区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })) },
  { key: 'status', label: '告警状态', type: 'select' as const, placeholder: '全部状态', options: [
    { label: '未阅', value: 'unread' },
    { label: '已阅', value: 'read' }
  ] },
  { key: 'kw', label: '关键词', type: 'text' as const, placeholder: '请输入告警编号或摄像头编号', width: '232px' }
]

const filtered = computed(() =>
  all.value.filter((r) => {
    const f = filter.value
    if (f.level && r.levelKey !== f.level) return false
    if (f.area && r.area !== f.area) return false
    if (f.status === 'read' && !r.read) return false
    if (f.status === 'unread' && r.read) return false
    if (f.kw) {
      const kw = f.kw.trim().toLowerCase()
      if (!r.eventId.toLowerCase().includes(kw) && !r.cameraId.toLowerCase().includes(kw)) return false
    }
    return true
  })
)

const page = ref(1)
const size = ref(10)
watch([filtered, size], () => {
  page.value = 1
})
const paged = computed(() => filtered.value.slice((page.value - 1) * size.value, page.value * size.value))

const COLS: YzColumn[] = [
  { key: 'eventId', label: '告警编号', width: '1.2fr' },
  { key: 'ts', label: '发生时间', width: '1.4fr' },
  { key: 'area', label: '所属区域', width: '0.9fr' },
  { key: 'cameraId', label: '摄像头编号', width: '1fr' },
  { key: 'level', label: '告警等级', width: '90px' },
  { key: 'thumb', label: '抓拍缩略图', width: '110px' },
  { key: 'status', label: '告警状态', width: '88px' },
  { key: 'op', label: '操作', width: '150px', align: 'right' }
]

const rows = computed(() => paged.value.map((r) => ({ ...r, ts: fmtDateTime(r.ts) })))

const FRAME_LABEL: Record<string, string> = {
  holding: '持烟观测',
  throwing: '疑似抛掷',
  landed: '落点观测'
}

function markRead(id: string) {
  if (!readIds.value.includes(id)) readIds.value = [...readIds.value, id]
  ElMessage.success('已标记为已阅')
}

function markPickedRead() {
  if (!pickedIds.value.length) {
    ElMessage.warning('请先选择需要标记的告警')
    return
  }
  readIds.value = [...new Set([...readIds.value, ...pickedIds.value])]
  ElMessage.success(`已标记 ${pickedIds.value.length} 条告警`)
  pickedIds.value = []
}

function openEvidence(row: Record<string, any>) {
  if (!row.event) {
    ElMessage.warning('该事件暂无可回看的证据帧')
    return
  }
  evidenceTarget.value = row.event as ViolationEvent
  markRead(row.id)
}

function exportExcel() {
  ElMessage.success(`已导出 ${filtered.value.length} 条告警记录（演示环境，未生成真实文件）`)
}
</script>

<template>
  <div class="ad-page">
    <div class="summary">
      <span class="yz-tag yz-tag--info">未闭告警 {{ all.filter((r) => !r.read).length }}</span>
      <span class="yz-tag yz-tag--success">今日新增 {{ Math.min(all.length, 128) }}</span>
      <button class="ad-btn ad-btn--primary" type="button" style="margin-left: auto" @click="exportExcel">
        导出告警列表 Excel
      </button>
    </div>

    <YzPanel title="告警筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="告警数据列表" :count="filtered.length" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="markPickedRead">批量标记已阅</button>
        <button class="ad-btn ad-btn--sm ad-btn--icon" type="button" aria-label="列表设置">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4">
            <circle cx="8" cy="8" r="2.4" />
            <path d="M8 1.6v2M8 12.4v2M1.6 8h2M12.4 8h2M3.5 3.5l1.4 1.4M11.1 11.1l1.4 1.4M12.5 3.5l-1.4 1.4M4.9 11.1l-1.4 1.4" />
          </svg>
        </button>
      </template>

      <YzTable :columns="COLS" :rows="rows" selectable row-key="id" @pick="pickedIds = $event">
        <template #cell-level="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.levelTone}`">{{ row.levelText }}</span>
        </template>
        <template #cell-thumb="{ row }">
          <span class="thumb">
            <img v-if="row.thumb" :src="row.thumb" alt="" />
            <i v-else>无图</i>
          </span>
        </template>
        <template #cell-status="{ row }">
          <span class="yz-tag" :class="row.read ? 'yz-tag--muted' : 'yz-tag--danger'">
            {{ row.read ? '已阅' : '未阅' }}
          </span>
        </template>
        <template #cell-op="{ row }">
          <button class="ad-link" type="button" @click="openEvidence(row)">查看证据</button>
          <button class="ad-link" type="button" style="margin-left: 10px" @click="markRead(row.id)">标记已阅</button>
        </template>
      </YzTable>

      <YzPager v-model:page="page" v-model:size="size" :total="filtered.length" />
    </YzPanel>

    <div v-if="evidenceTarget" class="evidence-mask" @click.self="evidenceTarget = null">
      <aside class="evidence-drawer" role="dialog" aria-modal="true" aria-label="事件证据详情">
        <header class="evidence-head">
          <div>
            <p class="evidence-kicker">AI 候选 · 等待人工复核</p>
            <h2>事件证据详情</h2>
            <span>{{ evidenceTarget.camera_name }} · {{ fmtDateTime(evidenceTarget.event_timestamp) }}</span>
          </div>
          <button type="button" aria-label="关闭证据详情" @click="evidenceTarget = null">×</button>
        </header>

        <div class="evidence-body">
          <div class="evidence-summary">
            <span><small>事件状态</small>候选事件</span>
            <span><small>模型置信度</small>{{ (evidenceTarget.confidence * 100).toFixed(1) }}%</span>
            <span><small>轨迹点</small>{{ evidenceTarget.trajectory.length }} 个</span>
          </div>

          <section>
            <div class="evidence-title">
              <h3>三阶段关键帧</h3>
              <span>演示素材</span>
            </div>
            <div class="evidence-frames">
              <figure v-for="frame in evidenceTarget.evidence_frames" :key="frame.frame_ts">
                <img :src="frame.path" :alt="FRAME_LABEL[frame.type]" />
                <figcaption>
                  <b>{{ FRAME_LABEL[frame.type] }}</b>
                  <time>{{ fmtDateTime(frame.frame_ts) }}</time>
                </figcaption>
              </figure>
            </div>
          </section>

          <p class="evidence-note">
            当前仅展示算法候选证据，不代表责任认定。需进入人工研判后才能确认、驳回或标记证据不足。
          </p>
        </div>

        <footer class="evidence-foot">
          <button class="ad-btn" type="button" @click="evidenceTarget = null">关闭</button>
          <button class="ad-btn ad-btn--primary" type="button" @click="$router.push('/platform/overview')">
            进入人工研判
          </button>
        </footer>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.summary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.thumb {
  display: inline-block;
  width: 76px;
  height: 40px;
  border-radius: 6px;
  overflow: hidden;
  background: #eaf1f6;
  border: 1px solid #dbe8f2;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb i {
  display: grid;
  place-items: center;
  height: 100%;
  font-size: 10px;
  font-style: normal;
  color: var(--yz-text-placeholder);
}

.evidence-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  justify-content: flex-end;
  background: rgba(17, 41, 90, 0.28);
}
.evidence-drawer {
  display: flex;
  flex-direction: column;
  width: min(620px, 92vw);
  height: 100%;
  background: var(--yz-surface);
  box-shadow: -16px 0 40px rgba(23, 63, 105, 0.18);
}
.evidence-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
  border-bottom: 1px solid var(--yz-border-faint);
}
.evidence-head h2 {
  margin: 5px 0;
  color: var(--yz-text-strong);
  font-size: 22px;
}
.evidence-head span,
.evidence-kicker {
  color: var(--yz-text-muted);
  font-size: 13px;
}
.evidence-kicker {
  margin: 0;
  color: var(--yz-warning);
  font-weight: 700;
}
.evidence-head > button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--yz-border-soft);
  border-radius: var(--yz-radius-btn);
  background: #fff;
  color: var(--yz-text-muted);
  font-size: 22px;
  cursor: pointer;
}
.evidence-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
}
.evidence-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.evidence-summary span {
  padding: 14px;
  border: 1px solid var(--yz-border-faint);
  border-radius: var(--yz-radius-btn);
  background: var(--yz-primary-soft);
  color: var(--yz-text-strong);
  font-size: 15px;
  font-weight: 700;
}
.evidence-summary small {
  display: block;
  margin-bottom: 6px;
  color: var(--yz-text-muted);
  font-size: 12px;
  font-weight: 400;
}
.evidence-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.evidence-title h3 {
  margin: 0;
  color: var(--yz-text-strong);
  font-size: 16px;
}
.evidence-title span {
  padding: 4px 8px;
  border-radius: var(--yz-radius-tag);
  background: #fff2d9;
  color: var(--yz-warning);
  font-size: 12px;
}
.evidence-frames {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.evidence-frames figure {
  overflow: hidden;
  margin: 0;
  border: 1px solid var(--yz-border-faint);
  border-radius: var(--yz-radius-btn);
  background: #fff;
}
.evidence-frames img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}
.evidence-frames figcaption {
  display: grid;
  gap: 4px;
  padding: 10px;
}
.evidence-frames b {
  color: var(--yz-text-strong);
  font-size: 13px;
}
.evidence-frames time {
  color: var(--yz-text-muted);
  font: 11px Consolas, monospace;
}
.evidence-note {
  margin: 22px 0 0;
  padding: 14px 16px;
  border-left: 3px solid var(--yz-warning);
  background: #fff8e9;
  color: var(--yz-text-muted);
  font-size: 13px;
  line-height: 1.7;
}
.evidence-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--yz-border-faint);
}

@media (max-width: 680px) {
  .evidence-drawer {
    width: 100%;
  }
  .evidence-summary,
  .evidence-frames {
    grid-template-columns: 1fr;
  }
}
</style>

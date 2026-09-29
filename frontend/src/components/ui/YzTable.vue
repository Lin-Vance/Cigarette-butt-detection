<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface YzColumn {
  key: string
  label: string
  /** 列宽，缺省为 1fr */
  width?: string
  align?: 'left' | 'center' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: YzColumn[]
    rows: Record<string, any>[]
    selectable?: boolean
    rowKey?: string
    empty?: string
    /** 行是否可点击高亮 */
    clickable?: boolean
    /** 紧凑行高（38 → 32），用于一屏要塞多行的页面 */
    dense?: boolean
  }>(),
  { selectable: false, rowKey: 'id', empty: '暂无数据', clickable: false, dense: false }
)

const emit = defineEmits<{
  (e: 'row-click', row: Record<string, any>): void
  (e: 'pick', keys: string[]): void
}>()

const picked = ref<string[]>([])

const gridTemplate = computed(
  () => (props.selectable ? '38px ' : '') + props.columns.map((c) => c.width ?? '1fr').join(' ')
)

const allPicked = computed(
  () => props.rows.length > 0 && picked.value.length === props.rows.length
)

function toggleAll() {
  picked.value = allPicked.value ? [] : props.rows.map((r) => String(r[props.rowKey]))
}

watch(picked, (v) => emit('pick', v))
// 数据源变化时清空已选，避免残留上一页的勾选
watch(
  () => props.rows,
  () => {
    picked.value = []
  }
)
</script>

<template>
  <div class="table" :class="{ dense }">
    <div class="tr th" :style="{ gridTemplateColumns: gridTemplate }">
      <span v-if="selectable" class="td check">
        <input type="checkbox" :checked="allPicked" aria-label="全选" @change="toggleAll" />
      </span>
      <span
        v-for="c in columns"
        :key="c.key"
        class="td"
        :style="{ textAlign: c.align ?? 'left' }"
      >
        {{ c.label }}
      </span>
    </div>

    <div
      v-for="row in rows"
      :key="String(row[rowKey])"
      class="tr"
      :class="{ clickable }"
      :style="{ gridTemplateColumns: gridTemplate }"
      @click="clickable && emit('row-click', row)"
    >
      <span v-if="selectable" class="td check" @click.stop>
        <input
          v-model="picked"
          type="checkbox"
          :value="String(row[rowKey])"
          :aria-label="`选择第 ${String(row[rowKey])} 行`"
        />
      </span>
      <span
        v-for="c in columns"
        :key="c.key"
        class="td"
        :style="{ textAlign: c.align ?? 'left' }"
      >
        <slot :name="`cell-${c.key}`" :row="row" :value="row[c.key]">
          {{ row[c.key] ?? '—' }}
        </slot>
      </span>
    </div>

    <p v-if="!rows.length" class="empty">{{ empty }}</p>
  </div>
</template>

<style scoped>
.table {
  display: flex;
  flex-direction: column;
  border: 1px solid #dce8f1;
  border-radius: 8px;
  overflow: auto;
  min-height: 0;
  background: rgba(255, 255, 255, 0.6);
}

/* 窄屏：列宽有下限，挤不下时改为横向滚动，而不是把文字压成半截 */
@media (max-width: 900px) {
  .table {
    overflow-x: auto;
    overflow-y: hidden;
  }
  .tr {
    min-width: max-content;
  }
}

.tr {
  display: grid;
  align-items: center;
  min-height: 38px;
  border-bottom: 1px solid #e8f0f6;
  font-size: 13px;
  font-weight: 500;
  color: var(--yz-text-body);
}

.tr:last-child {
  border-bottom: 0;
}

.tr.th {
  min-height: 34px;
  background: #f4f9fd;
  color: var(--yz-text-muted);
  font-weight: 800;
  position: sticky;
  top: 0;
  z-index: 2;
}

.dense .tr {
  min-height: 36px;
}

.dense .tr.th {
  min-height: 34px;
}

.tr.clickable {
  cursor: pointer;
}

.tr.clickable:hover {
  background: #f2f8fe;
}

.td {
  padding: 6px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.td.check {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.td.check input {
  width: 14px;
  height: 14px;
  accent-color: var(--yz-primary);
  cursor: pointer;
}

.empty {
  padding: 26px 0;
  text-align: center;
  font-size: 12px;
  color: var(--yz-text-muted);
}
</style>

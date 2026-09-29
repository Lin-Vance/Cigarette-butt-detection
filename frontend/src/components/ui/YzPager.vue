<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    total: number
    page: number
    size?: number
    sizeOptions?: number[]
  }>(),
  { size: 10, sizeOptions: () => [10, 20, 50] }
)

const emit = defineEmits<{
  (e: 'update:page', v: number): void
  (e: 'update:size', v: number): void
}>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.size)))

/** 最多显示 7 个页码位，超出用省略号 */
const items = computed<(number | '...')[]>(() => {
  const n = pageCount.value
  const cur = props.page
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)
  const out: (number | '...')[] = [1]
  const from = Math.max(2, cur - 1)
  const to = Math.min(n - 1, cur + 1)
  if (from > 2) out.push('...')
  for (let i = from; i <= to; i++) out.push(i)
  if (to < n - 1) out.push('...')
  out.push(n)
  return out
})

function go(p: number) {
  const target = Math.min(pageCount.value, Math.max(1, p))
  if (target !== props.page) emit('update:page', target)
}

function jump(e: Event) {
  const v = Number((e.target as HTMLInputElement).value)
  if (v) go(v)
  ;(e.target as HTMLInputElement).value = ''
}
</script>

<template>
  <div class="pager">
    <span class="total">共 {{ total.toLocaleString('zh-CN') }} 条</span>

    <select
      class="ad-ctrl size"
      :value="size"
      aria-label="每页条数"
      @change="emit('update:size', Number(($event.target as HTMLSelectElement).value))"
    >
      <option v-for="s in sizeOptions" :key="s" :value="s">{{ s }} 条/页</option>
    </select>

    <button class="pg" type="button" :disabled="page <= 1" aria-label="上一页" @click="go(page - 1)">
      ‹
    </button>
    <template v-for="(it, i) in items" :key="i">
      <span v-if="it === '...'" class="dots">…</span>
      <button
        v-else
        class="pg"
        type="button"
        :class="{ on: it === page }"
        :aria-current="it === page ? 'page' : undefined"
        @click="go(it as number)"
      >
        {{ it }}
      </button>
    </template>
    <button
      class="pg"
      type="button"
      :disabled="page >= pageCount"
      aria-label="下一页"
      @click="go(page + 1)"
    >
      ›
    </button>

    <label class="jump">
      前往
      <input class="ad-ctrl jump-input" type="number" min="1" :max="pageCount" @keydown.enter.prevent="jump($event)" @blur="jump($event)" />
      页
    </label>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 10px;
  flex-wrap: wrap;
  flex: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--yz-text-muted);
}

.total {
  margin-right: auto;
}

.size {
  height: 28px;
  min-width: 92px;
  font-size: 12px;
}

.pg {
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  border: 1px solid var(--yz-border-soft);
  border-radius: 6px;
  background: #fff;
  color: var(--yz-text-2);
  font-size: 13px;
  cursor: pointer;
}

.pg:hover:not(:disabled) {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}

.pg:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pg.on {
  border-color: transparent;
  color: #fff;
  background: var(--yz-primary);
}

.dots {
  padding: 0 2px;
}

.jump {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.jump-input {
  width: 52px;
  height: 28px;
  min-width: 0;
  padding: 0 6px;
  text-align: center;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .pager { gap: 5px; }
  .total { flex-basis: 100%; }
}
</style>

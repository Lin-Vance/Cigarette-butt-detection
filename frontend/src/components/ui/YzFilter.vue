<script setup lang="ts">
export interface YzFilterField {
  key: string
  label: string
  type?: 'text' | 'select' | 'date' | 'datetime'
  options?: { label: string; value: string }[]
  placeholder?: string
  width?: string
}

const props = withDefaults(
  defineProps<{
    fields: YzFilterField[]
    /** 是否显示「重置 / 查询 / 刷新」三件套 */
    actions?: boolean
  }>(),
  { actions: true }
)

const model = defineModel<Record<string, string>>({ required: true })

const emit = defineEmits<{
  (e: 'query'): void
  (e: 'refresh'): void
  (e: 'reset'): void
}>()

function reset() {
  for (const f of props.fields) model.value[f.key] = ''
  emit('reset')
}
</script>

<template>
  <form class="filter" @submit.prevent="emit('query')">
    <label v-for="f in fields" :key="f.key" class="field">
      <span class="label">{{ f.label }}</span>
      <select
        v-if="f.type === 'select'"
        v-model="model[f.key]"
        class="ad-ctrl"
        :style="{ width: f.width ?? '132px' }"
      >
        <option value="">{{ f.placeholder ?? '全部' }}</option>
        <option v-for="o in f.options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <input
        v-else
        v-model="model[f.key]"
        class="ad-ctrl"
        :type="f.type === 'datetime' ? 'datetime-local' : f.type === 'date' ? 'date' : 'text'"
        :placeholder="f.placeholder"
        :style="{ width: f.width ?? '168px' }"
      />
    </label>

    <div v-if="actions" class="acts">
      <button type="button" class="ad-btn ad-btn--ghost" @click="reset">重置</button>
      <button type="submit" class="ad-btn ad-btn--primary">查询</button>
      <button type="button" class="ad-btn ad-btn--icon" aria-label="刷新" @click="emit('refresh')">
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M13.5 8a5.5 5.5 0 1 1-1.9-4.2M13.5 2.5V6H10" />
        </svg>
      </button>
    </div>
  </form>
</template>

<style scoped>
.filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 18px;
}

.field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 12px;
  color: var(--yz-text-muted);
  white-space: nowrap;
}

.acts {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
</style>

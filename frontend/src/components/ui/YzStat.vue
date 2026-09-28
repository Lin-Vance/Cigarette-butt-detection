<script setup lang="ts">
export interface YzStatItem {
  label: string
  value: string | number
  /** 底部说明，如「较上周 +3.2%」 */
  hint?: string
  /** 说明文字的方向语义：up=红（变差） down=绿（改善） flat=中性 */
  trend?: 'up' | 'down' | 'flat'
  /** 数值强调色 */
  tone?: 'primary' | 'danger' | 'warning' | 'success'
}

withDefaults(defineProps<{ items: YzStatItem[]; compact?: boolean }>(), { compact: false })

const fmt = (v: string | number) =>
  typeof v === 'number' ? v.toLocaleString('zh-CN') : v
</script>

<template>
  <div class="stats" :class="{ compact }">
    <article v-for="s in items" :key="s.label" class="stat">
      <p class="label">{{ s.label }}</p>
      <p class="value yz-num" :class="s.tone ?? 'primary'">{{ fmt(s.value) }}</p>
      <p v-if="s.hint" class="hint" :class="s.trend ?? 'flat'">{{ s.hint }}</p>
    </article>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.stat {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid #dbe8f2;
  border-radius: 11px;
  box-shadow: 0 2px 7px rgba(61, 112, 150, 0.06);
}

.compact .stat {
  padding: 9px 14px;
}

.label {
  font-size: 12px;
  color: var(--yz-text-muted);
}

.value {
  margin-top: 4px;
  font-size: 26px;
  line-height: 1.2;
  font-weight: 700;
  color: #117fba;
}

.compact .value {
  font-size: 22px;
}

.value.danger {
  color: var(--yz-danger);
}
.value.warning {
  color: var(--yz-warning);
}
.value.success {
  color: var(--yz-success);
}

.hint {
  margin-top: 3px;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.hint.up {
  color: #fb5b4b;
}
.hint.down {
  color: #00a971;
}
</style>

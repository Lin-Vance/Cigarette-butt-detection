<script setup lang="ts">
/** 后台面板：统一标题栏 + 计数 + 右上工具槽 */
defineProps<{
  title: string
  count?: number | string
  countUnit?: string
  /** 面板是否撑满剩余高度 */
  grow?: boolean
}>()
</script>

<template>
  <section class="panel" :class="{ grow }">
    <header class="head">
      <h2 class="title">{{ title }}</h2>
      <span v-if="count !== undefined" class="count">
        共 {{ typeof count === 'number' ? count.toLocaleString('zh-CN') : count }}{{ countUnit ?? '条' }}
      </span>
      <div class="tools"><slot name="tools" /></div>
    </header>
    <div class="body"><slot /></div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid #dbe8f2;
  border-radius: 11px;
  box-shadow: 0 2px 7px rgba(61, 112, 150, 0.06);
}

.grow {
  flex: 1;
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  padding: 10px 16px;
  border-bottom: 1px solid #e6eef5;
}

.title {
  font-size: 14px;
  font-weight: 700;
  color: var(--yz-text-strong);
  white-space: nowrap;
}

.count {
  font-size: 11px;
  color: var(--yz-text-muted);
}

.tools {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.body {
  flex: 1;
  min-height: 0;
  padding: 12px 16px 14px;
}

/* 表格型 grow 面板将剩余空间均匀分给数据行，避免数据只挤在顶部、
   下半块留下大面积无信息白区。仅作用于直属表格，不影响图表与表单。 */
.grow .body {
  display: flex;
  flex-direction: column;
}
.grow .body > :deep(.table) {
  flex: 1;
}
.grow .body > :deep(.table > .tr:not(.th)) {
  flex: 1 0 32px;
}
</style>

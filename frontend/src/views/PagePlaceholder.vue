<script setup lang="ts">
/**
 * 未迁移页面的占位视图
 *
 * 页面迁移期间的兜底组件；正常菜单页均应由真实视图渲染。
 * 明确标注设计稿页号与待实现要点，避免"看起来像坏了"。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { findModuleByPageNo } from '@/config/pages'

const route = useRoute()
const router = useRouter()

const pageNo = computed(() => Number(route.meta.pageNo ?? 0))
const title = computed(() => String(route.meta.title ?? ''))
const note = computed(() => String(route.meta.note ?? ''))
const moduleLabel = computed(() => String(route.meta.module ?? ''))
const moduleDef = computed(() => findModuleByPageNo(pageNo.value))

const siblings = computed(() => moduleDef.value?.pages ?? [])
</script>

<template>
  <div class="placeholder">
    <div class="ph-card">
      <div class="ph-head">
        <span class="ph-no">{{ pageNo }}</span>
        <div>
          <h2 class="ph-title">{{ title }}</h2>
          <p class="ph-sub">{{ moduleLabel }} · 设计稿页 {{ pageNo }} / 18</p>
        </div>
        <span class="yz-tag yz-tag--warning ph-flag">待迁移</span>
      </div>

      <p v-if="note" class="ph-note">{{ note }}</p>

      <div class="ph-block">
        <h3 class="ph-h3">迁移时要做的三件事</h3>
        <ol class="ph-list">
          <li>
            <b>还原版式</b> —— 以
            <code>页面编号 {{ pageNo }}</code>
            为像素级参照，Element Plus 只提供行为（分页 / 校验 / 弹窗），外观按设计令牌覆盖。
          </li>
          <li>
            <b>接上数据</b> —— 列表类替换为 <code>useDemoStore()</code> 的
            <code>events / workOrders / suggestions</code>；统计卡替换为
            <code>metrics</code>；<b>图表贴图一律换成可交互 ECharts</b>。
          </li>
          <li>
            <b>打通链路</b> —— 与「模拟一次违规」产生的数据联动，保证从告警到工单闭环全程可按。
          </li>
        </ol>
      </div>

      <div class="ph-block">
        <h3 class="ph-h3">同模块其他页面</h3>
        <div class="ph-chips">
          <button
            v-for="p in siblings"
            :key="p.name"
            class="ph-chip"
            :class="{ on: p.name === String(route.name) }"
            type="button"
            @click="router.push({ name: p.name })"
          >
            <component :is="p.icon" class="ph-chip-icon" />
            {{ p.short }}
            <span v-if="!p.migrated" class="ph-chip-dot">待迁移</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.ph-card {
  width: 1040px;
  padding: 34px 40px 32px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid #dbe8f2;
  border-radius: var(--yz-radius-card);
  box-shadow: 0 2px 7px rgba(61, 112, 150, 0.06);
}

.ph-head {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e6eef5;
}
.ph-no {
  flex: none;
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: var(--yz-radius-btn);
  background: var(--yz-primary-soft);
  color: var(--yz-primary);
  font-size: 22px;
  font-weight: 700;
}
.ph-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--yz-text-strong);
}
.ph-sub {
  margin-top: 6px;
  font-size: 13px;
  color: var(--yz-text-muted);
}
.ph-flag {
  margin-left: auto;
}

.ph-note {
  margin-top: 18px;
  padding: 12px 16px;
  background: #f4f9fd;
  border-left: 3px solid var(--yz-accent-cyan);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--yz-text-2);
}

.ph-block {
  margin-top: 24px;
}
.ph-h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--yz-text-strong);
  margin-bottom: 12px;
}
.ph-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  counter-reset: ph;
}
.ph-list li {
  position: relative;
  padding-left: 30px;
  font-size: 13px;
  line-height: 1.75;
  color: var(--yz-text-2);
  counter-increment: ph;
}
.ph-list li::before {
  content: counter(ph);
  position: absolute;
  left: 0;
  top: 3px;
  width: 19px;
  height: 19px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--yz-primary-soft);
  color: var(--yz-primary);
  font-size: 11px;
  font-weight: 700;
}
code {
  padding: 1px 6px;
  background: #eef4f9;
  border-radius: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: #2b6aa3;
}

.ph-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.ph-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid var(--yz-border-soft);
  border-radius: 17px;
  font-size: 13px;
  color: var(--yz-text-2);
}
.ph-chip:hover {
  border-color: var(--yz-primary);
  color: var(--yz-primary);
}
.ph-chip.on {
  background: var(--yz-primary-soft);
  border-color: var(--yz-primary);
  color: var(--yz-primary);
  font-weight: 700;
}
.ph-chip-icon {
  width: 14px;
  height: 14px;
}
.ph-chip-dot {
  color: var(--yz-warning);
  font-size: 11px;
}
</style>

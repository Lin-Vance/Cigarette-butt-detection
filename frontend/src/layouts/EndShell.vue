<script setup lang="ts">
/**
 * 非管理端页面的通用外壳（入口页 / 市民端 / 环卫工人端）。
 *
 * 目的：让这三个页面与**管理端同一套外观**——
 * 顶栏用同一组设计令牌（`--yz-*`）、同样的品牌区与数据源标记，
 * 内容区背景用 `--yz-canvas-bg`，卡片一律复用 `.ad-*` 原子类与
 * `YzPanel / YzStat / YzTable`。
 *
 * 与管理端的差异只有一处：这里**不套 FitShell 定宽缩放**，
 * 因为这三页要能在手机上看，收敛的是「视觉语言」而不是「画布尺寸」。
 */
import { computed } from 'vue'
import { USE_API } from '@/api/client'
import { useDemoStore } from '@/stores/demo'

const props = withDefaults(
  defineProps<{
    /** 顶栏标题 */
    title: string
    /** 顶栏副标题 */
    subtitle?: string
    /** 顶栏右侧的身份显示，如「张建国 · worker01」 */
    user?: string
    /** 内容区最大宽度（数字或 CSS 长度），默认 1240 */
    width?: number | string
    /** 当前所在端，用于高亮顶栏的跳转快捷键；留空则不显示该组 */
    end?: '' | 'index' | 'auth' | 'citizen' | 'worker' | 'admin'
  }>(),
  { subtitle: '', user: '', width: 1240, end: '' }
)

/** 数字自动补 px，字符串按原样用（便于传 "100%" 之类的长度） */
const maxWidth = computed(() =>
  typeof props.width === 'number' ? `${props.width}px` : props.width
)

const demo = useDemoStore()

/** 数据源标记：明确当前是后端数据还是本地模拟，避免演示时说不清 */
const sourceText = computed(() => {
  if (!USE_API) return '本地模拟数据'
  return demo.backendOnline ? '已连接后端' : '后端离线 · 已回退本地模拟'
})
const sourceLive = computed(() => USE_API && demo.backendOnline)
</script>

<template>
  <div class="end-shell">
    <header class="es-bar">
      <a class="es-brand" href="./index.html" title="返回入口页">
        <img src="/logo-horizontal.png" alt="烟踪智治" />
        <span class="es-brand-txt">
          <strong>{{ title }}</strong>
          <small>{{ subtitle || '烟踪智治 · 城市公共空间治理原型' }}</small>
        </span>
      </a>

      <nav class="es-nav" aria-label="页面导航"><slot name="nav" /></nav>

      <div class="es-right">
        <span class="es-source" :class="{ live: sourceLive }">{{ sourceText }}</span>
        <span v-if="user" class="es-user">{{ user }}</span>
        <slot name="actions" />
      </div>
    </header>

    <main class="es-main">
      <div class="es-inner" :style="{ maxWidth }">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.end-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--yz-canvas-bg);
  color: var(--yz-text-body);
  font-family: var(--yz-font);
}

/* ---------- 顶栏（对齐管理端 --yz-topbar-* 令牌） ---------- */
.es-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: none;
  height: var(--yz-topbar-h);
  padding: 0 24px;
  border-bottom: 1px solid var(--yz-topbar-border);
  background: var(--yz-topbar-bg);
  box-shadow: var(--yz-topbar-shadow);
  z-index: 10;
}

.es-brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  text-decoration: none;
  color: inherit;
}
.es-brand img {
  height: 34px;
  width: auto;
}
.es-brand-txt strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--yz-text-strong);
  letter-spacing: 0.4px;
}
.es-brand-txt small {
  display: block;
  margin-top: 1px;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.es-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow-x: auto;
}

.es-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.es-source {
  padding: 4px 10px;
  border-radius: var(--yz-radius-pill);
  border: 1px solid var(--yz-border-soft);
  background: #fff;
  font-size: 11px;
  color: var(--yz-warning);
  white-space: nowrap;
}
.es-source.live {
  color: var(--yz-success);
  border-color: #b7e3d2;
  background: #e6f5f0;
}

.es-user {
  font-size: 13px;
  color: var(--yz-text-2);
  white-space: nowrap;
}

/* ---------- 内容区 ---------- */
.es-main {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  /* 底部原先留了 74px，是给「页面底部固定换端条 .yz-ends」让位的。
     换端条现在只挂在入口页 `index.html`（挂在 #app 之外，不走这个外壳），
     这 74px 就变成了所有非管理端页滚到底后的一条纯空白带。
     这里收回到与其它方向一致的 16px，页面自身的内边距继续提供留白。 */
  padding: 16px 24px;
}
.es-inner {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 0 auto;
}

@media (max-width: 860px) {
  .es-bar {
    gap: 12px;
    padding: 0 14px;
  }
  .es-brand-txt small {
    display: none;
  }
  .es-main {
    padding: 12px 14px 20px;
  }
  .es-nav {
    display: none;
  }
  .es-source {
    font-size: 10px;
    padding: 3px 8px;
  }
}

@media (max-width: 520px) {
  /* 手机宽度下顶栏只剩「标识 + 标题 + 右侧动作」，来源与用户名让位给标题 */
  .es-bar {
    gap: 8px;
    padding: 0 10px;
  }
  .es-brand {
    flex: 1 1 auto;
    min-width: 0;
    gap: 8px;
  }
  .es-brand img {
    height: 26px;
  }
  .es-brand-txt {
    min-width: 0;
  }
  .es-brand-txt strong {
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .es-source,
  .es-user {
    display: none;
  }
  .es-right {
    flex: none;
    gap: 8px;
  }
}
</style>

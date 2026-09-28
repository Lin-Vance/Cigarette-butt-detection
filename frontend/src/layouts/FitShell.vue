<script setup lang="ts">
/**
 * FitShell · 定宽等比缩放外壳
 *
 * 设计画布固定 1672 × 941（= 16:9），整体等比缩放到视口内并居中。
 * 这是现有 18 页设计稿采用的策略，必须在 Vue3 中继承：
 * 答辩投影时无论分辨率如何，"永远不崩版"。
 *
 * 缩放系数取 contain 策略并封顶 1（不放大）：
 *   scale = min(1, vw / 1672, vh / 941)
 * 相比设计稿原始实现（仅按宽度缩放，高于 16:9 的窗口会裁掉底部），
 * 这里同时约束高度，保证画面完整可见。
 */
import { onBeforeUnmount, onMounted, ref, computed } from 'vue'
import { DESIGN_W, DESIGN_H } from '@/config/design'

/** 管理端是可读性的下限：窄于此宽度不再缩放，改提示用宽屏（缺陷 D-06）。 */
const MIN_READABLE_W = 900

const viewportRef = ref<HTMLElement | null>(null)
const scale = ref(1)
const canvasHeight = ref(DESIGN_H)
const tooNarrow = ref(false)

let ro: ResizeObserver | null = null

function fit() {
  const el = viewportRef.value
  if (!el) return
  const { width, height } = el.getBoundingClientRect()
  if (!width || !height) return
  // 管理端以宽度为第一适配基准；高一些的浏览器把额外空间交给内容区，
  // 矮一些的浏览器则由各页面内部滚动，避免 contain 缩放后上下露出灰带。
  scale.value = Math.min(1, width / DESIGN_W)
  canvasHeight.value = Math.max(DESIGN_H, Math.ceil(height / scale.value))
  // 1672 定宽画布按 390px 缩，字号实际只有 3~4px，比"不响应式"更糟：
  // 直接给一个可见的宽屏提示，而不是把界面缩成蚂蚁。
  tooNarrow.value = width < MIN_READABLE_W
}

onMounted(() => {
  fit()
  if (typeof ResizeObserver !== 'undefined' && viewportRef.value) {
    ro = new ResizeObserver(fit)
    ro.observe(viewportRef.value)
  }
  window.addEventListener('resize', fit)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', fit)
})

const stageStyle = computed(() => ({
  width: `${DESIGN_W}px`,
  height: `${canvasHeight.value}px`,
  transform: `scale(${scale.value})`
}))
</script>

<template>
  <div ref="viewportRef" class="fit-viewport">
    <div class="fit-stage" :style="stageStyle">
      <slot />
    </div>

    <!-- 窄屏兜底：管理端是桌面后台，不做完整响应式可以接受，
         但必须**说清楚**，而不是把 1672 宽画布缩成不可读（缺陷 D-06）。 -->
    <div v-if="tooNarrow" class="fit-guard" role="alertdialog" aria-live="polite">
      <div class="fg-card">
        <span class="fg-badge">管理员端 · 桌面后台</span>
        <h2>请在 1280px 及以上的宽屏使用</h2>
        <p>
          管理端按 1672×941 定宽画布设计，窄屏强行缩放会把字号压到不可读。
          手机 / 平板请改用下面两个端：
        </p>
        <div class="fg-acts">
          <a class="fg-solid" href="./citizen.html">进入市民端</a>
          <a class="fg-ghost" href="./worker.html">进入环卫端</a>
          <a class="fg-ghost" href="./index.html">返回入口页</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fit-viewport {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow: hidden;
  background: var(--yz-canvas-bg);
}

.fit-stage {
  flex: none;
  position: relative;
  transform-origin: center top;
  overflow: hidden;
  background: var(--yz-canvas-bg);
}

/* ---------- 窄屏兜底提示 ---------- */
.fit-guard {
  position: fixed;
  inset: 0;
  z-index: 2147483000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(223, 230, 237, 0.94);
  backdrop-filter: blur(3px);
  font-family: var(--yz-font, "Microsoft YaHei", sans-serif);
}

.fg-card {
  width: 100%;
  max-width: 380px;
  padding: 24px 22px;
  border: 1px solid #cbdbe9;
  border-radius: 18px;
  background: #fff;
  text-align: center;
  box-shadow: 0 14px 34px rgba(72, 135, 177, 0.22);
}

.fg-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: #eaf5ff;
  color: #087ce0;
  font-size: 11px;
}

.fg-card h2 {
  margin: 12px 0 8px;
  color: #1c2d44;
  font-size: 17px;
}

.fg-card p {
  margin: 0 0 16px;
  color: #7d8999;
  font-size: 12.5px;
  line-height: 1.75;
  text-align: left;
}

.fg-acts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fg-acts a {
  padding: 11px 0;
  border-radius: 11px;
  font-size: 13px;
  text-decoration: none;
}

.fg-solid {
  color: #fff;
  background: linear-gradient(100deg, #216eff, #4baedb);
}

.fg-ghost {
  border: 1px solid #cbdbe9;
  color: #293b61;
  background: #fff;
}
</style>

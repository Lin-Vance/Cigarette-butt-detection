<script setup lang="ts">
/**
 * 管理员端主框架
 * 管理端总览仍包含设计稿的绝对定位模块，因此保留等比适配外壳，
 * 同时由 `.ad-page` 统一普通管理页面的内容边距。
 */
import { onMounted } from 'vue'
import AppTopbar from '@/components/AppTopbar.vue'
import FitShell from '@/layouts/FitShell.vue'
import { useDemoStore } from '@/stores/demo'

const demo = useDemoStore()

onMounted(() => {
  demo.init()
})
</script>

<template>
  <FitShell>
    <div class="admin-shell">
      <AppTopbar />
      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </FitShell>
</template>

<style scoped>
.admin-shell {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--yz-canvas-bg);
}

.admin-content {
  position: absolute;
  left: 0;
  top: var(--yz-topbar-h);
  width: 100%;
  height: calc(100% - var(--yz-topbar-h));
  overflow: hidden;
}
</style>

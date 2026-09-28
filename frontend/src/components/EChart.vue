<script setup lang="ts">
/**
 * ECharts 轻量封装
 *
 * 注意：全站画布是固定 1672 × 941（由 FitShell 整体 transform 缩放），
 * DOM 布局尺寸恒定，因此图表无需跟随视口 resize —— transform 不改变 layout。
 * 这里只在容器尺寸真实变化时 resize，避免无谓开销。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  option: echarts.EChartsOption
  /** 用于实例化时关闭动画（截图/演示场景可传 false 保留动画） */
  animation?: boolean
}>()

const el = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value, undefined, { renderer: 'canvas' })
  render()
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(() => chart?.resize())
    ro.observe(el.value)
  }
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  ro?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="echart-host" />
</template>

<style scoped>
.echart-host {
  width: 100%;
  height: 100%;
}
</style>

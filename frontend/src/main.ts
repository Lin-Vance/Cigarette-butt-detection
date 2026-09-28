import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
/**
 * 只注册**实际用到**的图标（缺陷 D-15）。
 *
 * 以前这里是 `import * as ElementPlusIconsVue` + 整包循环注册，
 * 直接把全部 300+ 图标打进主包（`main` 1385KB / gzip 459KB），
 * 并让 Rollup 无法 tree-shake。
 *
 * 图标在页面里是**按名字符串**动态解析的（`<component :is="p.icon" />`，
 * 名字来自 `config/pages.ts` 的 `icon` 字段与各页面的 icon 声明），
 * 不能用标签形式按需引入 —— 所以这里显式列出全集。
 *
 * ⚠️ 在 `config/pages.ts` 或任意页面新增 `icon: 'Xxx'` 时，
 *    必须把 Xxx 补进下面的 import 与 ICONS，否则图标会静默不渲染。
 */
import {
  Bell,
  Box,
  Cpu,
  DataAnalysis,
  Document,
  Finished,
  Grid,
  Histogram,
  List,
  MapLocation,
  Monitor,
  Odometer,
  Operation,
  Setting,
  Stamp,
  Tickets,
  User,
  Van,
  VideoCamera,
  Warning
} from '@element-plus/icons-vue'

import 'element-plus/dist/index.css'
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/admin.css'

import App from './App.vue'
import router from './router'

const ICONS = {
  Bell,
  Box,
  Cpu,
  DataAnalysis,
  Document,
  Finished,
  Grid,
  Histogram,
  List,
  MapLocation,
  Monitor,
  Odometer,
  Operation,
  Setting,
  Stamp,
  Tickets,
  User,
  Van,
  VideoCamera,
  Warning
}

const app = createApp(App)

for (const [key, component] of Object.entries(ICONS)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      // 离线能力属于渐进增强；注册失败不影响网站基本使用。
    })
  })
}

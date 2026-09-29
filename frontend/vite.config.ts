import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const entry = (name: string) => fileURLToPath(new URL(`./${name}.html`, import.meta.url))

export default defineConfig({
  /**
   * `base: './'` 只改写**打包引用**（`<script src>`、CSS url()），
   * 改不动代码里的运行时字符串。
   *
   * ⚠️ 因此构建产物**不能** `file://` 双击打开（缺陷 D-09）：
   * 页面里 `/media/...` 是绝对路径，
   * 双击打开时协议是 file://，这些请求会全部 404，设计稿图片全丢。
   *
   * 正确打开方式：用本地静态服务（见 `start-frontend.bat` / `preview-build.bat`）。
   */
  base: './',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5180,
    // 固定端口：端口漂移会连带 CORS 白名单失配（历史缺陷 D-01），
    // 这里显式拒绝自动换端口，让问题在启动瞬间就暴露，而不是变成运行期 403。
    strictPort: true,
    host: '127.0.0.1',
    /** 所有 HTTP、文件和 WebSocket 请求统一使用 FastAPI，避免双后端状态与权限不一致。 */
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      /**
       * 后端存活探测。**必须代理**，否则 `/healthz` 会被 Vite 的 SPA fallback
       * 以「200 + index.html」应答，任何基于它的探活都会永远报"在线"（历史缺陷 D-14）。
       * 代理到位后：后端没起 → 代理返回 5xx → 探活正确判离线。
       */
      '/healthz': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // 后端把本地 storage/ 挂在 /storage 下（替代 MinIO），
      // 证据帧与闭环照片都从这里取，必须一并代理，否则图片 404。
      '/storage': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      // 多页构建：每个端一个独立 HTML，彼此可单独打开与互相跳转。
      // 交警端已并入管理端（执法协同模块），不再单列页面。
      input: {
        index: entry('index'),
        auth: entry('auth'),
        citizen: entry('citizen'),
        worker: entry('worker'),
        admin: entry('admin')
      }
    }
  }
})

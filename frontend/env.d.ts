/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** 设为 '1' 时业务数据走后端 API；否则走本地模拟数据（默认） */
  readonly VITE_USE_API?: string
  /** 后端接口前缀，默认 '/api/v1'（由 vite 代理到 127.0.0.1:8000） */
  readonly VITE_API_BASE?: string
}

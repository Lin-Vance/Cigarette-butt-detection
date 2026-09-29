# 烟踪智治前端

Vue 3、TypeScript、Pinia、Element Plus 与 Vite 组成的多入口前端。

## 页面入口

- `index.html`：公开官网。
- `auth.html`：统一登录与注册。
- `citizen.html`：市民 App。
- `worker.html`：环卫作业端。
- `admin.html`：管理与执法协同端。

## 开发

```powershell
npm ci
npm run dev
```

开发服务器默认监听 `127.0.0.1:5180`，并将 `/api`、`/healthz`、`/storage` 与 `/ws` 统一代理到 FastAPI `127.0.0.1:8000`。

## 检查与构建

```powershell
npm run typecheck
npm run build
npm audit

$env:BASE='http://127.0.0.1:5180/'
npm run qa
npm run qa:ends
```

源文件命名约定：Vue 组件使用 `PascalCase.vue`，TypeScript 模块使用 `camelCase.ts`，静态资源使用小写 kebab-case。

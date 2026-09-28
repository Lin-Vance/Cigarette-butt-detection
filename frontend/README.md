# 烟踪智治 · 前端工程

五个独立页面（入口长滚动 / 登录注册 / 市民端 / 环卫端 / 管理端）+ 后台 18 页。

> Vue3 + TypeScript + Vite + Element Plus + ECharts 工程化重写版
> 替代 `smoke-admin/` 的 18 页静态设计稿复现。

---

## 一、为什么重写

现有 `smoke-admin/` 是 18 页**定宽 1672×941 + fit-shell JS 缩放**的设计稿复现（原生 HTML/CSS/JS），
数据全部写死、部分图表是 PNG 贴图。要接真实数据、做完整闭环，必须工程化。

重写的**硬约束**（详见 `../docs/烟踪智治-文档缺陷与修订说明.md` C4）：

1. **视觉以设计稿为准** —— `smoke-admin/` 的配色、间距、圆角、图标语义是视觉规范来源。
   Element Plus 只提供**行为**（分页、校验、弹窗、表格滚动），外观必须按
   `src/styles/tokens.css` 覆盖，**不得退回 EP 默认外观**。
2. **保留定宽缩放** —— 1672×941 画布 + 整体等比缩放，答辩投影"永远不崩版"，
   由 `src/layouts/FitShell.vue` 继承。
3. **复用现有图片资源** —— 86 张 PNG（品牌 logo、地图底图、摄像头缩略图、图标）
   已复制到 `public/design-assets/{页号}/`，按设计稿页号分目录避免重名冲突。

---

## 二、快速开始

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5180
```

演示账号：`admin` / `123456`（后端未接入，登录走本地模拟校验）

其它命令：

```bash
npm run build      # 产物输出到 dist/
npm run preview    # 预览构建产物
npm run typecheck  # vue-tsc 类型检查
npm run qa         # 全站质检（CDP 驱动，需先启动 dev/preview）
npm run qa:ends    # 多端页面质检：五个页面 + 端间跳转 + 端内交互
```

`npm run qa` 会在一个浏览器会话里跑完 44 条用例：五个页面、23 条 hash 路由、
6 条移动端视口、入口页 5 屏长滚动（章节数 / 顶栏跳转命中 / 真实页面链接 / 底部切换条）、
市民端 tab 与上报流程、管理员登录，以及后台 5 项深度交互（AI 阈值联动、GIS 图层开关、
权限抽屉、表格翻页、量级切换）。
每条用例同时校验运行时异常、console.error、资源 4xx/5xx 与横向溢出。

> 写用例时注意：**路由签名要用「挂载后不会变」的类名**。像入口页根节点 `.lp`
> 和登录页根节点 `.au` 会在 `onMounted` 里追加状态类（`.lp solid` / `.au ready`），
> 用 `class="au"` 这种精确串匹配会把好页面判成「未渲染」。脚本里现在用
> `lp-glow` / `au-bloom` 这类稳定的内部类名。

`npm run qa:ends` 单独验「五个页面彼此分开、能互相跳转」这件事本身：卡片 href 是否为
真实 `.html` 跳转、点击是否真的换页、切换条是否每页都在且高亮正确、顶栏端间快捷键是否
与底部切换条一致、登录页能否按身份跳进对应端、端内交互是否可用。

---

## 三、目录结构

```
frontend/
├── index.html                     # 入口页（5 屏长滚动）
├── auth.html                      # 登录 / 注册
├── citizen.html / worker.html / admin.html
├── public/
│   ├── design-assets/{1..18}/     # 复用设计稿图片资源（86 张）
│   ├── media/street-hero.png      # 入口页首屏实景图
│   ├── logo-horizontal.png        # 【品牌】透明底横版，浅色背景通用
│   ├── logo-mark.png              # 【品牌】透明底方形徽标，深色背景用
│   ├── favicon.png / apple-touch-icon.png   # 由同一个源 logo 派生
│   └── end-switcher.css           # 入口页底部「端」切换固定条（窄屏贴底铺满）
├── scripts/
│   ├── qa.mjs                     # 全站质检（CDP 驱动，见 §二）
│   ├── qa-ends.mjs                # 多端页面与端间跳转质检
│   ├── shot.mjs                   # 截图小工具（--url / --w / --h / --js）
│   ├── make-logo-mark.py          # 从管理端 logo 派生全站统一品牌资产
│   └── erase-baked-logo.py        # 抹掉登录页背景图里烘焙的旧 logo
├── src/
│   ├── config/
│   │   ├── design.ts              # 画布常量 1672×941 / 顶栏 60px
│   │   └── pages.ts               # 18 页 + 7 模块注册表（全站唯一数据源）
│   ├── styles/
│   │   ├── tokens.css             # 设计令牌（从设计稿 styles.css 提取）
│   │   ├── base.css               # reset + 通用卡片/标题/标签
│   │   └── admin.css              # 后台 `.ad-*` 原子类（全局，各端复用）
│   ├── layouts/
│   │   ├── FitShell.vue           # 定宽等比缩放外壳（仅后台）
│   │   ├── AdminLayout.vue        # 顶栏 + 内容区
│   │   └── EndShell.vue           # 入口/登录/市民/环卫共用外壳（顶栏 + 数据源标记）
│   ├── components/
│   │   ├── ui/                       # 通用组件（页面 3-18 复用）
│   │   │   ├── YzPanel.vue           # 面板：标题 + 计数 + 右上工具槽
│   │   │   ├── YzTable.vue           # 表格：列定义驱动，支持勾选 / 行插槽 / dense 紧凑行高
│   │   │   ├── YzStat.vue            # 统计卡组
│   │   │   ├── YzFilter.vue          # 筛选条 + 重置/查询/刷新三件套
│   │   │   ├── YzPager.vue           # 分页（共 N 条 / N 条每页 / 页码 / 前往）
│   │   │   └── YzMapStage.vue        # 抽象地图舞台：街网底图 + 点位/热力/路线图层 + 缩放
│   │   ├── AppTopbar.vue             # 全站顶栏 + yz-dd v4 悬浮卡片菜单
│   │   └── EChart.vue                # ECharts 轻量封装
│   ├── stores/
│   │   ├── auth.ts                   # 登录态 + RBAC 页面裁剪
│   │   └── demo.ts                   # 模拟数据状态 + 一键演示一次违规
│   ├── mock/
│   │   ├── types.ts                  # 对齐 PRD §7.1 / §8.3 的数据契约
│   │   ├── config.ts                 # 演示数据量级两档（design / pilot）
│   │   ├── engine.ts                 # 合规事件生成器
│   │   └── pages.ts                  # 各页面列表数据 + 地图投影工具
│   └── views/
│       ├── PortalView.vue            # 入口页：5 屏长滚动叙事
│       ├── AuthView.vue              # 登录 / 注册（Arc × Apple 风）
│       ├── CitizenLoginView.vue      # 市民手机号登录
│       ├── CitizenAppView.vue        # 市民用户端
│       ├── WorkerAppView.vue         # 环卫工人端
│       ├── LawCasesView.vue          # 执法协同 · 线索核查
│       ├── LawTrailView.vue          # 执法协同 · 处置留痕
│       ├── LoginView.vue             # 页面 1
│       ├── OverviewView.vue          # 页面 2
│       ├── GovernanceView.vue        # 页面 3
│       ├── DeviceStatusView.vue      # 页面 4
│       ├── WorkboardView.vue         # 页面 5
│       ├── AlertsView.vue            # 页面 6
│       ├── ReportView.vue            # 页面 7
│       ├── DispatchPoolView.vue      # 页面 8
│       ├── DispatchRecordsView.vue   # 页面 9
│       ├── GisView.vue               # 页面 10
│       ├── DeviceArchiveView.vue     # 页面 11
│       ├── SanitationView.vue        # 页面 12
│       ├── AiModelView.vue           # 页面 13
│       ├── AiConfigView.vue          # 页面 14
│       ├── AnalysisView.vue          # 页面 15
│       ├── UsersView.vue             # 页面 16
│       ├── PlatformConfigView.vue    # 页面 17
│       ├── AuditView.vue             # 页面 18
│       └── PagePlaceholder.vue       # 兜底占位视图
```

### 3.1 五个页面（多页构建）

站点是 **Vite 多页（MPA）** 结构：五个彼此独立的 HTML，各自能单独打开、互相能跳。

换端入口的定位（2026-09-28 缺陷 D-04 的决策，**以此为准**）：

- **入口页 `index.html` 底部固定条**：`public/end-switcher.css` 的 `.yz-ends`，
  挂在 `#app` 之外，不受 Vue 布局与定宽缩放影响。
  **所有宽度都显示**，窄屏（≤640px）贴底铺满、可横向滚动 —— 手机用户不会被锁在单一端里。
- **正式端页（登录/市民/环卫/管理）不再出现换端条**：各端顶栏的品牌 logo 指向 `./index.html`，
  需要换端时先回入口页。登录/注册页顶栏另有「首页 / 市民端 / 环卫端 / 管理端」直达链接。
- 历史文档里提到的「`EndShell` 顶栏 `.es-cross` 快捷组（≥900px 显示）」**已不存在**，
  不要再按它去改代码或用例。

| 页面 | 文件 | 起始路由 | 说明 |
|------|------|----------|------|
| 入口页 | `index.html` | `#/` → `PortalView` | **5 屏长滚动叙事**：主张 / 断点 / 机制 / 分端 / 边界；底部含换端固定条 |
| 登录 · 注册 | `auth.html` | `#/auth` → `AuthView` | 三种身份（市民 / 环卫 / 管理）统一入口，登录后跳对应端 |
| 市民用户端 | `citizen.html` | `#/citizen-login` → `#/citizen` | 未登录自动转市民登录页 |
| 环卫工人端 | `worker.html` | `#/worker` | `WorkerAppView`，端内自带登录 |
| 管理员端 | `admin.html` | `#/platform/overview` | 未登录自动转管理员登录页；**含执法协同模块** |

> 五个 HTML 的 `<html data-end="…">` 决定「未知路由（catch-all）回落到本端哪个默认页」，
> 新增端时记得同步 `src/router/index.ts` 的 `END_HOME`。

**入口页只保留叙事，不再有「选择要进入的端」那种后台面板**：端入口是 §04「分端」这一屏
里的三张卡，叙事本身承担引导职责。首屏是整屏 Hero（实景图 + 大标题 +
INPUT/REVIEW/OUTPUT 三胶囊），滚动驱动逐屏显影与顶部进度条。

**交警端已并入管理员端**，成为后台的「执法协同」模块（两页）：

| 页 | 路由名 | 文件 | 说明 |
|----|--------|------|------|
| 执法线索核查 | `law-cases` | `LawCasesView.vue` | 已复核线索的核查、认领、处置（三个动作都要留痕） |
| 处置结果与留痕 | `law-trail` | `LawTrailView.vue` | 只读留痕：认领 / 退回 / 驳回 / 处置完成 |

线索状态与留痕放在 `stores/law.ts`，两个页面共享。执法协同**不做算法定性**，
也不展示举报人实名与被举报对象可识别画面。

**关键点**：入口页的卡片是真实的 `&lt;a href="./citizen.html"&gt;` **页面跳转**，
不是站内 hash 路由——各端是分开的页面，必须真的跳过去，而不是在同一个页面里换视图。

### 3.2 品牌标识只有一个源

全站 logo 只有一个来源：**管理端顶栏那张**
`public/design-assets/2/smoke_control_brand_logo.png`。其余位置一律用它派生的透明底版本，
不再各自为政（原先登录页用竖版 `super_admin_brand_logo`、favicon 是另一套配色的手绘 SVG，
平台配置预览又是第三张）。

派生由 `scripts/make-logo-mark.py` 完成：

| 产出 | 用途 |
|------|------|
| `logo-horizontal.png` | 浅色背景通用：后台顶栏、`EndShell` 顶栏、登录页、平台配置预览 |
| `logo-mark.png` | 深色背景：入口页长滚动顶栏与页脚 |
| `favicon.png` / `apple-touch-icon.png` | 浏览器标签 / 添加到主屏，图形与上面同源 |

两个脚本的原因记一下：

- 登录页背景图里**烘焙了旧 logo**（连 SUPER ADMIN 字样都画在图上），
  页面换成统一 logo 后会叠成两个。`scripts/erase-baked-logo.py` 把它抹掉——
  用固定比例框定区域 + 左右像素线性插值填充（**不要**用饱和度自动找包围盒，
  水彩左边缘和城市剪影会一起命中，抹出横向色带）。
- 品牌 png 是**白底**的，直接放在浅蓝水彩或深色背景上会出现白方块，
  所以派生素材统一做了「白→透明」。

### 3.3 非管理端页面的外观

入口页 / 市民端 / 环卫端**与管理端同一套视觉**：

- 共用 `layouts/EndShell.vue` 外壳：顶栏（品牌 + 导航槽 + 数据源标记 + 用户 + 退出）
  用 `--yz-topbar-*` 系列令牌，内容区背景用 `--yz-canvas-bg`；
- 共用 `.ad-*` 原子类（`admin.css`，全局引入）与 `YzPanel / YzStat / YzTable`；
- 市民端原有的 `--app-*` 变量保留变量名、值改为引用 `--yz-*` 令牌，
  这样不必逐条改样式就能整体对齐；旧的深色侧边栏与底部导航已由 EndShell 顶栏取代。

与管理端的**唯一差异**：这三页不套 `FitShell` 定宽缩放——它们要能在手机上看，
统一的是「视觉语言」而不是「画布尺寸」。

其它仍可访问的页：

| 路径 | 内容 |
|------|------|
| `#/auth` | 登录 / 注册（`auth.html`） |
| `#/citizen-login` / `#/login` | 市民登录 / 管理员登录 |
| `#/platform/xxx` | `AdminLayout` + 后台 18 页，需登录并按角色裁剪 |

开发期可在 URL 里带 `autologin=1` 跳过管理员登录（仅 DEV 生效），例如
`http://127.0.0.1:5180/#/platform/alerts?autologin=1`。
注意 hash 路由的 query 必须写在 `#` **内部**，写成 `/?autologin=1#/platform/alerts` 不会生效。
市民端同理，用 `#/citizen?autologin=citizen`。

> `autologin` 会**写入 localStorage 并持久化**。演示时不希望停留在已登录态，
> 可在后台顶栏点「退出」，或清掉 `localStorage` 里的 `yz.auth` / `yz.citizen`。

### 3.4 怎么打开

| 方式 | 做法 | 适用 |
|------|------|------|
| 开发态（推荐） | 双击 `start-frontend.bat`（等价 `npm run dev`），浏览器打开 `http://127.0.0.1:5180/index.html` | 日常演示、改代码即时生效 |
| 构建产物 | 双击 `preview-build.bat`（必要时先构建，再 `vite preview`） | 看正式构建结果 |

> `dist/` 里的 `index.html` **不能直接双击**（`file://`）：页面里的
> `/design-assets/...` 是绝对路径，在 `file://` 下会解析到磁盘根目录。
> 这些路径也不能改成 `./design-assets/...` —— Vue 模板里的相对 `src` 会被
> Rollup 当成模块去解析，构建直接失败。所以统一用本地静态服务打开。

---

## 四、迁移进度

| 页 | 标题 | 状态 |
|----|------|------|
| 1 | 管理员登录 | ✅ 已迁移（像素级还原） |
| 2 | 项目总览首页 | ✅ 已迁移（图表已换 ECharts） |
| 3 | 治理态势 · 未闭环预警 | ✅ 已迁移 |
| 4 | 设备运行地图 | ✅ 已迁移 |
| 5 | 区域任务分布地图 | ✅ 已迁移 |
| 6 | 告警数据列表 | ✅ 已迁移 |
| 7 | 事件报表 | ✅ 已迁移 |
| 8 | 调度中心任务池 | ✅ 已迁移 |
| 9 | 调度记录管理 | ✅ 已迁移 |
| 10 | 全域治理 GIS 地图 | ✅ 已迁移 |
| 11 | 设备档案管理 | ✅ 已迁移 |
| 12 | 环卫资源管理 | ✅ 已迁移 |
| 13 | 模型与数据集管理 | ✅ 已迁移 |
| 14 | AI 阈值配置 | ✅ 已迁移 |
| 15 | 数据分析 | ✅ 已迁移 |
| 16 | 用户账号管理 | ✅ 已迁移 |
| 17 | 全平台基础配置 | ✅ 已迁移（含演示数据量级切换） |
| 18 | 审计日志 | ✅ 已迁移 |

18 页全部迁移完成。`PagePlaceholder.vue` 保留作为新增路由未注册视图时的兜底，不再有页面走它。

### 4.1 迁移方式说明

页面 1、2 是**逐值移植设计稿坐标**（`position: absolute` + 精确 left/top/width/height）。
页面 3–18 改为**栅格化重建**：外观仍严格取自 `tokens.css` 令牌（配色、圆角、阴影、字号全部引用变量），
但排布改用 flex/grid，以便在 1672×941 画布内自适应、并保证内容不溢出画布。

改动前后逐页用 CDP 截了 1672×941 的对比图（`../shots/admin/`），并脚本化校验每页
`scrollHeight` 是否超出容器高度 —— 当前 17 个视图页面全部无溢出、无控制台报错。

---

## 五、关键设计决策

### 5.1 缩放策略

```ts
scale = min(1, vw / 1672, vh / 941)
```

设计稿原实现只按**宽度**缩放（`Math.min(1, w/1672)`），窗口比 16:9 更高时会裁掉底部。
这里同时约束高度，保证画面完整可见；封顶 1 不放大，避免投影时糊。

### 5.2 模拟数据引擎

AI 算法管道（三段式状态机、ByteTrack、光流法、抛物线拟合）**均未实现**，
因此 `src/mock/engine.ts` 承担"合规事件生成器"职责，生成的事件必须能通过
修订后的证据链校验：

- 三帧证据齐全且 `path` **非空**（对应修订说明缺陷 A4）
- 三帧时间戳严格递增（持烟 → 抛掷 → 落地）
- 轨迹点 ≥ 5（对应 PRD §5.2.1）
- 时间戳带 `+08:00` 时区（对应修订说明缺陷 C3）

### 5.3 演示数据量级两档

`src/mock/config.ts` 提供：

| 档位 | 用途 | 今日违规 | 在线设备 |
|------|------|----------|----------|
| `design`（默认） | 沿用设计稿数值，视觉与已验收页面一致 | 1,286 | 3,842 |
| `pilot` | 与 2-4 路摄像头试点规模匹配，答辩讲解用 | 27 | 4 |

对应修订说明缺陷 C2。切换入口后续放在「系统管理 → 全平台基础配置（页面 17）」。

### 5.4 热力图做了经度投影修正

`OverviewView.vue` 的 KDE 计算中：

```ts
const kx = Math.cos((lat * Math.PI) / 180)
const dx = (lon - c.longitude) * kx * 111320
```

对应修订说明缺陷 B10 —— 原文直接在 `(lat, lon)` 上算欧氏距离，
在信阳约 32°N 会把热区东西向拉扁 1.18 倍。

---

## 六、连后端（可开关）

后端已实现（见 `../backend/README.md`：FastAPI 单体 + 6 模块 + 2 个 WebSocket 频道 + 58 个接口）。

**默认不连**——不配任何环境变量时业务数据全部走本地模拟，保证没有后端也能完整演示。
要连后端：

```bash
cd frontend
cp .env.example .env.local     # 里面已写 VITE_USE_API=1
npm run dev
```

代理已在 `vite.config.ts` 配好，**三条统一指向同一个后端**：

| 前端路径 | 后端地址 | 用途 |
|----------|----------|------|
| `/api/*` | `http://127.0.0.1:8000` | 业务接口 |
| `/storage/*` | `http://127.0.0.1:8000` | 证据帧与闭环照片（替代 MinIO） |
| `/ws/*` | `ws://127.0.0.1:8000` | 实时推送 |

> `/storage` 这条代理是必须的：后端把本地 `storage/` 挂在 `/storage` 下，
> 不代理的话证据缩略图会 404。

#### 后端选型（唯一口径，别再改乱 —— 缺陷 D-03）

| 目录 | 端口 | 状态 | 说明 |
|------|------|------|------|
| `backend/`（FastAPI） | **8000** | ✅ **唯一被代理引用** | 接口清单完整：`/events`、`/workorders`、`/stats`、`/users`、`/audit`、`/suggestions`、`/citizen/*`、`/ai/*` 全部齐备；`/storage` 静态映射也在这里 |
| `backend-java/`（Spring Boot） | 8080 | ⚪️ 备选实现，**前端已不引用** | 只实现约四成接口（探测 14 个前端必需接口有 11 个 404），且没有 `/storage` 静态映射 |

> 历史坑：`/api` 曾指向 8080 而 `/storage`、`/ws` 指向 8000，导致 API 模式「半瘫」。
> 现在把三条统一到 8000 了；要换回 Java 必须先补齐上表接口清单和 `/storage` 映射。

> ⚠️ `VITE_USE_API=1` 时**必须先启动 `backend/`（8000）**，否则登录会失败。
> 后端没起也不会白屏：`stores/demo.ts` 会自动回退本地模拟数据，顶栏标记为
> 「后端离线 · 已回退本地模拟」。

开关打开后的实际差异：

| 位置 | 本地模拟 | 连接后端 |
|------|----------|----------|
| `stores/auth.ts` `login()` | 前端模拟校验 | `POST /auth/login`，**页面权限以后端下发为准** |
| `stores/demo.ts` `refresh()` | 每次重建随机数据 | `GET /cameras｜events｜workorders｜suggestions｜stats/*` |
| 一键演示违规 | 仅前端新增一条 | `POST /events/simulate` → 落库 + WS 广播 + 自动建单 |
| 工单动作 | 改本地状态 | `POST /workorders/{id}/accept｜start｜complete｜verify` |
| `stores/citizen.ts` | 只推进前端步骤 | 上报提交/查询/撤回/申诉全部落库 |
| 后端掉线 | — | **自动回退本地模拟**，页面不白屏 |

接口封装在 `src/api/`：`client.ts`（axios + 令牌 + 错误归一）、`endpoints.ts`（类型化端点）、
`ws.ts`（频道订阅，带自动重连与心跳）。

数据源提示在后台顶栏的报警铃下拉里，会显示「数据源：后端服务 / 本地模拟」，
答辩时可以当场说明当前是哪一种。

类型补充：`mock/types.ts` 的 `EventStatus` 增加了 `candidate` / `referred`，
`WorkOrderStatus` 增加了 `verifying`——这三个是后端状态机的状态，本地模拟用不到。

---

## 七、入口页的 5 屏长滚动

入口页（`index.html` → `PortalView.vue`）是一段**单页长滚动叙事**，共 5 屏：

| 屏 | 锚点 | 内容 |
|----|------|------|
| §01 主张 | `c1` | 整屏 Hero：实景图 + 「我们识别的不是烟头，是动作」+ INPUT/REVIEW/OUTPUT 三胶囊 |
| §02 断点 | `c2` | 对照两组：只看到一枚烟头能/不能说明什么 vs 还原一段连续动作能/不能说明什么 |
| §03 机制 | `c3` | 捕捉 → 串联 → 研判 → 调度 → 复盘，逐段给出产出物 |
| §04 分端 | `c4` | 三个端的职责与**真实页面跳转**卡片 |
| §05 边界 | `c5` | 不做的事 / 不公开的东西 / 数据是演示的 + 演示账号 + 收束 CTA |

技术取向：**不引任何动画库**。滚动驱动由 `PortalView.vue` 内部完成——
`scroll` 事件经 `requestAnimationFrame` 节流，映射到顶栏实体化（`barSolid`）、
顶部进度条（`progress`）、当前章节（顶栏高亮），并用 `data-reveal` 给未显影的
章节加 `.in` 类触发过渡。同时尊重 `prefers-reduced-motion`。

视觉令牌全部写在本组件内（`--ink / --ember / --cyan` 等），**不引用后台的 `--yz-*`**，
避免两套体系互相污染。

> 早前还有一套纸白「取证制图学」的九幕长卷（独立 `landing/` 工程，
> 托管在 `/story/index.html`）。按需求已整体移除，相关用例也从质检脚本中删掉了。

### 7.1 品牌标识与深色背景

长滚动页面是深色底，所以顶栏与页脚用 `logo-mark.png`（方形透明徽标）+ 白字
「烟踪智治」，**不能**直接把横版 logo 反白：那张图自带白底，
`filter: brightness(0) invert(1)` 会把白底一起反成实心白块。


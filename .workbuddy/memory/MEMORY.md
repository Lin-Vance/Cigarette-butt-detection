# 烟踪智治 · 项目长期记忆

## 项目基本信息

- 全称：烟踪智治 — 基于行为证据链的公共场所烟头乱扔智能识别与环卫调度决策系统
- 单位：信阳学院 计算机与人工智能学院｜PRD 申请人：黄忠楷｜指导老师：李进
- 周期：2026.05 — 2027.04；部署级别：校园试点（2-4 路摄像头）
- 工作区：`C:\Users\20262\Desktop\烟头行为监测`

## 已确立的技术决策

| 决策项 | 结论 |
|--------|------|
| 项目目标 | **答辩演示原型**，非真实校园试点 |
| 前端路线 | **Vue3 + Element Plus 工程化重写**（放弃"静态页 + 注入层"） |
| 数据来源 | **全模拟数据**，后端按业务逻辑生成，支持"一键演示一次违规" |
| 交付范围 | **18 页全做，不分阶段**；前端 + 后端全由我负责 |
| 部署 | 用户自行完成（交付需可本地启动）；根目录 `start-all.bat` 一键同起前后端 |
| 后端 | **唯一后端 = `backend/`（FastAPI，8000）**。`backend-java/`（8080）保留为备选实现但**前端已不引用** |
| Element Plus | 接受"用 EP 的行为、按现有页面调外观"，不要求像素级还原；图标改为**白名单按需注册**（20 个） |

**已确认事实**：AI 算法侧完全没实现（三段式状态机/ByteTrack/光流/抛物线拟合均无），仅有 `best.pt` + `data.yaml` → 后端必须内置**合规事件生成器**。数据集 `G:/科研数据集/datasets` 存在。

## 强制约定

- **架构降级原则**：InfluxDB / MinIO 集群 / Redis Streams / K8s+Helm / 微信小程序 均为过配；单机 PostgreSQL + 本地目录即可。
- **视觉底线**：`smoke-admin/` 18 页设计稿是**视觉规范来源**，不得退回 EP 默认外观。
- **定宽缩放保留**：1672×941 + fit-shell（后台）；非管理端三页不套 FitShell（要能手机看）。
- **「五页多端」MPA 结构**：五个独立 HTML，各自可单开、互相可跳。
  | 页面 | 文件 | 起始路由 |
  |---|---|---|
  | 入口页（5 屏长滚动） | `index.html` | `#/` → `PortalView` |
  | 登录/注册（Arc×Apple 风） | `auth.html` | `#/auth` → `AuthView` |
  | 市民端 | `citizen.html` | `#/citizen-login` → `#/citizen` |
  | 环卫端 | `worker.html` | `#/worker` → `WorkerAppView` |
  | 管理员端（含执法协同） | `admin.html` | `#/platform/overview` |
  换端入口现状（2026-09-28 已决策并落地）：**只在入口页 `index.html` 底部放 `.yz-ends` 固定条**
（挂在 `#app` 之外，所有宽度可见，≤640px 贴底铺满可横向滚动）；正式端页不暴露，改由顶栏 logo 回入口页。
`qa-ends.mjs` 已收紧断言：入口页 `ends>=1` 为硬断言、正式端页 `ends!==0` 即失败。
**历史文档里的 `.es-cross`（EndShell 顶栏 ≥900px 快捷组）确认不存在，不要再按它改代码或用例。**
- **入口页卡片必须是真实 `<a href="./worker.html">`**，不能用 `router-link`（用户原话："一直来回还是那张页面"）。
- **品牌标识唯一源**：`design-assets/2/smoke_control_brand_logo.png` → 派生 `logo-horizontal.png`（浅底）、`logo-mark.png`（深底）、`favicon.png`。脚本 `frontend/scripts/make-logo-mark.py`。
  ① 原 png 是**白底**，直接用会出白方块，必须做白→透明；② 横版 logo **不能**用 `filter: brightness(0) invert(1)` 反白（白底会变实心白块）。
- **交警端已并入管理端**为「执法协同」：`law-cases`(`LawCasesView`) + `law-trail`(`LawTrailView`)，状态在 `stores/law.ts`。这两页在 `allowedPageNames` 里对 admin/manager 显式授权并与后端 `apiPages` 求并集（后端 RBAC 矩阵尚未同步这两个页名）。
- **前端资源路径一律绝对 `/design-assets/...`**：`.vue` 里写 `./design-assets/...` 会被 Rollup 当模块解析，`vite build` 报 `Could not resolve`。故 **dist 不能 `file://` 双击**，必须本地静态服务（`start-frontend.bat` / `preview-build.bat`，文件名用 ASCII）。
- **演示数据量级**要与"2-4 路摄像头校园试点"匹配（设计稿的"在线设备 3,842 / 今日违规 1,286"会被质疑）。已在 `frontend/src/mock/config.ts` 做 `design` / `pilot` 两档。
- **开发期自动登录**：`#/platform/alerts?autologin=1`、`#/citizen?autologin=citizen` —— query 必须写在 `#` 内部。
- **PRD/FDD 不可照抄**：缺陷清单见 `docs/烟踪智治-文档缺陷与修订说明.md`（8 过配 + 21 缺陷 + 4 口径不一致，标原文行号）。**判断文档/代码问题前必须读原文并标行号**（曾凭印象误报一条，核实不成立）。

## 高频 bug 类（改代码前必看）

- **✅ 换端入口已修复并定稿**（2026-09-28）：`.yz-ends` 固定条**只放在入口页 `index.html`**（静态 HTML，非 Vue），
  配套 `public/end-switcher.css`（已从孤儿文件变为被引用）。正式端页不暴露。qa.mjs 的「底部端切换条」用例靠它通过。
- **✅ 后端已收敛为单后端**（2026-09-28）：`/api`、`/storage`、`/ws` 三条代理**统一 `127.0.0.1:8000`（FastAPI）**，
  `vite.config.ts` 另加 `strictPort: true`。Java 侧接口覆盖率低（14 个前端必需接口 11 个 404）且无 `/storage` 映射。
- **CORS 403 根因（保留备查）**：Spring 的 CORS 对不在白名单的 Origin **直接 403**，且 `allowCredentials(true)` 时无法用通配符绕过；
  **走 Vite 代理也躲不掉**（Vite 透传原始 `Origin`）。`backend-java` 已改 `allowedOriginPatterns("http://127.0.0.1:*",...)`（需重新构建才生效）。
- **⚠️ 后端改代码必须重启**：本机手动起的 uvicorn **没带 `--reload`**，改路由/权限/种子后不重启就是旧行为（曾误判"改了没生效"）。
- **⚠️ `deps.require_pages` 是 any-of 语义**（2026-09-28 修正）：命中任一页面权限即放行。
  改成 all-of 会让 `/workorders` 只对 admin 开放 → **环卫端工单池恒空**（D-18）。
- **⚠️ 种子数据的"待接单"必须用工单序号判定 + `created_at` 拉近**：`orders.is_overdue` 30 分钟 SLA 扫描
  会把陈旧 pending 直接升级为 timeout；用事件下标判定会因前 3 个事件是 pending_review/false_alarm 而变成死代码（D-19）。
- **⚠️ 图标是白名单注册**：`main.ts` 只注册 20 个图标（按名字符串经 `<component :is>` 解析）。
  新增 `icon: 'Xxx'` 必须同时补进 import 与 `ICONS`，否则**图标静默不渲染**。
- **未登录不要打业务接口**：入口页会调 `demo.init()`，靠 `hasAdminToken()` 挡住，否则匿名打 6 个 401（D-20）。
- **✅ 路由守卫越权兜底已修**（2026-09-28）：兜底改为 `PAGE_PATH_BY_NAME[auth.allowedPageNames[0]]`；
  兜底也兜不住时 `window.location.replace` 换回本角色自己的端，**绝不能回 `login`**（已登录时回 login 会被 public 分支
  立刻反弹到 `/platform/overview`，仍是死循环）。另加 `router.onError` 可见兜底，不再留白屏。
  旧的兜底是固定跳 `/platform/overview`，而 worker 的允许列表只有 `['dispatch-pool','dispatch-records']` → 无限重定向 → 整页白屏。
- **测试时别踩的三个坑**：① `/healthz` 在 dev 下被 SPA fallback 以 **200 + index.html** 应答（Vite 只代理 `/api`、`/storage`、`/ws`）→ 任何基于它的探活都必然误报"在线"（`probeBackend()` 已按 D-14 删除，探活改用业务接口）；② 登录页**默认身份是「市民」**（无密码框），测管理员/环卫必须带 `?role=admin|worker`，且提交按钮是 **`.au-submit`**（页头另有个文案同为"登录"的 `.au-text` 按钮）；③ **只改 hash 不算导航** → CDP 里 `Page.navigate` 到同文档不同 hash 不触发重载，Pinia 不重建、`restore()` 不执行，会造出"token 在却判未登录"的假象，验持久化必须 `Page.reload`。
- **CDP 探针两个必踩点**（写探针时照抄 `qa.mjs` 的 `goto`）：① 必须先 `spawn` Edge 并带 `--remote-debugging-port`，否则 `waitForTarget` 永远等不到；② Vite dev 下**首次加载某个端要现编译模块图**，等 1.5s 不够，统一给 3s；③ 登录成功后是**整页跳转**，在途 CDP 命令会报 `-32000 navigated or closed` 触发重试，重试时页面已是目标端 → 在页面脚本开头加"已经跳走了就直接返回成功"的短路，否则会二次提交。
- **旧路径残留**：路由从 `/overview` 挪到 `/platform/overview` 时残留 4 处（3 处在 `router/index.ts` redirect，1 处藏在 `LoginView.onSubmit()` 的 `query.redirect || '/overview'` 兜底）。这类字符串字面量 grep `to="..."` / `router.push(` 覆盖不到，**必须直接 grep 路径字符串本身**。症状：登录后跳回官网首页（命中 catch-all）。
- **改结构后必须同步改 QA 选择器**：市民端顶栏 nav 是 `.es-nav button`（非 `.desktop-sidebar nav button`）；环卫端列表是 `.table .tr`（非 `.card`）。用例失配会伪装成"页面崩了"。
- **QA 期望根节点签名要用挂载后不变的类名**：根节点 `onMounted` 会追加状态类（`.lp`→`.lp solid`），精确串会误判"未渲染"。统一用稳定内部类：入口页 `lp-glow`、登录页 `au-bloom`、后台 `class="ad-page"`。
- **长滚动页最后一屏要 `min-height: 100vh`**：否则 `scrollTo` 被 clamp，顶栏跳转差一截（实测差 146px）。
- **同轮内对同一文件连续 Edit**，Vite 可能拿到中间版本（报"未导出某函数"/页面空白）→ 改完共享模块**重启 dev server**。判断真空白：`scrollHeight` 是否只有一屏、`[data-chapter]` 是否为零个。
- **该工程可能被其他会话并行修改** → 每次开工前重新扫路由与文件列表，核对跳转链接。

## 交付物索引

| 路径 | 说明 |
|------|------|
| `docs/烟踪智治-缺陷修复与复核报告.md` | **2026-09-28 修复轮成果**：D-01～D-17 处置表 + 新发现 D-18～D-21 + 变更清单 + 回归证据 + 可落地性复核 + 残留项 R-1～R-7 |
| `docs/烟踪智治-网站缺陷检测报告.md` | **2026-09-28 软件测试检测报告**：17 项缺陷（P0×2/P1×3/P2×6/P3×6）+ 复现证据 + 修复建议 + 回归顺序 + 健康面基线 |
| `docs/烟踪智治-文档缺陷与修订说明.md` | **修复依据**：缺陷清单 + 修订方案 + 修订后技术基线 + 优先级 |
| `docs/原始文档/` | PRD v1.0、功能设计文档 v1.0 原件归档 |
| `start-all.bat`（根目录） | 一键同起后端 8000 + 前端 5180 并打开浏览器 |
| `frontend/` | Vue3 工程（Vite+TS+EP+ECharts+Pinia）：`index.html` / `auth.html` / `citizen` / `worker` / `admin.html`。后台 18 页 + 执法协同 2 页已完成，进度见 `frontend/README.md` |
| `backend/app/routers/activity.py` | 跨端活动摘要 `/admin/activity/summary`（顶栏「三端同步 N」），数据源复用 `audit_logs` |
| `shots/qa-20260928-verify/probe-fix.mjs` | 修复复核探针（8 项：登录连通/越权不白屏/错误文案/未知路由/换端条/窄屏兜底），可复跑 |
| `frontend/src/layouts/EndShell.vue` | 非管理端通用外壳（`--yz-topbar-*` + `--yz-canvas-bg`），入口/登录/市民/环卫共用 |
| `frontend/src/stores/law.ts` | 执法协同线索状态与留痕（两页共享） |
| `frontend/public/design-assets/{1..18}/` | 设计稿 86 张 PNG（17MB），按页号分目录 |
| `frontend/public/{logo-horizontal,logo-mark}.png`、`media/street-hero.png` | 全站品牌资产 / 入口页首屏图 |
| `frontend/scripts/` | `make-logo-mark.py`、`erase-baked-logo.py`、`shot.mjs`（CDP 截图：`--url/--w/--h/--ys auto/--js/--out/--probe`）、`qa.mjs`（44 条用例，`npm run qa`）、`qa-ends.mjs`（16 条，`npm run qa:ends`） |
| `smoke-admin/` | 18 页静态设计稿，**保留为视觉规范来源** |
| `best.pt` / `data.yaml` | YOLO 3 类（cigarette/hand/person）权重与数据集配置 |

**已删除**：`landing/`（米白「取证制图学」九幕长卷，66M）+ `public/story/` + `HomeView.vue` + `/landing` 路由（2026-09-27 晚，用户要求）。`street-hero.png` 与 `shot.mjs` 已迁入主工程。
2026-09-28 修复轮移出（**未直删**，在 `%TEMP%\yanzong-removed-20260928\`）：`frontend/vite.config.ts.timestamp-*.mjs` ×4 + 临时调试脚本 `debug-auth.mjs` + 验证构建产物 `dist-verify/`。
**教训**：工具脚本要放在不会被删的主工程里。
**环境变更**：演示库已重新种子化（`backend/data/yanzong.db`），原库备份在 `%TEMP%\yanzong-db-backup-20260928\yanzong.db`。

## 环境备忘（本机踩坑）

- **Bash 的 PATH 被 shim 破坏**（`ls`/`tail`/`dirname` not found）→ 每条命令先执行：
  `export PATH="/c/Users/20262/.workbuddy/binaries/node/versions/22.22.2-3:/usr/bin:/bin:/c/Windows/System32:/c/Windows"`
- **PowerShell 工具不回显 stdout**（exit 0 无输出）→ 用 Bash 或 Python。
- node：`C:\Users\20262\.workbuddy\binaries\node\versions\22.22.2-3\node.exe`（npm 10.9.7，npmmirror 源）。
- **npm install 卡在 esbuild postinstall**（`spawnSync node.exe EBUSY`）→ 用 `npm install --ignore-scripts`（二进制已就位，不影响 vite）。
- 前端 dev server 端口 **5180**；`/api`、`/storage`、`/ws` 代理到 `127.0.0.1:8000`。
- 本机 Edge：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`。**headless `--window-size` 有 500px 最小窗口限制** → 精确视口必须走 CDP（`shot.mjs`）。截图必加 `--disable-extensions`（否则插件悬浮按钮入镜）。
- **删除物移入备份目录而非直删**（本机无 git）：`%TEMP%\yanzong-removed-20260927\`。PowerShell 的 `Add-Type`/`Microsoft.VisualBasic` 被安全策略拦，用 `Move-Item`。
- `smoke-admin/README.md` 是 **UTF-16**，Read 报 binary，须 python `decode('utf-16')`。
- **CV 环境与 backend 环境分开**：`envs/default`（fastapi/sqlalchemy）**不要塞 torch**；YOLO 用 `...\python\envs\yolo\Scripts\python.exe`（3.13.14）。
- **PyTorch CUDA 走 SJTU 镜像**（`download.pytorch.org` 不通）：`mirror.sjtu.edu.cn/pytorch-wheels/cu128/` 实测 2.9–4.6MB/s（阿里云仅 0.8–1）。`torch-2.9.1+cu128` = 2.67GB，配 torchvision 0.24.1。写法：`pip install --find-links <目录> "torch==2.9.1+cu128" "torchvision==0.24.1+cu128" -i <TUNA>`（**加 `--no-index` 会装不上依赖**；显式 `+cu128` 避免装到 CPU 版）。
- **后台任务被 TaskStop 会连带杀掉 `nohup` 子进程**（曾导致 2.67GB 下载停在 92MB）→ 长下载与安装**放在同一后台任务内串行**，或用 `curl -C -`。
- 本机 **RTX 4070 Laptop（8GB）**，驱动 616.92 / CUDA UMD 13.4。`data.yaml` 的 `G:/` 在 bash 沙箱**不可见**（只挂 C:/D:），训练前确认 G: 盘已连接。
- **pip 索引别用清华 TUNA**（本沙箱下报 `from versions: none`，但 curl 访问它是 200 —— 判断源是否可用必须用 pip 实测）。可用：`mirrors.aliyun.com/pypi/simple`、`mirrors.ustc.edu.cn/pypi/simple`、`pypi.org/simple`。
- **市民端「上传即检测」要真跑，必须三件事**（2026-09-28 实测，缺一即静默回退假预检）：
  ① 后端跑在**装了 ultralytics 的环境**（`envs/default` 没有 → 503 `AI_RUNTIME_MISSING`；现已把后端 requirements 装进 `envs/yolo` 并用它跑 uvicorn）；
  ② **只跑一个后端实例**（多实例抢同一个 SQLite → `database is locked`）；
  ③ **启动必须预热**（`main.py` lifespan → `inference.warmup()`；否则首次请求额外付 `import ultralytics` 3.5s + 模型加载）。
  就绪标志：启动日志「AI 预检已预热：best.pt · device=0」或 `GET /api/v1/public/ai/status` → `loaded:true`。
- ⚠️ **不要用 curl / python-requests 测本地接口延迟**：本沙箱惩罚本地 HTTP 客户端（服务端 `timings.total_ms` 59ms，curl 客户端等 30–60s）。**要用浏览器内 fetch 测**（真值：端到端 225ms / infer 32ms）。
- ⚠️ `shot.mjs` 每次运行建一个 `edge-cdp-shot-<pid>` 临时 profile 且不清理，已累积 200+（每个约 300 文件）→ 应改为复用或运行后自删。另：bash `rm` 单轮删超 50 文件会被 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` 拦。

## 预留接口

- MCP 地图：页 10 `.map-art`、页 4 `.map-viewport/.map-image`、页 5 `.map-panel/.map-image`
- Agent 问答：AI 治理 13/14/15，建议 `POST /api/ai/agent/ask`
- 数据接口替换点：列表类 6/8/9/11/12/16/18，统计卡 2/3/5/7/15

## 协作偏好

- 用户喜欢**"慢慢来"的分轮迭代**：先给框架再逐页补细节，不要一次堆大量内容。每轮以用户验收为准再细调。
- **"继续"≠"扩大范围"**：说"继续"指继续原本那件事；范围扩张（如新增后端）必须先问一句。
- **用户找东西时，先给确切路径 + 可点开的地址**，不要继续汇报新进展。
- **要"能互相跳转"时必须是真实多页**（不同 `.html`），不能是站内 hash 路由。
- **改完页面按需截图自查**：顶栏 logo 变白块、登录页叠出两个 logo 两个问题都**只有看图才发现**。本会话具备读图能力。

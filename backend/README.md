# 烟踪智治 · 后端服务

> FastAPI 单体 · SQLAlchemy 2.x async · 6 个业务模块 · 2 个 WebSocket 频道
> 依据 `docs/烟踪智治-文档缺陷与修订说明.md`「三、修订后的技术基线（编码依据）」

---

## 零、先说清楚一件事

**AI 行为识别管道尚未实现**（三段式状态机 / ByteTrack / 光流法 / 抛物线拟合都没有）。
因此本服务内置**合规事件生成器**（`app/generator.py`）替代真实 AI 管道。

- 所有事件、指标、建议都由本服务按业务规则生成，**全部标注为演示数据**；
- 事件的**形态**是合规的：三段证据帧齐全且 `path` 非空、时间戳严格递增且带 `+08:00`、
  轨迹点 ≥ 5、采样率口径 100 fps——这些正是评审会核对的地方；
- **不伪造**：`video_clip_path` 为空串（真实视频片段属 M1 算法阶段），
  GPU / 推理耗时等指标显式带 `"demo": true`。

---

## 一、快速开始

```bash
cd backend
start.bat            # Windows：自动建 .venv → 装依赖 → 启动
                     # macOS / Linux / Git Bash：./start.sh
```

首次运行会自动建虚拟环境并安装依赖，然后启动到 `http://127.0.0.1:8000`。
接口文档：<http://127.0.0.1:8000/docs>

手动启动：

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**默认 SQLite**（`backend/data/yanzong.db`），零外部依赖即可启动。
切 PostgreSQL：复制 `.env.example` 为 `.env`，取消 `requirements.txt` 里 `asyncpg` 的注释，
把 `DATABASE_URL` 改成 `postgresql+asyncpg://user:pwd@127.0.0.1:5432/yanzong`。

---

## 二、演示账号

| 账号 | 口令 | 角色 | 可见页面 |
|------|------|------|----------|
| `admin` | `123456` | 超级管理员 | 全部 17 页 |
| `manager` | `123456` | 后勤管理员 | 10 页（无账号与平台配置） |
| `worker01` / `worker02` | `123456` | 环卫工人 | 仅 2 页（任务池、调度记录） |
| `aidev` | `123456` | AI 开发人员 | 5 页（总览、告警、模型、阈值、分析） |

市民端：任意 11 位手机号 + 验证码 `123456`。
**演示手机号 `13800000000`** —— 种子里已有的上报记录都挂在这个号下。

---

## 三、目录结构

```
backend/
├── start.bat / start.sh          # 一键启动
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                   # 应用入口：CORS、错误处理、静态挂载、路由注册
│   ├── config.py                 # 配置（DB / JWT / 存储目录 / CORS）
│   ├── db.py                     # async engine + session
│   ├── models.py                 # ORM：User/Camera/Event/EvidenceFrame/WorkOrder/
│   │                             #      CitizenReport/AnalysisTask/Suggestion/AuditLog
│   ├── schemas.py                # 请求体模型
│   ├── security.py               # PBKDF2 口令 + JWT + RBAC 页面矩阵
│   ├── deps.py                   # 依赖：当前用户 / 角色校验 / 市民身份
│   ├── errors.py                 # 统一错误码（MODULE_ERROR_TYPE）
│   ├── statemachine.py           # 事件/工单/上报/分析任务 四条状态机
│   ├── generator.py              # ★ 合规事件生成器
│   ├── rules.py                  # ★ 调度建议规则引擎 + 热力聚合
│   ├── stats.py                  # 统计聚合
│   ├── orders.py                 # 工单编号与创建
│   ├── services.py               # 序列化 / 审计 / 脱敏
│   ├── timeutil.py               # 东八区时间与 100fps 帧号口径
│   ├── ws.py                     # WebSocket 连接管理（2 频道）
│   ├── seed.py                   # 演示数据种子（幂等）
│   └── routers/                  # auth / camera / event / workorder / report /
│                                 # stats / decision / audit / ws
├── storage/evidence/             # 证据帧与闭环照片（替代 MinIO，经 /storage 暴露）
├── data/yanzong.db               # SQLite（首次启动自动创建）
└── tests/test_golden_path.py     # 端到端黄金路径验收（40 项）
```

---

## 四、接口一览（58 个）

| 模块 | 端点 |
|------|------|
| 认证 | `POST /auth/login`、`POST /auth/refresh`、`GET /auth/me`、`POST /auth/logout`、`POST /auth/citizen/login` |
| 账号 | `GET/POST /users`、`PATCH /users/{id}`、`POST /users/{id}/reset-password`、`GET /users/roles` |
| 摄像头 | `GET/POST /cameras`、`GET/PATCH /cameras/{camera_id}` |
| AI 控制 | `POST /ai/config`、`POST /ai/preprocess/toggle`、`GET /ai/metrics` |
| 事件 | `GET /events`、`GET /events/{event_id}`、`GET /events/heatmap`、`GET /events/summary`、`POST /events/{id}/review`、**`POST /events/simulate`** |
| 工单 | `GET /workorders`、`GET /workorders/stats`、`POST /workorders/{id}/accept｜start｜complete｜verify` |
| 市民上报 | `POST/GET /citizen/reports`、`GET /citizen/reports/{no}`、`POST /citizen/reports/{no}/supplement｜withdraw｜appeal` |
| 公开查询 | `GET /public/cases/{report_no}`（脱敏，无需登录） |
| 上报受理 | `GET /reports`、`POST /reports/{no}/analyze｜accept｜reject｜finish｜start` |
| 统计 | `GET /stats/overview｜trend｜hourly｜areas｜types｜health` |
| 决策 | `GET /suggestions`、`POST /suggestions/recompute`、`POST /suggestions/{id}/feedback`、`GET /heatmap` |
| 审计 | `GET /audit/logs`、`GET /audit/actions`（只读，无写入接口） |
| 运维 | `GET /`、`GET /healthz`、`POST /admin/reseed`、`GET /ws/stats` |
| WebSocket | `/ws/alerts`、`/ws/workorders` |

统一错误响应：

```json
{ "error_code": "AUTH_INVALID_CREDENTIALS", "message": "用户名或密码错误" }
```

---

## 五、四条状态机

任何流转都要过 `statemachine.py` 的白名单，前端不能直接改状态。非法流转返回 409。

| 对象 | 状态链 | 错误码前缀 |
|------|--------|-----------|
| 事件 | 候选 → 待复核 → 已确认 / 已驳回 → 已移送 → 已闭环 | `EVT_` |
| 工单 | 待派发 → 待接单 → 处理中 → 待验收 → 已闭环（异常：超时） | `WO_` |
| 市民上报 | 已提交 → 分析中 → 待复核 → 已受理 → 处理中 → 已完成 / 不予受理（可申诉） | `RPT_` |
| 分析任务 | 上传中 → 排队中 → 分析中 → 证据生成中 → 待复核 → 完成 / 失败 | `TASK_` |

**与 FDD §9.4 的一处有意偏差**：FDD 把「上传闭环照片」直接置为 `closed`；
《竞赛风险逐项解决规划》§5.1 的黄金路径要求「作业端上传 → **审核员确认闭环**」两步，
所以拆成 `POST /workorders/{id}/complete`（提交，转待验收）与
`POST /workorders/{id}/verify`（验收，转已闭环或打回处理中）。

---

## 六、合规事件生成器

`app/generator.py` 的时间口径与前端 `frontend/src/mock/engine.ts` 完全一致，
所以后端接管后页面上的数值不会跳变：

```
录制窗口 clip_start = 事件时刻 - 7400 ms
持烟帧 holding      = clip_start + 1000 ms   → F-0100
抛掷帧 throwing     = clip_start + 6200 ms   → F-0620
落地帧 landed       = clip_start + 7300 ms   → F-0730（= event_timestamp）
轨迹                12 点，从持烟到落地等间隔，x 线性右移 / y 抛物线加速
```

`validate_evidence_chain()` 会拦下任何不合规的事件（三帧缺失、`path` 为空、
时间戳未递增或缺时区、轨迹点不足），不写库。

**证据帧素材**：首次启动会把主站已归档的设计稿实景图复制进 `storage/evidence/_pool/`
（来源见 `POOL_SOURCES`），之后可脱离主站目录独立运行；找不到源图时退化为生成 SVG 帧，
**绝不会让 `path` 为空**。

---

## 七、调度建议规则引擎

`app/rules.py` 不写死文案，四条规则全部从库里的事件推导，阈值集中在文件顶部：

| 规则 | 阈值 | 输出 |
|------|------|------|
| 区域高频 → 增设设施 | 近 7 天日均超 30 天基线 30% | `add_facility` |
| 时段峰值 → 调整班次 | 某小时占全天 ≥ 25% | `adjust_schedule` |
| 同区域重复 → 复发预警 | 7 天内同一区域 ≥ 3 次 | `warning` |
| 环比下降 → 治理有效 | 近 7 天较前 7 天降 ≥ 20% | `treatment_effective` |

已有建议若被再次命中，**保留其处理状态与反馈说明**；不再命中的置为 `expired`，不物理删除。

---

## 八、端到端验收

```bash
# 先启动后端
python tests/test_golden_path.py
```

覆盖《竞赛风险逐项解决规划》§5.4 的验收门槛，共 **40 项**：

- 三角色登录后菜单与数据范围不同；权限不足返回 403
- 错误口令返回统一错误码；管理员令牌不能当市民令牌用
- WebSocket 收到 `event.created` 推送（含缩略图）
- 一键演示一次违规：三帧齐全且 `path` 非空、时间戳严格递增带 `+08:00`、轨迹点 ≥ 5
- **黄金路径**：市民提交 → 分析任务派生候选事件 → 受理并自动建单 → 作业端接单 →
  上传清理后照片 → 管理端验收 → 市民端收到完成通知与公开回复
- **一端操作、另一端可见**：作业端接单后市民端状态变「处理中」；验收后变「已完成」
- 重复提交被拦截（409）、已闭环工单不能再次接单（409）、验收权限仅管理端（403）
- 状态持久化（重复查询结果一致，不是每次重建）
- 关键操作全部写入审计日志；公开查询手机号脱敏

---

## 九、与前端对接

前端默认**不连**后端（走本地模拟数据），要连就开开关：

```bash
cd frontend
cp .env.example .env.local     # 里面已写 VITE_USE_API=1
npm run dev
```

前端 dev server 已代理：`/api`、`/storage`、`/ws` → `127.0.0.1:8000`。

打开开关后的差异：

| 项 | 本地模拟 | 连接后端 |
|----|----------|----------|
| 登录校验 | 前端模拟 | `POST /auth/login`，权限以后端下发为准 |
| 事件/工单/上报 | 每次刷新重建 | 落库，刷新不丢 |
| 证据图 | 设计稿素材 | 后端 `storage/evidence/` |
| 一键演示违规 | 仅前端新增 | 落库 + WebSocket 广播 + 自动建单 |
| 后端掉线 | — | 自动回退本地模拟，报警面板会提示「后端离线」 |

数据源提示在后台顶栏的报警铃下拉里（「数据源：后端服务 / 本地模拟」）。

---

## 十、尚未实现 / 边界

- **AI 识别管道**：生成器是替代品，不是识别能力。见 `docs/竞赛风险逐项解决规划.md` M1。
- **视频片段**：`video_clip_path` 为空串，不伪造。
- **GPU 指标**：`GET /ai/metrics` 里的显存、推理耗时、丢帧数均为演示数值，带 `"demo": true`。
- **实时流**：`/cameras/{id}/stream` 未实现（原设计要 Redis + Nginx + HLS，已按修订基线砍掉）。
- **账号口令**：PBKDF2-SHA256（12 万次迭代），标准库实现，不依赖 bcrypt 原生编译。
- **JWT 密钥**：演示固定值，正式部署必须通过 `JWT_SECRET` 更换。
- **SQLite 并发**：单进程 uvicorn + 试点量级足够；正式部署换 PostgreSQL。

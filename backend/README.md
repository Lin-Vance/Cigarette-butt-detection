# 烟踪智治后端

FastAPI 单体后端，MySQL 负责业务持久化，Redis 负责动态验证码、登录限频与 WebSocket 跨进程广播。

## 启动

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 使用 MySQL 管理员执行 scripts/mysql-bootstrap.sql，并把专用账号密码写入 .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/healthz`。开发环境接口文档：`/docs`。

## 配置

- `DATABASE_URL`：MySQL 8.0 异步连接，格式为 `mysql+aiomysql://...`。
- `REDIS_URL`：Redis 连接，默认 `redis://127.0.0.1:6379/0`。
- `JWT_SECRET`：生产环境必须是至少 32 位的随机值。
- `ENVIRONMENT=production`：关闭接口文档并启用生产密钥校验。
- `EXPOSE_DEMO_CODES=false`：生产环境必须关闭验证码回显。
- `AI_WARMUP=1`：启动后后台预热 `cigarette-detector.pt`。
- `AI_BASELINE_FRAMES=30`：每路摄像头冷启动时用于登记历史遗留目标的帧数。
- `AI_MAX_MISSED_FRAMES=8`：遮挡或漏检后允许续接原目标 ID 的帧数。
- `AI_PERSON_WINDOW_MS=3000`：新地面目标与附近人员做候选关联的前后时间窗。

## 固定摄像头地面目标跟踪

`POST /api/v1/ai/ground-tracking/frame` 接收连续图片帧（multipart）：

- `camera_id`：已登记摄像头编号；
- `file`：当前图片帧；
- `timestamp_ms`：采集时间戳；
- `ground_roi`：可选的二维坐标 JSON。未传时使用摄像头档案 ROI，再缺省时取画面下方 55%。

推理会把地面 ROI 划分成带重叠的 640px 切片，各自放大 2 倍后使用现有
`cigarette-detector.pt` 检测，避免整帧缩放丢失 10–20px 小目标。返回目标的
`target_id`、`first_seen_ms`、`last_confirmed_ms`、位置、新旧分类和人员候选关联。

跟踪状态保存在进程内，因此摄像头帧必须按时间顺序提交，部署时使用单个 Uvicorn worker。
服务重启后会按设计重新执行冷启动基线。人员关联只表示时间窗内距离最近，不构成责任认定。

## 安全边界

- 管理、环卫、市民令牌相互隔离，接口按角色授权。
- 验证码动态生成、限频、五分钟过期且只能使用一次。
- 图片按文件签名、解码结果、格式、像素数和容量校验。
- WebSocket 需要有效访问令牌。
- 验证码、登录失败计数和广播消息不再保存在 Python 单进程内存中。
- AI 输出是候选线索，正式处置必须经过人工复核。

## 验证

```powershell
python -m compileall -q app
python -m unittest discover -s tests -p "test_ground_tracking.py" -v
python tests\test_golden_path.py
python -m pip check
```

历史 SQLite 数据迁移：

```powershell
python scripts\migrate_sqlite_to_mysql.py --replace
```

Python 模块与测试文件使用 `snake_case.py`，配置模板使用 `.env.example`，Windows 脚本使用小写 kebab-case。

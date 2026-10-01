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
python tests\test_golden_path.py
python -m pip check
```

历史 SQLite 数据迁移：

```powershell
python scripts\migrate_sqlite_to_mysql.py --replace
```

Python 模块与测试文件使用 `snake_case.py`，配置模板使用 `.env.example`，Windows 脚本使用小写 kebab-case。

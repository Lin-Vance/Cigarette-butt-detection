# 烟踪智治后端

FastAPI 单体后端，负责认证与 RBAC、摄像机与事件、AI 图片检测、市民上报、工单闭环、统计报表、WebSocket 消息和证据文件服务。

## 启动

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/healthz`。开发环境接口文档：`/docs`。

## 配置

- `DATABASE_URL`：默认使用 `data/yanzong.db`。
- `JWT_SECRET`：生产环境必须是至少 32 位的随机值。
- `ENVIRONMENT=production`：关闭接口文档并启用生产密钥校验。
- `EXPOSE_DEMO_CODES=false`：生产环境必须关闭验证码回显。
- `AI_WARMUP=1`：启动后后台预热 `cigarette-detector.pt`。

## 安全边界

- 管理、环卫、市民令牌相互隔离，接口按角色授权。
- 验证码动态生成、限频、五分钟过期且只能使用一次。
- 图片按文件签名、解码结果、格式、像素数和容量校验。
- WebSocket 需要有效访问令牌。
- AI 输出是候选线索，正式处置必须经过人工复核。

## 验证

```powershell
python -m compileall -q app
python tests\test_golden_path.py
python -m pip check
```

Python 模块与测试文件使用 `snake_case.py`，配置模板使用 `.env.example`，Windows 脚本使用小写 kebab-case。

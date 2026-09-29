# 烟踪智治

面向公共区域的烟头目标检测、人工复核、环卫调度与处置闭环网站。当前代码以 FastAPI 为唯一后端，Vue 3 提供官网、统一登录、市民端、环卫端和管理端五个入口。

## 目录

- `frontend/`：Vue 3 + TypeScript + Vite 前端。
- `backend/`：FastAPI、SQLite、AI 图片检测与证据文件服务。
- `cigarette-detector.pt`：烟头目标检测模型。
- `start-all.bat`：Windows 一键启动脚本。

项目只保留网站运行、开发和部署所需文件；历史设计稿、测试截图、论文材料和旧版 Java 后端已移除。

## 本地启动

环境要求：Node.js 20.19+ 或 22.12+、Python 3.11+。

1. 安装后端依赖：

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. 安装前端依赖：

   ```powershell
   cd frontend
   npm ci
   ```

3. 在项目根目录运行 `start-all.bat`，或分别启动：

   ```powershell
   # backend/
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

   # frontend/
   npm run dev -- --port 5180
   ```

打开 `http://127.0.0.1:5180/`。本地演示账号为 `admin`、`worker01` 或 `13800000000`，演示密码均为 `123456`。动态验证码由“获取验证码”按钮生成；生产环境必须关闭验证码回显。

## 验证

```powershell
cd frontend
npm run typecheck
npm run build
npm audit

cd ..\backend
python -m compileall -q app
python tests\test_golden_path.py
```

浏览器全站回归：

```powershell
cd frontend
$env:BASE='http://127.0.0.1:5180/'
npm run qa
```

## 安全配置

- 生产环境设置 `ENVIRONMENT=production`，并通过 `JWT_SECRET` 提供至少 32 位随机密钥。
- 生产环境设置 `EXPOSE_DEMO_CODES=false` 并接入真实短信服务。
- 不要将 `.env`、日志、缓存、上传数据或依赖目录提交到版本库。
- AI 结果仅作为候选线索，不能直接作为行政处罚或身份认定依据。

更多接口和运行说明见 [backend/README.md](backend/README.md) 与 [frontend/README.md](frontend/README.md)。

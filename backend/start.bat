@echo off
REM 烟踪智治 · 后端一键启动（Windows）
REM 首次运行会自动建虚拟环境并装依赖；已存在则直接启动。
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建虚拟环境 .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo 创建失败：请确认已安装 Python 3.11+ 并加入 PATH。
    pause
    exit /b 1
  )
  echo [2/3] 安装依赖 ...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 依赖安装失败。
    pause
    exit /b 1
  )
)

echo [3/3] 启动服务 http://127.0.0.1:8000  （接口文档 /docs）
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
endlocal

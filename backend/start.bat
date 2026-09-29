@echo off
REM 烟踪智治 · 后端一键启动（Windows）
REM 优先复用本机已准备的 YOLO 环境；不存在时再创建项目内虚拟环境。
setlocal
cd /d "%~dp0"

set "YZ_PY=C:\Users\20262\.workbuddy\binaries\python\envs\yolo\Scripts\python.exe"
if exist "%YZ_PY%" goto start_service

set "YZ_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%YZ_PY%" (
  echo [1/3] 创建虚拟环境 .venv ...
  py -3.10 -m venv .venv
  if errorlevel 1 (
    echo 创建失败：请确认已安装 Python 3.11+ 并加入 PATH。
    pause
    exit /b 1
  )
  echo [2/3] 安装依赖 ...
  "%YZ_PY%" -m pip install --upgrade pip
  "%YZ_PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 依赖安装失败。
    pause
    exit /b 1
  )
)

:start_service
echo [3/3] 启动服务 http://127.0.0.1:8000  （接口文档 /docs）
"%YZ_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
endlocal

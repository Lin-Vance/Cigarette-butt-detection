#!/usr/bin/env bash
# 烟踪智治 · 后端一键启动（macOS / Linux / Git Bash）
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ] && [ ! -x ".venv/Scripts/python.exe" ]; then
  echo "[1/3] 创建虚拟环境 .venv ..."
  python -m venv .venv
  PY=".venv/bin/python"
  [ -x "$PY" ] || PY=".venv/Scripts/python.exe"
  echo "[2/3] 安装依赖 ..."
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
fi

PY=".venv/bin/python"
[ -x "$PY" ] || PY=".venv/Scripts/python.exe"

echo "[3/3] 启动服务 http://127.0.0.1:8000  （接口文档 /docs）"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

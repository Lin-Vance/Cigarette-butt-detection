@echo off
REM ============================================================
REM  yanzong-zhizhi backend launcher (reuse the prepared AI env)
REM  This env already has: fastapi / uvicorn / sqlalchemy /
REM  torch 2.9.1+cu128 (GPU) / ultralytics 8.4.159
REM  -> does NOT re-download the 2.7GB torch wheel.
REM
REM  Note: run ONE instance only. Two instances share the same
REM  SQLite file and will lock each other ("database is locked").
REM ============================================================
setlocal
cd /d "%~dp0"

set "YZ_PY=C:\Users\20262\.workbuddy\binaries\python\envs\yolo\Scripts\python.exe"

if not exist "%YZ_PY%" (
  echo [ERROR] AI env not found: %YZ_PY%
  echo         Use start.bat instead ^(it builds backend\.venv,
  echo         but must download torch ~2.7GB again^).
  pause
  exit /b 1
)

echo.
echo  Starting backend  http://127.0.0.1:8000    docs: /docs
echo  First start warms up best.pt (about 10-40s).
echo  Ready when you see: "AI ... best.pt ... device=0"
echo  Keep only ONE instance running.
echo.

"%YZ_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Backend stopped.
pause

@echo off
REM ============================================================
REM  YanZong ZhiZhi - start BOTH backend (8000) and frontend (5180)
REM  Double-click this file. Two console windows will open.
REM
REM  Window 1: FastAPI backend  -> http://127.0.0.1:8000/docs
REM  Window 2: Vite dev server  -> http://127.0.0.1:5180/index.html
REM
REM  Close either window to stop that service.
REM  Frontend alone also works: if the backend is down, the UI
REM  falls back to local mock data (topbar shows "后端离线").
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/2] Starting backend on http://127.0.0.1:8000 ...
start "yanzong-backend" /D "%~dp0backend" cmd /k start.bat

echo [2/2] Starting frontend on http://127.0.0.1:5180 ...
timeout /t 3 /nobreak >nul
start "yanzong-frontend" /D "%~dp0frontend" cmd /k start-frontend.bat

echo.
echo Both services are starting in separate windows.
echo Waiting for the backend to become healthy before opening the browser...
timeout /t 5 /nobreak >nul
start "" http://127.0.0.1:5180/index.html

echo Done. (Demo accounts: admin / 123456, worker01 / 123456, citizen 13800000000 / 123456)
endlocal

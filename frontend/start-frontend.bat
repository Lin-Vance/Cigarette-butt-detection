@echo off
REM YanZong ZhiZhi - start dev server (5 ends) and open the browser.
REM Double-click this file. Requires Node.js installed.
setlocal
cd /d "%~dp0"

if not exist "node_modules" (
  echo [1/2] Installing dependencies ...
  call npm install --ignore-scripts --no-audit --no-fund
  if errorlevel 1 (
    echo Install failed. Please check Node.js is installed.
    pause
    exit /b 1
  )
)

echo [2/2] Starting dev server at http://127.0.0.1:5180/index.html
start "" http://127.0.0.1:5180/index.html
call npm run dev
endlocal

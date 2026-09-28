@echo off
REM YanZong ZhiZhi - serve the production build (dist/) and open the browser.
REM Use this to show the 5 ends from the built files.
setlocal
cd /d "%~dp0"

if not exist "dist\index.html" (
  echo [1/2] dist not found, building ...
  call npm run build
  if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
  )
)

echo [2/2] Serving dist at http://127.0.0.1:4173/index.html
start "" http://127.0.0.1:4173/index.html
call npm run preview
endlocal

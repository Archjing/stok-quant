@echo off
chcp 65001 >nul
setlocal

cd /d %~dp0..
cd frontend

:: 只在 node_modules 不存在时安装依赖
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo Starting frontend on http://localhost:5174
echo.
call npm run dev

endlocal

@echo off
chcp 65001 >nul
title 前端服务 - localhost:5173

echo ============================================
echo   US Stock Quant - 前端启动
echo ============================================
echo.

cd /d %~dp0frontend

echo 启动中...
npm run dev

pause

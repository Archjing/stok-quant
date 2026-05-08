@echo off
chcp 65001 >nul
title 后端服务 - localhost:8777

echo ============================================
echo   US Stock Quant - 后端启动
echo ============================================
echo.

call conda activate stock
cd /d %~dp0

echo 启动中...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8777 --reload

pause

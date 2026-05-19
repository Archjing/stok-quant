@echo off
chcp 65001 >nul
title 后端服务 - localhost:8777

echo ============================================
echo   US Stock Quant - 后端启动
echo ============================================
echo.

cd /d %~dp0

echo 同步 uv 环境...
uv sync
if errorlevel 1 goto :end

echo 启动中...
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8777

:end
pause

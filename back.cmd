@echo off
chcp 65001 >nul
cd /d %~dp0
uv sync
if errorlevel 1 goto :end
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8777
:end
pause

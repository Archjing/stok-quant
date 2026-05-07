v@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0..
echo ============================================
echo  US Stock Quant System - Backend
echo ============================================
echo.

call conda activate stock 2>nul || echo [WARN] conda env not found

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting backend on http://localhost:8777
echo API docs: http://localhost:8777/docs
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8777 --reload

endlocal

@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0..
echo ============================================
echo  US Stock Quant System - Frontend
echo ============================================
echo.

cd frontend
echo Installing dependencies...
call npm install

echo.
echo Starting frontend on http://localhost:5173
echo.
npm run dev

endlocal

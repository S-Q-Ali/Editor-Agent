@echo off
echo ========================================
echo   Editor Agent - Development Mode
echo ========================================

cd /d "%~dp0\.."

echo Starting frontend dev server and Electron...
echo Frontend: http://localhost:5173
echo Backend: http://127.0.0.1:8000
echo.

call npm run electron:dev

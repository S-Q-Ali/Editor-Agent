@echo off
echo ========================================
echo   Editor Agent - Full Build Pipeline
echo ========================================

cd /d "%~dp0\.."

echo.
echo [1/4] Building Frontend...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Frontend build failed!
    pause
    exit /b 1
)
cd ..

echo.
echo [2/4] Bundling Python Backend...
call scripts\build-python.bat
if %errorlevel% neq 0 (
    echo ERROR: Python build failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Installing Electron dependencies...
call npm install
if %errorlevel% neq 0 (
    echo ERROR: npm install failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Building Electron App...
call npx electron-builder --win
if %errorlevel% neq 0 (
    echo ERROR: Electron build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD COMPLETE!
echo   Output: dist-electron\Editor Agent Setup *.exe
echo ========================================
pause

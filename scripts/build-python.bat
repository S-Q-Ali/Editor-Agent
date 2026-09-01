@echo off
echo ========================================
echo   Building Python Backend (PyInstaller)
echo ========================================

cd /d "%~dp0\.."

echo [1/2] Cleaning previous builds...
if exist "backend\dist" rmdir /s /q "backend\dist"
if exist "backend\build" rmdir /s /q "backend\build"

echo [2/2] Running PyInstaller...
pyinstaller scripts\build-python.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo SUCCESS: Backend built to backend\dist\main\
echo.
pause

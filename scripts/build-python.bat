@echo off
echo ========================================
echo   Building Python Backend (PyInstaller)
echo ========================================

cd /d "%~dp0\.."

echo Working directory: %cd%
echo.

echo [1/2] Cleaning previous builds...
if exist "backend\dist" rmdir /s /q "backend\dist"
if exist "backend\build" rmdir /s /q "backend\build"
if exist "dist\main" rmdir /s /q "dist\main"
if exist "build\build-python" rmdir /s /q "build\build-python"

echo [2/2] Running PyInstaller...
pyinstaller scripts\build-python.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo Copying to backend\dist\main\...
if not exist "backend\dist" mkdir "backend\dist"
xcopy /E /I /Y "dist\main" "backend\dist\main"
if %errorlevel% neq 0 (
    echo ERROR: Copy failed!
    pause
    exit /b 1
)

echo.
echo SUCCESS: Backend built to backend\dist\main\
echo.
pause

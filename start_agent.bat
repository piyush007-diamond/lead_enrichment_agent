@echo off
echo ===================================================
echo   BALAJI ENT VOICE AGENT - AUTO LAUNCHER
echo ===================================================
echo.
echo 1. Cleanup old processes...
taskkill /F /IM python.exe >nul 2>&1
echo Done.

echo 2. Check for Internet Connection...
ping -n 1 www.google.com >nul 2>&1
if errorlevel 1 (
    echo [WARNING] No Internet Connection detected!
    echo The Zrok tunnel and Vapi update will likely fail.
    echo Please fix your internet connections.
    echo.
    pause
)

echo 3. Starting System (Server + Tunnel + Vapi Update)...
echo.
python execution/launcher.py
pause

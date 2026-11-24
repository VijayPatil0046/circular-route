@echo off
echo ========================================================
echo Launching CircularRoute (Backend + Frontend)
echo ========================================================
curl.exe --silent --fail http://127.0.0.1:8000/health >nul 2>nul
if errorlevel 1 (
    start "CircularRoute Backend" cmd /k "%~dp0start_backend.bat"
    echo Waiting for backend health check at http://127.0.0.1:8000/health...
    for /L %%i in (1,1,90) do (
        curl.exe --silent --fail http://127.0.0.1:8000/health >nul 2>nul
        if not errorlevel 1 goto backend_ready
        timeout /t 1 /nobreak >nul
    )
    echo Backend did not become healthy within 90 seconds. Check the backend terminal.
    exit /b 1
)

:backend_ready
curl.exe --silent --fail http://127.0.0.1:5173/ >nul 2>nul
if errorlevel 1 start "CircularRoute Frontend" cmd /k "%~dp0start_frontend.bat"
echo Applications launched.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173

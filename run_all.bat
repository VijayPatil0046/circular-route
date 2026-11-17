@echo off
echo ========================================================
echo Launching CircularRoute (Backend + Frontend)
echo ========================================================
start "CircularRoute Backend" cmd /k "%~dp0start_backend.bat"
start "CircularRoute Frontend" cmd /k "%~dp0start_frontend.bat"
echo Applications launched.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173

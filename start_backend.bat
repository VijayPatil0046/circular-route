@echo off
echo Starting CircularRoute Backend Server...
cd /d "%~dp0"
set PYTHONPATH=backend
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

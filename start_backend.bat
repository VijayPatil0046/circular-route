@echo off
setlocal
echo Starting CircularRoute Backend Server...
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
    echo Backend virtual environment not found at backend\venv.
    echo Create it with: python -m venv venv
    echo Then install dependencies with: venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
call "venv\Scripts\activate.bat"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
endlocal

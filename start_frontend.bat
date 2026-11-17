@echo off
echo Starting CircularRoute Frontend Dev Server...
cd /d "%~dp0\frontend"
pnpm run dev --host
pause

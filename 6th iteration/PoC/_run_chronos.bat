@echo off
cd /d "%~dp0backend\chronos_service"
call .venv\Scripts\activate.bat
uvicorn app:app --host 127.0.0.1 --port 9001
pause

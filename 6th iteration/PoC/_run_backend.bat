@echo off
cd /d "%~dp0backend"
uvicorn main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
pause

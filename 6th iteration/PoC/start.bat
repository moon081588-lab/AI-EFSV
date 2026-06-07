@echo off
setlocal
set "D=%~dp0"
title AI-EFSV Launcher

echo.
echo =====================================================
echo  AI-EFSV PoC Launcher
echo =====================================================
echo.

REM --- .env setup ---
if not exist "%D%backend\.env" (
    if exist "%D%backend\.env.example" (
        copy "%D%backend\.env.example" "%D%backend\.env" >nul
        echo [INFO] .env created. Edit it if needed, then press any key.
        pause >nul
    )
)

REM --- npm install ---
if not exist "%D%frontend\node_modules" (
    echo [INFO] npm install ...
    pushd "%D%frontend"
    call npm install --silent
    popd
)

REM --- Ollama ---
curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo [1/5] Starting Ollama ...
    start "Ollama" cmd /c "ollama serve & pause"
    timeout /t 3 /nobreak >nul
) else (
    echo [1/5] Ollama already running.
)

REM --- Chronos ---
if exist "%D%backend\chronos_service\.venv\Scripts\activate.bat" (
    echo [2/5] Starting Chronos ...
    start "Chronos" "%D%_run_chronos.bat"
    timeout /t 5 /nobreak >nul
) else (
    echo [SKIP] Chronos .venv not found.
)

REM --- Backend ---
echo [3/5] Starting Backend ...
start "Backend API" "%D%_run_backend.bat"
timeout /t 6 /nobreak >nul

REM --- Frontend ---
echo [4/5] Starting Frontend ...
start "Frontend" "%D%_run_frontend.bat"
timeout /t 6 /nobreak >nul

REM --- ngrok ---
where ngrok >nul 2>&1
if not errorlevel 1 (
    echo [5/5] Starting ngrok ...
    start "ngrok" "%D%_run_ngrok.bat"
    timeout /t 5 /nobreak >nul
    set NGROK_URL=
    for /f "delims=" %%U in ('curl -s http://localhost:4040/api/tunnels 2^>nul ^| python -c "import sys,json; d=json.load(sys.stdin); [print(t[\"public_url\"]) for t in d.get(\"tunnels\",[]) if t[\"public_url\"].startswith(\"https\")]" 2^>nul') do set NGROK_URL=%%U
) else (
    echo [SKIP] ngrok not found.
)

echo.
echo =====================================================
echo  Ready
echo =====================================================
echo  Backend   : http://127.0.0.1:8000
echo  Frontend  : http://localhost:5173
if defined NGROK_URL echo  Public URL: %NGROK_URL%
echo =====================================================
echo.
start http://localhost:5173
echo Press any key to exit launcher (services keep running).
pause >nul
endlocal

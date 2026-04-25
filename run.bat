@echo off
REM Khoi dong RAG server (Windows)
REM   run.bat          = chi chay server
REM   run.bat ngrok    = chay server + ngrok

cd /d "%~dp0"

set PYTHON=venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo [ERROR] venv not found. Run: python -m venv venv
    pause
    exit /b 1
)

if not exist "data\sqlite\hr.db" (
    echo Seeding database...
    %PYTHON% -m app.db.seed
)

set PORT=8000

if "%~1"=="ngrok" goto START_NGROK
goto START_SERVER

:START_NGROK
echo Starting server on port %PORT%...
start /b %PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
timeout /t 3 /nobreak >nul
echo.
echo === QUAN TRONG ===
echo Copy URL ngrok vao local.properties cua Android app:
echo   RAG_BASE_URL=https://xxxx.ngrok-free.app
echo ==================
echo.
ngrok http %PORT%
goto END

:START_SERVER
echo Starting server on port %PORT%...
echo Truy cap: http://localhost:%PORT%/docs
echo.
%PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload
goto END

:END

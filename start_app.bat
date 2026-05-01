@echo off
title EmoTrace - Mental Health Monitor
color 0D

echo ============================================
echo   EmoTrace - Mental Health Monitor
echo ============================================
echo.

:: Check if venv exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo [1/3] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [1/3] No venv found, using system Python...
)

:: Install missing packages silently
echo [2/3] Checking dependencies...
venv\Scripts\pip.exe install streamlit requests pandas --quiet

:: Start FastAPI backend in a new window
echo [3/3] Starting FastAPI backend (backend)...
start "EmoTrace API Server" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for the API to start
echo.
echo Waiting for API server to start...
timeout /t 5 /nobreak > nul

:: Start Streamlit frontend
echo Starting Streamlit frontend...
echo.
echo ============================================
echo  App will open in your browser shortly...
echo  API Docs: http://127.0.0.1:8000/docs
echo  Streamlit: http://localhost:8501
echo ============================================
echo.
venv\Scripts\python.exe -m streamlit run "%~dp0frontend\app.py"

pause

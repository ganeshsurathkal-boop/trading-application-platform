@echo off
echo ========================================
echo   TICKR — Starting Backend (FastAPI)
echo ========================================
echo.

REM Check for embedded (portable) Python first, then fall back to system Python
set EMBED_PYTHON=%~dp0..\python-embed\python.exe
if exist "%EMBED_PYTHON%" (
    echo Using embedded Python: %EMBED_PYTHON%
    set PYTHON="%EMBED_PYTHON%"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        where py >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo ERROR: Python not found. No embedded package at %%EMBED_PYTHON%% and no system Python detected.
            pause
            exit /b 1
        )
        set PYTHON=py
    ) else (
        set PYTHON=python
    )
)

echo Python found: %PYTHON%
echo.

REM Create .env if missing
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please edit backend\.env with your credentials before running in production.
    echo.
)

REM Install dependencies
echo Installing Python dependencies...
%PYTHON% -m pip install -r requirements.txt -q

echo.
echo Starting FastAPI server on http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
%PYTHON% -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

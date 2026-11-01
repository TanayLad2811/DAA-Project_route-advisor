@echo off
title Emergency Evacuation Route Analyzer Launcher
echo ============================================================
echo   Emergency Evacuation Route Analyzer Launcher
echo ============================================================
echo.

set "ROOT_DIR=%~dp0"

echo [1/3] Starting Backend API (FastAPI + Uvicorn on http://localhost:8000)...
start "Evac-Analyzer Backend" cmd /k "cd /d "%ROOT_DIR%backend" && "%ROOT_DIR%backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000"

echo [2/3] Starting Frontend Dev Server (Vite on http://localhost:5173)...
start "Evac-Analyzer Frontend" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

echo.
echo [3/3] Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening browser at http://localhost:5173...
start http://localhost:5173

echo.
echo ============================================================
echo   Both servers have been launched in separate windows!
echo   - Backend:  http://localhost:8000  (Docs: /docs)
echo   - Frontend: http://localhost:5173
echo.
echo   To stop either server, close its corresponding window.
echo ============================================================
echo.
pause


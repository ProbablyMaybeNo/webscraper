@echo off
echo Starting Webscraper in DEV mode (backend + frontend)...
cd /d "%~dp0"
start "Webscraper API" cmd /k "py -3.13 -m uvicorn backend.main:app --host 0.0.0.0 --port 8091 --reload"
timeout /t 2 /nobreak >nul
start "Webscraper UI" cmd /k "cd frontend && npm run dev"
echo.
echo Backend:  http://localhost:8091
echo Frontend: http://localhost:5174
echo API docs: http://localhost:8091/docs

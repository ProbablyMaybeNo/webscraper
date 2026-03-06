@echo off
echo =====================================================
echo  Webscraper Dev Mode
echo  - Backend API:  http://localhost:8092
echo  - Frontend UI:  http://localhost:5174   <-- open this in your browser
echo  - API docs:     http://localhost:8092/docs
echo =====================================================
echo.
cd /d "%~dp0"
start "Webscraper API" cmd /k "py -3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8092 --reload"
timeout /t 2 /nobreak >nul
start "Webscraper UI" cmd /k "cd frontend && npm run dev"
timeout /t 3 /nobreak >nul
start http://localhost:5174

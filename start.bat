@echo off
echo Starting Webscraper backend on http://127.0.0.1:8092
echo Open http://localhost:8092 in your browser (or run start_dev.bat for hot-reload UI)
cd /d "%~dp0"
py -3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8092 --reload

@echo off
echo Starting Webscraper backend on port 8090...
cd /d "%~dp0"
py -3.13 -m uvicorn backend.main:app --host 0.0.0.0 --port 8090 --reload

@echo off
setlocal
cd /d "%~dp0"
set "PY=C:\Users\vegavjzhang\AppData\Local\Python\bin\python3.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m pip install -r requirements.txt --quiet
start "Benchmark Idea Radar" http://127.0.0.1:5000
"%PY%" -m radar.web.app

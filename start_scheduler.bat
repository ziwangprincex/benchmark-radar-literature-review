@echo off
setlocal
cd /d "%~dp0"
set "PY=C:\Users\vegavjzhang\AppData\Local\Python\bin\python3.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m radar.publish.scheduler --interval-hours 24

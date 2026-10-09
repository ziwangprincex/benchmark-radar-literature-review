@echo off
set "PY=C:\Users\vegavjzhang\AppData\Local\Python\bin\python3.exe"
"%PY%" "%~dp0..\..\..\offline_eval.py" combine --package-dir "%~dp0" --input-dir "%~dp0" --output "%~dp0completed_responses.jsonl"
pause

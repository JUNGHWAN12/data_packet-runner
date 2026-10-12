@echo off
REM Data Packet Runner - booth mode (fullscreen, hidden cursor, hold ESC 3 s to quit)
cd /d "%~dp0"
python main.py --booth
if errorlevel 1 pause

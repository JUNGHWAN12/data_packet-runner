@echo off
REM Data Packet Runner - booth mode (fullscreen, hidden cursor, hold ESC 3 s to quit)
REM If the game stops because of an error it is started again (up to 10 times).
REM Error details: logs\game.log
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py -3
set RESTARTS=0
:run
%PY% main.py --booth
if not errorlevel 1 goto end
set /a RESTARTS+=1
if %RESTARTS% geq 10 goto failed
echo The game stopped with an error. Restarting... (%RESTARTS%/10)
timeout /t 2 /nobreak >nul
goto run
:failed
echo The game stopped 10 times. Please check logs\game.log
pause
:end

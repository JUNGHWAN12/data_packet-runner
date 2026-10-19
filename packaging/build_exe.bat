@echo off
REM Build the Windows executable on a PC with Python 3.10+ (result: dist\PacketRunner\PacketRunner.exe)
cd /d "%~dp0\.."
python -m pip install -r requirements.txt pyinstaller==6.22.3
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm packaging\PacketRunner.spec
if errorlevel 1 goto fail
start "" /wait dist\PacketRunner\PacketRunner.exe --check
if errorlevel 1 goto fail
echo Done: dist\PacketRunner\PacketRunner.exe  (copy the whole PacketRunner folder)
pause
exit /b 0
:fail
echo Build failed. See the messages above.
pause
exit /b 1

@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 goto :error
py -m pip install pyinstaller
if errorlevel 1 goto :error
set "ICON_ARG="
if exist "app.ico" set "ICON_ARG=--icon=app.ico"
py -m PyInstaller --noconfirm --clean --onefile --windowed --name HelloTasks %ICON_ARG% main.py
if errorlevel 1 goto :error
echo.
echo Build complete: dist\HelloTasks.exe
pause
exit /b 0
:error
echo Build failed. Check the errors above.
pause
exit /b 1

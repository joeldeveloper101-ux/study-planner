@echo off
REM ------------------------------------------------------------
REM  Study Planner - one-click build
REM  1) Installs dependencies  2) Builds the app with PyInstaller
REM  3) Compiles the installer with Inno Setup (if found)
REM ------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo.
echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt || goto :error

echo.
echo [2/3] Building app with PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --clean --noconsole ^
    --name StudyPlanner ^
    --icon app.ico ^
    --add-data "app.ico;." ^
    main.py || goto :error

echo.
echo [3/3] Compiling installer with Inno Setup...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo Inno Setup not found. Open StudyPlanner.iss in the Inno Setup Compiler and press Ctrl+F9.
    goto :done
)
"%ISCC%" StudyPlanner.iss || goto :error

:done
echo.
echo Done. Installer is in the "installer" folder.
pause
exit /b 0

:error
echo.
echo Build failed. See the messages above.
pause
exit /b 1

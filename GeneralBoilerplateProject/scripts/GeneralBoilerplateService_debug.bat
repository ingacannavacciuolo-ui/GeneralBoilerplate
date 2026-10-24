@echo off
TITLE Build DEBUG - GeneralBoilerplateService
cd /d "%~dp0"
cd ..
set "ROOT_DIR=%CD%"

echo ============================================================
echo   BUILD DEBUG - GeneralBoilerplateService
echo   Root Progetto: %ROOT_DIR%
echo ============================================================
echo.

echo [1/4] Arresto processi GeneralBoilerplateService in esecuzione...
taskkill /F /IM GeneralBoilerplateService.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/4] Pulizia cartella di destinazione...
if exist "%ROOT_DIR%\compiling\dist\GeneralBoilerplateService" (
    rd /s /q "%ROOT_DIR%\compiling\dist\GeneralBoilerplateService" >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [3/4] Compilazione PyInstaller in modalita Console (DEBUG)...
"%ROOT_DIR%\venv\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --console ^
    --name "GeneralBoilerplateService" ^
    --distpath "%ROOT_DIR%\compiling\dist" ^
    --workpath "%ROOT_DIR%\compiling\build" ^
    --specpath "%ROOT_DIR%\compiling\specs" ^
    --clean ^    
    --hidden-import "socketio" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --add-data "%ROOT_DIR%\library;library" ^
    GeneralBoilerplateService.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Compilazione fallita.
    pause
    exit /b %ERRORLEVEL%
)

echo [4/4] Creazione cartella log e copia GeneralBoilerplateconfig.ini...
if not exist "%ROOT_DIR%\compiling\dist\log" mkdir "%ROOT_DIR%\compiling\dist\log"

:: Copia GeneralBoilerplateconfig.ini esclusivamente nella root di dist (sopra GeneralBoilerplateService)
if exist "%ROOT_DIR%\GeneralBoilerplateconfig.ini" (
    copy /Y "%ROOT_DIR%\GeneralBoilerplateconfig.ini" "%ROOT_DIR%\compiling\dist\" >nul
)

cd /d "%ROOT_DIR%"

echo.
echo ============================================================
echo   BUILD DEBUG COMPLETATA CON SUCCESSO!
echo   Eseguibile generato in: compiling\dist\GeneralBoilerplateService\
echo ============================================================
echo.
pause
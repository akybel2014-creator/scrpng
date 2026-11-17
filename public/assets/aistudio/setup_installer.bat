@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

title One-Click Setup — CasaLavoroPRO & XPart
cd /d "%~dp0"

echo ============================================================================
echo    ONE-CLICK SETUP — CasaLavoroPRO & XPart (CasaLavoroOutreach.exe)
echo ============================================================================
echo.

:: 1. Individua CasaLavoroOutreach.exe nella cartella corrente o in dist\
set "EXE_SRC="
if exist "CasaLavoroOutreach.exe" (
    set "EXE_SRC=%~dp0CasaLavoroOutreach.exe"
) else if exist "dist\CasaLavoroOutreach.exe" (
    set "EXE_SRC=%~dp0dist\CasaLavoroOutreach.exe"
)

if "%EXE_SRC%"=="" (
    echo [ERRORE] File "CasaLavoroOutreach.exe" non trovato nella cartella corrente!
    echo Assicurati di aver compilato l'eseguibile (es. tramite install_and_build.bat)
    echo oppure posiziona setup_installer.bat nella stessa cartella dell'exe.
    echo.
    pause
    exit /b 1
)

:: 2. Cartella dedicata su PC (%LOCALAPPDATA%\CasaLavoroPRO evita blocchi permessi di scrittura su .env e CSV)
set "TARGET_DIR=%LOCALAPPDATA%\CasaLavoroPRO"
echo [*] Preparazione cartella dedicata: "%TARGET_DIR%"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

:: 3. Copia eseguibile principale
echo [*] Copia di CasaLavoroOutreach.exe...
copy /Y "%EXE_SRC%" "%TARGET_DIR%\CasaLavoroOutreach.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Impossibile copiare CasaLavoroOutreach.exe.
    echo Chiudi eventuali istanze aperte dell'applicazione e riprova.
    echo.
    pause
    exit /b 1
)

:: 4. Copia file di configurazione .env (o .env.example come fallback)
if exist ".env" (
    echo [*] Copia configurazione .env...
    copy /Y ".env" "%TARGET_DIR%\.env" >nul
) else if exist ".env.example" (
    if not exist "%TARGET_DIR%\.env" (
        echo [*] Creazione .env da .env.example...
        copy /Y ".env.example" "%TARGET_DIR%\.env" >nul
    )
)

:: Copia eventuale cartella assets e CSV iniziali (senza sovrascrivere CSV gia' esistenti)
if exist "assets" (
    echo [*] Copia cartella assets...
    xcopy /E /I /Y "assets" "%TARGET_DIR%\assets" >nul
)
for %%F in (artigiani_estratti.csv registro_contattati.csv xpart_ricambi_estratti.csv) do (
    if not exist "%TARGET_DIR%\%%F" (
        if exist "%%F" copy /Y "%%F" "%TARGET_DIR%\%%F" >nul
    )
)

:: 5. Creazione automatica del collegamento sul Desktop ("CasaLavoroPRO & XPart")
echo [*] Creazione collegamento sul Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$lnkPath = Join-Path $desktop 'CasaLavoroPRO & XPart.lnk'; " ^
  "$sc = $ws.CreateShortcut($lnkPath); " ^
  "$sc.TargetPath = '%TARGET_DIR%\CasaLavoroOutreach.exe'; " ^
  "$sc.WorkingDirectory = '%TARGET_DIR%'; " ^
  "$sc.Description = 'CasaLavoroPRO & XPart'; " ^
  "$customIco = '%TARGET_DIR%\assets\icon.ico'; " ^
  "if (Test-Path $customIco) { $sc.IconLocation = $customIco } else { $sc.IconLocation = '%TARGET_DIR%\CasaLavoroOutreach.exe,0' }; " ^
  "$sc.Save();"

if %ERRORLEVEL% NEQ 0 (
    echo [AVVISO] Copia eseguibile riuscita, ma creazione collegamento Desktop non completata.
)

:: 6. Messaggio finale di successo
echo.
echo ============================================================================
echo   Installazione completata con successo! Ora puoi aprire l'app dal Desktop
echo ============================================================================
echo.
echo   Percorso app: %TARGET_DIR%\CasaLavoroOutreach.exe
echo   Collegamento: Desktop -> "CasaLavoroPRO & XPart"
echo.
pause

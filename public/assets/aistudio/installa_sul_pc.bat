@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

title Installazione CasaLavoroPRO & XPart su Windows
cd /d "%~dp0"

echo ============================================================================
echo    INSTALLAZIONE GUIDATA SU PC WINDOWS — CasaLavoroPRO & XPart Suite
echo ============================================================================
echo.

:: 1. Individua l'eseguibile CasaLavoroOutreach.exe
set "EXE_SRC="
if exist "CasaLavoroOutreach.exe" (
    set "EXE_SRC=%~dp0CasaLavoroOutreach.exe"
) else if exist "dist\CasaLavoroOutreach.exe" (
    set "EXE_SRC=%~dp0dist\CasaLavoroOutreach.exe"
)

if "%EXE_SRC%"=="" (
    echo [!] CasaLavoroOutreach.exe non trovato in questa cartella.
    if exist "install_and_build.bat" (
        echo [*] Avvio compilazione automatica tramite install_and_build.bat...
        echo.
        call "install_and_build.bat"
        if exist "CasaLavoroOutreach.exe" (
            set "EXE_SRC=%~dp0CasaLavoroOutreach.exe"
        ) else if exist "dist\CasaLavoroOutreach.exe" (
            set "EXE_SRC=%~dp0dist\CasaLavoroOutreach.exe"
        )
    )
)

if "%EXE_SRC%"=="" (
    echo.
    echo [ERRORE] Impossibile trovare o compilare CasaLavoroOutreach.exe.
    echo Assicurati di avere install_and_build.bat o CasaLavoroOutreach.exe in questa cartella.
    echo.
    pause
    exit /b 1
)

:: 2. Cartella di installazione locale dell'utente (nessun privilegio Admin richiesto)
set "INSTALL_DIR=%LOCALAPPDATA%\CasaLavoroOutreach"
echo [*] Cartella di installazione: "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Copia eseguibile principale
echo [*] Copia di CasaLavoroOutreach.exe...
copy /Y "%EXE_SRC%" "%INSTALL_DIR%\CasaLavoroOutreach.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Impossibile copiare l'eseguibile. Chiudi l'app se e' aperta e riprova.
    pause
    exit /b 1
)

:: 4. Configurazione .env e cartella assets (preserva impostazioni gia' esistenti)
if not exist "%INSTALL_DIR%\.env" (
    if exist ".env" (
        copy /Y ".env" "%INSTALL_DIR%\.env" >nul
    ) else if exist ".env.example" (
        copy /Y ".env.example" "%INSTALL_DIR%\.env" >nul
    )
)

if exist "assets" (
    echo [*] Copia cartella assets (loghi/immagini)...
    xcopy /E /I /Y "assets" "%INSTALL_DIR%\assets" >nul
)

:: 5. Copia archivi CSV iniziali solo se non gia' presenti sul PC (non sovrascrive i dati)
for %%F in (artigiani_estratti.csv registro_contattati.csv xpart_ricambi_estratti.csv) do (
    if not exist "%INSTALL_DIR%\%%F" (
        if exist "%%F" (
            copy /Y "%%F" "%INSTALL_DIR%\%%F" >nul
        )
    )
)

:: 6. Crea collegamenti su Desktop e Menu Start tramite PowerShell
echo [*] Creazione collegamenti su Desktop e Menu Start...
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desk = [Environment]::GetFolderPath('Desktop'); " ^
  "$sc1 = $ws.CreateShortcut((Join-Path $desk 'CasaLavoroPRO & XPart.lnk')); " ^
  "$sc1.TargetPath = '%INSTALL_DIR%\CasaLavoroOutreach.exe'; " ^
  "$sc1.WorkingDirectory = '%INSTALL_DIR%'; " ^
  "$sc1.Description = 'CasaLavoroPRO & XPart — Lead Generation & Outreach Suite'; " ^
  "$sc1.Save(); " ^
  "$sc2 = $ws.CreateShortcut('%START_MENU_DIR%\CasaLavoroPRO & XPart.lnk'); " ^
  "$sc2.TargetPath = '%INSTALL_DIR%\CasaLavoroOutreach.exe'; " ^
  "$sc2.WorkingDirectory = '%INSTALL_DIR%'; " ^
  "$sc2.Description = 'CasaLavoroPRO & XPart — Lead Generation & Outreach Suite'; " ^
  "$sc2.Save();"

:: 7. Crea script di disinstallazione nella cartella del programma
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo echo Disinstallazione di CasaLavoroPRO ^& XPart...
    echo del /f /q "%%USERPROFILE%%\Desktop\CasaLavoroPRO ^& XPart.lnk" 2^>nul
    echo del /f /q "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\CasaLavoroPRO ^& XPart.lnk" 2^>nul
    echo echo Collegamenti rimossi. I tuoi file CSV in "%INSTALL_DIR%" sono stati conservati per sicurezza.
    echo pause
) > "%INSTALL_DIR%\disinstalla.bat"

echo.
echo ============================================================================
echo   [OK] INSTALLAZIONE COMPLETATA CON SUCCESSO!
echo.
echo   Programma installato in: %INSTALL_DIR%
echo   Collegamento creato sul Desktop: "CasaLavoroPRO & XPart"
echo   Collegamento creato nel Menu Start di Windows.
echo ============================================================================
echo.

set /p RUN_NOW="Vuoi avviare subito CasaLavoroPRO & XPart? (S/N) [S]: "
if /I "%RUN_NOW%"=="" set "RUN_NOW=S"
if /I "%RUN_NOW%"=="S" (
    start "" "%INSTALL_DIR%\CasaLavoroOutreach.exe"
)

exit /b 0

@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

title CasaLavoroPRO & XPart — Installazione e Compilazione EXE
cd /d "%~dp0"

echo ============================================================================
echo    CASALAVOROPRO & XPART — INSTALLAZIONE DIPENDENZE E BUILD STANDALONE
echo ============================================================================
echo.

:: 1. Verifica presenza di Python sul PC
set "PYTHON_CMD="
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERRORE] Python non rilevato su questo PC!
    echo.
    echo Scarica e installa Python 3.10+ da:
    echo   https://www.python.org/downloads/
    echo IMPORTANTE: Durante l'installazione spunta "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo [OK] Rilevato: %PY_VER% (comando: %PYTHON_CMD%)
echo.

:: 2. Aggiornamento pip e installazione automatica dipendenze
echo [*] Aggiornamento di pip in corso...
%PYTHON_CMD% -m pip install --upgrade pip
echo.

if exist "requirements.txt" (
    echo [*] Installazione dipendenze da requirements.txt...
    %PYTHON_CMD% -m pip install -r requirements.txt
) else (
    echo [*] requirements.txt non trovato, installazione diretta pacchetti...
    %PYTHON_CMD% -m pip install selenium pywebview customtkinter supabase postgrest phonenumbers beautifulsoup4 requests urllib3 python-dotenv rich pyinstaller
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Installazione delle dipendenze non riuscita.
    echo Verifica la connessione internet o i permessi e riprova.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Tutte le dipendenze sono installate correttamente.
echo.

:: 3. Compilazione pulita con PyInstaller usando CasaLavoroOutreach.spec
if not exist "CasaLavoroOutreach.spec" (
    echo [ERRORE] File CasaLavoroOutreach.spec non trovato nella cartella del progetto!
    echo Assicurati di salvare CasaLavoroOutreach.spec insieme a main.py.
    echo.
    pause
    exit /b 1
)

echo [*] Avvio compilazione PyInstaller (--clean --noconfirm)...
%PYTHON_CMD% -m PyInstaller CasaLavoroOutreach.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Si e' verificato un problema durante la compilazione con PyInstaller.
    echo.
    pause
    exit /b 1
)

:: 4. Copia dell'eseguibile finale nella cartella principale
if exist "dist\CasaLavoroOutreach.exe" (
    echo.
    echo [*] Copia di CasaLavoroOutreach.exe nella cartella principale...
    copy /Y "dist\CasaLavoroOutreach.exe" "CasaLavoroOutreach.exe" >nul
    if !ERRORLEVEL! EQU 0 (
        echo.
        echo ============================================================================
        echo   [OK] COMPILAZIONE COMPLETATA CON SUCCESSO!
        echo.
        echo   Eseguibile standalone pronto:
        echo     %~dp0CasaLavoroOutreach.exe
        echo.
        echo   Nota: copia eventuali file .env nella stessa cartella dell'eseguibile.
        echo ============================================================================
    ) else (
        echo [AVVISO] Compilato in dist\CasaLavoroOutreach.exe, ma copia nella root non riuscita.
    )
) else (
    echo.
    echo [ERRORE] dist\CasaLavoroOutreach.exe non trovato al termine della compilazione.
    pause
    exit /b 1
)

echo.
pause

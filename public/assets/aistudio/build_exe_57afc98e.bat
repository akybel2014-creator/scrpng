@echo off
chcp 65001 >nul
echo =====================================================================
echo    COMPILAZIONE ESEGUIBILE WINDOWS: CasaLavoroOutreach.exe
echo =====================================================================
echo.

cd /d "%~dp0"

echo [*] Verifica ambiente Python e PyInstaller...
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installazione PyInstaller in corso...
    python -m pip install pyinstaller
)

echo.
echo [*] Avvio compilazione PyInstaller (--onefile)...
pyinstaller --noconfirm --clean --onefile --windowed ^
    --name "CasaLavoroOutreach" ^
    --collect-all selenium ^
    --collect-all pywebview ^
    --collect-all phonenumbers ^
    --collect-all customtkinter ^
    --collect-all supabase ^
    --collect-all postgrest ^
    --hidden-import "clr_loader" ^
    --hidden-import "pythonnet" ^
    --hidden-import "webview.platforms.winforms" ^
    --hidden-import "webview.platforms.edgechromium" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "geo_data" ^
    --hidden-import "stealth_engine" ^
    --hidden-import "supabase_client" ^
    --hidden-import "xpart_scraper" ^
    --hidden-import "bs4" ^
    --hidden-import "dotenv" ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =====================================================================
    echo  [OK] COMPILAZIONE COMPLETATA CON SUCCESSO!
    echo  [->] Eseguibile standalone: dist\CasaLavoroOutreach.exe
    echo =====================================================================
    echo.
    if exist "dist\CasaLavoroOutreach.exe" (
        echo [*] Copia di CasaLavoroOutreach.exe nella cartella dello script...
        copy /Y "dist\CasaLavoroOutreach.exe" "CasaLavoroOutreach.exe"
        echo [OK] Pronto all'uso: .\CasaLavoroOutreach.exe
    )
) else (
    echo.
    echo [!] Si e' verificato un errore durante la compilazione con PyInstaller.
)

echo.
pause

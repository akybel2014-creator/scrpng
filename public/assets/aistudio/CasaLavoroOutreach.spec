# -*- mode: python ; coding: utf-8 -*-
"""
Specifica PyInstaller (--onefile --windowed) per CasaLavoroOutreach.exe
Entry point: main.py (PyWebView EdgeChromium + fallback CustomTkinter/Tkinter)
"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    # Moduli interni dell'applicazione (importati anche dinamicamente da main.py)
    "app_gui",
    "app_tkinter",
    "config",
    "geo_data",
    "scraper",
    "deep_scraper",
    "normalizer",
    "outreach",
    "stealth_engine",
    "supabase_client",
    "xpart_scraper",

    # PyWebView + EdgeChromium / WinForms (.NET / pythonnet)
    "webview",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr_loader",
    "pythonnet",
    "bottle",
    "proxy_tools",

    # CustomTkinter & Tkinter
    "customtkinter",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.filedialog",

    # Selenium WebDriver
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.chrome.service",
    "selenium.webdriver.common.by",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",

    # Supabase & PostgREST
    "supabase",
    "postgrest",
    "gotrue",
    "realtime",
    "storage3",
    "supafunc",
    "httpx",
    "httpcore",
    "h2",
    "certifi",

    # Scraping, normalizzazione, SMTP & ambiente
    "bs4",
    "soupsieve",
    "requests",
    "urllib3",
    "phonenumbers",
    "dotenv",
    "rich",
    "smtplib",
    "email.mime.text",
    "email.mime.multipart",
    "mimetypes",
    "base64",
]

# Raccolta completa di dati, binari (es. WebView2Loader.dll, temi CustomTkinter) e submoduli
for pkg in (
    "selenium",
    "webview",
    "clr_loader",
    "pythonnet",
    "customtkinter",
    "phonenumbers",
    "supabase",
    "postgrest",
    "bs4",
):
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

# Rimuove eventuali duplicati mantenendo l'ordine
hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CasaLavoroOutreach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

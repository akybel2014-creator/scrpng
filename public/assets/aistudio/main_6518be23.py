#!/usr/bin/env python3
"""
ENTRY POINT UNIFICATO PER L'ESEGUIBILE WINDOWS (CasaLavoroOutreach.exe)
=====================================================================
Avvia l'interfaccia grafica principale (PyWebView moderna).
In caso di assenza dei componenti WebView2 o errore di runtime,
effettua il fallback automatico e trasparente su Tkinter nativo.
"""

import sys
import os

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def launch():
    try:
        # Prova prima con l'interfaccia PyWebView
        from app_gui import run_pywebview_gui
        run_pywebview_gui()
    except Exception as e:
        print(f"[!] PyWebView non disponibile o errore runtime: {e}")
        print("[*] Avvio interfaccia nativa Tkinter di fallback...")
        try:
            from app_tkinter import main as run_tkinter_gui
            run_tkinter_gui()
        except Exception as e_tk:
            print(f"[!] Errore critico avvio interfaccia grafica: {e_tk}")
            input("Premi INVIO per uscire...")

if __name__ == "__main__":
    launch()

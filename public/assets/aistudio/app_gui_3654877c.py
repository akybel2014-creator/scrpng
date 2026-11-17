#!/usr/bin/env python3
"""
APPLICAZIONE DESKTOP WINDOWS — CASALAVOROPRO & XPART SUITE
==========================================================
Interfaccia grafica (GUI) standalone avanzata:
1. Configurazione Dati Utente Fissi: bellosi2022@gmail.com & 3423255008
2. Integrazione Browser Google Chrome per Email: apre direttamente Chrome con la bozza
   precompilata (Gmail) pronta per l'aggiunta manuale di logo e foto prima dell'invio.
3. Sistema Anti-Doppio Invio (Spunta di Controllo): colonna con spunta/flag visivo
   automatico o manuale e blocco preventivo contro invii duplicati.
4. CasaLavoroPRO: Ricerca artigiani e creazione bozze ('draft_scraping') su Supabase con recensioni.
5. XPart Ricambi Auto: Scraping codici OEM, cross-reference aftermarket e compatibilità veicoli.
6. Motore Stealth: Rate limiting con jitter umano e User-Agent rotanti anti-blocco.
"""

import os
import re
import sys
import json
import time
import queue
import base64
import smtplib
import mimetypes
import threading
import subprocess
import webbrowser
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import moduli interni del sistema
import config as app_config
from config import (
    BASE_DIR,
    BUNDLE_DIR,
    FILE_ESTRATTI,
    FILE_REGISTRO,
    FILE_XPART_CSV,
    CATEGORIE_RAGGRUPPATE,
    DEFAULT_CATEGORIE,
    DEFAULT_CITTA,
    DEFAULT_LIMIT_PER_SEARCH,
    PLATFORM_NAME,
    PLATFORM_URL,
    SENDER_NAME,
    SENDER_PHONE,
    SENDER_EMAIL,
    LOGO_URL,
    FOTO_ALLEGATE,
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_TABLE_BOZZE,
    SUPABASE_TABLE_XPART,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    WHATSAPP_MESSAGE_TEMPLATE,
    EMAIL_SUBJECT_TEMPLATE,
    EMAIL_TEXT_TEMPLATE
)
from geo_data import (
    ITALIA_GEO_DATABASE,
    get_all_regions,
    resolve_search_locations
)
from normalizer import clean_text
from scraper import setup_selenium_driver, scrape_google_maps_multi_zone
from xpart_scraper import (
    CATEGORIE_RICAMBI_XPART,
    MARCHE_AUTO_XPART,
    scrape_xpart_oem_catalog,
    FILE_XPART_CSV
)
from outreach import (
    load_csv_data,
    load_contacted_registry,
    open_whatsapp_custom,
    open_email_custom,
    open_gmail_in_chrome,
    toggle_contacted_status,
    send_single_email_smtp,
    run_email_outreach
)
from supabase_client import (
    is_supabase_configured,
    update_supabase_credentials
)

# HTML / CSS / JS dell'interfaccia grafica moderna
GUI_HTML_CONTENT = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CasaLavoroPRO & XPart — Lead Generation & Outreach Suite</title>
  <style>
    :root {
      --bg-dark: #0b0f19;
      --panel-bg: #141b2d;
      --card-bg: #1e293b;
      --border-color: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary-orange: #ea580c;
      --primary-orange-hover: #c2410c;
      --whatsapp-green: #22c55e;
      --whatsapp-green-hover: #16a34a;
      --chrome-blue: #2563eb;
      --chrome-blue-hover: #1d4ed8;
      --blue-accent: #38bdf8;
      --purple-accent: #a855f7;
      --red-stop: #ef4444;
      --red-stop-hover: #dc2626;
      --yellow-warn: #eab308;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg-dark); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; user-select: none; }
    
    /* Header & Nav */
    header {
      background-color: var(--panel-bg);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .brand-box { display: flex; align-items: center; gap: 14px; }
    .brand-logo-clp {
      background: linear-gradient(135deg, #ea580c, #f97316);
      color: white; font-weight: 800; font-size: 15px; padding: 6px 12px; border-radius: 8px;
      box-shadow: 0 2px 10px rgba(234, 88, 12, 0.4);
    }
    .brand-logo-xpart {
      background: linear-gradient(135deg, #2563eb, #38bdf8);
      color: white; font-weight: 800; font-size: 15px; padding: 6px 12px; border-radius: 8px;
      box-shadow: 0 2px 10px rgba(37, 99, 235, 0.4);
    }
    .brand-info h1 { font-size: 17px; font-weight: 800; letter-spacing: -0.3px; }
    .brand-info p { font-size: 11px; color: var(--text-muted); }
    .brand-fixed-user {
      display: inline-flex; align-items: center; gap: 8px; background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 3px 8px; font-size: 11px; color: #38bdf8;
    }
    
    .nav-tabs { display: flex; gap: 6px; background-color: #0b0f19; padding: 4px; border-radius: 8px; border: 1px solid var(--border-color); }
    .nav-tab-btn {
      background: transparent; border: none; color: var(--text-muted); padding: 7px 16px; border-radius: 6px;
      font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s;
    }
    .nav-tab-btn:hover { color: white; }
    .nav-tab-btn.active { background: #1e293b; color: white; border: 1px solid var(--border-color); }
    .nav-tab-btn.active.clp { color: #fb923c; border-color: rgba(234, 88, 12, 0.4); }
    .nav-tab-btn.active.xpart { color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); }

    .header-btns { display: flex; gap: 8px; align-items: center; }
    .btn-top {
      background-color: #1e293b; border: 1px solid var(--border-color); color: var(--text-main);
      padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px; transition: background-color 0.2s;
    }
    .btn-top:hover { background-color: #334155; }

    /* Layout Body */
    .app-body { display: flex; flex-direction: column; flex: 1; padding: 14px 24px; gap: 14px; overflow: hidden; }
    .tab-content { display: none; flex-direction: column; flex: 1; gap: 14px; overflow: hidden; }
    .tab-content.active { display: flex; }

    /* Control Panel */
    .controls-card {
      background-color: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 12px;
      padding: 12px 18px; display: flex; flex-direction: column; gap: 10px; flex-shrink: 0;
    }
    .inputs-row { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
    .input-group { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 160px; }
    .input-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
    .ctrl-input, .ctrl-select {
      background-color: #0b0f19; border: 1px solid var(--border-color); color: white;
      padding: 8px 12px; border-radius: 8px; font-size: 13px; outline: none; transition: border-color 0.2s;
    }
    .ctrl-input:focus, .ctrl-select:focus { border-color: var(--primary-orange); }
    .ctrl-select optgroup { font-weight: 800; color: #fb923c; background-color: #141b2d; font-size: 12px; }
    .ctrl-select option { font-weight: normal; color: white; background-color: #0b0f19; padding: 4px; }
    
    .btn-action-primary {
      background: linear-gradient(135deg, #ea580c, #f97316); color: white; border: none;
      padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;
      display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(234, 88, 12, 0.35);
      transition: all 0.2s; height: 38px;
    }
    .btn-action-primary:hover { filter: brightness(1.1); transform: translateY(-1px); }
    .btn-action-blue {
      background: linear-gradient(135deg, #2563eb, #38bdf8); color: white; border: none;
      padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;
      display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
      transition: all 0.2s; height: 38px;
    }
    .btn-action-blue:hover { filter: brightness(1.1); transform: translateY(-1px); }

    .btn-stop {
      background: var(--red-stop); color: white; border: none; padding: 9px 16px; border-radius: 8px;
      font-size: 13px; font-weight: 700; cursor: pointer; display: none; align-items: center; gap: 6px; height: 38px;
    }
    .btn-stop:hover { background: var(--red-stop-hover); }

    /* Progress Panel */
    .progress-panel {
      display: none; flex-direction: column; gap: 6px; background-color: #0b0f19;
      border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 14px;
    }
    .progress-header { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
    .progress-status { color: #38bdf8; font-weight: 600; }
    .progress-count { color: var(--text-muted); font-weight: 700; }
    .progress-track { background-color: #1e293b; height: 6px; border-radius: 3px; overflow: hidden; }
    .progress-bar-fill {
      background: linear-gradient(90deg, #ea580c, #22c55e); height: 100%; width: 0%;
      border-radius: 3px; transition: width 0.3s ease;
    }
    .progress-bar-fill.xpart-bar { background: linear-gradient(90deg, #2563eb, #38bdf8); }

    /* Stats Grid */
    .stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; flex-shrink: 0; }
    .stat-pill {
      background-color: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 10px;
      padding: 8px 14px; display: flex; flex-direction: column;
    }
    .stat-pill-label { font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); }
    .stat-pill-val { font-size: 18px; font-weight: 800; margin-top: 2px; }
    .val-orange { color: #f97316; }
    .val-green { color: #22c55e; }
    .val-blue { color: #38bdf8; }
    .val-purple { color: #c084fc; }

    /* Table & Filter Bar */
    .table-container {
      background-color: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 12px;
      display: flex; flex-direction: column; flex: 1; overflow: hidden;
    }
    .table-toolbar {
      padding: 10px 16px; border-bottom: 1px solid var(--border-color); display: flex;
      justify-content: space-between; align-items: center; gap: 12px; flex-shrink: 0;
    }
    .table-search {
      background-color: #0b0f19; border: 1px solid var(--border-color); color: white;
      padding: 6px 12px; border-radius: 6px; font-size: 12px; min-width: 250px; outline: none;
    }
    .table-search:focus { border-color: var(--primary-orange); }
    .table-filter-tabs { display: flex; gap: 6px; }
    .tab-btn {
      background: transparent; border: 1px solid transparent; color: var(--text-muted);
      padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;
    }
    .tab-btn.active { background-color: #1e293b; border-color: var(--border-color); color: white; }

    /* Scrollable Table */
    .table-scroll { flex: 1; overflow-y: auto; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left; }
    th {
      position: sticky; top: 0; background-color: #182238; color: var(--text-muted);
      padding: 9px 12px; font-weight: 700; font-size: 11px; text-transform: uppercase;
      letter-spacing: 0.5px; border-bottom: 1px solid var(--border-color); z-index: 10;
    }
    td { padding: 8px 12px; border-bottom: 1px solid #1e293b; vertical-align: middle; }
    tr:hover td { background-color: #1c263c; }

    /* Badges */
    .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .badge-cellulare { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .badge-fisso { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
    .badge-draft { background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.4); }
    .badge-supabase-ok { background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.4); }
    .badge-sent { background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid #22c55e; }
    .badge-todo { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }
    .badge-stars { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }

    /* Controllo Anti-Doppio Invio (Spunta) */
    .anti-duplicate-box {
      display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;
    }
    .custom-checkbox {
      width: 17px; height: 17px; accent-color: var(--whatsapp-green); cursor: pointer;
    }
    .anti-duplicate-label {
      font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;
    }

    /* Action Buttons */
    .row-actions { display: flex; gap: 6px; align-items: center; }
    .btn-wa-action {
      background-color: var(--whatsapp-green); color: white; font-weight: 700; padding: 5px 10px;
      border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center;
      gap: 5px; font-size: 11.5px; box-shadow: 0 2px 6px rgba(34, 197, 94, 0.3); transition: all 0.2s;
    }
    .btn-wa-action:hover { background-color: var(--whatsapp-green-hover); transform: translateY(-1px); }
    .btn-wa-action.already-sent { background-color: #334155; color: #94a3b8; box-shadow: none; }
    
    .btn-email-action {
      background: linear-gradient(135deg, #2563eb, #38bdf8); color: white; font-weight: 700; padding: 5px 10px;
      border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center;
      gap: 5px; font-size: 11.5px; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3); transition: all 0.2s;
    }
    .btn-email-action:hover { filter: brightness(1.1); transform: translateY(-1px); }
    .btn-email-action.already-sent { background: #334155; color: #94a3b8; box-shadow: none; }

    /* Modal Dialogs */
    .modal-overlay {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px);
      display: none; justify-content: center; align-items: center; z-index: 1000;
    }
    .modal-card {
      background: #141b2d; border: 1px solid var(--border-color); border-radius: 14px;
      width: 90%; max-width: 680px; max-height: 90vh; display: flex; flex-direction: column;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6); overflow: hidden;
    }
    .modal-header {
      padding: 16px 20px; border-bottom: 1px solid var(--border-color);
      display: flex; justify-content: space-between; align-items: center;
    }
    .modal-title { font-size: 16px; font-weight: 800; }
    .modal-close {
      background: transparent; border: none; color: var(--text-muted);
      font-size: 20px; cursor: pointer; font-weight: bold;
    }
    .modal-body {
      padding: 18px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;
    }
    .modal-info-box {
      background: #0b0f19; border: 1px solid var(--border-color); border-radius: 8px;
      padding: 10px 14px; font-size: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    }
    .modal-textarea {
      background-color: #0b0f19; border: 1px solid var(--border-color); color: white;
      padding: 12px; border-radius: 8px; font-size: 13px; font-family: inherit; line-height: 1.5;
      resize: vertical; min-height: 140px; outline: none;
    }
    .modal-textarea:focus { border-color: var(--primary-orange); }
    .modal-footer {
      padding: 14px 20px; border-top: 1px solid var(--border-color);
      display: flex; justify-content: flex-end; gap: 10px; align-items: center;
    }
    .btn-modal-cancel {
      background: #334155; color: white; border: none; padding: 8px 16px; border-radius: 6px;
      font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .btn-modal-chrome {
      background: linear-gradient(135deg, #2563eb, #38bdf8); color: white; border: none;
      padding: 9px 18px; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer;
      display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
    }
    .btn-modal-chrome:hover { filter: brightness(1.1); transform: translateY(-1px); }

    .logo-preview-box {
      display: flex; align-items: center; gap: 12px; background: #0b0f19; border: 1px solid var(--border-color);
      padding: 8px 12px; border-radius: 8px; font-size: 12px;
    }
    .logo-thumb { max-height: 34px; max-width: 100px; object-fit: contain; }

    /* Toast */
    .toast {
      position: fixed; bottom: 20px; right: 20px; background: #1e293b;
      border: 1px solid var(--whatsapp-green); color: white; padding: 10px 18px;
      border-radius: 8px; font-size: 13px; font-weight: 600; opacity: 0;
      pointer-events: none; transition: opacity 0.3s; z-index: 9999;
    }
    .toast.show { opacity: 1; }
  </style>
</head>
<body>
  <!-- Header -->
  <header>
    <div class="brand-box">
      <div id="brandBadge" class="brand-logo-clp">CLP</div>
      <div class="brand-info">
        <h1 id="brandHeaderTitle">CasaLavoroPRO — Lead Generation & Outreach</h1>
        <p>Email Chrome Bozza Precompilata • Spunta Anti-Doppio Invio • Bozze Supabase</p>
      </div>
      <div class="brand-fixed-user">
        <span>✉️ bellosi2022@gmail.com</span>
        <span>•</span>
        <span>📱 3423255008</span>
      </div>
    </div>

    <!-- Navigazione a Schede -->
    <div class="nav-tabs">
      <button class="nav-tab-btn active clp" onclick="switchMainTab('clp', this)">🔨 CasaLavoroPRO</button>
      <button class="nav-tab-btn" onclick="switchMainTab('xpart', this)">🚗 XPart Ricambi Auto</button>
      <button class="nav-tab-btn" onclick="switchMainTab('settings', this)">⚙️ Impostazioni Brand</button>
    </div>

    <div class="header-btns">
      <button class="btn-top" onclick="openDataFolder()">📁 Cartella CSV</button>
      <button class="btn-top" onclick="refreshData()">🔄 Ricarica</button>
    </div>
  </header>

  <div class="app-body">
    <!-- ===================================================================== -->
    <!-- TAB 1: CASALAVOROPRO (ARTIGIANI, BOZZE SUPABASE, OUTREACH)            -->
    <!-- ===================================================================== -->
    <div id="tabContentClp" class="tab-content active">
      <!-- Card Controlli di Ricerca -->
      <div class="controls-card">
        <div class="inputs-row">
          <div class="input-group" style="flex: 1.5; min-width: 220px;">
            <label class="input-label">Categoria Artigiano (6 Macro-Settori)</label>
            <select id="categoriaSelect" class="ctrl-select">
              <optgroup label="Impianti e Climatizzazione">
                <option value="Elettricista" selected>Elettricista</option>
                <option value="Idraulico">Idraulico</option>
                <option value="Caldaie e Scaldabagni">Caldaie e Scaldabagni</option>
                <option value="Climatizzazione e Pompe di Calore">Climatizzazione e Pompe di Calore</option>
                <option value="Fotovoltaico e Batterie">Fotovoltaico e Batterie</option>
                <option value="Antennista e Reti Dati">Antennista e Reti Dati</option>
                <option value="Allarmi e Videosorveglianza">Allarmi e Videosorveglianza</option>
                <option value="Domotica">Domotica</option>
              </optgroup>
              <optgroup label="Edilizia e Strutture">
                <option value="Impresa Edile">Impresa Edile</option>
                <option value="Muratore">Muratore</option>
                <option value="Cartongessista">Cartongessista</option>
                <option value="Cappotti Termici e Isolamento">Cappotti Termici e Isolamento</option>
                <option value="Rifacimento Tetti e Lattoniere">Rifacimento Tetti e Lattoniere</option>
                <option value="Scavi e Demolizioni">Scavi e Demolizioni</option>
              </optgroup>
              <optgroup label="Finiture e Pitture">
                <option value="Imbianchino">Imbianchino</option>
                <option value="Pavimentista">Pavimentista</option>
                <option value="Parquettista">Parquettista</option>
                <option value="Resine e Microcemento">Resine e Microcemento</option>
                <option value="Lucidatore Marmi">Lucidatore Marmi</option>
              </optgroup>
              <optgroup label="Infissi, Porte e Metalli">
                <option value="Serramentista (Porte e Finestre)">Serramentista (Porte e Finestre)</option>
                <option value="Fabbro">Fabbro</option>
                <option value="Falegname">Falegname</option>
                <option value="Riparazione Tapparelle e Serrande">Riparazione Tapparelle e Serrande</option>
                <option value="Tende da Sole e Pergotende">Tende da Sole e Pergotende</option>
                <option value="Vetraio">Vetraio</option>
              </optgroup>
              <optgroup label="Esterni, Verde e Pulizie">
                <option value="Giardiniere">Giardiniere</option>
                <option value="Impianti di Irrigazione">Impianti di Irrigazione</option>
                <option value="Disinfestazioni">Disinfestazioni</option>
                <option value="Impresa di Pulizie">Impresa di Pulizie</option>
                <option value="Spurghi e Fognature">Spurghi e Fognature</option>
              </optgroup>
              <optgroup label="Tecnici Abilitati">
                <option value="Geometra">Geometra</option>
                <option value="Architetto">Architetto</option>
                <option value="Ingegnere">Ingegnere</option>
                <option value="Perito Termotecnico">Perito Termotecnico</option>
              </optgroup>
            </select>
          </div>

          <div class="input-group" style="min-width: 140px; max-width: 180px;">
            <label class="input-label">Regione d'Italia</label>
            <select id="regioneSelect" class="ctrl-select" onchange="onRegionChange()">
              <!-- Popolato dinamicamente con le 20 regioni -->
            </select>
          </div>

          <div class="input-group" style="min-width: 220px;">
            <label class="input-label">Provincia / Territorio</label>
            <select id="zonaSelect" class="ctrl-select" onchange="onZoneSelectChange()">
              <!-- Popolato con province della regione -->
            </select>
            <input type="text" id="cittaLiberaInput" class="ctrl-input" placeholder="Comune specifico..." style="margin-top: 4px; display: none;">
          </div>

          <div class="input-group" style="max-width: 140px;">
            <label class="input-label">Limite Contatti</label>
            <select id="limiteSelect" class="ctrl-select">
              <option value="100" selected>100 contatti</option>
              <option value="200">200 contatti</option>
              <option value="300">300 contatti</option>
              <option value="400">400 contatti</option>
              <option value="500">500 contatti</option>
              <option value="600">600 contatti</option>
              <option value="700">700 contatti</option>
              <option value="800">800 contatti</option>
              <option value="900">900 contatti</option>
              <option value="1000">1000 contatti (Max)</option>
              <option value="20">20 (Test veloce)</option>
              <option value="50">50 contatti</option>
            </select>
          </div>

          <div class="input-group" style="max-width: 130px; justify-content: center;">
            <label class="input-label">Deep Scraping</label>
            <label style="font-size: 12px; display: flex; align-items: center; gap: 6px; cursor: pointer; margin-top: 6px;">
              <input type="checkbox" id="deepScrapeCheckbox" checked> Siti Web & Email
            </label>
          </div>

          <button id="btnSearch" class="btn-action-primary" onclick="startScraping()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            Avvia Ricerca Artigiani
          </button>

          <button id="btnStop" class="btn-stop" onclick="stopScraping()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>
            Interrompi
          </button>

          <button id="btnClearView" type="button" class="btn-top" style="height: 38px; border-radius: 8px; padding: 0 14px;" onclick="clearScrapingView()" title="Svuota solo la tabella a schermo senza cancellare i file CSV o Supabase">
            🧹 Pulisci Schermata
          </button>
        </div>

        <!-- Barra di Avanzamento -->
        <div id="progressPanel" class="progress-panel">
          <div class="progress-header">
            <span id="progressStatus" class="progress-status">Inizializzazione sessione stealth...</span>
            <span id="progressCount" class="progress-count">0 / 100</span>
          </div>
          <div class="progress-track">
            <div id="progressBarFill" class="progress-bar-fill"></div>
          </div>
        </div>
      </div>

      <!-- Statistiche CasaLavoroPRO con Focus Anti-Doppio Invio -->
      <div class="stats-row">
        <div class="stat-pill">
          <span class="stat-pill-label">Totale Estratti</span>
          <span id="statTotale" class="stat-pill-val">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Da Inviare (In Attesa)</span>
          <span id="statDaInviare" class="stat-pill-val val-orange">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Spunta Attiva (Già Inviati)</span>
          <span id="statSpuntaInviati" class="stat-pill-val val-green">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Cellulari WhatsApp</span>
          <span id="statCellulari" class="stat-pill-val val-blue">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Email B2B</span>
          <span id="statEmail" class="stat-pill-val val-purple">0</span>
        </div>
      </div>

      <!-- Tabella Risultati CasaLavoroPRO -->
      <div class="table-container">
        <div class="table-toolbar">
          <input type="text" id="tableSearchInput" class="table-search" placeholder="Filtra per nome ditta, comune, telefono, email..." oninput="renderArtisansTable()">
          <div class="table-filter-tabs">
            <button class="tab-btn active" onclick="setArtisanFilter('all', this)">Tutti (<span id="countAll">0</span>)</button>
            <button class="tab-btn" onclick="setArtisanFilter('todo', this)">⏳ Da Inviare (<span id="countTodo">0</span>)</button>
            <button class="tab-btn" onclick="setArtisanFilter('sent', this)">✔ Già Inviati (<span id="countSent">0</span>)</button>
            <button class="tab-btn" onclick="setArtisanFilter('has_email', this)">Con Email (<span id="countEmail">0</span>)</button>
            <button class="tab-btn" onclick="setArtisanFilter('has_reviews', this)">Con Recensioni (<span id="countReviews">0</span>)</button>
          </div>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="min-width: 140px;">Controllo Anti-Doppio Invio</th>
                <th>Ditta / Professionista</th>
                <th>Categoria & Città</th>
                <th>Recapito Telefonico</th>
                <th>Email B2B</th>
                <th>Recensioni Web</th>
                <th>Stato Supabase</th>
                <th>Outreach Interattivo</th>
              </tr>
            </thead>
            <tbody id="artisansTableBody">
              <!-- Righe dinamiche -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- TAB 2: XPART RICAMBI AUTO (SCRAPING OEM, CROSS-REF, COMPATIBILITÀ)    -->
    <!-- ===================================================================== -->
    <div id="tabContentXpart" class="tab-content">
      <div class="controls-card">
        <div class="inputs-row">
          <div class="input-group" style="max-width: 170px;">
            <label class="input-label">Marca Veicolo</label>
            <select id="xpartMarcaSelect" class="ctrl-select">
              <option value="FIAT">FIAT</option>
              <option value="FORD" selected>FORD</option>
              <option value="VOLKSWAGEN">VOLKSWAGEN</option>
              <option value="BMW">BMW</option>
              <option value="AUDI">AUDI</option>
              <option value="ALFA ROMEO">ALFA ROMEO</option>
              <option value="MERCEDES-BENZ">MERCEDES-BENZ</option>
              <option value="RENAULT">RENAULT</option>
              <option value="PEUGEOT">PEUGEOT</option>
              <option value="JEEP">JEEP</option>
              <option value="TOYOTA">TOYOTA</option>
              <option value="OPEL">OPEL</option>
              <option value="CITROEN">CITROEN</option>
            </select>
          </div>

          <div class="input-group" style="min-width: 160px;">
            <label class="input-label">Modello Veicolo</label>
            <input type="text" id="xpartModelloInput" class="ctrl-input" value="Focus Mk3" placeholder="es. Focus, Golf VII, Panda 319...">
          </div>

          <div class="input-group" style="flex: 1.5; min-width: 220px;">
            <label class="input-label">Categoria Ricambio Auto</label>
            <select id="xpartCategoriaSelect" class="ctrl-select">
              <option value="Fari e Fanali (Illuminazione)" selected>Fari e Fanali (Illuminazione)</option>
              <option value="Motore Completo e Monoblocco">Motore Completo e Monoblocco</option>
              <option value="Alternatore e Motorino Avviamento">Alternatore e Motorino Avviamento</option>
              <option value="Compressore Aria Condizionata">Compressore Aria Condizionata</option>
              <option value="Turbina e Turbocompressore">Turbina e Turbocompressore</option>
              <option value="Pompa Iniezione e Iniettori">Pompa Iniezione e Iniettori</option>
              <option value="Cambio Manuale / Automatico">Cambio Manuale / Automatico</option>
              <option value="Centralina Motore (ECU) e Moduli">Centralina Motore (ECU) e Moduli</option>
              <option value="Pompa Idroguida e Servosterzo">Pompa Idroguida e Servosterzo</option>
              <option value="Pinze Freno e Impianto Frenante">Pinze Freno e Impianto Frenante</option>
              <option value="Ammortizzatori e Sospensioni">Ammortizzatori e Sospensioni</option>
              <option value="Specchietti Retrovisori e Portiere">Specchietti Retrovisori e Portiere</option>
              <option value="Cofano e Paraurti Anteriore/Posteriore">Cofano e Paraurti Anteriore/Posteriore</option>
            </select>
          </div>

          <div class="input-group" style="max-width: 130px;">
            <label class="input-label">Limite Ricambi</label>
            <select id="xpartLimiteSelect" class="ctrl-select">
              <option value="25">25 ricambi</option>
              <option value="50" selected>50 ricambi</option>
              <option value="100">100 ricambi</option>
              <option value="200">200 ricambi</option>
            </select>
          </div>

          <button id="btnXpartSearch" class="btn-action-blue" onclick="startXpartScraping()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            Avvia Scraping OEM XPart
          </button>

          <button id="btnXpartStop" class="btn-stop" onclick="stopXpartScraping()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>
            Interrompi
          </button>
        </div>

        <!-- Barra di Avanzamento XPart -->
        <div id="xpartProgressPanel" class="progress-panel">
          <div class="progress-header">
            <span id="xpartProgressStatus" class="progress-status">Estrazione catalogo OEM...</span>
            <span id="xpartProgressCount" class="progress-count">0 / 50</span>
          </div>
          <div class="progress-track">
            <div id="xpartProgressBarFill" class="progress-bar-fill xpart-bar"></div>
          </div>
        </div>
      </div>

      <!-- Statistiche XPart -->
      <div class="stats-row">
        <div class="stat-pill">
          <span class="stat-pill-label">Ricambi Estratti</span>
          <span id="statXpartTotale" class="stat-pill-val val-blue">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Codici OEM Unici</span>
          <span id="statXpartOem" class="stat-pill-val val-green">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Cross-References</span>
          <span id="statXpartCross" class="stat-pill-val val-purple">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Sincronizzati Supabase</span>
          <span id="statXpartSupabase" class="stat-pill-val val-orange">0</span>
        </div>
        <div class="stat-pill">
          <span class="stat-pill-label">Stato Magazzino</span>
          <span class="stat-pill-val" style="color: #38bdf8; font-size: 14px; margin-top: 5px;">GRADO A • ATTIVO</span>
        </div>
      </div>

      <!-- Tabella Ricambi XPart -->
      <div class="table-container">
        <div class="table-toolbar">
          <input type="text" id="xpartTableSearchInput" class="table-search" placeholder="Cerca per codice OEM, marca, motore, cross-reference..." oninput="renderXpartTable()">
          <div style="font-size: 12px; color: var(--text-muted);">
            Database Ricambi: <strong>xpart_ricambi_estratti.csv</strong>
          </div>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Codice OEM</th>
                <th>Descrizione Ricambio</th>
                <th>Compatibilità Veicolo</th>
                <th>Motorizzazione</th>
                <th>Cross-Reference Aftermarket</th>
                <th>Prezzo Stimato</th>
                <th>Scaffale / Grado</th>
                <th>Supabase</th>
              </tr>
            </thead>
            <tbody id="xpartTableBody">
              <!-- Righe dinamiche ricambi -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- TAB 3: IMPOSTAZIONI BRAND, OUTREACH E SUPABASE                        -->
    <!-- ===================================================================== -->
    <div id="tabContentSettings" class="tab-content" style="overflow-y: auto; padding-bottom: 16px;">
      <div class="controls-card" style="max-width: 800px; margin: 0 auto; width: 100%;">
        <h2 style="font-size: 16px; font-weight: 800; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
          ⚙️ Personalizzazione Mittente (Dati Fissi), Brand e Database Supabase
        </h2>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 8px;">
          <div class="input-group">
            <label class="input-label">Tuo Nome / Nome Mittente</label>
            <input type="text" id="settingsSenderName" class="ctrl-input" value="Marco Bellosi">
          </div>

          <div class="input-group">
            <label class="input-label">Tuo Numero WhatsApp Mittente (Fisso)</label>
            <input type="text" id="settingsSenderPhone" class="ctrl-input" value="3423255008" oninput="refreshSandboxEmailPreview()">
          </div>

          <div class="input-group">
            <label class="input-label">Tua Email Mittente (Fissa)</label>
            <input type="text" id="settingsSenderEmail" class="ctrl-input" value="bellosi2022@gmail.com">
          </div>

          <div class="input-group">
            <label class="input-label">Logo o Foto Aziendale (URL o File da PC)</label>
            <div style="display: flex; gap: 8px; align-items: center;">
              <input type="text" id="settingsLogoUrl" class="ctrl-input" style="flex: 1; min-width: 0;" placeholder="https://casalavoropro.com/logo.png o assets/logo.png" oninput="onLogoUrlManualInput()">
              <input type="file" id="settingsLogoFileInput" accept="image/png,image/jpeg,image/jpg,image/webp,image/gif,image/svg+xml" style="display: none;" onchange="handleLogoFileSelected(event)">
              <button type="button" class="btn-top" style="height: 36px; white-space: nowrap; border-color: rgba(56, 189, 248, 0.45); color: #38bdf8;" onclick="document.getElementById('settingsLogoFileInput').click()">
                📁 Sfoglia / Carica Logo o Foto da PC
              </button>
            </div>
          </div>
        </div>

        <div class="input-group" style="margin-top: 6px;">
          <label class="input-label">Link Galleria Foto / Lavori (opzionale per messaggi)</label>
          <input type="text" id="settingsFotoAllegate" class="ctrl-input" placeholder="https://casalavoropro.com/lavori" oninput="refreshSandboxEmailPreview()">
        </div>

        <div class="logo-preview-box" style="margin-top: 4px;">
          <img id="settingsLogoThumb" class="logo-thumb" src="" alt="Anteprima Logo" onerror="this.style.display='none'">
          <span id="settingsLogoLabel" style="color: var(--text-muted);">Anteprima logo mittente per email e presentazioni</span>
        </div>

        <h3 style="font-size: 14px; font-weight: 800; margin-top: 14px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; color: #38bdf8;">
          Connessione Database Supabase (CasaLavoroPRO & XPart)
        </h3>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="input-group">
            <label class="input-label">Supabase Project URL</label>
            <input type="text" id="settingsSupabaseUrl" class="ctrl-input" placeholder="https://xyzcompany.supabase.co">
          </div>

          <div class="input-group">
            <label class="input-label">Supabase Key (Anon o Service Role)</label>
            <input type="password" id="settingsSupabaseKey" class="ctrl-input" placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...">
          </div>

          <div class="input-group">
            <label class="input-label">Tabella Bozze CasaLavoroPRO</label>
            <input type="text" id="settingsTableBozze" class="ctrl-input" value="aziende_drafts">
          </div>

          <div class="input-group">
            <label class="input-label">Tabella Ricambi XPart</label>
            <input type="text" id="settingsTableXpart" class="ctrl-input" value="xpart_ricambi">
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
          <button class="btn-action-primary" onclick="saveSettings()">
            💾 Salva Impostazioni
          </button>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- BOX INDIPENDENTE: SPAZIO TEST GENERAZIONE EMAIL (SANDBOX)           -->
      <!-- =================================================================== -->
      <div class="controls-card" style="max-width: 800px; margin: 0 auto; width: 100%; border-color: rgba(56, 189, 248, 0.35);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
          <h2 style="font-size: 16px; font-weight: 800; color: #38bdf8;">
            🧪 Spazio Test Generazione Email
          </h2>
          <span class="badge" style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35);">
            Sandbox Isolata • Nessun impatto su CSV/Supabase
          </span>
        </div>

        <div style="display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; margin-top: 4px;">
          <div class="input-group" style="flex: 2; min-width: 240px;">
            <label class="input-label">Email di Prova (Destinatario Test)</label>
            <input type="email" id="sandboxTestEmail" class="ctrl-input" placeholder="la-tua-email@esempio.it" value="bellosi2022@gmail.com">
          </div>

          <button type="button" class="btn-top" style="height: 36px;" onclick="refreshSandboxEmailPreview(true)">
            🔄 Rigenera Testo
          </button>

          <button type="button" class="btn-action-blue" onclick="sendSandboxTestEmail()">
            ✉️ Genera &amp; Invia Email di Test
          </button>
        </div>

        <div class="input-group">
          <label class="input-label">Oggetto Email di Test</label>
          <input type="text" id="sandboxEmailSubject" class="ctrl-input" value="Invito gratuito su CasaLavoroPRO — Nuove richieste clienti nella tua zona">
        </div>

        <div class="input-group">
          <label class="input-label">Anteprima Esatta Email (Mittente: CasaLavoroPRO &lt;info@casalavoropro.com&gt;)</label>
          <textarea id="sandboxEmailPreview" class="modal-textarea" rows="12" style="min-height: 210px; font-size: 12.5px;"></textarea>
        </div>

        <div id="sandboxTestFeedback" style="font-size: 11.5px; color: var(--text-muted);">
          Invia tramite SMTP se configurato in .env, altrimenti apre direttamente la bozza precompilata in Google Chrome senza registrare il contatto nel registro anti-doppio invio.
        </div>
      </div>
    </div>
  </div>

  <!-- ===================================================================== -->
  <!-- MODALE COMPOSER OUTREACH WHATSAPP                                     -->
  <!-- ===================================================================== -->
  <div id="modalWhatsApp" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#22c55e"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
          <span class="modal-title">Composer WhatsApp — Personalizza Messaggio</span>
        </div>
        <button class="modal-close" onclick="closeWhatsAppModal()">✕</button>
      </div>

      <div class="modal-body">
        <div class="modal-info-box">
          <div>Destinatario: <strong id="waModalDestinatario">Ditta</strong></div>
          <div>Cellulare WhatsApp: <strong id="waModalTelefono" style="color: #4ade80;">+39 ...</strong></div>
          <div>Categoria & Città: <span id="waModalCategoriaCitta" style="color: var(--text-muted);">...</span></div>
          <div>Tuo Mittente: <span id="waModalMittenteInfo" style="color: #fb923c;">Marco Bellosi (3423255008)</span></div>
        </div>

        <div class="input-group">
          <label class="input-label">Testo del Messaggio WhatsApp (Completamente Modificabile)</label>
          <textarea id="waModalText" class="modal-textarea" rows="8"></textarea>
        </div>

        <div style="font-size: 11.5px; color: var(--text-muted); line-height: 1.4;">
          💡 <em>Apre direttamente l'app WhatsApp ufficiale (o WhatsApp Web). Il contatto viene contrassegnato automaticamente con la <strong>Spunta Anti-Doppio Invio</strong>.</em>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-modal-cancel" onclick="closeWhatsAppModal()">Annulla</button>
        <button class="btn-wa-action" onclick="confirmSendWhatsApp()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
          Apri WhatsApp Desktop / Web
        </button>
      </div>
    </div>
  </div>

  <!-- ===================================================================== -->
  <!-- MODALE COMPOSER OUTREACH EMAIL B2B (GOOGLE CHROME INTEGRATO)          -->
  <!-- ===================================================================== -->
  <div id="modalEmail" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
          <span class="modal-title">Composer Email B2B — Invio tramite Google Chrome</span>
        </div>
        <button class="modal-close" onclick="closeEmailModal()">✕</button>
      </div>

      <div class="modal-body">
        <div class="modal-info-box">
          <div>Destinatario: <strong id="emailModalDestinatario">Ditta</strong></div>
          <div>Indirizzo Email: <strong id="emailModalIndirizzo" style="color: #38bdf8;">email@...</strong></div>
          <div>Categoria & Città: <span id="emailModalCategoriaCitta" style="color: var(--text-muted);">...</span></div>
          <div>Tuo Mittente: <span id="emailModalMittenteInfo" style="color: #fb923c;">Marco Bellosi (bellosi2022@gmail.com)</span></div>
        </div>

        <div class="input-group">
          <label class="input-label">Oggetto dell'Email</label>
          <input type="text" id="emailModalSubject" class="ctrl-input">
        </div>

        <div class="input-group">
          <label class="input-label">Testo Email (con recapiti fissi e firma)</label>
          <textarea id="emailModalBody" class="modal-textarea" rows="9"></textarea>
        </div>

        <div style="background: rgba(37, 99, 235, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 10px 12px; font-size: 11.5px; color: #94a3b8; line-height: 1.4;">
          🚀 <strong>Integrazione Google Chrome</strong>: Cliccando sul pulsante blu, si aprirà direttamente <strong>Google Chrome</strong> con la schermata di composizione Gmail precompilata con questo destinatario, oggetto e corpo del testo. Potrai allegare il tuo logo e le tue foto con un semplice trascinamento prima di inviare.
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-modal-cancel" onclick="closeEmailModal()">Annulla</button>
        <button class="btn-modal-chrome" onclick="confirmOpenEmailInChrome()">
          🌐 Apri Bozza in Google Chrome
        </button>
        <button class="btn-top" onclick="confirmOpenEmailClient()" title="Apri in Outlook o altro client installato">
          ✉️ Client Predefinito
        </button>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Azione eseguita con successo</div>

  <!-- SCRIPT JAVASCRIPT APPLICATIVO -->
  <script>
    let artisansData = [];
    let xpartData = [];
    let geoDb = {};
    let allRegions = [];
    let currentArtisanFilter = 'all';
    
    // Dati utente fissi
    let appSettings = {
      sender_name: "Marco Bellosi",
      sender_phone: "3423255008",
      sender_email: "bellosi2022@gmail.com",
      logo_url: "https://casalavoropro.com/logo.png",
      foto_allegate: ""
    };

    let activeWaArtisan = null;
    let activeEmailArtisan = null;

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 3200);
    }

    // Switch tra Tab Principali
    function switchMainTab(tabId, btn) {
      document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active', 'clp', 'xpart'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      if (tabId === 'clp') {
        document.getElementById('tabContentClp').classList.add('active');
        btn.classList.add('active', 'clp');
        document.getElementById('brandBadge').className = 'brand-logo-clp';
        document.getElementById('brandBadge').textContent = 'CLP';
        document.getElementById('brandHeaderTitle').textContent = 'CasaLavoroPRO — Lead Generation & Outreach';
      } else if (tabId === 'xpart') {
        document.getElementById('tabContentXpart').classList.add('active');
        btn.classList.add('active', 'xpart');
        document.getElementById('brandBadge').className = 'brand-logo-xpart';
        document.getElementById('brandBadge').textContent = 'XPART';
        document.getElementById('brandHeaderTitle').textContent = 'XPart Ricambi Auto — Scraping Codici OEM & Catalogo';
      } else if (tabId === 'settings') {
        document.getElementById('tabContentSettings').classList.add('active');
        btn.classList.add('active');
      }
    }

    // Regioni e Territori
    function populateRegions(regions, db) {
      allRegions = regions || [];
      geoDb = db || {};
      const regSelect = document.getElementById('regioneSelect');
      regSelect.innerHTML = '';
      
      allRegions.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r;
        opt.textContent = r;
        if (r === 'Veneto') opt.selected = true;
        regSelect.appendChild(opt);
      });
      onRegionChange();
    }

    function onRegionChange() {
      const reg = document.getElementById('regioneSelect').value;
      const zonaSelect = document.getElementById('zonaSelect');
      zonaSelect.innerHTML = '';

      const zones = (geoDb[reg]) ? Object.keys(geoDb[reg]) : [];
      zones.forEach(z => {
        const opt = document.createElement('option');
        opt.value = z;
        opt.textContent = z;
        if (z.includes('Vicenza e provincia')) opt.selected = true;
        zonaSelect.appendChild(opt);
      });

      const customOpt = document.createElement('option');
      customOpt.value = '__custom__';
      customOpt.textContent = '✏️ Scrivi comune specifico...';
      zonaSelect.appendChild(customOpt);

      onZoneSelectChange();
    }

    function onZoneSelectChange() {
      const val = document.getElementById('zonaSelect').value;
      const customInput = document.getElementById('cittaLiberaInput');
      if (val === '__custom__') {
        customInput.style.display = 'block';
        customInput.focus();
      } else {
        customInput.style.display = 'none';
      }
    }

    // Caricamento Dati Iniziali dal Backend Python
    async function loadInitialData() {
      if (window.pywebview && window.pywebview.api) {
        try {
          const res = await window.pywebview.api.get_initial_data();
          if (res) {
            artisansData = res.artisans || [];
            xpartData = res.xpart_parts || [];
            if (res.settings) {
              appSettings = Object.assign(appSettings, res.settings);
            }

            if (res.regions && res.geo_database) {
              populateRegions(res.regions, res.geo_database);
            }

            populateSettingsFields(appSettings);
            updateArtisansStats();
            renderArtisansTable();
            updateXpartStats();
            renderXpartTable();
          }
        } catch (e) {
          console.error("Errore caricamento dati:", e);
        }
      }
    }

    let localLogoPreviewDataUrl = '';

    function populateSettingsFields(s) {
      document.getElementById('settingsSenderName').value = s.sender_name || 'Marco Bellosi';
      document.getElementById('settingsSenderPhone').value = s.sender_phone || '3423255008';
      document.getElementById('settingsSenderEmail').value = s.sender_email || 'bellosi2022@gmail.com';
      document.getElementById('settingsLogoUrl').value = s.logo_url || 'https://casalavoropro.com/logo.png';
      document.getElementById('settingsFotoAllegate').value = s.foto_allegate || '';
      document.getElementById('settingsSupabaseUrl').value = s.supabase_url || '';
      document.getElementById('settingsSupabaseKey').value = s.supabase_key || '';
      document.getElementById('settingsTableBozze').value = s.supabase_table_bozze || 'aziende_drafts';
      document.getElementById('settingsTableXpart').value = s.supabase_table_xpart || 'xpart_ricambi';
      localLogoPreviewDataUrl = s.logo_preview_data || '';
      updateLogoPreview();
      refreshSandboxEmailPreview();
    }

    function buildSandboxEmailBody() {
      const waPhone = (document.getElementById('settingsSenderPhone').value || '3423255008').trim();
      const waDigits = waPhone.replace(/\D/g, '').replace(/^0039/, '').replace(/^39(?=\d{9,})/, '');
      const waCleanLink = waDigits ? `https://wa.me/39${waDigits}` : 'https://casalavoropro.com';
      const fotoLink = (document.getElementById('settingsFotoAllegate').value || '').trim();
      const extraFotoLine = fotoLink ? `\nGalleria lavori e foto: ${fotoLink}\n` : '';

      return (
`Gentile Professionista,

Ti scriviamo dal team di CasaLavoroPRO (https://casalavoropro.com).

Abbiamo selezionato la tua attività tra i migliori professionisti locali e stiamo attivando gratuitamente le schede di presentazione sulla nostra piattaforma per metterti in contatto diretto con clienti della tua zona alla ricerca di lavori per la casa.

Perché scegliere CasaLavoroPRO:
- ZERO gettoni per rispondere alle richieste di preventivo
- ZERO commissioni sui lavori conclusi (incassi il 100% direttamente dal cliente)
- Contatto diretto tramite telefono, email o WhatsApp
${extraFotoLine}
Visita il portale ufficiale: https://casalavoropro.com
Attiva o verifica la tua scheda gratuita: https://casalavoropro.com

Per qualsiasi informazione o supporto diretto:
WhatsApp: ${waPhone} (${waCleanLink})
Email: info@casalavoropro.com

Un cordiale saluto,
CasaLavoroPRO
Sito web: https://casalavoropro.com
Email: info@casalavoropro.com
WhatsApp: ${waPhone}`
      );
    }

    function refreshSandboxEmailPreview(notify) {
      const subjectInput = document.getElementById('sandboxEmailSubject');
      const previewArea = document.getElementById('sandboxEmailPreview');
      if (subjectInput && !subjectInput.value.trim()) {
        subjectInput.value = 'Invito gratuito su CasaLavoroPRO — Nuove richieste clienti nella tua zona';
      }
      if (previewArea) {
        previewArea.value = buildSandboxEmailBody();
      }
      if (notify) {
        showToast('Anteprima Email Sandbox rigenerata con i dati CasaLavoroPRO.');
      }
    }

    async function sendSandboxTestEmail() {
      const testEmail = (document.getElementById('sandboxTestEmail').value || '').trim();
      const subject = (document.getElementById('sandboxEmailSubject').value || '').trim() || 'Invito gratuito su CasaLavoroPRO';
      const previewArea = document.getElementById('sandboxEmailPreview');
      if (previewArea && !previewArea.value.trim()) {
        previewArea.value = buildSandboxEmailBody();
      }
      const body = previewArea ? previewArea.value : buildSandboxEmailBody();
      const feedbackEl = document.getElementById('sandboxTestFeedback');

      if (!testEmail || !testEmail.includes('@')) {
        showToast("Inserisci un'email di prova valida prima di inviare.");
        return;
      }

      if (window.pywebview && window.pywebview.api && window.pywebview.api.send_sandbox_test_email) {
        const res = await window.pywebview.api.send_sandbox_test_email(testEmail, subject, body);
        if (res && res.success) {
          const msg = res.mode === 'smtp'
            ? `Email di test inviata via SMTP a ${testEmail}`
            : `Bozza email di test aperta in Google Chrome per ${testEmail}`;
          if (feedbackEl) {
            feedbackEl.style.color = '#4ade80';
            feedbackEl.textContent = '✔ ' + msg + ' (Sandbox isolata: CSV e Supabase invariati).';
          }
          showToast(msg);
        } else {
          const err = (res && res.error) || 'Errore sconosciuto';
          if (feedbackEl) {
            feedbackEl.style.color = '#f87171';
            feedbackEl.textContent = '⚠ ' + err;
          }
          showToast('Errore test email: ' + err);
        }
      }
    }

    function onLogoUrlManualInput() {
      localLogoPreviewDataUrl = '';
      updateLogoPreview();
    }

    function updateLogoPreview() {
      const url = document.getElementById('settingsLogoUrl').value.trim();
      const img = document.getElementById('settingsLogoThumb');
      const label = document.getElementById('settingsLogoLabel');
      const previewSrc = localLogoPreviewDataUrl || url;
      if (previewSrc) {
        img.src = previewSrc;
        img.style.display = 'inline-block';
      } else {
        img.style.display = 'none';
      }
      if (label) {
        label.textContent = url
          ? 'Logo attivo per bozze e presentazioni: ' + url
          : 'Anteprima logo mittente per email e presentazioni';
      }
    }

    function handleLogoFileSelected(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async function (e) {
        const dataUrl = e.target && e.target.result ? String(e.target.result) : '';
        if (!dataUrl) return;
        if (window.pywebview && window.pywebview.api && window.pywebview.api.upload_brand_logo) {
          const res = await window.pywebview.api.upload_brand_logo(file.name, dataUrl);
          if (res && res.success) {
            document.getElementById('settingsLogoUrl').value = res.path;
            localLogoPreviewDataUrl = res.preview_data || dataUrl;
            appSettings.logo_url = res.path;
            updateLogoPreview();
            showToast('Logo salvato in locale: ' + res.path);
          } else {
            showToast('Errore caricamento logo: ' + ((res && res.error) || 'operazione non riuscita'));
          }
        } else {
          document.getElementById('settingsLogoUrl').value = 'assets/' + file.name;
          localLogoPreviewDataUrl = dataUrl;
          updateLogoPreview();
        }
        event.target.value = '';
      };
      reader.readAsDataURL(file);
    }

    async function saveSettings() {
      const newSettings = {
        sender_name: document.getElementById('settingsSenderName').value.trim() || 'Marco Bellosi',
        sender_phone: document.getElementById('settingsSenderPhone').value.trim() || '3423255008',
        sender_email: document.getElementById('settingsSenderEmail').value.trim() || 'bellosi2022@gmail.com',
        logo_url: document.getElementById('settingsLogoUrl').value.trim(),
        foto_allegate: document.getElementById('settingsFotoAllegate').value.trim(),
        supabase_url: document.getElementById('settingsSupabaseUrl').value.trim(),
        supabase_key: document.getElementById('settingsSupabaseKey').value.trim(),
        supabase_table_bozze: document.getElementById('settingsTableBozze').value.trim(),
        supabase_table_xpart: document.getElementById('settingsTableXpart').value.trim()
      };

      if (window.pywebview && window.pywebview.api) {
        const ok = await window.pywebview.api.save_settings(newSettings);
        if (ok) {
          appSettings = newSettings;
          refreshSandboxEmailPreview();
          showToast("Impostazioni e dati utente aggiornati con successo!");
        }
      }
    }

    // =========================================================================
    // MODULO SCRAPING CASALAVOROPRO
    // =========================================================================
    async function startScraping() {
      const cat = document.getElementById('categoriaSelect').value;
      const reg = document.getElementById('regioneSelect').value;
      let zone = document.getElementById('zonaSelect').value;
      if (zone === '__custom__') {
        zone = document.getElementById('cittaLiberaInput').value.trim();
      }
      const lim = parseInt(document.getElementById('limiteSelect').value, 10);
      const deep = document.getElementById('deepScrapeCheckbox').checked;

      if (!cat || !zone) {
        showToast("Seleziona categoria e zona di ricerca");
        return;
      }

      document.getElementById('btnSearch').style.display = 'none';
      document.getElementById('btnStop').style.display = 'inline-flex';
      document.getElementById('progressPanel').style.display = 'flex';
      document.getElementById('progressStatus').textContent = `Scansione Google Maps per '${cat}' su '${zone}'...`;
      document.getElementById('progressCount').textContent = `0 / ${lim}`;
      document.getElementById('progressBarFill').style.width = '2%';

      if (window.pywebview && window.pywebview.api) {
        try {
          await window.pywebview.api.start_scraping(cat, reg, zone, lim, deep);
        } catch (err) {
          showToast("Errore avvio: " + err);
          resetSearchButtons();
        }
      }
    }

    async function stopScraping() {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.stop_scraping();
        showToast("Arresto scraper richiesto...");
      }
    }

    window.onScraperProgress = function(data) {
      if (!data) return;
      if (data.status_text) {
        document.getElementById('progressStatus').textContent = data.status_text;
      }

      const current = data.current_count || 0;
      const target = data.target_limit || 100;
      document.getElementById('progressCount').textContent = `${current} / ${target}`;

      const pct = Math.min(100, Math.round((current / target) * 100));
      document.getElementById('progressBarFill').style.width = `${Math.max(4, pct)}%`;

      if (data.record) {
        const existingIdx = artisansData.findIndex(a => a.telefono === data.record.telefono_principale);
        if (existingIdx === -1) {
          artisansData.unshift({
            id: artisansData.length + 1,
            nome_attivita: data.record.nome_attivita,
            categoria: data.record.categoria,
            citta: data.record.citta,
            telefono: data.record.telefono_principale,
            tipo_telefono: data.record.tipo_telefono,
            email: data.record.email,
            sito_web: data.record.sito_web,
            rating_recensioni: data.record.rating_recensioni || "",
            numero_recensioni: data.record.numero_recensioni || "",
            recensioni_estratte: data.record.recensioni_estratte || "",
            stato_bozza: "draft_scraping",
            is_contacted: false,
            wa_contacted: false,
            wa_date: "",
            em_contacted: false
          });
        }
        updateArtisansStats();
        renderArtisansTable();
      }

      if (data.completed) {
        resetSearchButtons();
        showToast(`Scraping completato: ${current} contatti elaborati con bozze Supabase!`);
      }
    };

    function resetSearchButtons() {
      document.getElementById('btnSearch').style.display = 'inline-flex';
      document.getElementById('btnStop').style.display = 'none';
      setTimeout(() => {
        document.getElementById('progressPanel').style.display = 'none';
      }, 4000);
    }

    function clearScrapingView() {
      artisansData = [];
      updateArtisansStats();
      renderArtisansTable();

      const progressPanel = document.getElementById('progressPanel');
      const progressBarFill = document.getElementById('progressBarFill');
      const progressCount = document.getElementById('progressCount');
      const progressStatus = document.getElementById('progressStatus');
      const limitSelect = document.getElementById('limiteSelect');
      const currentLimit = limitSelect ? limitSelect.value : '100';

      if (progressPanel) progressPanel.style.display = 'none';
      if (progressBarFill) progressBarFill.style.width = '0%';
      if (progressCount) progressCount.textContent = `0 / ${currentLimit}`;
      if (progressStatus) progressStatus.textContent = 'Pronto per una nuova ricerca.';

      showToast('Schermata di scraping pulita');
    }

    // =========================================================================
    // SISTEMA ANTI-DOPPIO INVIO & SPUNTA DI CONTROLLO
    // =========================================================================
    async function toggleSpunta(artisanId, isChecked) {
      const art = artisansData.find(a => a.id === artisanId);
      if (!art) return;

      art.is_contacted = isChecked;
      if (isChecked) {
        art.wa_contacted = true;
      }

      if (window.pywebview && window.pywebview.api) {
        const targetVal = art.telefono || art.email || art.nome_attivita;
        await window.pywebview.api.toggle_contact_check(art.nome_attivita, targetVal, isChecked);
      }

      showToast(isChecked 
        ? `✔ Spunta attivata: "${art.nome_attivita}" segnato come inviato (Anti-Doppio Invio ATTIVO)`
        : `Spunta rimossa per "${art.nome_attivita}"`
      );

      updateArtisansStats();
      renderArtisansTable();
    }

    function checkAntiDoppioInvio(art) {
      if (art && art.is_contacted) {
        return confirm(
          `⚠️ ATTENZIONE ANTI-DOPPIO INVIO:\n\n` +
          `Risulta che hai già contattato o inviato a: "${art.nome_attivita}".\n\n` +
          `Vuoi davvero procedere e inviare un messaggio duplicato?`
        );
      }
      return true;
    }

    // =========================================================================
    // MODALI OUTREACH INTERATTIVI (WHATSAPP & GOOGLE CHROME EMAIL)
    // =========================================================================
    function openWhatsAppModal(artisanId) {
      const art = artisansData.find(a => a.id === artisanId);
      if (!art) return;

      if (!checkAntiDoppioInvio(art)) {
        return;
      }

      activeWaArtisan = art;

      document.getElementById('waModalDestinatario').textContent = art.nome_attivita;
      document.getElementById('waModalTelefono').textContent = art.telefono || 'N/D';
      document.getElementById('waModalCategoriaCitta').textContent = `${art.categoria} • ${art.citta}`;
      document.getElementById('waModalMittenteInfo').textContent = `${appSettings.sender_name || 'Marco Bellosi'} (${appSettings.sender_phone || '3423255008'})`;

      const fotoPart = appSettings.foto_allegate ? `\nGuarda i nostri lavori: ${appSettings.foto_allegate}` : '';

      const msg = `Ciao ${art.nome_attivita}, sono ${appSettings.sender_name || 'Marco Bellosi'} di CasaLavoroPRO.\n\n` +
        `Ho notato la tua attività di ${art.categoria} a ${art.citta} e la qualità dei tuoi interventi. ` +
        `Stiamo inserendo gratuitamente i migliori professionisti della zona sulla nostra piattaforma ` +
        `per metterli in contatto diretto con clienti locali che cercano lavori di casa, senza gettoni e senza commissioni sui preventivi.\n\n` +
        `Puoi vedere il portale qui: https://casalavoropro.com${fotoPart}\n\n` +
        `Se vuoi farti trovare gratis, ti predisponiamo noi la scheda o puoi registrarti in 2 minuti. Buon lavoro!\n` +
        `(${appSettings.sender_name || 'Marco Bellosi'} - ${appSettings.sender_phone || '3423255008'})`;

      document.getElementById('waModalText').value = msg;
      document.getElementById('modalWhatsApp').style.display = 'flex';
    }

    function closeWhatsAppModal() {
      document.getElementById('modalWhatsApp').style.display = 'none';
      activeWaArtisan = null;
    }

    async function confirmSendWhatsApp() {
      if (!activeWaArtisan) return;
      const customMsg = document.getElementById('waModalText').value.trim();

      if (window.pywebview && window.pywebview.api) {
        const ok = await window.pywebview.api.send_custom_whatsapp(activeWaArtisan.telefono, customMsg, activeWaArtisan.nome_attivita);
        if (ok) {
          activeWaArtisan.is_contacted = true;
          activeWaArtisan.wa_contacted = true;
          activeWaArtisan.wa_date = new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
          showToast(`WhatsApp aperto! Spunta anti-doppio invio attivata per ${activeWaArtisan.nome_attivita}`);
          updateArtisansStats();
          renderArtisansTable();
        }
      }
      closeWhatsAppModal();
    }

    function openEmailModal(artisanId) {
      const art = artisansData.find(a => a.id === artisanId);
      if (!art || !art.email) return;

      if (!checkAntiDoppioInvio(art)) {
        return;
      }

      activeEmailArtisan = art;

      document.getElementById('emailModalDestinatario').textContent = art.nome_attivita;
      document.getElementById('emailModalIndirizzo').textContent = art.email;
      document.getElementById('emailModalCategoriaCitta').textContent = `${art.categoria} • ${art.citta}`;
      document.getElementById('emailModalMittenteInfo').textContent = `${appSettings.sender_name || 'Marco Bellosi'} (${appSettings.sender_email || 'bellosi2022@gmail.com'})`;

      document.getElementById('emailModalSubject').value = `Richieste preventivo e visibilità gratuita a ${art.citta} per ${art.nome_attivita}`;

      const fotoPart = appSettings.foto_allegate ? `\nPuoi visualizzare alcuni progetti già pubblicati qui: ${appSettings.foto_allegate}\n` : '';

      const body = `Gentile ${art.nome_attivita},\n\n` +
        `Mi chiamo ${appSettings.sender_name || 'Marco Bellosi'} e ti scrivo dal team di CasaLavoroPRO (casalavoropro.com).\n\n` +
        `Ho notato la tua attività di ${art.categoria} a ${art.citta} e l'ottima qualità dei tuoi lavori sul territorio. Stiamo selezionando e inserendo gratuitamente i migliori professionisti della zona sulla nostra piattaforma per metterli in contatto diretto con clienti locali che richiedono interventi per la casa.\n\n` +
        `Perché CasaLavoroPRO è diversa?\n` +
        `• ZERO gettoni: non paghi per sbloccare i contatti o fare preventivi.\n` +
        `• ZERO commissioni: il cliente paga direttamente te al 100%.\n` +
        `• Contatto diretto telefonico e WhatsApp con i committenti.\n` +
        `${fotoPart}\n` +
        `Se vuoi attivare la tua vetrina gratuita ed essere contattato per i lavori nella tua zona, puoi rispondere direttamente a questa email confermando il tuo interesse, oppure registrarti su: https://casalavoropro.com\n\n` +
        `Resto a tua completa disposizione anche telefonicamente al ${appSettings.sender_phone || '3423255008'}.\n\n` +
        `Cordiali saluti,\n` +
        `${appSettings.sender_name || 'Marco Bellosi'}\n` +
        `CasaLavoroPRO — Il portale etico dei professionisti della casa\n` +
        `Telefono: ${appSettings.sender_phone || '3423255008'}\n` +
        `Email: ${appSettings.sender_email || 'bellosi2022@gmail.com'}`;

      document.getElementById('emailModalBody').value = body;
      document.getElementById('modalEmail').style.display = 'flex';
    }

    function closeEmailModal() {
      document.getElementById('modalEmail').style.display = 'none';
      activeEmailArtisan = null;
    }

    // Apertura Google Chrome per Email (Specifiche Utente Obbligatorie)
    async function confirmOpenEmailInChrome() {
      if (!activeEmailArtisan) return;
      const subj = document.getElementById('emailModalSubject').value.trim();
      const body = document.getElementById('emailModalBody').value.trim();

      if (window.pywebview && window.pywebview.api) {
        const ok = await window.pywebview.api.open_gmail_chrome(activeEmailArtisan.email, subj, body, activeEmailArtisan.nome_attivita);
        if (ok) {
          activeEmailArtisan.is_contacted = true;
          activeEmailArtisan.em_contacted = true;
          showToast(`Bozza aperta in Google Chrome! Spunta anti-doppio invio attivata per ${activeEmailArtisan.nome_attivita}`);
          updateArtisansStats();
          renderArtisansTable();
        }
      }
      closeEmailModal();
    }

    async function confirmOpenEmailClient() {
      if (!activeEmailArtisan) return;
      const subj = document.getElementById('emailModalSubject').value.trim();
      const body = document.getElementById('emailModalBody').value.trim();

      if (window.pywebview && window.pywebview.api) {
        const ok = await window.pywebview.api.open_custom_email(activeEmailArtisan.email, subj, body, activeEmailArtisan.nome_attivita);
        if (ok) {
          activeEmailArtisan.is_contacted = true;
          activeEmailArtisan.em_contacted = true;
          showToast(`Client email aperto! Spunta anti-doppio invio attivata`);
          updateArtisansStats();
          renderArtisansTable();
        }
      }
      closeEmailModal();
    }

    // =========================================================================
    // RENDERING TABELLA ARTIGIANI CASALAVOROPRO
    // =========================================================================
    function setArtisanFilter(f, btn) {
      currentArtisanFilter = f;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderArtisansTable();
    }

    function updateArtisansStats() {
      const tot = artisansData.length;
      const sent = artisansData.filter(a => a.is_contacted).length;
      const todo = tot - sent;
      const cell = artisansData.filter(a => a.tipo_telefono === 'cellulare').length;
      const em = artisansData.filter(a => a.email && a.email.includes('@')).length;
      const reviews = artisansData.filter(a => a.rating_recensioni).length;

      document.getElementById('statTotale').textContent = tot;
      document.getElementById('statDaInviare').textContent = todo;
      document.getElementById('statSpuntaInviati').textContent = sent;
      document.getElementById('statCellulari').textContent = cell;
      document.getElementById('statEmail').textContent = em;

      document.getElementById('countAll').textContent = tot;
      document.getElementById('countTodo').textContent = todo;
      document.getElementById('countSent').textContent = sent;
      document.getElementById('countEmail').textContent = em;
      document.getElementById('countReviews').textContent = reviews;
    }

    function renderArtisansTable() {
      const search = document.getElementById('tableSearchInput').value.toLowerCase();
      const tbody = document.getElementById('artisansTableBody');
      tbody.innerHTML = '';

      artisansData.forEach(a => {
        const matchSearch = !search ||
          a.nome_attivita.toLowerCase().includes(search) ||
          (a.citta && a.citta.toLowerCase().includes(search)) ||
          (a.categoria && a.categoria.toLowerCase().includes(search)) ||
          (a.telefono && a.telefono.includes(search)) ||
          (a.email && a.email.toLowerCase().includes(search));

        let matchFilter = true;
        if (currentArtisanFilter === 'todo') {
          matchFilter = !a.is_contacted;
        } else if (currentArtisanFilter === 'sent') {
          matchFilter = a.is_contacted;
        } else if (currentArtisanFilter === 'has_email') {
          matchFilter = Boolean(a.email);
        } else if (currentArtisanFilter === 'has_reviews') {
          matchFilter = Boolean(a.rating_recensioni);
        }

        if (matchSearch && matchFilter) {
          const tr = document.createElement('tr');

          const isCell = a.tipo_telefono === 'cellulare';
          const telBadge = isCell
            ? '<span class="badge badge-cellulare">Cellulare</span>'
            : '<span class="badge badge-fisso">Fisso</span>';

          const reviewsBadge = a.rating_recensioni
            ? `<span class="badge badge-stars">⭐ ${a.rating_recensioni} (${a.numero_recensioni || '0'})</span>`
            : '<span style="color:#64748b; font-size:11px;">Nessuna</span>';

          const supabaseBadge = `<span class="badge badge-draft">draft_scraping</span>`;

          // Controllo Anti-Doppio Invio (Spunta Obbligatoria)
          const spuntaHtml = `
            <div class="anti-duplicate-box" title="Spunta per segnare il contatto come già inviato ed evitare doppi invii">
              <input type="checkbox" id="check_${a.id}" class="custom-checkbox" ${a.is_contacted ? 'checked' : ''} onchange="toggleSpunta(${a.id}, this.checked)">
              <label for="check_${a.id}" class="anti-duplicate-label">
                <span class="badge ${a.is_contacted ? 'badge-sent' : 'badge-todo'}">
                  ${a.is_contacted ? '✔ Inviato' : '⏳ Da inviare'}
                </span>
              </label>
            </div>
          `;

          const waBtn = isCell
            ? `<button class="btn-wa-action ${a.is_contacted ? 'already-sent' : ''}" onclick="openWhatsAppModal(${a.id})" title="${a.is_contacted ? 'Già inviato (clicca per conferma)' : 'Invia WhatsApp'}">
                 💬 ${a.is_contacted ? 'Riapri WA' : 'Invia WhatsApp'}
               </button>`
            : '<span style="color:#64748b; font-size:11px;">Solo fisso</span>';

          const emailBtn = a.email
            ? `<button class="btn-email-action ${a.is_contacted ? 'already-sent' : ''}" onclick="openEmailModal(${a.id})" title="${a.is_contacted ? 'Già inviato (clicca per conferma)' : 'Apri in Google Chrome'}">
                 🌐 ${a.is_contacted ? 'Riapri Email' : 'Email Chrome'}
               </button>`
            : '<span style="color:#64748b; font-size:11px;">No email</span>';

          tr.innerHTML = `
            <td>${spuntaHtml}</td>
            <td>
              <strong>${a.nome_attivita}</strong>
              ${a.sito_web ? `<div style="margin-top:2px;"><a href="${a.sito_web}" target="_blank" style="color:#38bdf8; font-size:11px; text-decoration:none;">${a.sito_web} ↗</a></div>` : ''}
            </td>
            <td>
              <div>${a.categoria}</div>
              <div style="font-size:11px; color:#94a3b8;">${a.citta}</div>
            </td>
            <td>
              <div>${a.telefono || '<span style="color:#64748b;">N/D</span>'}</div>
              <div style="margin-top:3px;">${telBadge}</div>
            </td>
            <td>
              ${a.email ? `<span style="color:#38bdf8; font-size:12px;">${a.email}</span>` : '<span style="color:#64748b;">-</span>'}
            </td>
            <td>${reviewsBadge}</td>
            <td>${supabaseBadge}</td>
            <td>
              <div class="row-actions">
                ${waBtn}
                ${emailBtn}
              </div>
            </td>
          `;
          tbody.appendChild(tr);
        }
      });
    }

    // =========================================================================
    // MODULO SCRAPING XPART (RICAMBI AUTO OEM)
    // =========================================================================
    async function startXpartScraping() {
      const marca = document.getElementById('xpartMarcaSelect').value;
      const modello = document.getElementById('xpartModelloInput').value.trim();
      const categoria = document.getElementById('xpartCategoriaSelect').value;
      const limit = parseInt(document.getElementById('xpartLimiteSelect').value, 10);

      document.getElementById('btnXpartSearch').style.display = 'none';
      document.getElementById('btnXpartStop').style.display = 'inline-flex';
      document.getElementById('xpartProgressPanel').style.display = 'flex';
      document.getElementById('xpartProgressStatus').textContent = `Scansione cataloghi OEM per ${marca} ${modello}...`;
      document.getElementById('xpartProgressCount').textContent = `0 / ${limit}`;
      document.getElementById('xpartProgressBarFill').style.width = '2%';

      if (window.pywebview && window.pywebview.api) {
        try {
          await window.pywebview.api.start_xpart_scraping(marca, modello, categoria, limit);
        } catch (err) {
          showToast("Errore avvio XPart: " + err);
          resetXpartButtons();
        }
      }
    }

    async function stopXpartScraping() {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.stop_xpart_scraping();
        showToast("Arresto scraping XPart inviato...");
      }
    }

    window.onXpartProgress = function(data) {
      if (!data) return;
      if (data.status_text) {
        document.getElementById('xpartProgressStatus').textContent = data.status_text;
      }

      const current = data.current_count || 0;
      const target = data.target_limit || 50;
      document.getElementById('xpartProgressCount').textContent = `${current} / ${target}`;

      const pct = Math.min(100, Math.round((current / target) * 100));
      document.getElementById('xpartProgressBarFill').style.width = `${Math.max(4, pct)}%`;

      if (data.record) {
        xpartData.unshift(data.record);
        updateXpartStats();
        renderXpartTable();
      }

      if (data.completed) {
        resetXpartButtons();
        showToast(`Scraping XPart completato: ${current} ricambi e codici OEM sincronizzati su Supabase!`);
      }
    };

    function resetXpartButtons() {
      document.getElementById('btnXpartSearch').style.display = 'inline-flex';
      document.getElementById('btnXpartStop').style.display = 'none';
      setTimeout(() => {
        document.getElementById('xpartProgressPanel').style.display = 'none';
      }, 4000);
    }

    function updateXpartStats() {
      const tot = xpartData.length;
      const oemSet = new Set(xpartData.map(x => x.codice_oem));
      const crossCount = xpartData.reduce((acc, x) => acc + ((x.cross_references && x.cross_references.length) ? 2 : 0), 0);

      document.getElementById('statXpartTotale').textContent = tot;
      document.getElementById('statXpartOem').textContent = oemSet.size;
      document.getElementById('statXpartCross').textContent = crossCount;
      document.getElementById('statXpartSupabase').textContent = tot;
    }

    function renderXpartTable() {
      const search = document.getElementById('xpartTableSearchInput').value.toLowerCase();
      const tbody = document.getElementById('xpartTableBody');
      tbody.innerHTML = '';

      xpartData.forEach(x => {
        const crossStr = Array.isArray(x.cross_references) ? x.cross_references.join(' | ') : (x.cross_references || '');
        const match = !search ||
          (x.codice_oem && x.codice_oem.toLowerCase().includes(search)) ||
          (x.nome_ricambio && x.nome_ricambio.toLowerCase().includes(search)) ||
          (x.marca_veicolo && x.marca_veicolo.toLowerCase().includes(search)) ||
          (x.modello_veicolo && x.modello_veicolo.toLowerCase().includes(search)) ||
          crossStr.toLowerCase().includes(search);

        if (match) {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong style="color: #38bdf8; font-family: monospace; font-size: 13px;">${x.codice_oem}</strong></td>
            <td>
              <div><strong>${x.nome_ricambio}</strong></div>
              <div style="font-size: 11px; color: var(--text-muted);">${x.categoria}</div>
            </td>
            <td>
              <div>${x.marca_veicolo} ${x.modello_veicolo}</div>
              <div style="font-size: 11px; color: #94a3b8;">${x.anno_compatibilita || '2012-2022'}</div>
            </td>
            <td style="font-size: 11.5px; color: #cbd5e1;">${x.motorizzazione || '-'}</td>
            <td style="font-size: 11px; color: #a855f7;">${crossStr || '-'}</td>
            <td><strong>${x.prezzo || 'N/D'}</strong></td>
            <td>
              <div>${x.scaffale || 'B-04-L2'}</div>
              <div style="font-size: 10px; color: #4ade80;">${x.condizione || 'GRADO A'}</div>
            </td>
            <td><span class="badge badge-supabase-ok">Sincronizzato</span></td>
          `;
          tbody.appendChild(tr);
        }
      });
    }

    async function openDataFolder() {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.open_data_folder();
      }
    }

    async function refreshData() {
      await loadInitialData();
      showToast("Dati aggiornati dall'archivio locale");
    }

    // Eventi di Inizializzazione WebView
    window.addEventListener('pywebviewready', () => {
      loadInitialData();
    });
    window.addEventListener('DOMContentLoaded', () => {
      setTimeout(loadInitialData, 300);
    });
  </script>
</body>
</html>
"""


class DesktopAppApi:
    """API Python esposta all'interfaccia grafica JavaScript."""

    def __init__(self):
        self.window = None
        self.scraper_thread = None
        self.xpart_thread = None
        self.stop_event = threading.Event()
        self.xpart_stop_event = threading.Event()
        self.active_driver = None

    def set_window(self, window):
        self.window = window

    def get_initial_data(self):
        """Carica i dati di CasaLavoroPRO, XPart e le impostazioni iniziali."""
        try:
            # 1. Carica artigiani
            raw_artisans = load_csv_data(FILE_ESTRATTI)
            registry = load_contacted_registry(FILE_REGISTRO)

            enriched = []
            for idx, a in enumerate(raw_artisans, start=1):
                tel = a.get("telefono_principale", "").strip()
                nome = a.get("nome_attivita", "").strip()
                em = a.get("email", "").strip()
                cat = a.get("categoria", "").strip()
                cit = a.get("citta", "").strip()
                sito = a.get("sito_web", "").strip()
                tipo = a.get("tipo_telefono", "").strip().lower()
                rating = a.get("rating_recensioni", "").strip()
                num_rec = a.get("numero_recensioni", "").strip()
                rec_estr = a.get("recensioni_estratte", "").strip()

                wa_key = f"WHATSAPP:{tel}"
                wa_contacted = wa_key in registry or f"WHATSAPP:name:{nome.lower()}" in registry
                wa_date = registry.get(wa_key, {}).get("data_ora", "")

                em_key = f"EMAIL:{em.lower()}"
                em_contacted = bool(em and (em_key in registry or f"EMAIL:name:{nome.lower()}" in registry))

                # Spunta generale anti-doppio invio
                manual_key = f"MANUALE:{tel}" if tel else ""
                manual_em = f"MANUALE:{em.lower()}" if em else ""
                manual_name = f"MANUALE:name:{nome.lower()}" if nome else ""

                is_contacted = bool(
                    wa_contacted or
                    em_contacted or
                    (manual_key and manual_key in registry) or
                    (manual_em and manual_em in registry) or
                    (manual_name and manual_name in registry)
                )

                enriched.append({
                    "id": idx,
                    "nome_attivita": nome,
                    "categoria": cat,
                    "citta": cit,
                    "telefono": tel,
                    "tipo_telefono": tipo,
                    "email": em,
                    "sito_web": sito,
                    "rating_recensioni": rating,
                    "numero_recensioni": num_rec,
                    "recensioni_estratte": rec_estr,
                    "is_contacted": is_contacted,
                    "wa_contacted": wa_contacted,
                    "wa_date": wa_date,
                    "em_contacted": em_contacted
                })

            # 2. Carica ricambi XPart
            raw_xpart = load_csv_data(FILE_XPART_CSV)

            # 3. Impostazioni correnti (con dati utente fissi)
            settings_payload = {
                "sender_name": SENDER_NAME,
                "sender_phone": SENDER_PHONE,
                "sender_email": SENDER_EMAIL,
                "logo_url": LOGO_URL,
                "logo_preview_data": self._build_logo_preview_data(LOGO_URL),
                "foto_allegate": FOTO_ALLEGATE,
                "supabase_url": SUPABASE_URL,
                "supabase_key": SUPABASE_KEY,
                "supabase_table_bozze": SUPABASE_TABLE_BOZZE,
                "supabase_table_xpart": SUPABASE_TABLE_XPART
            }

            return {
                "artisans": enriched,
                "xpart_parts": raw_xpart,
                "settings": settings_payload,
                "regions": get_all_regions(),
                "geo_database": ITALIA_GEO_DATABASE
            }
        except Exception as e:
            print(f"[!] Errore get_initial_data: {e}")
            return {
                "artisans": [],
                "xpart_parts": [],
                "settings": {},
                "regions": get_all_regions(),
                "geo_database": ITALIA_GEO_DATABASE
            }

    # =========================================================================
    # METODI CASALAVOROPRO (SCRAPING GOOGLE MAPS & BOZZE SUPABASE)
    # =========================================================================
    def start_scraping(self, categoria: str, regione: str, zona: str, limit: int, deep_scrape: bool):
        """Avvia la scansione Google Maps multi-zona in thread dedicato."""
        if self.scraper_thread and self.scraper_thread.is_alive():
            return {"status": "already_running"}

        self.stop_event.clear()
        locations = resolve_search_locations(regione, zona)

        def worker():
            driver = None
            try:
                self.notify_gui_clp(status_text=f"Inizializzazione browser Stealth per '{categoria}' ({len(locations)} zone)...")
                driver = setup_selenium_driver(headless=True)
                self.active_driver = driver

                def on_progress(record, current_count, target_limit, status_msg):
                    self.notify_gui_clp(
                        record=record,
                        current_count=current_count,
                        target_limit=target_limit,
                        status_text=status_msg
                    )

                total_found = scrape_google_maps_multi_zone(
                    driver=driver,
                    categoria=categoria,
                    locations=locations,
                    target_limit=limit,
                    deep_scrape=deep_scrape,
                    progress_callback=on_progress,
                    stop_event=self.stop_event
                )

                self.notify_gui_clp(
                    completed=True,
                    current_count=total_found,
                    target_limit=limit,
                    status_text=f"Completato: {total_found} contatti estratti e sincronizzati su Supabase!"
                )
            except Exception as e:
                self.notify_gui_clp(completed=True, status_text=f"Errore: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                self.active_driver = None

        self.scraper_thread = threading.Thread(target=worker, daemon=True)
        self.scraper_thread.start()
        return {"status": "started"}

    def stop_scraping(self):
        """Arresta lo scraper di CasaLavoroPRO."""
        self.stop_event.set()
        if self.active_driver:
            try:
                self.active_driver.quit()
            except Exception:
                pass
        return {"status": "stopped"}

    # =========================================================================
    # METODI XPART (SCRAPING OEM RICAMBI AUTO)
    # =========================================================================
    def start_xpart_scraping(self, marca: str, modello: str, categoria: str, limit: int):
        """Avvia lo scraping di codici OEM per XPart."""
        if self.xpart_thread and self.xpart_thread.is_alive():
            return {"status": "already_running"}

        self.xpart_stop_event.clear()

        def xpart_worker():
            try:
                self.notify_gui_xpart(status_text=f"Inizializzazione sessione stealth XPart per {marca} {modello}...")

                def on_xpart_progress(record, current_count, target_limit, status_msg):
                    self.notify_gui_xpart(
                        record=record,
                        current_count=current_count,
                        target_limit=target_limit,
                        status_text=status_msg
                    )

                total_parts = scrape_xpart_oem_catalog(
                    marca=marca,
                    modello=modello,
                    categoria=categoria,
                    target_limit=limit,
                    progress_callback=on_xpart_progress,
                    stop_event=self.xpart_stop_event
                )

                self.notify_gui_xpart(
                    completed=True,
                    current_count=total_parts,
                    target_limit=limit,
                    status_text=f"Completato: {total_parts} ricambi OEM sincronizzati su Supabase!"
                )
            except Exception as e:
                self.notify_gui_xpart(completed=True, status_text=f"Errore XPart: {e}")

        self.xpart_thread = threading.Thread(target=xpart_worker, daemon=True)
        self.xpart_thread.start()
        return {"status": "started"}

    def stop_xpart_scraping(self):
        """Arresta lo scraper di XPart."""
        self.xpart_stop_event.set()
        return {"status": "stopped"}

    # =========================================================================
    # OUTREACH INTERATTIVO CONTROLLATO & GOOGLE CHROME EMAIL
    # =========================================================================
    def send_custom_whatsapp(self, phone: str, message: str, artisan_name: str) -> bool:
        """Apre l'app desktop di WhatsApp con il messaggio personalizzato dall'utente."""
        try:
            return open_whatsapp_custom(phone=phone, message=message, artisan_name=artisan_name)
        except Exception as e:
            print(f"[!] Errore apertura WhatsApp personalizzato: {e}")
            return False

    def open_gmail_chrome(self, email: str, subject: str, body: str, artisan_name: str) -> bool:
        """Apre direttamente Google Chrome con la bozza Gmail precompilata."""
        try:
            return open_gmail_in_chrome(to_email=email, subject=subject, body=body, artisan_name=artisan_name)
        except Exception as e:
            print(f"[!] Errore apertura Google Chrome per Email: {e}")
            return False

    def open_custom_email(self, email: str, subject: str, body: str, artisan_name: str) -> bool:
        """Apre il client di posta predefinito di sistema."""
        try:
            return open_email_custom(email=email, subject=subject, body=body, artisan_name=artisan_name)
        except Exception as e:
            print(f"[!] Errore apertura mailto client: {e}")
            return False

    def toggle_contact_check(self, nome_attivita: str, destinatario: str, is_checked: bool) -> bool:
        """Attiva o disattiva la spunta anti-doppio invio nel registro."""
        try:
            return toggle_contacted_status(FILE_REGISTRO, nome_attivita=nome_attivita, destinatario=destinatario, is_contacted=is_checked)
        except Exception as e:
            print(f"[!] Errore toggle spunta anti-doppio invio: {e}")
            return False

    def send_custom_email_smtp(self, email: str, name: str, subject: str, body: str) -> dict:
        """Invia direttamente via SMTP l'email personalizzata se configurato."""
        try:
            return send_single_email_smtp(
                recipient_email=email,
                recipient_name=name,
                subject=subject,
                body_text=body,
                logo_url=LOGO_URL
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_sandbox_test_email(self, test_email: str, subject: str, body: str) -> dict:
        """
        Spazio Test Email (Sandbox isolata):
        Invia una email di prova direttamente via SMTP se configurato, oppure apre
        la bozza in Google Chrome. NON scrive nel registro anti-doppio invio e NON tocca Supabase.
        """
        target_email = (test_email or "").strip()
        if not target_email or "@" not in target_email:
            return {"success": False, "error": "Indirizzo email di prova non valido."}

        smtp_host = os.getenv("SMTP_HOST", SMTP_HOST).strip()
        smtp_port = int(os.getenv("SMTP_PORT", str(SMTP_PORT or 587)))
        smtp_user = os.getenv("SMTP_USER", SMTP_USER).strip()
        smtp_pass = os.getenv("SMTP_PASS", SMTP_PASS).strip()
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
        smtp_use_ssl = os.getenv("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")

        # 1. Invio diretto via SMTP se configurato
        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject or "Test CasaLavoroPRO"
                msg["From"] = "CasaLavoroPRO <info@casalavoropro.com>"
                msg["Reply-To"] = "info@casalavoropro.com"
                msg["To"] = target_email

                msg.attach(MIMEText(body, "plain", "utf-8"))
                html_body = body.replace("\n", "<br>")
                html_content = (
                    '<html><body><div style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">'
                    f"{html_body}</div></body></html>"
                )
                msg.attach(MIMEText(html_content, "html", "utf-8"))

                if smtp_use_ssl:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
                else:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                    if smtp_use_tls:
                        server.starttls()

                server.login(smtp_user, smtp_pass)
                server.sendmail("info@casalavoropro.com", [target_email], msg.as_string())
                server.quit()
                return {"success": True, "mode": "smtp"}
            except Exception as e:
                print(f"[!] Errore invio SMTP Sandbox ({e}), fallback su Google Chrome...")

        # 2. Altrimenti apre bozza precompilata in Google Chrome (senza loggare nel registro contatti)
        try:
            gmail_url = (
                f"https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={quote(target_email)}&su={quote(subject)}&body={quote(body)}"
            )
            chrome_candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")
            ]
            opened = False
            for cp in chrome_candidates:
                if os.path.exists(cp):
                    try:
                        subprocess.Popen([cp, gmail_url])
                        opened = True
                        break
                    except Exception:
                        pass
            if not opened:
                webbrowser.open(gmail_url)
            return {"success": True, "mode": "chrome"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SALVATAGGIO IMPOSTAZIONI & UTILITY
    # =========================================================================
    def _build_logo_preview_data(self, logo_value: str) -> str:
        """Converte un eventuale percorso file locale del logo in data URI per l'anteprima WebView."""
        val = (logo_value or "").strip()
        if not val or val.startswith(("http://", "https://", "data:")):
            return ""
        candidate = Path(val)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        try:
            if candidate.is_file():
                mime, _ = mimetypes.guess_type(str(candidate))
                mime = mime or "image/png"
                encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
                return f"data:{mime};base64,{encoded}"
        except Exception as e:
            print(f"[!] Avviso lettura anteprima logo locale: {e}")
        return ""

    def _persist_env_settings(self):
        """Scrive le impostazioni correnti nel file .env locale."""
        env_path = BASE_DIR / ".env"
        env_lines = [
            f'PLATFORM_NAME="{PLATFORM_NAME}"',
            f'PLATFORM_URL="{PLATFORM_URL}"',
            f'SENDER_NAME="{SENDER_NAME}"',
            f'SENDER_PHONE="{SENDER_PHONE}"',
            f'SENDER_EMAIL="{SENDER_EMAIL}"',
            f'LOGO_URL="{LOGO_URL}"',
            f'FOTO_ALLEGATE="{FOTO_ALLEGATE}"',
            f'SUPABASE_URL="{SUPABASE_URL}"',
            f'SUPABASE_KEY="{SUPABASE_KEY}"',
            f'SUPABASE_TABLE_BOZZE="{SUPABASE_TABLE_BOZZE}"',
            f'SUPABASE_TABLE_XPART="{SUPABASE_TABLE_XPART}"',
            f'FILE_ESTRATTI="artigiani_estratti.csv"',
            f'FILE_REGISTRO="registro_contattati.csv"'
        ]
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines) + "\n")

    def upload_brand_logo(self, filename: str, data_url: str) -> dict:
        """Salva un'immagine logo/foto caricata dal PC nella cartella locale assets/."""
        global LOGO_URL
        try:
            if not data_url or "," not in data_url:
                return {"success": False, "error": "Formato immagine non valido"}

            header, b64_data = data_url.split(",", 1)
            raw_bytes = base64.b64decode(b64_data)

            assets_dir = BASE_DIR / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            orig_name = Path(filename or "brand_logo.png").name
            stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", Path(orig_name).stem).strip("_") or "brand_logo"
            ext = Path(orig_name).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
                if "jpeg" in header or "jpg" in header:
                    ext = ".jpg"
                elif "webp" in header:
                    ext = ".webp"
                elif "svg" in header:
                    ext = ".svg"
                elif "gif" in header:
                    ext = ".gif"
                else:
                    ext = ".png"

            safe_filename = f"{stem}{ext}"
            target_path = assets_dir / safe_filename
            with open(target_path, "wb") as f:
                f.write(raw_bytes)

            rel_path = f"assets/{safe_filename}"
            LOGO_URL = rel_path
            os.environ["LOGO_URL"] = LOGO_URL
            app_config.LOGO_URL = LOGO_URL
            self._persist_env_settings()

            return {
                "success": True,
                "path": rel_path,
                "abs_path": str(target_path),
                "preview_data": data_url
            }
        except Exception as e:
            print(f"[!] Errore upload logo locale: {e}")
            return {"success": False, "error": str(e)}

    def save_settings(self, settings_dict: dict) -> bool:
        """Aggiorna le impostazioni in memoria e nel file .env."""
        global SENDER_NAME, SENDER_PHONE, SENDER_EMAIL, LOGO_URL, FOTO_ALLEGATE
        global SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE_BOZZE, SUPABASE_TABLE_XPART

        try:
            SENDER_NAME = settings_dict.get("sender_name", SENDER_NAME)
            SENDER_PHONE = settings_dict.get("sender_phone", SENDER_PHONE)
            SENDER_EMAIL = settings_dict.get("sender_email", SENDER_EMAIL)
            LOGO_URL = settings_dict.get("logo_url", LOGO_URL)
            FOTO_ALLEGATE = settings_dict.get("foto_allegate", FOTO_ALLEGATE)
            SUPABASE_URL = settings_dict.get("supabase_url", SUPABASE_URL)
            SUPABASE_KEY = settings_dict.get("supabase_key", SUPABASE_KEY)
            SUPABASE_TABLE_BOZZE = settings_dict.get("supabase_table_bozze", SUPABASE_TABLE_BOZZE)
            SUPABASE_TABLE_XPART = settings_dict.get("supabase_table_xpart", SUPABASE_TABLE_XPART)

            os.environ["LOGO_URL"] = LOGO_URL
            app_config.LOGO_URL = LOGO_URL

            update_supabase_credentials(SUPABASE_URL, SUPABASE_KEY)
            self._persist_env_settings()

            return True
        except Exception as e:
            print(f"[!] Errore salvataggio impostazioni: {e}")
            return False

    def open_data_folder(self):
        """Apre la cartella dei file CSV in Windows Explorer."""
        try:
            os.startfile(str(BASE_DIR))
            return True
        except Exception as e:
            print(f"[!] Errore apertura cartella: {e}")
            return False

    def notify_gui_clp(self, record=None, current_count=0, target_limit=100, status_text="", completed=False):
        """Invia eventi streaming JavaScript per CasaLavoroPRO."""
        if not self.window:
            return
        payload = {
            "record": record,
            "current_count": current_count,
            "target_limit": target_limit,
            "status_text": status_text,
            "completed": completed
        }
        js_cmd = f"if (window.onScraperProgress) {{ window.onScraperProgress({json.dumps(payload, ensure_ascii=False)}); }}"
        try:
            self.window.evaluate_js(js_cmd)
        except Exception:
            pass

    def notify_gui_xpart(self, record=None, current_count=0, target_limit=50, status_text="", completed=False):
        """Invia eventi streaming JavaScript per XPart."""
        if not self.window:
            return
        payload = {
            "record": record,
            "current_count": current_count,
            "target_limit": target_limit,
            "status_text": status_text,
            "completed": completed
        }
        js_cmd = f"if (window.onXpartProgress) {{ window.onXpartProgress({json.dumps(payload, ensure_ascii=False)}); }}"
        try:
            self.window.evaluate_js(js_cmd)
        except Exception:
            pass

    def cleanup(self):
        """Termina i thread e chiude il browser attivo."""
        self.stop_event.set()
        self.xpart_stop_event.set()
        if self.active_driver:
            try:
                self.active_driver.quit()
            except Exception:
                pass


def run_pywebview_gui():
    """Avvia la finestra desktop con Edge Chromium."""
    import webview

    api = DesktopAppApi()
    window = webview.create_window(
        title="CasaLavoroPRO & XPart — Lead Generation, Bozze Supabase & Outreach Suite",
        html=GUI_HTML_CONTENT,
        js_api=api,
        width=1320,
        height=850,
        min_size=(1024, 650),
        background_color="#0b0f19"
    )
    api.set_window(window)
    window.events.closing += api.cleanup
    webview.start(gui="edgechromium")


def main():
    try:
        run_pywebview_gui()
    except Exception as e:
        print(f"[!] Errore avvio webview: {e}")
        from outreach import serve_dashboard
        serve_dashboard()


if __name__ == "__main__":
    main()

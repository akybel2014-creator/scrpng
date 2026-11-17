#!/usr/bin/env python3
"""
MODULO 2: DISPATCHER OUTREACH WHATSAPP ED EMAIL - CasaLavoroPRO
==============================================================
Gestisce il flusso di outreach verso gli artigiani estratti:
1. Genera una Dashboard HTML locale interattiva per WhatsApp click-to-chat (wa.me)
   con messaggio precompilato strategico e pulsante verde.
2. Traccia automaticamente ogni click e segna il contatto nel 'registro_contattati.csv'.
3. Invia email B2B personalizzate via SMTP ai contatti dotati di indirizzo email valido,
   con supporto Dry-Run, anteprima e pause casuali tra gli invii.
"""

import os
import csv
import sys
import json
import time
import random
import smtplib
import argparse
import webbrowser
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote, urlparse, parse_qs

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    FILE_ESTRATTI,
    FILE_REGISTRO,
    FILE_DASHBOARD,
    PLATFORM_NAME,
    PLATFORM_URL,
    SENDER_NAME,
    SENDER_EMAIL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_USE_TLS,
    SMTP_USE_SSL,
    WHATSAPP_MESSAGE_TEMPLATE,
    EMAIL_SUBJECT_TEMPLATE,
    EMAIL_TEXT_TEMPLATE,
    MIN_DELAY_SECONDS,
    MAX_DELAY_SECONDS
)

REGISTRO_FIELDNAMES = [
    "id",
    "nome_attivita",
    "canale",
    "destinatario",
    "data_ora",
    "stato",
    "note"
]


def load_csv_data(filepath) -> list[dict]:
    """Carica i dati dal file CSV degli artigiani estratti."""
    if not os.path.exists(filepath):
        return []
    rows = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    except Exception as e:
        print(f"[!] Errore lettura {filepath}: {e}")
    return rows


def load_contacted_registry(filepath) -> dict:
    """
    Carica il registro dei contatti già inviati.
    Ritorna un dizionario con chiavi univoche (destinatario/nome).
    """
    contacted = {}
    if not os.path.exists(filepath):
        return contacted
        
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                dest = r.get("destinatario", "").strip()
                name = r.get("nome_attivita", "").strip().lower()
                canale = r.get("canale", "").strip().upper()
                stato = r.get("stato", "").strip()
                
                if dest:
                    contacted[f"{canale}:{dest}"] = r
                if name:
                    contacted[f"{canale}:name:{name}"] = r
    except Exception as e:
        print(f"[!] Avviso lettura registro: {e}")
    return contacted


def log_contact_action(filepath, nome_attivita: str, canale: str, destinatario: str, stato: str = "INVIATO", note: str = ""):
    """Registra l'azione di contatto nel file CSV di storico."""
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(filepath, mode="a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRO_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "id": f"{int(time.time())}-{random.randint(100, 999)}",
            "nome_attivita": nome_attivita,
            "canale": canale.upper(),
            "destinatario": destinatario,
            "data_ora": now_str,
            "stato": stato,
            "note": note
        })

    # Aggiorna anche stato bozza su Supabase se configurato
    try:
        from supabase_client import update_artisan_draft_status
        update_artisan_draft_status(destinatario or nome_attivita, f"contattato_{canale.lower()}", note)
    except Exception:
        pass


def open_whatsapp_custom(phone: str, message: str, artisan_name: str = "") -> bool:
    """
    Apre l'app desktop di WhatsApp o WhatsApp Web con il messaggio personalizzato dall'utente.
    Registra l'azione nel file storico e aggiorna lo stato su Supabase.
    """
    if not phone:
        return False
        
    cifre = "".join(filter(str.isdigit, phone))
    if cifre.startswith("0039"):
        cifre = cifre[4:]
    elif cifre.startswith("39") and len(cifre) >= 11:
        cifre = cifre[2:]
        
    full_digits = f"39{cifre}"
    encoded_text = quote(message)
    wa_app_url = f"whatsapp://send?phone={full_digits}&text={encoded_text}"
    wa_web_url = f"https://wa.me/{full_digits}?text={encoded_text}"
    
    opened = False
    try:
        os.startfile(wa_app_url)
        opened = True
    except Exception:
        try:
            webbrowser.open(wa_web_url)
            opened = True
        except Exception as e:
            print(f"[!] Errore apertura WhatsApp: {e}")
            
    if opened:
        log_contact_action(FILE_REGISTRO, artisan_name or phone, "WHATSAPP", phone, stato="INVIATO", note="Inviato via WhatsApp Desktop con messaggio personalizzato")
        
    return opened


def open_email_custom(email: str, subject: str, body: str, artisan_name: str = "") -> bool:
    """
    Apre il client di posta predefinito del sistema (es. Outlook, Thunderbird, o client web)
    precompilando destinatario, oggetto e corpo del messaggio personalizzato.
    """
    if not email:
        return False

    encoded_subject = quote(subject)
    encoded_body = quote(body)
    mailto_url = f"mailto:{email}?subject={encoded_subject}&body={encoded_body}"

    opened = False
    try:
        os.startfile(mailto_url)
        opened = True
    except Exception:
        try:
            webbrowser.open(mailto_url)
            opened = True
        except Exception as e:
            print(f"[!] Errore apertura client mail: {e}")

    if opened:
        log_contact_action(FILE_REGISTRO, artisan_name or email, "EMAIL", email, stato="INVIATO", note="Aperto client email predefinito")

    return opened


def open_gmail_in_chrome(to_email: str, subject: str, body: str, artisan_name: str = "") -> bool:
    """
    Apre direttamente Google Chrome con la bozza di invio Gmail precompilata
    (destinatario, oggetto, corpo del testo), pronta per l'aggiunta manuale di logo e foto.
    Registra l'azione nel registro_contattati.csv per attivare la spunta anti-doppio invio.
    """
    if not to_email:
        return False

    encoded_subject = quote(subject)
    encoded_body = quote(body)
    # URL di composizione diretta di Gmail con destinatario, oggetto e corpo
    gmail_compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(to_email)}&su={encoded_subject}&body={encoded_body}"

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
                subprocess.Popen([cp, gmail_compose_url])
                opened = True
                break
            except Exception as e:
                print(f"[!] Errore lancio Chrome ({cp}): {e}")

    if not opened:
        # Fallback su webbrowser di sistema
        try:
            webbrowser.open(gmail_compose_url)
            opened = True
        except Exception as e:
            print(f"[!] Fallback browser error: {e}")

    if opened:
        log_contact_action(FILE_REGISTRO, artisan_name or to_email, "EMAIL", to_email, stato="INVIATO", note="Aperta bozza in Google Chrome")

    return opened


def toggle_contacted_status(filepath, nome_attivita: str, destinatario: str, is_contacted: bool) -> bool:
    """
    Aggiorna lo stato della spunta di controllo anti-doppio invio per un contatto.
    Se is_contacted è True, registra l'invio; se False, revoca la spunta nel registro.
    """
    if is_contacted:
        log_contact_action(filepath, nome_attivita or destinatario, "MANUALE", destinatario, stato="INVIATO", note="Spunta anti-doppio invio attivata")
        return True
    else:
        if not os.path.exists(filepath):
            return True
        try:
            rows = []
            with open(filepath, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or REGISTRO_FIELDNAMES
                for r in reader:
                    r_dest = r.get("destinatario", "").strip()
                    r_name = r.get("nome_attivita", "").strip().lower()
                    if (destinatario and r_dest == destinatario) or (nome_attivita and r_name == nome_attivita.lower()):
                        continue
                    rows.append(r)
            with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            return True
        except Exception as e:
            print(f"[!] Errore rimozione spunta da registro: {e}")
            return False



def send_single_email_smtp(recipient_email: str, recipient_name: str, subject: str, body_text: str, logo_url: str = "") -> dict:
    """Invia una singola email direttamente tramite server SMTP con verifica credenziali."""
    from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_USE_TLS, SMTP_USE_SSL, SENDER_EMAIL, SENDER_NAME
    
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return {"success": False, "error": "Credenziali SMTP non configurate in .env"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = f"{recipient_name} <{recipient_email}>"

        # Testo semplice
        part1 = MIMEText(body_text, "plain", "utf-8")
        msg.attach(part1)

        # HTML con logo se specificato
        html_body = body_text.replace("\n", "<br>")
        if logo_url:
            html_content = f"""<html><body>
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="margin-bottom: 20px;"><img src="{logo_url}" alt="Logo" style="max-height: 50px;"/></div>
                <div>{html_body}</div>
            </div></body></html>"""
        else:
            html_content = f"""<html><body><div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">{html_body}</div></body></html>"""
        
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part2)

        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=12)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12)
            if SMTP_USE_TLS:
                server.starttls()

        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SENDER_EMAIL, [recipient_email], msg.as_string())
        server.quit()

        log_contact_action(FILE_REGISTRO, recipient_name, "EMAIL", recipient_email, stato="INVIATO", note="Inviata via SMTP")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}



def open_whatsapp_for_artisan(record: dict) -> bool:
    """
    Apre direttamente l'app desktop di WhatsApp o la chat web con il messaggio precompilato,
    e registra l'azione nel registro_contattati.csv.
    """
    tel = record.get("telefono_principale", "") or record.get("telefono", "")
    tipo = record.get("tipo_telefono", "").lower()
    nome = record.get("nome_attivita", "Professionista")
    cat = record.get("categoria", "artigiano")
    cit = record.get("citta", "la tua zona")
    
    if not tel:
        return False
        
    cifre = "".join(filter(str.isdigit, tel))
    if cifre.startswith("0039"):
        cifre = cifre[4:]
    elif cifre.startswith("39") and len(cifre) >= 11:
        cifre = cifre[2:]
        
    full_digits = f"39{cifre}"
    
    msg = WHATSAPP_MESSAGE_TEMPLATE.format(
        nome_attivita=nome,
        sender_name=SENDER_NAME,
        categoria=cat,
        citta=cit,
        platform_name=PLATFORM_NAME,
        platform_url=PLATFORM_URL
    )
    
    encoded_text = quote(msg)
    wa_app_url = f"whatsapp://send?phone={full_digits}&text={encoded_text}"
    wa_web_url = f"https://wa.me/{full_digits}?text={encoded_text}"
    
    opened = False
    # 1. Prova prima con il protocollo nativo dell'app desktop WhatsApp
    try:
        os.startfile(wa_app_url)
        opened = True
    except Exception:
        # 2. Fallback sul browser / WhatsApp Web
        try:
            webbrowser.open(wa_web_url)
            opened = True
        except Exception as e:
            print(f"[!] Errore apertura WhatsApp: {e}")
            
    if opened:
        log_contact_action(FILE_REGISTRO, nome, "WHATSAPP", tel, stato="INVIATO", note="Aperta chat WhatsApp da app desktop")
        
    return opened


def build_whatsapp_url(record: dict) -> str:
    """Compone il link wa.me con il messaggio strategico precompilato."""
    telefono = record.get("telefono_principale", "")
    tipo = record.get("tipo_telefono", "").lower()
    
    if tipo != "cellulare" or not telefono:
        return ""
        
    # Estrai solo cifre per il link wa.me
    cifre = "".join(filter(str.isdigit, telefono))
    if not cifre.startswith("39") and len(cifre) == 10:
        cifre = f"39{cifre}"
        
    nome = record.get("nome_attivita", "Professionista")
    cat = record.get("categoria", "artigiano")
    cit = record.get("citta", "la tua zona")
    
    msg = WHATSAPP_MESSAGE_TEMPLATE.format(
        nome_attivita=nome,
        sender_name=SENDER_NAME,
        categoria=cat,
        citta=cit,
        platform_name=PLATFORM_NAME,
        platform_url=PLATFORM_URL
    )
    
    encoded_text = quote(msg)
    return f"https://wa.me/{cifre}?text={encoded_text}"


def generate_dashboard_html() -> str:
    """Genera la dashboard HTML locale per l'invio rapido WhatsApp ed Email."""
    artigiani = load_csv_data(FILE_ESTRATTI)
    registro = load_contacted_registry(FILE_REGISTRO)
    
    tot_estratti = len(artigiani)
    tot_cellulari = sum(1 for a in artigiani if a.get("tipo_telefono", "").lower() == "cellulare")
    tot_fissi = sum(1 for a in artigiani if a.get("tipo_telefono", "").lower() == "fisso")
    tot_email = sum(1 for a in artigiani if a.get("email", "").strip())
    
    # Arricchisci gli artigiani con stato e link
    enriched = []
    for idx, a in enumerate(artigiani, start=1):
        tel = a.get("telefono_principale", "").strip()
        tipo = a.get("tipo_telefono", "").strip().lower()
        nome = a.get("nome_attivita", "").strip()
        em = a.get("email", "").strip()
        cat = a.get("categoria", "").strip()
        cit = a.get("citta", "").strip()
        sito = a.get("sito_web", "").strip()
        
        wa_url = build_whatsapp_url(a)
        
        # Verifica se già contattato via WhatsApp
        wa_key = f"WHATSAPP:{tel}"
        wa_contacted = wa_key in registro or f"WHATSAPP:name:{nome.lower()}" in registro
        wa_date = registro.get(wa_key, {}).get("data_ora", "")
        
        # Verifica se già contattato via Email
        em_key = f"EMAIL:{em.lower()}"
        em_contacted = bool(em and (em_key in registro or f"EMAIL:name:{nome.lower()}" in registro))
        em_date = registro.get(em_key, {}).get("data_ora", "")
        
        enriched.append({
            "id": idx,
            "nome_attivita": nome,
            "categoria": cat,
            "citta": cit,
            "telefono": tel,
            "tipo_telefono": tipo,
            "email": em,
            "sito_web": sito,
            "whatsapp_url": wa_url,
            "wa_contacted": wa_contacted,
            "wa_date": wa_date,
            "em_contacted": em_contacted,
            "em_date": em_date
        })

    tot_wa_inviati = sum(1 for x in enriched if x["wa_contacted"])
    tot_em_inviati = sum(1 for x in enriched if x["em_contacted"])
    tot_da_contattare = sum(1 for x in enriched if not x["wa_contacted"] and x["tipo_telefono"] == "cellulare")

    # Inietta i dati JSON nella dashboard
    json_data = json.dumps(enriched, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard Outreach Artigiani — {PLATFORM_NAME}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --border-color: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary-orange: #ea580c;
      --primary-orange-hover: #c2410c;
      --whatsapp-green: #22c55e;
      --whatsapp-green-hover: #16a34a;
      --blue-accent: #3b82f6;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    /* Header */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 28px;
    }}
    .logo-container {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo-badge {{
      background: linear-gradient(135deg, #ea580c, #f97316);
      color: white;
      font-weight: 800;
      font-size: 20px;
      padding: 8px 14px;
      border-radius: 10px;
      box-shadow: 0 4px 14px rgba(234, 88, 12, 0.4);
    }}
    .logo-title h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}
    .logo-title p {{
      color: var(--text-muted);
      font-size: 13px;
    }}
    .header-actions {{
      display: flex;
      gap: 12px;
    }}
    .btn {{
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: none;
      transition: all 0.2s;
    }}
    .btn-secondary {{
      background-color: #334155;
      color: white;
    }}
    .btn-secondary:hover {{
      background-color: #475569;
    }}
    /* Stat Cards */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
    }}
    .stat-label {{
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }}
    .stat-value {{
      font-size: 28px;
      font-weight: 800;
    }}
    .val-orange {{ color: #f97316; }}
    .val-green {{ color: #22c55e; }}
    .val-blue {{ color: #38bdf8; }}
    .val-purple {{ color: #c084fc; }}
    /* Filter Bar */
    .filter-panel {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
    }}
    .filter-group {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .search-input {{
      background-color: #0f172a;
      border: 1px solid var(--border-color);
      color: white;
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 14px;
      min-width: 260px;
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--primary-orange);
    }}
    .select-filter {{
      background-color: #0f172a;
      border: 1px solid var(--border-color);
      color: white;
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
    }}
    /* Table */
    .table-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background-color: #172033;
      color: var(--text-muted);
      padding: 14px 18px;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.8px;
      border-bottom: 1px solid var(--border-color);
    }}
    td {{
      padding: 14px 18px;
      border-bottom: 1px solid #293548;
      vertical-align: middle;
    }}
    tr:hover td {{
      background-color: #243044;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-mobile {{
      background-color: rgba(34, 197, 94, 0.15);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }}
    .badge-fixed {{
      background-color: rgba(148, 163, 184, 0.15);
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.3);
    }}
    .badge-status-sent {{
      background-color: rgba(34, 197, 94, 0.2);
      color: #22c55e;
      border: 1px solid #22c55e;
    }}
    .badge-status-todo {{
      background-color: rgba(249, 115, 22, 0.15);
      color: #fb923c;
      border: 1px solid rgba(249, 115, 22, 0.4);
    }}
    .btn-wa {{
      background-color: var(--whatsapp-green);
      color: white;
      font-weight: 700;
      padding: 8px 14px;
      border-radius: 8px;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      transition: all 0.2s;
      box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
    }}
    .btn-wa:hover {{
      background-color: var(--whatsapp-green-hover);
      transform: translateY(-1px);
    }}
    .btn-wa.sent {{
      background-color: #334155;
      color: #94a3b8;
      box-shadow: none;
      cursor: default;
    }}
    .btn-email {{
      background-color: #2563eb;
      color: white;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 6px;
      text-decoration: none;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .btn-email:hover {{
      background-color: #1d4ed8;
    }}
    .website-link {{
      color: #38bdf8;
      text-decoration: none;
      font-size: 12px;
    }}
    .website-link:hover {{
      text-decoration: underline;
    }}
    .actions-cell {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .mark-btn {{
      background: transparent;
      border: 1px solid #475569;
      color: #cbd5e1;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
    }}
    .mark-btn:hover {{
      background: #334155;
      color: white;
    }}
    /* Notification Toast */
    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      border: 1px solid var(--whatsapp-green);
      color: white;
      padding: 12px 20px;
      border-radius: 10px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      font-size: 14px;
      font-weight: 600;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
      z-index: 1000;
    }}
    #toast.show {{
      opacity: 1;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-container">
        <div class="logo-badge">CLP</div>
        <div class="logo-title">
          <h1>{PLATFORM_NAME} — Outreach Console</h1>
          <p>Dispatcher autonomo WhatsApp Click-to-Chat & Email B2B</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" onclick="exportUpdatedCSV()">Scarica Registro Aggiornato</button>
        <button class="btn btn-secondary" onclick="window.location.reload()">Ricarica Dati</button>
      </div>
    </header>

    <!-- Statistiche Superiori -->
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">Artigiani Estratti</span>
        <span class="stat-value" id="stat-totale">{tot_estratti}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Cellulari (WhatsApp)</span>
        <span class="stat-value val-green" id="stat-cellulari">{tot_cellulari}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Email Trovate</span>
        <span class="stat-value val-blue" id="stat-email">{tot_email}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">WhatsApp Inviati</span>
        <span class="stat-value val-purple" id="stat-wa-inviati">{tot_wa_inviati}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Da Contattare</span>
        <span class="stat-value val-orange" id="stat-da-contattare">{tot_da_contattare}</span>
      </div>
    </div>

    <!-- Filtri e Ricerca -->
    <div class="filter-panel">
      <div class="filter-group">
        <input type="text" id="searchInput" class="search-input" placeholder="Cerca attività, categoria o città..." oninput="filterTable()">
        <select id="categoryFilter" class="select-filter" onchange="filterTable()">
          <option value="">Tutte le categorie</option>
        </select>
        <select id="cityFilter" class="select-filter" onchange="filterTable()">
          <option value="">Tutte le città</option>
        </select>
        <select id="statusFilter" class="select-filter" onchange="filterTable()">
          <option value="all">Tutti i contatti</option>
          <option value="todo" selected>Da Contattare (WhatsApp)</option>
          <option value="sent">Già Contattati (WhatsApp)</option>
          <option value="has_email">Con Email B2B</option>
        </select>
      </div>
      <div style="font-size: 13px; color: var(--text-muted);">
        Mostrati: <strong id="visibleCount" style="color: white;">0</strong>
      </div>
    </div>

    <!-- Tabella Artigiani -->
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th>Attività</th>
            <th>Categoria & Città</th>
            <th>Telefono</th>
            <th>Email</th>
            <th>Sito Web</th>
            <th>Stato WhatsApp</th>
            <th>Azione Rapida</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <!-- Righe iniettate via JavaScript -->
        </tbody>
      </table>
    </div>
  </div>

  <div id="toast">Messaggio registrato</div>

  <script>
    const artisans = {json_data};

    // Popola i filtri di categoria e città
    function initFilters() {{
      const categories = [...new Set(artisans.map(a => a.categoria).filter(Boolean))].sort();
      const cities = [...new Set(artisans.map(a => a.citta).filter(Boolean))].sort();

      const catSelect = document.getElementById('categoryFilter');
      categories.forEach(c => {{
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        catSelect.appendChild(opt);
      }});

      const citySelect = document.getElementById('cityFilter');
      cities.forEach(c => {{
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        citySelect.appendChild(opt);
      }});
    }}

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 3000);
    }}

    // Invia segnale al backend (se attivo) o salva in localStorage
    async function markContacted(artisanId, channel = 'WHATSAPP') {{
      const art = artisans.find(a => a.id === artisanId);
      if (!art) return;

      art.wa_contacted = true;
      art.wa_date = new Date().toLocaleString('it-IT');

      // 1. Chiamata API locale (se server Python attivo)
      try {{
        await fetch('/api/mark_contacted', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            nome_attivita: art.nome_attivita,
            canale: channel,
            destinatario: art.telefono,
            note: 'Inviato da console web WhatsApp'
          }})
        }});
      }} catch (err) {{
        console.log('Server locale non raggiungibile, salvo in locale');
      }}

      // 2. Salva in localStorage per persistenza standalone
      const saved = JSON.parse(localStorage.getItem('casalavoro_sent') || '[]');
      if (!saved.includes(art.telefono)) {{
        saved.push(art.telefono);
        localStorage.setItem('casalavoro_sent', JSON.stringify(saved));
      }}

      showToast(`Segnato come contattato: ${{art.nome_attivita}}`);
      updateStats();
      renderTable();
    }}

    function openWhatsApp(artisanId, waUrl) {{
      window.open(waUrl, '_blank');
      markContacted(artisanId, 'WHATSAPP');
    }}

    function updateStats() {{
      const sentWa = artisans.filter(a => a.wa_contacted).length;
      const todoWa = artisans.filter(a => !a.wa_contacted && a.tipo_telefono === 'cellulare').length;
      document.getElementById('stat-wa-inviati').textContent = sentWa;
      document.getElementById('stat-da-contattare').textContent = todoWa;
    }}

    function filterTable() {{
      renderTable();
    }}

    function renderTable() {{
      const search = document.getElementById('searchInput').value.toLowerCase();
      const cat = document.getElementById('categoryFilter').value;
      const city = document.getElementById('cityFilter').value;
      const status = document.getElementById('statusFilter').value;

      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = '';

      let count = 0;
      artisans.forEach(a => {{
        // Filtro ricerca testo
        const matchSearch = !search || 
          a.nome_attivita.toLowerCase().includes(search) ||
          a.categoria.toLowerCase().includes(search) ||
          a.citta.toLowerCase().includes(search) ||
          (a.telefono && a.telefono.includes(search));

        // Filtro categoria e città
        const matchCat = !cat || a.categoria === cat;
        const matchCity = !city || a.citta === city;

        // Filtro stato
        let matchStatus = true;
        if (status === 'todo') {{
          matchStatus = !a.wa_contacted && a.tipo_telefono === 'cellulare';
        }} else if (status === 'sent') {{
          matchStatus = a.wa_contacted;
        }} else if (status === 'has_email') {{
          matchStatus = Boolean(a.email);
        }}

        if (matchSearch && matchCat && matchCity && matchStatus) {{
          count++;
          const tr = document.createElement('tr');

          // Tipo telefono badge
          const isMobile = a.tipo_telefono === 'cellulare';
          const telBadge = isMobile 
            ? '<span class="badge badge-mobile">Cellulare</span>'
            : '<span class="badge badge-fixed">Fisso</span>';

          // Stato WhatsApp badge
          const statusBadge = a.wa_contacted
            ? `<span class="badge badge-status-sent">Inviato (${{a.wa_date || 'Registrato'}})</span>`
            : `<span class="badge badge-status-todo">Da inviare</span>`;

          // Bottone WhatsApp
          let actionBtn = '';
          if (isMobile && a.whatsapp_url) {{
            actionBtn = `<button class="btn-wa" onclick="openWhatsApp(${{a.id}}, '${{a.whatsapp_url}}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
              Invia WhatsApp
            </button>`;
          }} else {{
            actionBtn = `<span style="color: var(--text-muted); font-size: 12px;">Solo fisso o n/d</span>`;
          }}

          // Tasto rapido segna manuale
          const toggleBtn = `<button class="mark-btn" onclick="markContacted(${{a.id}}, 'WHATSAPP')">
            ${{a.wa_contacted ? '✔ Inviato' : 'Segna fatto'}}
          </button>`;

          tr.innerHTML = `
            <td>
              <strong>${{a.nome_attivita}}</strong>
            </td>
            <td>
              <div>${{a.categoria}}</div>
              <div style="font-size: 12px; color: var(--text-muted);">${{a.citta}}</div>
            </td>
            <td>
              <div>${{a.telefono || '<span style="color:#64748b">Nessuno</span>'}}</div>
              <div style="margin-top: 3px;">${{telBadge}}</div>
            </td>
            <td>
              ${{a.email 
                ? `<a href="mailto:${{a.email}}" class="btn-email">✉ ${{a.email}}</a>` 
                : '<span style="color:#64748b; font-size:12px;">Non trovata</span>'}}
            </td>
            <td>
              ${{a.sito_web 
                ? `<a href="${{a.sito_web}}" target="_blank" class="website-link">Visita sito ↗</a>` 
                : '<span style="color:#64748b; font-size:12px;">-</span>'}}
            </td>
            <td>${{statusBadge}}</td>
            <td>
              <div class="actions-cell">
                ${{actionBtn}}
                ${{toggleBtn}}
              </div>
            </td>
          `;
          tbody.appendChild(tr);
        }}
      }});

      document.getElementById('visibleCount').textContent = count;
    }}

    function exportUpdatedCSV() {{
      const headers = ['nome_attivita', 'categoria', 'citta', 'telefono', 'email', 'stato_whatsapp', 'data_contatto'];
      const rows = artisans.map(a => [
        `"${{a.nome_attivita.replace(/"/g, '""')}}"`,
        `"${{a.categoria}}"`,
        `"${{a.citta}}"`,
        `"${{a.telefono}}"`,
        `"${{a.email}}"`,
        a.wa_contacted ? 'INVIATO' : 'DA_INVIARE',
        `"${{a.wa_date || ''}}"`
      ]);

      const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', 'registro_whatsapp_esportato.csv');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    // Inizializza al caricamento
    window.addEventListener('DOMContentLoaded', () => {{
      initFilters();
      renderTable();
    }});
  </script>
</body>
</html>
"""
    return html_content


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Server HTTP locale per gestire la dashboard e le chiamate API di log."""
    
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/dashboard", "/dashboard_contatti.html"):
            html = generate_dashboard_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/api/stats":
            artigiani = load_csv_data(FILE_ESTRATTI)
            registro = load_contacted_registry(FILE_REGISTRO)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "totale": len(artigiani),
                "contattati": len(registro)
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/mark_contacted":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode("utf-8"))
                nome = data.get("nome_attivita", "")
                canale = data.get("canale", "WHATSAPP")
                destinatario = data.get("destinatario", "")
                note = data.get("note", "Registrato da console")
                
                log_contact_action(FILE_REGISTRO, nome, canale, destinatario, stato="INVIATO", note=note)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Contatto registrato con successo"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silenzia i log di routine delle richieste GET per mantenere pulito il terminale
        pass


def serve_dashboard(port: int = 8765):
    """Avvia il server web locale ed apre la dashboard nel browser predefinito."""
    server_address = ("127.0.0.1", port)
    
    # Scrivi anche il file statico su disco
    html_content = generate_dashboard_html()
    with open(FILE_DASHBOARD, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    try:
        httpd = HTTPServer(server_address, DashboardRequestHandler)
    except OSError:
        port += 1
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, DashboardRequestHandler)
        
    dashboard_url = f"http://127.0.0.1:{port}/"
    print("\n" + "=" * 65)
    print("   CASALAVOROPRO — DASHBOARD OUTREACH WHATSAPP AVVIATA")
    print("=" * 65)
    print(f"[*] Dashboard attiva su: {dashboard_url}")
    print(f"[*] File locale generato: {FILE_DASHBOARD}")
    print(f"[*] File registro: {FILE_REGISTRO}")
    print("[*] Premi Ctrl+C nel terminale per arrestare il server quando hai finito.")
    print("=" * 65 + "\n")
    
    # Apri automaticamente il browser
    webbrowser.open(dashboard_url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[i] Server dashboard arrestato. Buona continuazione!")
        httpd.server_close()


def send_single_email(smtp_server, record: dict, dry_run: bool = False) -> tuple[bool, str]:
    """Invia una singola email B2B personalizzata all'artigiano."""
    dest_email = record.get("email", "").strip()
    nome = record.get("nome_attivita", "Professionista")
    cat = record.get("categoria", "il tuo settore")
    cit = record.get("citta", "la tua zona")
    
    if not dest_email or "@" not in dest_email:
        return False, "Indirizzo email non valido o assente"
        
    subject = EMAIL_SUBJECT_TEMPLATE.format(citta=cit, nome_attivita=nome)
    body_text = EMAIL_TEXT_TEMPLATE.format(
        nome_attivita=nome,
        sender_name=SENDER_NAME,
        categoria=cat,
        citta=cit,
        platform_name=PLATFORM_NAME,
        platform_url=PLATFORM_URL,
        sender_email=SENDER_EMAIL
    )
    
    # Formattazione HTML pulita e moderna
    body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; margin: 0; padding: 20px; background-color: #f8fafc; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; }}
    .header {{ border-bottom: 2px solid #ea580c; padding-bottom: 16px; margin-bottom: 24px; }}
    .logo {{ font-size: 20px; font-weight: 800; color: #ea580c; }}
    .badge {{ background: #ffedd5; color: #9a3412; font-size: 12px; font-weight: 700; padding: 4px 8px; border-radius: 4px; display: inline-block; }}
    h2 {{ color: #0f172a; font-size: 18px; margin-top: 0; }}
    .highlight-box {{ background: #f1f5f9; border-left: 4px solid #ea580c; padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 20px 0; font-size: 14px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 8px; }}
    .cta-btn {{ display: inline-block; background-color: #ea580c; color: #ffffff !important; text-decoration: none; font-weight: 700; padding: 12px 24px; border-radius: 8px; margin-top: 16px; }}
    .footer {{ margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="logo">{PLATFORM_NAME}</span>
      <span class="badge" style="float: right;">Selezione Professionisti {cit}</span>
    </div>
    
    <h2>Ciao {nome},</h2>
    
    <p>Mi chiamo <strong>{SENDER_NAME}</strong> e ti scrivo dal team di <a href="{PLATFORM_URL}" style="color: #ea580c; font-weight: 600;">{PLATFORM_NAME}</a>.</p>
    
    <p>Ho notato la tua attività di <strong>{cat}</strong> a <strong>{cit}</strong> e la qualità dei tuoi interventi. Stiamo selezionando e inserendo gratuitamente i migliori professionisti del territorio per metterli in contatto diretto con i proprietari di casa della tua provincia che cercano preventivi per lavori e ristrutturazioni.</p>
    
    <div class="highlight-box">
      <strong>Perché CasaLavoroPRO è diversa dai soliti portali a gettone?</strong>
      <ul>
        <li><strong>ZERO gettoni:</strong> nessun costo per rispondere o vedere le richieste.</li>
        <li><strong>ZERO percentuali sui preventivi:</strong> il compenso del lavoro è al 100% tuo.</li>
        <li><strong>Contatto diretto:</strong> parli direttamente con il cliente al telefono o su WhatsApp.</li>
        <li><strong>Visibilità locale continua:</strong> scheda attività con recensioni verificate.</li>
      </ul>
    </div>
    
    <p>Se desideri essere inserito gratuitamente tra i professionisti consigliati a {cit}, puoi registrarti in 2 minuti dal link qui sotto, oppure rispondere direttamente a questa email con un cenno di conferma:</p>
    
    <p style="text-align: center;">
      <a href="{PLATFORM_URL}" class="cta-btn">Crea la tua scheda gratuita su {PLATFORM_NAME} →</a>
    </p>
    
    <p>Ti auguro una buona giornata e buon lavoro!</p>
    
    <p>
      Un cordiale saluto,<br>
      <strong>{SENDER_NAME}</strong><br>
      <span style="color: #64748b; font-size: 13px;">Team di {PLATFORM_NAME} • <a href="{PLATFORM_URL}">{PLATFORM_URL}</a></span>
    </p>
    
    <div class="footer">
      Ricevi questa comunicazione informativa B2B perché la tua attività opera nel settore casa a {cit}. Se non desideri ricevere ulteriori aggiornamenti, rispondi semplicemente con 'Cancellami' per essere escluso.
    </div>
  </div>
</body>
</html>"""

    if dry_run:
        print(f"\n[DRY RUN] Invio simulato a: {dest_email} ({nome})")
        print(f"          Oggetto: {subject}")
        print(f"          Preview: Ho notato la tua attività di {cat} a {cit}...")
        return True, "Simulazione riuscita (Dry Run)"

    if not smtp_server:
        return False, "Connessione SMTP non fornita"
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = dest_email
        msg["Reply-To"] = SENDER_EMAIL
        
        part1 = MIMEText(body_text, "plain", "utf-8")
        part2 = MIMEText(body_html, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)
        
        smtp_server.sendmail(SENDER_EMAIL, [dest_email], msg.as_string())
        return True, "Email inviata con successo"
    except Exception as e:
        return False, f"Errore invio: {e}"


def run_email_outreach(dry_run: bool = False, test_recipient: str = ""):
    """Esegue la campagna email B2B verso i contatti estratti non ancora contattati."""
    artigiani = load_csv_data(FILE_ESTRATTI)
    registro = load_contacted_registry(FILE_REGISTRO)
    
    print("\n" + "=" * 65)
    print("   CASALAVOROPRO — SPEDIZIONE EMAIL OUTREACH B2B")
    print("=" * 65)
    
    if test_recipient:
        print(f"[*] Modalità TEST: invio di una singola email di prova a {test_recipient}")
        sample = artigiani[0] if artigiani else {
            "nome_attivita": "Impresa Edile Demo",
            "categoria": "Ristrutturazioni",
            "citta": "Vicenza",
            "email": test_recipient
        }
        sample["email"] = test_recipient
        to_send = [sample]
    else:
        # Filtra artigiani con email valida e non ancora contattati
        to_send = []
        for a in artigiani:
            em = a.get("email", "").strip().lower()
            nome = a.get("nome_attivita", "").strip().lower()
            if not em or "@" not in em:
                continue
            if f"EMAIL:{em}" in registro or f"EMAIL:name:{nome}" in registro:
                continue
            to_send.append(a)
            
    print(f"[*] Contatti con email validi da processare: {len(to_send)}")
    print(f"[*] Modalità Dry Run: {'ATTIVA (Nessuna email reale sarà inviata)' if dry_run else 'DISATTIVATA (Invio reale)'}")
    
    if not to_send:
        print("[v] Nessuna nuova email da inviare. Tutti i contatti sono già stati processati!")
        return

    smtp_conn = None
    if not dry_run:
        if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
            print("\n[!] ATTENZIONE: Credenziali SMTP non configurate nel file .env!")
            print("    Modifica il file 'scripts/artigiani_scraper_outreach/.env' inserendo:")
            print("    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SENDER_EMAIL")
            print("    Nel frattempo puoi usare l'opzione '--dry-run' per testare i messaggi.\n")
            return
            
        print(f"[*] Connessione al server SMTP {SMTP_HOST}:{SMTP_PORT}...")
        try:
            if SMTP_USE_SSL:
                smtp_conn = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
            else:
                smtp_conn = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
                if SMTP_USE_TLS:
                    smtp_conn.starttls()
            smtp_conn.login(SMTP_USER, SMTP_PASS)
            print("[v] Connessione SMTP stabilita e autenticata.")
        except Exception as e:
            print(f"[!] Errore connessione SMTP: {e}")
            return

    success_count = 0
    try:
        for idx, art in enumerate(to_send, start=1):
            nome = art.get("nome_attivita", "")
            em = art.get("email", "")
            print(f"\n[{idx}/{len(to_send)}] Elaborazione: {nome} <{em}>")
            
            ok, msg = send_single_email(smtp_conn, art, dry_run=dry_run)
            if ok:
                success_count += 1
                print(f"   [+] Esito: {msg}")
                if not dry_run and not test_recipient:
                    log_contact_action(FILE_REGISTRO, nome, "EMAIL", em, stato="INVIATO", note="Email B2B inviata via SMTP")
            else:
                print(f"   [!] Fallito: {msg}")
                if not dry_run and not test_recipient:
                    log_contact_action(FILE_REGISTRO, nome, "EMAIL", em, stato="ERRORE", note=msg)
                    
            # Pausa casuale di cortesia tra invii per deliverability ottimale
            if idx < len(to_send) and not dry_run:
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"   [...] Pausa di {delay:.1f}s tra gli invii...")
                time.sleep(delay)
                
    finally:
        if smtp_conn:
            try:
                smtp_conn.quit()
            except Exception:
                pass

    print("\n" + "=" * 65)
    print(f" [OK] SESSIONE EMAIL CONCLUSA: {success_count}/{len(to_send)} invii completati.")
    print(f" [OK] Registro aggiornato in: {FILE_REGISTRO}")
    print("=" * 65 + "\n")


def display_stats():
    """Visualizza le statistiche riassuntive sui contatti estratti e l'outreach."""
    artigiani = load_csv_data(FILE_ESTRATTI)
    registro = load_contacted_registry(FILE_REGISTRO)
    
    tot = len(artigiani)
    cellulari = sum(1 for a in artigiani if a.get("tipo_telefono", "").lower() == "cellulare")
    fissi = sum(1 for a in artigiani if a.get("tipo_telefono", "").lower() == "fisso")
    email = sum(1 for a in artigiani if a.get("email", "").strip())
    
    print("\n" + "=" * 60)
    print("   CASALAVOROPRO — STATISTICHE LEAD & OUTREACH")
    print("=" * 60)
    print(f"  • Totale aziende/artigiani estratti: {tot}")
    print(f"  • Numeri di cellulare (WhatsApp):    {cellulari} ({cellulari/tot*100:.1f}%)" if tot else "0")
    print(f"  • Numeri di rete fissa:              {fissi}")
    print(f"  • Email aziendali trovate:           {email} ({email/tot*100:.1f}%)" if tot else "0")
    print(f"  • Contatti registrati in storico:    {len(registro)}")
    print("=" * 60 + "\n")


def parse_arguments():
    """Argomenti da riga di comando per il modulo outreach."""
    parser = argparse.ArgumentParser(
        description="Modulo Outreach CasaLavoroPRO: Gestione WhatsApp Click-to-Chat ed Email B2B."
    )
    parser.add_argument(
        "-s", "--serve", 
        action="store_true", 
        help="Avvia il server locale con la dashboard interattiva WhatsApp"
    )
    parser.add_argument(
        "-g", "--generate-dashboard", 
        action="store_true", 
        help="Genera il file statico 'dashboard_contatti.html' senza avviare il server"
    )
    parser.add_argument(
        "-e", "--send-emails", 
        action="store_true", 
        help="Avvia la spedizione email B2B ai contatti estratti con indirizzo email"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Simula la spedizione email senza inviare messaggi reali"
    )
    parser.add_argument(
        "--test-email", 
        type=str, 
        default="", 
        help="Invia una singola email di test all'indirizzo specificato per verificare formattazione e SMTP"
    )
    parser.add_argument(
        "--stats", 
        action="store_true", 
        help="Mostra statistiche riassuntive sui contatti estratti"
    )
    parser.add_argument(
        "-p", "--port", 
        type=int, 
        default=8765, 
        help="Porta per il server dashboard locale (predefinita: 8765)"
    )
    return parser.parse_args()


def interactive_menu():
    """Menu rapido da terminale se lanciato senza argomenti."""
    print("=" * 65)
    print("   CASALAVOROPRO — OUTREACH DISPATCHER (WHATSAPP & EMAIL)")
    print("=" * 65)
    print("1. Avvia Dashboard WhatsApp Interattiva (Apre il browser con sync in tempo reale)")
    print("2. Invia Email di Outreach B2B (con opzione simulazione o reale)")
    print("3. Invia una singola Email di Test al tuo indirizzo")
    print("4. Genera solo il file HTML 'dashboard_contatti.html'")
    print("5. Mostra statistiche e contatti attuali")
    print("6. Esci")
    
    choice = input("\nSeleziona un'opzione (1-6) [default: 1]: ").strip() or "1"
    return choice


def main():
    args = parse_arguments()
    
    # Se viene richiesto un flag specifico
    if args.serve:
        serve_dashboard(port=args.port)
    elif args.generate_dashboard:
        html = generate_dashboard_html()
        with open(FILE_DASHBOARD, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[v] Dashboard HTML generata con successo: {FILE_DASHBOARD}")
        webbrowser.open(f"file://{os.path.abspath(FILE_DASHBOARD)}")
    elif args.send_emails:
        run_email_outreach(dry_run=args.dry_run, test_recipient=args.test_email)
    elif args.test_email:
        run_email_outreach(dry_run=False, test_recipient=args.test_email)
    elif args.stats:
        display_stats()
    else:
        # Menu interattivo
        choice = interactive_menu()
        if choice == "1":
            serve_dashboard(port=args.port)
        elif choice == "2":
            mode = input("Vuoi fare una simulazione Dry-Run prima di inviare realmente? (S/n) [default: S]: ").strip().lower()
            dry_run = mode not in ("n", "no")
            run_email_outreach(dry_run=dry_run)
        elif choice == "3":
            em = input("Inserisci il tuo indirizzo email per il test: ").strip()
            if em and "@" in em:
                run_email_outreach(dry_run=False, test_recipient=em)
            else:
                print("[!] Indirizzo email non valido.")
        elif choice == "4":
            html = generate_dashboard_html()
            with open(FILE_DASHBOARD, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[v] Dashboard HTML generata: {FILE_DASHBOARD}")
            webbrowser.open(f"file://{os.path.abspath(FILE_DASHBOARD)}")
        elif choice == "5":
            display_stats()
        else:
            print("Uscita.")


if __name__ == "__main__":
    main()

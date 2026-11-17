#!/usr/bin/env python3
"""
MODULO 1: SCRAPING GOOGLE MAPS & DEEP WEB SCRAPING - CasaLavoroPRO
==================================================================
Estrae contatti reali di artigiani locali da Google Maps, recensioni del web,
arricchisce i dati visitando i relativi siti web e sincronizza automaticamente
le schede in stato di bozza ('draft_scraping') nel database Supabase.

Funzionalità Anti-Blocco & Stealth:
- Rate limiting con ritardi casuali distribuiti (jitter) e backoff
- Pool rotante di User-Agent moderni e mascheramento CDP (navigator.webdriver)
- Supporto a proxy rotanti (HTTP/HTTPS/SOCKS5)
- Creazione bozze su Supabase con recensioni, indirizzo, telefono e categoria
"""

import os
import csv
import re
import sys
import time
import random
import argparse
from datetime import datetime
from urllib.parse import quote_plus
from typing import Dict, Any, List

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config as app_config
from config import (
    DEFAULT_CATEGORIE,
    DEFAULT_CITTA,
    DEFAULT_LIMIT_PER_SEARCH,
    MIN_DELAY_SECONDS,
    MAX_DELAY_SECONDS,
    HEADLESS_BROWSER,
    DEEP_SCRAPING_ENABLED,
    FILE_ESTRATTI
)
from normalizer import normalize_italian_phone, clean_website, clean_text
from deep_scraper import deep_scrape_artisan_website
from stealth_engine import stealth_engine, global_proxy_rotator
from supabase_client import create_artisan_draft, is_supabase_configured

# Campi del CSV principale (estesi con recensioni e stato bozza Supabase)
CSV_FIELDNAMES = [
    "nome_attivita",
    "categoria",
    "citta",
    "telefono_principale",
    "tipo_telefono",
    "email",
    "sito_web",
    "indirizzo",
    "whatsapp_link",
    "rating_recensioni",
    "numero_recensioni",
    "recensioni_estratte",
    "stato_bozza_supabase",
    "logo_aziendale",
    "data_estrazione"
]


def setup_selenium_driver(headless: bool = True) -> webdriver.Chrome:
    """Configura e inizializza il browser Chrome con opzioni anti-detection avanzate."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Risoluzione viewport casuale per simulare monitor diversi
    vw, vh = stealth_engine.get_random_viewport()
    options.add_argument(f"--window-size={vw},{vh}")
    options.add_argument("--lang=it-IT")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # User-agent realistico e ruotato dal pool
    ua = stealth_engine.get_random_user_agent()
    options.add_argument(f"user-agent={ua}")

    # Proxy se configurati
    if global_proxy_rotator.has_proxies():
        proxy_addr = global_proxy_rotator.get_next()
        if proxy_addr:
            options.add_argument(f"--proxy-server={proxy_addr}")

    driver = webdriver.Chrome(options=options)
    
    # Applica mascheramento CDP (navigator.webdriver, plugins, languages, window.chrome)
    stealth_engine.apply_selenium_stealth(driver)
    return driver


def handle_cookie_consent(driver: webdriver.Chrome):
    """Accetta o rifiuta i cookie di Google Maps per sbloccare l'interfaccia."""
    try:
        time.sleep(1.2)
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            txt = btn.text.strip().lower()
            if any(k in txt for k in ["rifiuta tutto", "accetta tutto", "reject all", "accept all", "prima di continuare"]):
                try:
                    btn.click()
                    time.sleep(1.2)
                    break
                except Exception:
                    pass
    except Exception:
        pass


def load_existing_keys(filepath) -> set:
    """Carica le chiavi dei contatti già presenti per evitare duplicati."""
    keys = set()
    if not os.path.exists(filepath):
        return keys
        
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row.get("telefono_principale", "").strip()
                name = row.get("nome_attivita", "").strip().lower()
                city = row.get("citta", "").strip().lower()
                if phone:
                    keys.add(f"tel:{phone}")
                if name and city:
                    keys.add(f"name:{name}:{city}")
    except Exception as e:
        print(f"[!] Avviso lettura duplicati esistenti: {e}")
        
    return keys


def save_record_to_csv(filepath, record: dict):
    """Salva o accoda un singolo record in tempo reale nel file CSV."""
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
    if file_exists:
        try:
            with open(filepath, mode="r", encoding="utf-8-sig", newline="") as rf:
                reader = csv.DictReader(rf)
                existing_fields = reader.fieldnames or []
                existing_rows = list(reader)
            if existing_fields and "logo_aziendale" not in existing_fields:
                with open(filepath, mode="w", encoding="utf-8-sig", newline="") as wf:
                    writer = csv.DictWriter(wf, fieldnames=CSV_FIELDNAMES)
                    writer.writeheader()
                    for row in existing_rows:
                        writer.writerow({k: row.get(k, "") for k in CSV_FIELDNAMES})
        except Exception:
            pass
    with open(filepath, mode="a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in CSV_FIELDNAMES})


def extract_reviews_from_detail(driver: webdriver.Chrome) -> Dict[str, Any]:
    """
    Estrae le informazioni sulle recensioni di Google Maps:
    - Voto medio (rating, es. 4.8)
    - Conteggio totale recensioni (es. 35)
    - Estratti / snippet significativi di recensioni
    """
    rating = ""
    recensioni_count = ""
    snippets: List[str] = []

    try:
        # 1. Parsing blocco metriche F7nice
        f7_elems = driver.find_elements(By.CSS_SELECTOR, "div.F7nice, div.fontDisplayLarge")
        for f7 in f7_elems:
            txt = f7.text.strip()
            if txt:
                lines = [l.strip() for l in txt.split("\n") if l.strip()]
                for l in lines:
                    m_rate = re.search(r"\b([1-5][\.,][0-9])\b", l)
                    if m_rate and not rating:
                        rating = m_rate.group(1).replace(",", ".")
                    m_cnt = re.search(r"\(?([0-9\.\,]+)\)?", l)
                    if m_cnt and m_cnt.group(1) != rating and not recensioni_count:
                        recensioni_count = m_cnt.group(1).replace(".", "").replace(",", "")

        # 2. Parsing aria-label del badge stelle
        if not rating or not recensioni_count:
            aria_elems = driver.find_elements(By.CSS_SELECTOR, 'span[role="img"][aria-label*="stelle" i], span[aria-label*="recensioni" i]')
            for el in aria_elems:
                aria = el.get_attribute("aria-label") or ""
                m_rate = re.search(r"([1-5][\.,][0-9])\s*stelle", aria, re.IGNORECASE)
                if m_rate and not rating:
                    rating = m_rate.group(1).replace(",", ".")
                m_cnt = re.search(r"([0-9\.\,]+)\s*recensioni", aria, re.IGNORECASE)
                if m_cnt and not recensioni_count:
                    recensioni_count = m_cnt.group(1).replace(".", "").replace(",", "")

        # 3. Snippet di recensioni / citazioni
        snippet_elems = driver.find_elements(By.CSS_SELECTOR, "div.wiI7pd, div.MyEned, div.review-snippet")
        for snip in snippet_elems[:3]:
            stxt = clean_text(snip.text)
            if stxt and len(stxt) > 15 and stxt not in snippets:
                snippets.append(stxt)
    except Exception:
        pass

    return {
        "rating": rating,
        "totale": recensioni_count,
        "snippets": snippets
    }


def scrape_google_maps(
    driver: webdriver.Chrome, 
    categoria: str, 
    citta: str, 
    limit: int = 20, 
    deep_scrape: bool = True,
    progress_callback = None,
    stop_event = None
) -> int:
    """
    Effettua la ricerca su Google Maps, estrae i dettagli e le recensioni,
    salva in locale su CSV e crea la bozza ('draft_scraping') su Supabase.
    """
    if stop_event and stop_event.is_set():
        return 0

    query = f"{categoria} {citta}"
    encoded_query = quote_plus(query)
    search_url = f"https://www.google.com/maps/search/{encoded_query}"
    
    print(f"\n=======================================================")
    print(f"[*] Avvio ricerca: '{categoria}' a '{citta}'")
    print(f"[*] URL: {search_url}")
    print(f"[*] Obiettivo: fino a {limit} contatti")
    print(f"=======================================================\n")
    
    if progress_callback:
        progress_callback(None, 0, limit, f"Apertura ricerca per '{categoria}' a '{citta}'...")

    driver.get(search_url)
    handle_cookie_consent(driver)
    
    if stop_event and stop_event.is_set():
        return 0

    # Attendi caricamento feed
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"], a.hfpxzc'))
        )
    except Exception:
        print("[!] Attesa feed risultati...")
        time.sleep(2.5)
        
    existing_keys = load_existing_keys(FILE_ESTRATTI)
    scraped_count = 0
    scroll_attempts = 0
    
    # 1. Scroll progressivo delle schede
    while True:
        if stop_event and stop_event.is_set():
            return scraped_count

        cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        current_cards_count = len(cards)
        
        if progress_callback:
            progress_callback(None, scraped_count, limit, f"Caricamento schede Google Maps ({current_cards_count} trovate)...")

        if current_cards_count >= limit or scroll_attempts >= 5:
            break
            
        feeds = driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"]')
        if feeds:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feeds[0])
            time.sleep(2.2)
            
        new_cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        if len(new_cards) == current_cards_count:
            scroll_attempts += 1
            time.sleep(1.8)
        else:
            scroll_attempts = 0
            
    cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
    print(f"[+] Schede trovate nell'elenco: {len(cards)} (elaborazione max {limit})")
    
    # 2. Iterazione e lettura dettagli delle schede
    for i in range(min(limit, len(cards))):
        if stop_event and stop_event.is_set():
            print("[!] Operazione interrotta dall'utente.")
            break

        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            if i >= len(cards):
                break
            card = cards[i]
            
            nome_attivita = clean_text(card.get_attribute("aria-label") or f"Attivita_{i+1}")
            
            if progress_callback:
                progress_callback(None, scraped_count, limit, f"Lettura dettagli: {nome_attivita}...")

            # Scorri la card in vista e cliccala per aprire il pannello laterale
            driver.execute_script("arguments[0].scrollIntoView(true);", card)
            time.sleep(0.4)
            
            try:
                card.click()
            except Exception:
                driver.execute_script("arguments[0].click();", card)
                
            # Pausa stealth casuale per rendering pannello
            stealth_engine.sleep_human(multiplier=0.8, reason="Rendering scheda Google Maps")
            
            if stop_event and stop_event.is_set():
                break
            
            # --- Estrazione Telefono ---
            raw_phone = ""
            phone_elems = driver.find_elements(By.CSS_SELECTOR, '[data-item-id^="phone:tel:"]')
            if phone_elems:
                raw_phone = phone_elems[0].get_attribute("data-item-id").replace("phone:tel:", "").strip()
            if not raw_phone:
                for el in driver.find_elements(By.CSS_SELECTOR, '[aria-label*="Telefono:"], [aria-label*="telefono:"]'):
                    aria = el.get_attribute("aria-label") or ""
                    raw_phone = aria.split(":")[-1].strip()
                    if raw_phone:
                        break
                        
            # --- Estrazione Sito Web ---
            raw_website = ""
            web_elems = driver.find_elements(By.CSS_SELECTOR, '[data-item-id="authority"]')
            if web_elems:
                raw_website = web_elems[0].get_attribute("href") or ""
            if not raw_website:
                for el in driver.find_elements(By.CSS_SELECTOR, 'a[aria-label*="Sito web:"], a[data-tooltip*="sito web" i]'):
                    raw_website = el.get_attribute("href") or ""
                    if raw_website:
                        break
                        
            # --- Estrazione Indirizzo ---
            indirizzo = ""
            addr_elems = driver.find_elements(By.CSS_SELECTOR, '[data-item-id="address"]')
            if addr_elems:
                indirizzo = clean_text(addr_elems[0].text)
            if not indirizzo:
                for el in driver.find_elements(By.CSS_SELECTOR, '[aria-label*="Indirizzo:"], [data-tooltip*="indirizzo" i]'):
                    indirizzo = clean_text((el.get_attribute("aria-label") or el.text).split(":")[-1])
                    if indirizzo:
                        break
                        
            # --- Estrazione Recensioni Web (Rating, Totale, Snippet) ---
            review_info = extract_reviews_from_detail(driver)
            
            sito_web = clean_website(raw_website)
            telefono_formattato, tipo_telefono, wa_cifre = normalize_italian_phone(raw_phone)
            
            # --- Deep Scraping del Sito Web (se presente) ---
            email = ""
            if deep_scrape and sito_web:
                print(f"    -> [Deep Scraping] Visita {sito_web}...")
                deep_res = deep_scrape_artisan_website(sito_web)
                email = deep_res.get("email", "")
                
                if tipo_telefono != "cellulare" and deep_res.get("tipo_cellulare") == "cellulare":
                    telefono_formattato = deep_res["cellulare_trovato"]
                    tipo_telefono = "cellulare"
                    wa_cifre = deep_res["whatsapp_cifre"]
                    print(f"    -> [Arricchimento] Cellulare WhatsApp: {telefono_formattato}")
                    
                if email:
                    print(f"    -> [Arricchimento] Email: {email}")

            whatsapp_link = f"https://wa.me/{wa_cifre}" if (tipo_telefono == "cellulare" and wa_cifre) else ""
            
            # Controllo duplicati
            key_tel = f"tel:{telefono_formattato}" if telefono_formattato else ""
            key_name = f"name:{nome_attivita.lower()}:{citta.lower()}"
            if (key_tel and key_tel in existing_keys) or (key_name in existing_keys):
                print(f"  [-] Già presente in archivio: {nome_attivita} ({telefono_formattato})")
                continue
                
            current_logo = (os.getenv("LOGO_URL") or getattr(app_config, "LOGO_URL", "") or "").strip()

            record = {
                "nome_attivita": nome_attivita,
                "categoria": categoria,
                "citta": citta,
                "telefono_principale": telefono_formattato,
                "tipo_telefono": tipo_telefono,
                "email": email,
                "sito_web": sito_web,
                "indirizzo": indirizzo,
                "whatsapp_link": whatsapp_link,
                "rating_recensioni": review_info["rating"],
                "numero_recensioni": review_info["totale"],
                "recensioni_estratte": " | ".join(review_info["snippets"]),
                "stato_bozza_supabase": "draft_scraping",
                "logo_aziendale": current_logo,
                "data_estrazione": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 1. Salva subito nel CSV locale
            save_record_to_csv(FILE_ESTRATTI, record)
            if key_tel:
                existing_keys.add(key_tel)
            existing_keys.add(key_name)
            scraped_count += 1
            
            # 2. Creazione automatica scheda Bozza su Supabase
            try:
                supabase_res = create_artisan_draft(record)
                if supabase_res.get("status") == "success":
                    print(f"      [Supabase] Bozza creata con successo (draft_scraping)")
                elif supabase_res.get("status") == "local_only":
                    pass
                else:
                    print(f"      [Supabase] Info: {supabase_res.get('error', 'non configurato')}")
            except Exception as e_sb:
                print(f"      [Supabase] Errore sync: {e_sb}")

            # Notifica la GUI del nuovo contatto
            if progress_callback:
                progress_callback(record, scraped_count, limit, f"Aggiunto: {nome_attivita} ({tipo_telefono})")
            
            tipo_color = "[CELLULARE]" if tipo_telefono == "cellulare" else "[FISSO]"
            print(f"  [+] #{scraped_count:02d} | {nome_attivita}")
            print(f"      {tipo_color} {telefono_formattato or 'N/D'} | Email: {email or 'N/D'}")
            print(f"      Sito: {sito_web or 'N/D'} | Indirizzo: {indirizzo or 'N/D'}")
            if review_info["rating"]:
                print(f"      Recensioni: {review_info['rating']} stelle ({review_info['totale'] or '0'})")
            
            # Pausa anti-blocco con jitter umano tra una scheda e la successiva
            stealth_engine.sleep_human(multiplier=1.0, reason=f"Pausa tra schede artigiano {i+1}")
            
        except Exception as e:
            print(f"  [!] Errore lettura scheda {i+1}: {e}")
            continue
            
    print(f"\n[v] Ricerca completata per '{categoria}' a '{citta}': {scraped_count} nuovi contatti salvati.")
    return scraped_count


def scrape_google_maps_multi_zone(
    driver: webdriver.Chrome,
    categoria: str,
    locations: list[str],
    target_limit: int = 100,
    deep_scrape: bool = True,
    progress_callback = None,
    stop_event = None
) -> int:
    """
    Esegue la ricerca estesa su più comuni/poli territoriali
    fino a raggiungere il limite totale richiesto (es. 100, 200, 500, 1000 contatti).
    """
    total_extracted = 0
    if not locations:
        locations = ["Vicenza"]

    print(f"\n=======================================================")
    print(f"[*] RICERCA ESTESA MULTI-ZONA CASALAVOROPRO")
    print(f"[*] Categoria: '{categoria}'")
    print(f"[*] Territorio: {len(locations)} zone ({', '.join(locations[:4])}...)")
    print(f"[*] Target Limite: {target_limit} contatti")
    print(f"=======================================================\n")

    for loc_idx, loc in enumerate(locations, start=1):
        if stop_event and stop_event.is_set():
            break

        remaining = target_limit - total_extracted
        if remaining <= 0:
            break

        sub_limit = min(remaining, 60)

        def sub_callback(record, count_in_city, city_target, status_msg):
            if progress_callback:
                curr_tot = total_extracted + (1 if record else 0)
                display_msg = f"[{loc_idx}/{len(locations)} {loc}] {status_msg}"
                progress_callback(record, curr_tot, target_limit, display_msg)

        if progress_callback:
            progress_callback(
                None,
                total_extracted,
                target_limit,
                f"Zona {loc_idx}/{len(locations)}: scansione '{categoria}' a '{loc}'..."
            )

        found_in_city = scrape_google_maps(
            driver=driver,
            categoria=categoria,
            citta=loc,
            limit=sub_limit,
            deep_scrape=deep_scrape,
            progress_callback=sub_callback,
            stop_event=stop_event
        )

        total_extracted += found_in_city
        print(f"[i] Progresso totale: {total_extracted}/{target_limit} contatti.")

        if total_extracted < target_limit and loc_idx < len(locations):
            stealth_engine.sleep_human(multiplier=1.2, reason="Pausa tra zone territoriali")

    return total_extracted


def parse_arguments():
    """Configura gli argomenti da riga di comando per lo scraper."""
    parser = argparse.ArgumentParser(
        description="Scraper autonomo per CasaLavoroPRO: estrae contatti di artigiani da Google Maps e siti web."
    )
    parser.add_argument(
        "-c", "--categoria", 
        type=str, 
        default="", 
        help="Categoria professionale (es. 'Idraulico', 'Elettricista', 'Impresa edile', o lista separata da virgole)"
    )
    parser.add_argument(
        "-z", "--citta", 
        type=str, 
        default="", 
        help="Città / Zona di ricerca (es. 'Vicenza', 'Bassano del Grappa', 'Padova' o lista separata da virgole)"
    )
    parser.add_argument(
        "-l", "--limite", 
        type=int, 
        default=DEFAULT_LIMIT_PER_SEARCH, 
        help=f"Numero massimo di attività da estrarre per query (predefinito: {DEFAULT_LIMIT_PER_SEARCH})"
    )
    parser.add_argument(
        "--no-deep", 
        action="store_true", 
        help="Disabilita il deep scraping dei siti web"
    )
    parser.add_argument(
        "--visible", 
        action="store_true", 
        help="Esegui Chrome con finestra visibile"
    )
    parser.add_argument(
        "--preset", 
        action="store_true", 
        help="Esegue la scansione automatica su tutte le categorie e città predefinite del Veneto"
    )
    return parser.parse_args()


def interactive_menu():
    """Menu da terminale per l'utente."""
    print("=" * 60)
    print("   CASALAVOROPRO — SCRAPER ARTIGIANI & BOZZE SUPABASE")
    print("=" * 60)
    print("1. Ricerca personalizzata (scegli Categoria e Città)")
    print("2. Preset rapido Veneto (Idraulici & Elettricisti a Vicenza/Padova/Bassano)")
    print("3. Preset completo tutte le categorie principali")
    print("4. Esci")
    
    choice = input("\nSeleziona un'opzione (1-4) [default: 1]: ").strip() or "1"
    
    if choice == "1":
        cat = input("Inserisci Categoria [default: Idraulico]: ").strip() or "Idraulico"
        cit = input("Inserisci Città [default: Vicenza]: ").strip() or "Vicenza"
        limit_str = input(f"Limite contatti [default: {DEFAULT_LIMIT_PER_SEARCH}]: ").strip()
        limit = int(limit_str) if limit_str.isdigit() else DEFAULT_LIMIT_PER_SEARCH
        return [cat], [cit], limit
    elif choice == "2":
        return ["Idraulico", "Elettricista"], ["Vicenza", "Bassano del Grappa"], 10
    elif choice == "3":
        return DEFAULT_CATEGORIE[:4], DEFAULT_CITTA[:3], 15
    else:
        print("Uscita.")
        sys.exit(0)


def main():
    args = parse_arguments()
    
    if not args.categoria and not args.citta and not args.preset:
        categorie, citta_list, limit = interactive_menu()
    elif args.preset:
        categorie = DEFAULT_CATEGORIE[:4]
        citta_list = DEFAULT_CITTA[:3]
        limit = args.limite
    else:
        categorie = [c.strip() for c in args.categoria.split(",") if c.strip()] if args.categoria else ["Idraulico"]
        citta_list = [z.strip() for z in args.citta.split(",") if z.strip()] if args.citta else ["Vicenza"]
        limit = args.limite
        
    headless = not args.visible if args.visible else HEADLESS_BROWSER
    deep_scrape = not args.no_deep and DEEP_SCRAPING_ENABLED
    
    print(f"\n[i] Inizializzazione browser Chrome Stealth (headless: {headless})...")
    driver = setup_selenium_driver(headless=headless)
    
    total_saved = 0
    try:
        for cat in categorie:
            for cit in citta_list:
                saved = scrape_google_maps(
                    driver=driver,
                    categoria=cat,
                    citta=cit,
                    limit=limit,
                    deep_scrape=deep_scrape
                )
                total_saved += saved
                stealth_engine.sleep_human(multiplier=1.0, reason="Pausa tra query di ricerca")
    finally:
        print("\n[i] Chiusura browser...")
        driver.quit()
        
    print("\n" + "=" * 60)
    print(f" [OK] SESSIONE COMPLETATA: {total_saved} nuovi contatti aggiunti.")
    print(f" [OK] Archivio locale aggiornato: {FILE_ESTRATTI}")
    if is_supabase_configured():
        print(f" [OK] Bozze sincronizzate su Supabase in stato 'draft_scraping'!")
    print(f" [->] Avvia la GUI per gestire le bozze e l'outreach WhatsApp / Email!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

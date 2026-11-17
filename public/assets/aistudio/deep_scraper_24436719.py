"""
Modulo di Deep Web Scraping per CasaLavoroPRO:
Visita il sito web dell'artigiano (homepage e sottopagine contatti/chi-siamo)
per estrarre indirizzi email aziendali e numeri di cellulare WhatsApp dedicati.
"""

import re
import time
import random
import urllib.parse
import urllib3
import requests
from bs4 import BeautifulSoup

from normalizer import clean_email, clean_website, normalize_italian_phone
from config import MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, MAX_DEEP_PAGES_PER_SITE

# Disabilita gli avvisi SSL non verificati quando si effettuano fallback
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parole chiave per identificare la pagina contatti
CONTACT_PAGE_KEYWORDS = [
    "contatt", "contatto", "contatti", "chi-siamo", "chi_siamo",
    "dove-siamo", "dove_siamo", "about", "contact", "info", "recapiti"
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


def deep_scrape_artisan_website(website_url: str) -> dict:
    """
    Effettua l'arricchimento dati visitando il sito web dell'attività.
    
    Ritorna un dizionario con:
      - 'email': prima email valida trovata (str)
      - 'emails': lista di tutte le email trovate (list)
      - 'cellulare_trovato': eventuale cellulare trovato sul sito (str)
      - 'tipo_cellulare': 'cellulare' o 'fisso'
      - 'whatsapp_cifre': cifre per il link wa.me
      - 'pagine_visitate': numero di pagine consultate
    """
    result = {
        "email": "",
        "emails": [],
        "cellulare_trovato": "",
        "tipo_cellulare": "",
        "whatsapp_cifre": "",
        "pagine_visitate": 0
    }
    
    if not website_url:
        return result
        
    clean_url = clean_website(website_url)
    if not clean_url:
        return result
        
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    
    pages_to_visit = [clean_url]
    visited = set()
    found_emails = set()
    found_mobiles = []
    
    base_parsed = urllib.parse.urlparse(clean_url)
    base_domain = base_parsed.netloc.lower().replace("www.", "")
    
    while pages_to_visit and len(visited) < MAX_DEEP_PAGES_PER_SITE:
        current_url = pages_to_visit.pop(0)
        if current_url in visited:
            continue
            
        visited.add(current_url)
        
        # Pausa casuale per rispetto e resilienza (1.5 - 3 secondi)
        time.sleep(random.uniform(1.2, 2.5))
        
        try:
            # Prova prima con verifica SSL, poi con fallback se certificato scaduto
            try:
                resp = session.get(current_url, timeout=8, verify=True)
            except requests.exceptions.SSLError:
                resp = session.get(current_url, timeout=8, verify=False)
                
            if resp.status_code != 200 or not resp.text:
                continue
                
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            
            # --- 1. ESTRAZIONE EMAIL DA MAILTO: ---
            for a in soup.select('a[href^="mailto:"]'):
                mailto = a.get("href", "").replace("mailto:", "").split("?")[0].strip()
                cleaned = clean_email(mailto)
                if cleaned:
                    found_emails.add(cleaned)
                    
            # --- 2. ESTRAZIONE EMAIL DA TESTO / REGEX ---
            raw_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html)
            for em in raw_emails:
                cleaned = clean_email(em)
                if cleaned:
                    found_emails.add(cleaned)
                    
            # --- 3. ESTRAZIONE LINK WHATSAPP / TELEFONI DEDICATI ---
            # Link a wa.me o api.whatsapp.com
            wa_links = soup.select('a[href*="wa.me"], a[href*="api.whatsapp.com"], a[href*="whatsapp.com/send"]')
            for wa in wa_links:
                href = wa.get("href", "")
                nums = re.findall(r'\d+', href)
                candidate = "".join(nums)
                if candidate:
                    fmt, tipo, wa_cifre = normalize_italian_phone(candidate)
                    if tipo == "cellulare":
                        found_mobiles.append((fmt, tipo, wa_cifre))
                        
            # Link telefonici tel:
            for tel_link in soup.select('a[href^="tel:"]'):
                tel_val = tel_link.get("href", "").replace("tel:", "").strip()
                fmt, tipo, wa_cifre = normalize_italian_phone(tel_val)
                if tipo == "cellulare":
                    found_mobiles.append((fmt, tipo, wa_cifre))
                    
            # --- 4. RICERCA PAGINE CONTATTI (se siamo sulla homepage) ---
            if current_url == clean_url:
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    anchor_text = a.get_text().lower().strip()
                    
                    # Controlla se il link o il testo contiene parole chiave contatti
                    is_contact = any(k in href.lower() or k in anchor_text for k in CONTACT_PAGE_KEYWORDS)
                    if is_contact:
                        abs_link = urllib.parse.urljoin(clean_url, href)
                        parsed_link = urllib.parse.urlparse(abs_link)
                        curr_domain = parsed_link.netloc.lower().replace("www.", "")
                        
                        # Assicurati che sia dello stesso sito e non già visitato
                        if curr_domain == base_domain and abs_link not in visited and abs_link not in pages_to_visit:
                            # Ignora anchor (#) interni
                            if not parsed_link.fragment or parsed_link.path != base_parsed.path:
                                pages_to_visit.append(abs_link)
                                
        except Exception:
            # Continua senza bloccare il flusso se il sito del singolo artigiano non risponde
            pass

    # Seleziona l'email più rilevante (preferibilmente info@, contatti@, preventivi@ o nome attività)
    sorted_emails = sorted(list(found_emails), key=lambda e: (
        0 if any(k in e for k in ["info@", "contatt", "preventiv", "ufficio@"]) else 1
    ))
    
    result["emails"] = sorted_emails
    result["email"] = sorted_emails[0] if sorted_emails else ""
    result["pagine_visitate"] = len(visited)
    
    if found_mobiles:
        result["cellulare_trovato"] = found_mobiles[0][0]
        result["tipo_cellulare"] = found_mobiles[0][1]
        result["whatsapp_cifre"] = found_mobiles[0][2]
        
    return result

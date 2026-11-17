"""
Configurazione per il sistema autonomo di Lead Generation & Outreach di CasaLavoroPRO e XPart.
Legge i parametri dall'ambiente (.env) o utilizza valori predefiniti ottimizzati.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Directory base dello script o dell'eseguibile compilato
if getattr(sys, 'frozen', False):
    # Se eseguito come .exe con PyInstaller, la cartella di lavoro è quella dell'eseguibile
    BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', BASE_DIR)).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = BASE_DIR

# Carica variabili d'ambiente se presente il file .env nella cartella dell'eseguibile
load_dotenv(BASE_DIR / ".env")

# --- CATEGORIE SUDDIVISE PER SETTORE (Senza numeri e senza trattini) ---
CATEGORIE_RAGGRUPPATE = {
    "Impianti e Climatizzazione": [
        "Elettricista",
        "Idraulico",
        "Caldaie e Scaldabagni",
        "Climatizzazione e Pompe di Calore",
        "Fotovoltaico e Batterie",
        "Antennista e Reti Dati",
        "Allarmi e Videosorveglianza",
        "Domotica"
    ],
    "Edilizia e Strutture": [
        "Impresa Edile",
        "Muratore",
        "Cartongessista",
        "Cappotti Termici e Isolamento",
        "Rifacimento Tetti e Lattoniere",
        "Scavi e Demolizioni"
    ],
    "Finiture e Pitture": [
        "Imbianchino",
        "Pavimentista",
        "Parquettista",
        "Resine e Microcemento",
        "Lucidatore Marmi"
    ],
    "Infissi, Porte e Metalli": [
        "Serramentista (Porte e Finestre)",
        "Fabbro",
        "Falegname",
        "Riparazione Tapparelle e Serrande",
        "Tende da Sole e Pergotende",
        "Vetraio"
    ],
    "Esterni, Verde e Pulizie": [
        "Giardiniere",
        "Impianti di Irrigazione",
        "Disinfestazioni",
        "Impresa di Pulizie",
        "Spurghi e Fognature"
    ],
    "Tecnici Abilitati": [
        "Geometra",
        "Architetto",
        "Ingegnere",
        "Perito Termotecnico"
    ]
}

# Lista piatta di tutte le categorie
DEFAULT_CATEGORIE = [cat for sublist in CATEGORIE_RAGGRUPPATE.values() for cat in sublist]

DEFAULT_CITTA = [
    "Vicenza",
    "Bassano del Grappa",
    "Padova",
    "Schio",
    "Thiene",
    "Arzignano",
    "Treviso",
    "Verona"
]

# Scaletta limiti selezionabili (fino a 1000 a passi di 100)
LIMITI_RICERCA = [20, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
DEFAULT_LIMIT_PER_SEARCH = int(os.getenv("SCRAPER_LIMIT", 100))

# Pause casuali per simulare comportamento umano ed evitare blocchi (in secondi)
MIN_DELAY_SECONDS = float(os.getenv("MIN_DELAY", 2.5))
MAX_DELAY_SECONDS = float(os.getenv("MAX_DELAY", 5.5))

# Esecuzione browser in modalità headless
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "True").lower() in ("true", "1", "yes")

# Esecuzione del deep scraping sui siti web trovati
DEEP_SCRAPING_ENABLED = os.getenv("DEEP_SCRAPING", "True").lower() in ("true", "1", "yes")
MAX_DEEP_PAGES_PER_SITE = int(os.getenv("MAX_DEEP_PAGES", 3))

# --- FILE DI DATI ---
FILE_ESTRATTI = BASE_DIR / os.getenv("FILE_ESTRATTI", "artigiani_estratti.csv")
FILE_REGISTRO = BASE_DIR / os.getenv("FILE_REGISTRO", "registro_contattati.csv")
FILE_DASHBOARD = BASE_DIR / "dashboard_contatti.html"
FILE_XPART_CSV = BASE_DIR / "xpart_ricambi_estratti.csv"

# --- INTEGRAZIONE DATABASE SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_TABLE_BOZZE = os.getenv("SUPABASE_TABLE_BOZZE", "aziende_drafts")
SUPABASE_TABLE_XPART = os.getenv("SUPABASE_TABLE_XPART", "xpart_ricambi")

# --- BRANDING & MITTENTE CASALAVOROPRO (Dati Utente Fissi) ---
PLATFORM_NAME = "CasaLavoroPRO"
PLATFORM_URL = os.getenv("PLATFORM_URL", "https://casalavoropro.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Marco Bellosi")
SENDER_PHONE = os.getenv("SENDER_PHONE", "3423255008")  # Numero WhatsApp mittente fisso
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "bellosi2022@gmail.com")  # Email mittente fissa
LOGO_URL = os.getenv("LOGO_URL", "https://casalavoropro.com/logo.png")
FOTO_ALLEGATE = os.getenv("FOTO_ALLEGATE", "")

# --- CONFIGURAZIONE SMTP PER OUTREACH EMAIL ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")

# --- TEMPLATE MESSAGGIO WHATSAPP ---
WHATSAPP_MESSAGE_TEMPLATE = (
    "Ciao {nome_attivita}, sono {sender_name} di CasaLavoroPRO.\n\n"
    "Ho notato la tua attività di {categoria} a {citta} e la qualità dei tuoi interventi sul territorio. "
    "Stiamo inserendo gratuitamente i migliori professionisti della zona sulla nostra piattaforma "
    "per metterli in contatto diretto con clienti locali che cercano lavori di casa, "
    "senza gettoni e senza alcuna commissione sui preventivi.\n\n"
    "Puoi vedere la piattaforma qui: {platform_url}\n"
    "Se vuoi farti trovare gratis dai proprietari di casa, ti predisponiamo noi la scheda "
    "oppure puoi registrarti direttamente in 2 minuti.\n\n"
    "Buon lavoro e a presto!"
)

# --- TEMPLATE EMAIL ---
EMAIL_SUBJECT_TEMPLATE = "Richieste preventivo e visibilità gratuita a {citta} per {nome_attivita}"

EMAIL_TEXT_TEMPLATE = """Ciao {nome_attivita},

Mi chiamo {sender_name} e ti scrivo dal team di {platform_name} ({platform_url}).

Ho notato la tua attività di {categoria} a {citta} e la qualità dei tuoi lavori. 
In questo periodo stiamo selezionando e inserendo gratuitamente i migliori professionisti del territorio sulla nostra piattaforma, per metterli in contatto diretto con clienti della provincia di {citta} che cercano interventi e ristrutturazioni per la casa.

Perché CasaLavoroPRO è diversa?
- ZERO gettoni per rispondere: non paghi per comprare contatti o fare preventivi a vuoto.
- ZERO commissioni sui lavori che concludi: il cliente paga direttamente te, al 100%.
- Profilo verificato con recensioni e galleria lavori per valorizzare la tua reputazione locale.
- Contatto diretto via telefono, chat o WhatsApp con i proprietari di casa.

Il nostro obiettivo è creare una rete locale etica, aperta e trasparente, lontana dalle logiche dei vecchi portali a gettone.

Se desideri avere una vetrina gratuita ed essere contattato per i lavori nella tua zona, puoi:
1. Rispondere direttamente a questa email con la tua conferma (provvederemo noi a predisporre la tua scheda)
2. Oppure registrarti autonomamente in 2 minuti su: {platform_url}

Ti auguro una buona giornata e buon lavoro!

Un cordiale saluto,
{sender_name}
{platform_name} — Il marketplace etico per i professionisti della casa
Sito web: {platform_url}
Email: {sender_email}

---
Ricevi questa comunicazione informativa B2B perché la tua attività opera nel settore casa nella zona di {citta}. Se non desideri ricevere ulteriori aggiornamenti, rispondi semplicemente con 'Cancellami' e rimuoveremo immediatamente il tuo contatto.
"""

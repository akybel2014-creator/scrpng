"""
Modulo di normalizzazione e validazione dati per CasaLavoroPRO:
- Formattazione e classificazione numeri di telefono italiani (Fisso / Cellulare).
- Normalizzazione link WhatsApp (wa.me).
- Pulizia e validazione email.
- Pulizia URL e stringhe di testo.
"""

import re
import urllib.parse
import phonenumbers
from phonenumbers import PhoneNumberType

# Estensioni e pattern da escludere per evitare falsi positivi nelle email
EXCLUDED_EMAIL_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico", 
    ".js", ".css", ".woff", ".woff2", ".ttf", ".pdf", ".zip"
)

IGNORED_EMAIL_KEYWORDS = (
    "sentry.io", "wixpress.com", "schema.org", "example.com",
    "domain.com", "yourdomain.com", "test@test", "email@email",
    "noreply", "no-reply", "donotreply", "wordpress@cloud"
)


def clean_text(text: str) -> str:
    """Rimuove caratteri speciali, icone e spaziature anomale."""
    if not text:
        return ""
    # Rimuove caratteri unicode di icone tipici di Google Maps (es. \ue0b0, \ue80b, \ue0c8)
    text = re.sub(r'[\ue000-\uf8ff]', '', text)
    # Rimuove spazi doppi o newline
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_italian_phone(raw_phone: str) -> tuple[str, str, str]:
    """
    Normalizza e classifica un numero di telefono italiano.
    
    Ritorna una tupla:
      (telefono_formattato, tipo_telefono, cifre_whatsapp)
      
    - telefono_formattato: es. '+39 340 396 9951' oppure '+39 0444 123456'
    - tipo_telefono: 'cellulare' oppure 'fisso'
    - cifre_whatsapp: es. '393403969951' (per comporre l'url wa.me/...)
    """
    if not raw_phone:
        return "", "sconosciuto", ""
        
    raw_str = clean_text(str(raw_phone))
    # Mantieni solo cifre e segno +
    digits_only = re.sub(r'[^\d+]', '', raw_str)
    if not digits_only:
        return "", "sconosciuto", ""
        
    # Gestisci prefisso 0039 -> +39
    if digits_only.startswith('0039'):
        digits_only = '+' + digits_only[2:]
    elif digits_only.startswith('39') and len(digits_only) >= 11 and not digits_only.startswith('+'):
        digits_only = '+' + digits_only
        
    # 1. Prova con la libreria internazionale phonenumbers
    try:
        parsed = phonenumbers.parse(digits_only, "IT")
        if phonenumbers.is_valid_number(parsed):
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            wa_digits = re.sub(r'[^\d]', '', e164)
            
            # Determina tipo
            p_type = phonenumbers.number_type(parsed)
            nat_str = re.sub(r'[^\d]', '', phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL))
            
            if p_type == PhoneNumberType.MOBILE or nat_str.startswith('3'):
                tipo = 'cellulare'
            else:
                tipo = 'fisso'
                
            return international, tipo, wa_digits
    except Exception:
        pass
        
    # 2. Regola euristica solida per l'Italia (cellulari 3... fissi 0...)
    pure_digits = re.sub(r'[^\d]', '', digits_only)
    if pure_digits.startswith('0039'):
        pure_digits = pure_digits[4:]
    elif pure_digits.startswith('39') and len(pure_digits) >= 11:
        pure_digits = pure_digits[2:]
        
    if pure_digits.startswith('3'):
        # Cellulare italiano
        formatted = f"+39 {pure_digits[:3]} {pure_digits[3:6]} {pure_digits[6:]}".strip()
        wa_digits = f"39{pure_digits}"
        return formatted, "cellulare", wa_digits
    elif pure_digits.startswith('0'):
        # Fisso italiano
        formatted = f"+39 {pure_digits}"
        wa_digits = f"39{pure_digits}"
        return formatted, "fisso", wa_digits
        
    # Default fallback
    return raw_str, "sconosciuto", re.sub(r'[^\d]', '', digits_only)


def clean_email(raw_email: str) -> str:
    """Valida e ripulisce un indirizzo email, escludendo falsi positivi."""
    if not raw_email:
        return ""
        
    email = raw_email.strip().lower()
    # Rimuovi prefissi mailto:
    if email.startswith("mailto:"):
        email = email.split("mailto:")[-1].split("?")[0].strip()
        
    # Estrai con regex se ci sono caratteri di troppo
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', email)
    if not match:
        return ""
    email = match.group(0).strip(".").lower()
    
    # Escludi estensioni di file immagine/asset scambiati per email
    if any(email.endswith(ext) for ext in EXCLUDED_EMAIL_EXTENSIONS):
        return ""
        
    # Escludi domini e keyword non utili
    if any(kw in email for kw in IGNORED_EMAIL_KEYWORDS):
        return ""
        
    return email


def clean_website(raw_url: str) -> str:
    """Ripulisce e normalizza l'indirizzo web."""
    if not raw_url:
        return ""
        
    url = clean_text(raw_url)
    
    # Se è un redirect di Google, estrai l'url reale
    if "google.com/url?q=" in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if "q" in params:
            url = params["q"][0]
            
    # Aggiungi protocollo https se mancante
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    # Rimuovi parametri di tracking comuni
    try:
        parsed = urllib.parse.urlparse(url)
        # Tieni solo schema + netloc + path pulito
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean.rstrip("/")
    except Exception:
        return url

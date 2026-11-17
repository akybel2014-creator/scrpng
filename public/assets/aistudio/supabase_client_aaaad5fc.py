"""
INTEGRAZIONE DATABASE SUPABASE PER CASALAVOROPRO E XPART
========================================================
Gestisce la sincronizzazione e il salvataggio automatico delle schede:
1. CasaLavoroPRO: Creazione automatica bozze in stato 'draft_scraping' con categoria,
   indirizzo (provincia/comune), recapiti ed estratti recensioni dal web.
2. XPart: Popolamento massivo del catalogo ricambi auto, codici OEM,
   cross-reference e compatibilità veicoli.
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger("SupabaseClient")

# Parametri di default configurabili da .env o interfaccia grafica
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
TABLE_BOZZE_CASALAVORO = os.getenv("SUPABASE_TABLE_BOZZE", "aziende_drafts")
TABLE_RICAMBI_XPART = os.getenv("SUPABASE_TABLE_XPART", "xpart_ricambi")

# Tentativo di inizializzazione client ufficiale Supabase
_supabase_sdk_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase_sdk_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("[Supabase] Connessione SDK inizializzata con successo.")
    except Exception as e:
        logger.debug(f"[Supabase] Inizializzazione SDK non riuscita, uso fallback REST: {e}")


def is_supabase_configured() -> bool:
    """Verifica se le credenziali Supabase sono state inserite."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    return bool(url and key)


def update_supabase_credentials(new_url: str, new_key: str):
    """Aggiorna le credenziali in memoria e ricarica il client."""
    global SUPABASE_URL, SUPABASE_KEY, _supabase_sdk_client
    SUPABASE_URL = new_url.strip().rstrip("/")
    SUPABASE_KEY = new_key.strip()
    os.environ["SUPABASE_URL"] = SUPABASE_URL
    os.environ["SUPABASE_KEY"] = SUPABASE_KEY

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            from supabase import create_client
            _supabase_sdk_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("[Supabase] Client aggiornato con nuove credenziali.")
        except Exception as e:
            _supabase_sdk_client = None
            logger.warning(f"[Supabase] Errore aggiornamento client: {e}")


# ==============================================================================
# MODULO 1: CASALAVOROPRO — GESTIONE BOZZE (draft_scraping)
# ==============================================================================

def create_artisan_draft(artisan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea automaticamente una scheda in stato di 'bozza' ('draft_scraping') su Supabase.
    Include:
      - categoria merceologica
      - indirizzo (provincia/comune)
      - contatti estratti (telefono fisso/cellulare, email, sito, wa.me)
      - recensioni web (voto medio, numero recensioni, estratti recensioni)
    """
    now_iso = datetime.now().isoformat()
    
    # Normalizzazione payload per Supabase
    draft_record = {
        "status": "draft_scraping",
        "nome": artisan_data.get("nome_attivita", "").strip(),
        "categoria": artisan_data.get("categoria", "").strip(),
        "comune": artisan_data.get("citta", "").strip(),
        "provincia": artisan_data.get("provincia", "") or artisan_data.get("citta", "").strip(),
        "indirizzo": artisan_data.get("indirizzo", "").strip(),
        "telefono": artisan_data.get("telefono_principale", "").strip(),
        "tipo_telefono": artisan_data.get("tipo_telefono", "").strip(),
        "email": artisan_data.get("email", "").strip(),
        "sito_web": artisan_data.get("sito_web", "").strip(),
        "whatsapp_link": artisan_data.get("whatsapp_link", "").strip(),
        "recensioni": {
            "rating": artisan_data.get("rating_recensioni", ""),
            "totale": artisan_data.get("numero_recensioni", ""),
            "estratti": artisan_data.get("recensioni_estratte", [])
        },
        "fonte": artisan_data.get("fonte", "Google Maps + Deep Scraping"),
        "logo_url": (
            artisan_data.get("logo_aziendale")
            or artisan_data.get("logo_url")
            or os.getenv("LOGO_URL", "")
        ).strip(),
        "created_at": now_iso,
        "updated_at": now_iso
    }

    if not is_supabase_configured():
        logger.debug("[Supabase] Credenziali non presenti: bozza salvata solo in locale CSV/JSON.")
        return {"status": "local_only", "record": draft_record}

    # 1. Prova con Supabase SDK se disponibile
    if _supabase_sdk_client:
        try:
            res = _supabase_sdk_client.table(TABLE_BOZZE_CASALAVORO).insert(draft_record).execute()
            logger.info(f"[Supabase] Bozza creata con successo: {draft_record['nome']}")
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.warning(f"[Supabase SDK] Errore inserimento bozza ({e}), provo fallback PostgREST...")

    # 2. Fallback diretto REST su PostgREST di Supabase
    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_BOZZE_CASALAVORO}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        resp = requests.post(endpoint, json=draft_record, headers=headers, timeout=8)
        if resp.status_code in (200, 201):
            logger.info(f"[Supabase REST] Bozza inserita con successo: {draft_record['nome']}")
            return {"status": "success", "data": resp.json()}
        else:
            logger.warning(f"[Supabase REST] Errore status {resp.status_code}: {resp.text}")
            return {"status": "error", "error": resp.text}
    except Exception as e:
        logger.error(f"[Supabase REST] Eccezione di rete: {e}")
        return {"status": "error", "error": str(e)}


def update_artisan_draft_status(destinatario_o_nome: str, nuovo_stato: str, note: str = "") -> bool:
    """Aggiorna lo stato della bozza su Supabase (es. da 'draft_scraping' a 'contattato_whatsapp')."""
    if not is_supabase_configured():
        return False

    now_iso = datetime.now().isoformat()
    update_payload = {
        "status": nuovo_stato,
        "note_outreach": note,
        "updated_at": now_iso
    }

    try:
        if _supabase_sdk_client:
            _supabase_sdk_client.table(TABLE_BOZZE_CASALAVORO).update(update_payload).or_(
                f"telefono.eq.{destinatario_o_nome},email.eq.{destinatario_o_nome},nome.eq.{destinatario_o_nome}"
            ).execute()
            return True
            
        endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_BOZZE_CASALAVORO}?or=(telefono.eq.{destinatario_o_nome},email.eq.{destinatario_o_nome})"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.patch(endpoint, json=update_payload, headers=headers, timeout=6)
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.debug(f"[Supabase] Impossibile aggiornare stato bozza: {e}")
        return False


# ==============================================================================
# MODULO 2: XPART — POPOLAMENTO RICAMBI, CODICI OEM E COMPATIBILITÀ
# ==============================================================================

def save_xpart_oem_part(part_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inserisce o aggiorna un ricambio auto nel database di XPart su Supabase:
    - codice OEM
    - codici cross-reference / aftermarket equivalenti
    - compatibilità veicoli (Marca, Modello, Anno, Motore/KW)
    - categoria ricambio, prezzo stimato, scaffale e condizione
    """
    now_iso = datetime.now().isoformat()

    record = {
        "id_articolo": part_data.get("id_articolo", f"RC-{int(datetime.now().timestamp()) % 100000:05d}"),
        "codice_oem": part_data.get("codice_oem", "").strip().upper(),
        "cross_references": part_data.get("cross_references", []),
        "nome_ricambio": part_data.get("nome_ricambio", "").strip(),
        "categoria": part_data.get("categoria", "").strip(),
        "marca_veicolo": part_data.get("marca_veicolo", "").strip().upper(),
        "modello_veicolo": part_data.get("modello_veicolo", "").strip(),
        "anno_compatibilita": part_data.get("anno_compatibilita", "").strip(),
        "motorizzazione": part_data.get("motorizzazione", "").strip(),
        "prezzo": part_data.get("prezzo", "N/D"),
        "condizione": part_data.get("condizione", "GRADO A"),
        "scaffale": part_data.get("scaffale", "B-04-L2"),
        "fonte_scraping": part_data.get("fonte_scraping", "Catalogo OEM Web"),
        "created_at": now_iso
    }

    if not is_supabase_configured():
        logger.debug("[XPart] Credenziali Supabase non configurate: ricambio salvato su file locale CSV.")
        return {"status": "local_only", "record": record}

    # Inserimento via SDK o REST
    if _supabase_sdk_client:
        try:
            res = _supabase_sdk_client.table(TABLE_RICAMBI_XPART).upsert(record).execute()
            logger.info(f"[XPart Supabase] Salvato ricambio OEM: {record['codice_oem']} - {record['nome_ricambio']}")
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.warning(f"[XPart SDK] Fallback REST per errore: {e}")

    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_RICAMBI_XPART}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        resp = requests.post(endpoint, json=record, headers=headers, timeout=8)
        if resp.status_code in (200, 201):
            logger.info(f"[XPart REST] Ricambio inserito: {record['codice_oem']}")
            return {"status": "success", "data": resp.json()}
        else:
            return {"status": "error", "error": resp.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

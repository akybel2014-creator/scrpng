"""
MODULO ANTI-TRACCIA E RATE LIMITING (STEALTH ENGINE)
====================================================
Implementa strategie avanzate anti-rilevamento per lo scraping di:
1. CasaLavoroPRO (Google Maps e siti web artigiani)
2. XPart (Cataloghi ricambi auto, codici OEM e cross-reference)

Funzionalità:
- Rate limiting con ritardi casuali distribuiti (jitter) per simulare navigazione umana.
- Pool dinamico e rotazione di User-Agent realistici e aggiornati.
- Supporto e rotazione automatica di Proxy (HTTP, HTTPS, SOCKS5).
- Mascheramento delle impronte digitali di Chromium (navigator.webdriver, plugins, languages).
- Backoff esponenziale automatico in caso di rallentamenti o blocchi di rete.
"""

import os
import time
import random
import logging
from typing import Optional, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger("StealthEngine")

# Pool di User-Agent moderni e realistici (Desktop Windows, Mac e Linux)
USER_AGENTS_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    # Safari / Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
]

VIEWPORTS_POOL = [
    (1920, 1080),
    (1536, 864),
    (1440, 900),
    (1366, 768),
    (1680, 1050)
]


class ProxyRotator:
    """Gestisce la rotazione e la verifica di proxy HTTP/HTTPS/SOCKS5."""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        self.proxies: List[str] = []
        if proxies:
            self.proxies = [p.strip() for p in proxies if p and p.strip()]
        self._current_idx = 0

    def load_from_file_or_env(self, filepath: Optional[str] = None):
        """Carica la lista di proxy da variabile d'ambiente o file di testo."""
        env_proxies = os.getenv("SCRAPER_PROXIES", "")
        if env_proxies:
            self.proxies = [p.strip() for p in env_proxies.split(",") if p.strip()]
            return

        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    self.proxies.extend(lines)
            except Exception as e:
                logger.warning(f"Errore lettura file proxy {filepath}: {e}")

    def get_next(self) -> Optional[str]:
        """Ritorna il prossimo proxy della lista a rotazione circolare."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._current_idx % len(self.proxies)]
        self._current_idx += 1
        return proxy

    def get_requests_dict(self) -> Optional[Dict[str, str]]:
        """Formatta il proxy corrente per le richieste della libreria requests."""
        p = self.get_next()
        if not p:
            return None
        if not p.startswith("http://") and not p.startswith("https://") and not p.startswith("socks5://"):
            p = f"http://{p}"
        return {"http": p, "https": p}

    def has_proxies(self) -> bool:
        return len(self.proxies) > 0


# Istanza singleton globale del proxy rotator
global_proxy_rotator = ProxyRotator()


class StealthController:
    """Controlla i ritardi casuali, le pause umane e l'applicazione delle impostazioni stealth."""
    
    def __init__(self, min_delay: float = 2.5, max_delay: float = 6.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.consecutive_errors = 0

    def sleep_human(self, multiplier: float = 1.0, reason: str = ""):
        """
        Esegue una pausa casuale con micro-variazioni (jitter) per simulare l'attesa umana.
        Se si verificano errori o rate-limit recenti, allunga progressivamente la pausa.
        """
        base_delay = random.uniform(self.min_delay, self.max_delay) * multiplier
        
        # Aggiungi jitter casuale (±15%)
        jitter = random.uniform(-0.15, 0.25) * base_delay
        total_delay = max(1.2, base_delay + jitter)
        
        # Se ci sono errori consecutivi, applica backoff progressivo
        if self.consecutive_errors > 0:
            extra_backoff = min(30.0, self.consecutive_errors * 3.5)
            total_delay += extra_backoff
            
        if reason:
            logger.debug(f"[Stealth] Pausa umana: {total_delay:.2f}s ({reason})")
        time.sleep(total_delay)

    def record_success(self):
        """Azzera il contatore di errori per ripristinare la velocità standard."""
        self.consecutive_errors = 0

    def record_throttle_or_error(self):
        """Registra una risposta rallentata o errore per applicare backoff automatico."""
        self.consecutive_errors += 1
        backoff_time = min(40.0, 5.0 * (2 ** (self.consecutive_errors - 1)))
        logger.warning(f"[Stealth Anti-Blocco] Rilevato potenziale rate-limit. Backoff automatico: {backoff_time:.1f}s...")
        time.sleep(backoff_time)

    def get_random_user_agent(self) -> str:
        """Restituisce un User-Agent realistico selezionato casualmente dal pool."""
        return random.choice(USER_AGENTS_POOL)

    def get_random_viewport(self) -> tuple[int, int]:
        """Restituisce una risoluzione casuale tipica di monitor desktop."""
        return random.choice(VIEWPORTS_POOL)

    def get_stealth_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Genera header HTTP completi di Client Hints per confondersi con browser reali."""
        ua = self.get_random_user_agent()
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site" if referer else "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"'
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def apply_selenium_stealth(self, driver):
        """
        Applica script CDP (Chrome DevTools Protocol) per nascondere navigator.webdriver
        e mascherare parametri di automazione rilevabili da Cloudflare, Akamai e Google.
        """
        try:
            # Rimuove il flag navigator.webdriver
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    // Simula plugin standard
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    // Lingue realistiche
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['it-IT', 'it', 'en-US', 'en']
                    });
                    // Oggetto window.chrome standard
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                """
            })
        except Exception as e:
            logger.debug(f"Impossibile applicare CDP stealth: {e}")


# Istanza singleton globale
stealth_engine = StealthController()

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search,
  Square,
  RotateCw,
  FolderOpen,
  MessageCircle,
  Globe,
  Mail,
  Check,
  Clock,
  AlertTriangle,
  Save,
  X,
  ExternalLink,
  Car,
  Hammer,
  Settings,
  Upload,
  FlaskConical,
  RefreshCw,
  Send,
  Eraser,
} from 'lucide-react';
import {
  CATEGORIE_RAGGRUPPATE,
  ITALIA_GEO_DATABASE,
  XPART_CATEGORIE,
  XPART_MARCHE,
} from './data/geoData';
import { parseCsv } from './utils/csvParser';

interface Artisan {
  id: number;
  nome_attivita: string;
  categoria: string;
  citta: string;
  telefono: string;
  tipo_telefono: string;
  email: string;
  sito_web: string;
  indirizzo: string;
  rating_recensioni: string;
  numero_recensioni: string;
  recensioni_estratte: string;
  is_contacted: boolean;
  wa_contacted: boolean;
  wa_date: string;
  em_contacted: boolean;
}

interface XPartItem {
  id_articolo: string;
  codice_oem: string;
  cross_references: string;
  nome_ricambio: string;
  categoria: string;
  marca_veicolo: string;
  modello_veicolo: string;
  anno_compatibilita: string;
  motorizzazione: string;
  prezzo: string;
  condizione: string;
  scaffale: string;
  fonte_scraping: string;
  data_estrazione: string;
}

interface AppSettings {
  sender_name: string;
  sender_phone: string;
  sender_email: string;
  logo_url: string;
  logo_preview_data?: string;
  foto_allegate: string;
  supabase_url: string;
  supabase_key: string;
  supabase_table_bozze: string;
  supabase_table_xpart: string;
}

type MainTab = 'clp' | 'xpart' | 'settings';
type ArtisanFilter = 'all' | 'todo' | 'sent' | 'has_email' | 'has_reviews';

const DEFAULT_SETTINGS: AppSettings = {
  sender_name: 'Marco Bellosi',
  sender_phone: '3423255008',
  sender_email: 'bellosi2022@gmail.com',
  logo_url: 'https://casalavoropro.com/logo.png',
  logo_preview_data: '',
  foto_allegate: '',
  supabase_url: '',
  supabase_key: '',
  supabase_table_bozze: 'aziende_drafts',
  supabase_table_xpart: 'xpart_ricambi',
};

const STORAGE_CHECKED_KEY = 'clp_preview_checked_overrides';
const STORAGE_SETTINGS_KEY = 'clp_preview_settings';

function formatPhoneForWa(phone: string): string {
  const cifre = phone.replace(/\D/g, '');
  if (cifre.startsWith('0039')) return `39${cifre.slice(4)}`;
  if (cifre.startsWith('39') && cifre.length >= 11) return cifre;
  return `39${cifre}`;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<MainTab>('clp');
  const [artisans, setArtisans] = useState<Artisan[]>([]);
  const [xpartItems, setXpartItems] = useState<XPartItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [toastMsg, setToastMsg] = useState<string>('');
  const toastTimerRef = useRef<number | null>(null);

  // Settings
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_SETTINGS_KEY);
      if (saved) return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
    } catch {
      // ignore
    }
    return DEFAULT_SETTINGS;
  });
  const [logoVisible, setLogoVisible] = useState(true);
  const logoFileInputRef = useRef<HTMLInputElement | null>(null);

  // Spazio Test Generazione Email (Sandbox isolata)
  const buildSandboxPreviewBody = (phone: string, fotoLink: string) => {
    const cleanPhone = (phone || '3423255008').trim() || '3423255008';
    const waDigits = cleanPhone
      .replace(/\D/g, '')
      .replace(/^0039/, '')
      .replace(/^39(?=\d{9,})/, '');
    const waLink = waDigits ? `https://wa.me/39${waDigits}` : 'https://casalavoropro.com';
    const extraFoto = fotoLink.trim()
      ? `\nGalleria lavori e foto: ${fotoLink.trim()}\n`
      : '';

    return `Gentile Professionista,

Ti scriviamo dal team di CasaLavoroPRO (https://casalavoropro.com).

Abbiamo selezionato la tua attività tra i migliori professionisti locali e stiamo attivando gratuitamente le schede di presentazione sulla nostra piattaforma per metterti in contatto diretto con clienti della tua zona alla ricerca di lavori per la casa.

Perché scegliere CasaLavoroPRO:
- ZERO gettoni per rispondere alle richieste di preventivo
- ZERO commissioni sui lavori conclusi (incassi il 100% direttamente dal cliente)
- Contatto diretto tramite telefono, email o WhatsApp
${extraFoto}
Visita il portale ufficiale: https://casalavoropro.com
Attiva o verifica la tua scheda gratuita: https://casalavoropro.com

Per qualsiasi informazione o supporto diretto:
WhatsApp: ${cleanPhone} (${waLink})
Email: info@casalavoropro.com

Un cordiale saluto,
CasaLavoroPRO
Sito web: https://casalavoropro.com
Email: info@casalavoropro.com
WhatsApp: ${cleanPhone}`;
  };

  const [sandboxTestEmail, setSandboxTestEmail] = useState('bellosi2022@gmail.com');
  const [sandboxSubject, setSandboxSubject] = useState(
    'Invito gratuito su CasaLavoroPRO — Nuove richieste clienti nella tua zona'
  );
  const [sandboxBody, setSandboxBody] = useState(() =>
    buildSandboxPreviewBody(settings.sender_phone, settings.foto_allegate)
  );
  const [sandboxStatus, setSandboxStatus] = useState('');

  // CLP Controls
  const [categoria, setCategoria] = useState('Elettricista');
  const [regione, setRegione] = useState('Veneto');
  const [zona, setZona] = useState('Vicenza e provincia (Tutta)');
  const [cittaLibera, setCittaLibera] = useState('');
  const [limite, setLimite] = useState(100);
  const [deepScrape, setDeepScrape] = useState(true);

  // CLP Table filters
  const [tableSearch, setTableSearch] = useState('');
  const [artisanFilter, setArtisanFilter] = useState<ArtisanFilter>('all');

  // CLP Simulated Scraping Progress (Preview)
  const [isScraping, setIsScraping] = useState(false);
  const [progressStatus, setProgressStatus] = useState('');
  const [progressCount, setProgressCount] = useState(0);
  const [progressTarget, setProgressTarget] = useState(100);
  const scrapeTimerRef = useRef<number | null>(null);

  // XPart Controls & Filter
  const [xpartMarca, setXpartMarca] = useState('FORD');
  const [xpartModello, setXpartModello] = useState('Focus Mk3');
  const [xpartCategoria, setXpartCategoria] = useState('Fari e Fanali (Illuminazione)');
  const [xpartLimite, setXpartLimite] = useState(50);
  const [xpartSearch, setXpartSearch] = useState('');
  const [isXpartScraping, setIsXpartScraping] = useState(false);
  const [xpartProgressStatus, setXpartProgressStatus] = useState('');
  const [xpartProgressCount, setXpartProgressCount] = useState(0);
  const xpartTimerRef = useRef<number | null>(null);

  // Modals
  const [waModalArtisan, setWaModalArtisan] = useState<Artisan | null>(null);
  const [waModalText, setWaModalText] = useState('');

  const [emailModalArtisan, setEmailModalArtisan] = useState<Artisan | null>(null);
  const [emailModalSubject, setEmailModalSubject] = useState('');
  const [emailModalBody, setEmailModalBody] = useState('');

  const [duplicateConfirm, setDuplicateConfirm] = useState<{
    artisan: Artisan;
    channel: 'whatsapp' | 'email';
  } | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToastMsg(''), 3200);
  };

  const loadDataFromCsv = async () => {
    setLoading(true);
    try {
      const [artRes, regRes, xpartRes] = await Promise.all([
        fetch('/assets/aistudio/artigiani_estratti_ca1fa768.csv'),
        fetch('/assets/aistudio/registro_contattati_e47fc4a0.csv'),
        fetch('/assets/aistudio/xpart_ricambi_estratti_2a6ff97c.csv'),
      ]);

      const [artText, regText, xpartText] = await Promise.all([
        artRes.text(),
        regRes.text(),
        xpartRes.text(),
      ]);

      const rawArtisans = parseCsv(artText);
      const rawRegistry = parseCsv(regText);
      const rawXpart = parseCsv(xpartText);

      // Build registry map mirroring app_gui.py / outreach.py
      const registry: Record<string, Record<string, string>> = {};
      for (const r of rawRegistry) {
        const dest = (r.destinatario || '').trim();
        const name = (r.nome_attivita || '').trim().toLowerCase();
        const canale = (r.canale || '').trim().toUpperCase();
        if (dest) registry[`${canale}:${dest}`] = r;
        if (name) registry[`${canale}:name:${name}`] = r;
      }

      let overrides: Record<string, boolean> = {};
      try {
        const rawOverrides = localStorage.getItem(STORAGE_CHECKED_KEY);
        if (rawOverrides) overrides = JSON.parse(rawOverrides);
      } catch {
        // ignore
      }

      const enriched: Artisan[] = rawArtisans.map((a, idx) => {
        const tel = (a.telefono_principale || '').trim();
        const nome = (a.nome_attivita || '').trim();
        const em = (a.email || '').trim();
        const cat = (a.categoria || '').trim();
        const cit = (a.citta || '').trim();
        const sito = (a.sito_web || '').trim();
        const tipo = (a.tipo_telefono || '').trim().toLowerCase();
        const indirizzo = (a.indirizzo || '').trim();
        const rating = (a.rating_recensioni || '').trim();
        const numRec = (a.numero_recensioni || '').trim();
        const recEstr = (a.recensioni_estratte || '').trim();

        const waKey = `WHATSAPP:${tel}`;
        const waContacted =
          Boolean(tel && registry[waKey]) ||
          Boolean(nome && registry[`WHATSAPP:name:${nome.toLowerCase()}`]);
        const waDate = registry[waKey]?.data_ora || '';

        const emKey = `EMAIL:${em.toLowerCase()}`;
        const emContacted = Boolean(
          em && (registry[emKey] || registry[`EMAIL:name:${nome.toLowerCase()}`])
        );

        const manualKey = tel ? `MANUALE:${tel}` : '';
        const manualEm = em ? `MANUALE:${em.toLowerCase()}` : '';
        const manualName = nome ? `MANUALE:name:${nome.toLowerCase()}` : '';

        const csvContacted = Boolean(
          waContacted ||
            emContacted ||
            (manualKey && registry[manualKey]) ||
            (manualEm && registry[manualEm]) ||
            (manualName && registry[manualName])
        );

        const overrideKey = `${nome}::${tel || em}`;
        const isContacted =
          overrideKey in overrides ? overrides[overrideKey] : csvContacted;

        return {
          id: idx + 1,
          nome_attivita: nome,
          categoria: cat,
          citta: cit,
          telefono: tel,
          tipo_telefono: tipo,
          email: em,
          sito_web: sito,
          indirizzo,
          rating_recensioni: rating,
          numero_recensioni: numRec,
          recensioni_estratte: recEstr,
          is_contacted: isContacted,
          wa_contacted: waContacted,
          wa_date: waDate,
          em_contacted: emContacted,
        };
      });

      setArtisans(enriched);
      setXpartItems(rawXpart as unknown as XPartItem[]);
    } catch (err) {
      console.error('Errore caricamento CSV:', err);
      showToast('Errore caricamento archivi CSV');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDataFromCsv();
    return () => {
      if (scrapeTimerRef.current) window.clearInterval(scrapeTimerRef.current);
      if (xpartTimerRef.current) window.clearInterval(xpartTimerRef.current);
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    };
  }, []);

  const regionZones = useMemo(() => {
    const db = ITALIA_GEO_DATABASE[regione];
    return db ? Object.keys(db) : [];
  }, [regione]);

  const handleRegionChange = (newRegion: string) => {
    setRegione(newRegion);
    const zones = Object.keys(ITALIA_GEO_DATABASE[newRegion] || {});
    setZona(zones[0] || '__custom__');
  };

  // Stats CLP
  const stats = useMemo(() => {
    const tot = artisans.length;
    const sent = artisans.filter((a) => a.is_contacted).length;
    const todo = tot - sent;
    const cell = artisans.filter((a) => a.tipo_telefono === 'cellulare').length;
    const em = artisans.filter((a) => a.email && a.email.includes('@')).length;
    const reviews = artisans.filter((a) => Boolean(a.rating_recensioni)).length;
    return { tot, sent, todo, cell, em, reviews };
  }, [artisans]);

  const filteredArtisans = useMemo(() => {
    const q = tableSearch.trim().toLowerCase();
    return artisans.filter((a) => {
      const matchSearch =
        !q ||
        a.nome_attivita.toLowerCase().includes(q) ||
        a.citta.toLowerCase().includes(q) ||
        a.categoria.toLowerCase().includes(q) ||
        a.telefono.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q);

      if (!matchSearch) return false;
      if (artisanFilter === 'todo') return !a.is_contacted;
      if (artisanFilter === 'sent') return a.is_contacted;
      if (artisanFilter === 'has_email') return Boolean(a.email);
      if (artisanFilter === 'has_reviews') return Boolean(a.rating_recensioni);
      return true;
    });
  }, [artisans, tableSearch, artisanFilter]);

  // Stats XPart
  const xpartStats = useMemo(() => {
    const tot = xpartItems.length;
    const oemSet = new Set(xpartItems.map((x) => x.codice_oem));
    const crossCount = xpartItems.reduce((acc, x) => {
      if (!x.cross_references) return acc;
      return acc + x.cross_references.split('|').length;
    }, 0);
    return { tot, oemUnique: oemSet.size, crossCount };
  }, [xpartItems]);

  const filteredXpart = useMemo(() => {
    const q = xpartSearch.trim().toLowerCase();
    if (!q) return xpartItems;
    return xpartItems.filter(
      (x) =>
        (x.codice_oem || '').toLowerCase().includes(q) ||
        (x.nome_ricambio || '').toLowerCase().includes(q) ||
        (x.marca_veicolo || '').toLowerCase().includes(q) ||
        (x.modello_veicolo || '').toLowerCase().includes(q) ||
        (x.cross_references || '').toLowerCase().includes(q)
    );
  }, [xpartItems, xpartSearch]);

  // Spunta Anti-Doppio Invio
  const updateContactedState = (artisan: Artisan, isChecked: boolean) => {
    setArtisans((prev) =>
      prev.map((item) =>
        item.id === artisan.id
          ? {
              ...item,
              is_contacted: isChecked,
              wa_contacted: isChecked ? true : item.wa_contacted,
            }
          : item
      )
    );

    try {
      const raw = localStorage.getItem(STORAGE_CHECKED_KEY);
      const map = raw ? JSON.parse(raw) : {};
      map[`${artisan.nome_attivita}::${artisan.telefono || artisan.email}`] = isChecked;
      localStorage.setItem(STORAGE_CHECKED_KEY, JSON.stringify(map));
    } catch {
      // ignore
    }

    showToast(
      isChecked
        ? `✔ Spunta attivata: "${artisan.nome_attivita}" segnato come inviato (Anti-Doppio Invio ATTIVO)`
        : `Spunta rimossa per "${artisan.nome_attivita}"`
    );
  };

  // Composer Openers with Anti-Doppio Invio check
  const openWhatsAppComposer = (art: Artisan, skipConfirm = false) => {
    if (!skipConfirm && art.is_contacted) {
      setDuplicateConfirm({ artisan: art, channel: 'whatsapp' });
      return;
    }
    const fotoPart = settings.foto_allegate
      ? `\nGuarda i nostri lavori: ${settings.foto_allegate}`
      : '';
    const msg =
      `Ciao ${art.nome_attivita}, sono ${settings.sender_name || 'Marco Bellosi'} di CasaLavoroPRO.\n\n` +
      `Ho notato la tua attività di ${art.categoria} a ${art.citta} e la qualità dei tuoi interventi. ` +
      `Stiamo inserendo gratuitamente i migliori professionisti della zona sulla nostra piattaforma ` +
      `per metterli in contatto diretto con clienti locali che cercano lavori di casa, senza gettoni e senza commissioni sui preventivi.\n\n` +
      `Puoi vedere il portale qui: https://casalavoropro.com${fotoPart}\n\n` +
      `Se vuoi farti trovare gratis, ti predisponiamo noi la scheda o puoi registrarti in 2 minuti. Buon lavoro!\n` +
      `(${settings.sender_name || 'Marco Bellosi'} - ${settings.sender_phone || '3423255008'})`;

    setWaModalArtisan(art);
    setWaModalText(msg);
  };

  const openEmailComposer = (art: Artisan, skipConfirm = false) => {
    if (!art.email) return;
    if (!skipConfirm && art.is_contacted) {
      setDuplicateConfirm({ artisan: art, channel: 'email' });
      return;
    }

    const subj = `Richieste preventivo e visibilità gratuita a ${art.citta} per ${art.nome_attivita}`;
    const fotoPart = settings.foto_allegate
      ? `\nPuoi visualizzare alcuni progetti già pubblicati qui: ${settings.foto_allegate}\n`
      : '';

    const body =
      `Gentile ${art.nome_attivita},\n\n` +
      `Mi chiamo ${settings.sender_name || 'Marco Bellosi'} e ti scrivo dal team di CasaLavoroPRO (casalavoropro.com).\n\n` +
      `Ho notato la tua attività di ${art.categoria} a ${art.citta} e l'ottima qualità dei tuoi lavori sul territorio. Stiamo selezionando e inserendo gratuitamente i migliori professionisti della zona sulla nostra piattaforma per metterli in contatto diretto con clienti locali che richiedono interventi per la casa.\n\n` +
      `Perché CasaLavoroPRO è diversa?\n` +
      `• ZERO gettoni: non paghi per sbloccare i contatti o fare preventivi.\n` +
      `• ZERO commissioni: il cliente paga direttamente te al 100%.\n` +
      `• Contatto diretto telefonico e WhatsApp con i committenti.\n` +
      `${fotoPart}\n` +
      `Se vuoi attivare la tua vetrina gratuita ed essere contattato per i lavori nella tua zona, puoi rispondere direttamente a questa email confermando il tuo interesse, oppure registrarti su: https://casalavoropro.com\n\n` +
      `Resto a tua completa disposizione anche telefonicamente al ${settings.sender_phone || '3423255008'}.\n\n` +
      `Cordiali saluti,\n` +
      `${settings.sender_name || 'Marco Bellosi'}\n` +
      `CasaLavoroPRO — Il portale etico dei professionisti della casa\n` +
      `Telefono: ${settings.sender_phone || '3423255008'}\n` +
      `Email: ${settings.sender_email || 'bellosi2022@gmail.com'}`;

    setEmailModalArtisan(art);
    setEmailModalSubject(subj);
    setEmailModalBody(body);
  };

  // Preview Scraping Simulation
  const startPreviewScraping = () => {
    const targetZone = zona === '__custom__' ? cittaLibera.trim() : zona;
    if (!categoria || !targetZone) {
      showToast('Seleziona categoria e zona di ricerca');
      return;
    }

    setIsScraping(true);
    setProgressTarget(limite);
    setProgressCount(0);
    setProgressStatus(
      `Anteprima UI: scansione Google Maps per '${categoria}' su '${targetZone}'...`
    );

    let step = 0;
    scrapeTimerRef.current = window.setInterval(() => {
      step += 1;
      const nextCount = Math.min(limite, Math.round((step / 10) * limite));
      setProgressCount(nextCount);
      setProgressStatus(
        step < 10
          ? `Anteprima flusso stealth (${nextCount}/${limite}) — Deep Scraping: ${deepScrape ? 'Attivo' : 'Disattivato'}`
          : `Anteprima completata (${limite} target). In locale usa CasaLavoroOutreach.exe per l'estrazione reale.`
      );
      if (step >= 10) {
        if (scrapeTimerRef.current) window.clearInterval(scrapeTimerRef.current);
        setIsScraping(false);
        showToast('Simulazione preview completata (database reale invariato)');
      }
    }, 450);
  };

  const stopPreviewScraping = () => {
    if (scrapeTimerRef.current) window.clearInterval(scrapeTimerRef.current);
    setIsScraping(false);
    setProgressStatus('Ricerca interrotta.');
    showToast('Arresto ricerca eseguito');
  };

  const clearScrapingView = () => {
    setArtisans([]);
    setProgressCount(0);
    setProgressStatus('');
    showToast('Schermata di scraping pulita');
  };

  const startXpartPreviewScraping = () => {
    setIsXpartScraping(true);
    setXpartProgressCount(0);
    setXpartProgressStatus(
      `Anteprima UI: scansione cataloghi OEM per ${xpartMarca} ${xpartModello}...`
    );
    let step = 0;
    xpartTimerRef.current = window.setInterval(() => {
      step += 1;
      const nextCount = Math.min(xpartLimite, Math.round((step / 8) * xpartLimite));
      setXpartProgressCount(nextCount);
      setXpartProgressStatus(
        step < 8
          ? `Estrazione OEM ${xpartMarca} ${xpartModello} (${nextCount}/${xpartLimite})...`
          : `Anteprima XPart completata (${xpartLimite} ricambi).`
      );
      if (step >= 8) {
        if (xpartTimerRef.current) window.clearInterval(xpartTimerRef.current);
        setIsXpartScraping(false);
        showToast('Simulazione XPart completata (database reale invariato)');
      }
    }, 450);
  };

  const stopXpartPreviewScraping = () => {
    if (xpartTimerRef.current) window.clearInterval(xpartTimerRef.current);
    setIsXpartScraping(false);
    showToast('Arresto scraping XPart eseguito');
  };

  const handleLogoFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = typeof reader.result === 'string' ? reader.result : '';
      if (!dataUrl) return;
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]+/g, '_');
      const localPath = `assets/${safeName}`;
      setLogoVisible(true);
      setSettings((prev) => {
        const next: AppSettings = {
          ...prev,
          logo_url: localPath,
          logo_preview_data: dataUrl,
        };
        try {
          localStorage.setItem(STORAGE_SETTINGS_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
      showToast(`Logo salvato in locale: ${localPath}`);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleSaveSettings = () => {
    try {
      localStorage.setItem(STORAGE_SETTINGS_KEY, JSON.stringify(settings));
    } catch {
      // ignore
    }
    showToast('Impostazioni e dati utente aggiornati con successo!');
  };

  const waHref = waModalArtisan
    ? `https://wa.me/${formatPhoneForWa(waModalArtisan.telefono)}?text=${encodeURIComponent(
        waModalText
      )}`
    : '#';

  const gmailHref = emailModalArtisan
    ? `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(
        emailModalArtisan.email
      )}&su=${encodeURIComponent(emailModalSubject)}&body=${encodeURIComponent(
        emailModalBody
      )}`
    : '#';

  const mailtoHref = emailModalArtisan
    ? `mailto:${emailModalArtisan.email}?subject=${encodeURIComponent(
        emailModalSubject
      )}&body=${encodeURIComponent(emailModalBody)}`
    : '#';

  return (
    <div className="h-screen flex flex-col bg-[#0b0f19] text-[#f8fafc] overflow-hidden select-none font-sans">
      {/* Header */}
      <header className="bg-[#141b2d] border-b border-[#334155] px-6 py-2.5 flex flex-wrap justify-between items-center gap-3 shrink-0">
        <div className="flex items-center gap-3.5">
          <div
            className={`text-white font-extrabold text-[15px] px-3 py-1.5 rounded-lg shadow-lg ${
              activeTab === 'xpart'
                ? 'bg-gradient-to-br from-[#2563eb] to-[#38bdf8] shadow-blue-600/40'
                : 'bg-gradient-to-br from-[#ea580c] to-[#f97316] shadow-orange-600/40'
            }`}
          >
            {activeTab === 'xpart' ? 'XPART' : 'CLP'}
          </div>
          <div>
            <h1 className="text-[17px] font-extrabold tracking-tight leading-tight">
              {activeTab === 'xpart'
                ? 'XPart Ricambi Auto — Scraping Codici OEM & Catalogo'
                : 'CasaLavoroPRO — Lead Generation & Outreach'}
            </h1>
            <p className="text-[11px] text-[#94a3b8]">
              Email Chrome Bozza Precompilata • Spunta Anti-Doppio Invio • Bozze Supabase
            </p>
          </div>
          <div className="hidden xl:inline-flex items-center gap-2 bg-[#38bdf8]/10 border border-[#38bdf8]/30 rounded-md px-2.5 py-1 text-[11px] text-[#38bdf8]">
            <span>✉️ {settings.sender_email}</span>
            <span>•</span>
            <span>📱 {settings.sender_phone}</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex gap-1.5 bg-[#0b0f19] p-1 rounded-lg border border-[#334155]">
          <button
            onClick={() => setActiveTab('clp')}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all inline-flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'clp'
                ? 'bg-[#1e293b] text-[#fb923c] border border-[#ea580c]/40'
                : 'text-[#94a3b8] hover:text-white border border-transparent'
            }`}
          >
            <Hammer className="w-3.5 h-3.5" />
            CasaLavoroPRO
          </button>
          <button
            onClick={() => setActiveTab('xpart')}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all inline-flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'xpart'
                ? 'bg-[#1e293b] text-[#38bdf8] border border-[#38bdf8]/40'
                : 'text-[#94a3b8] hover:text-white border border-transparent'
            }`}
          >
            <Car className="w-3.5 h-3.5" />
            XPart Ricambi Auto
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all inline-flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'settings'
                ? 'bg-[#1e293b] text-white border border-[#334155]'
                : 'text-[#94a3b8] hover:text-white border border-transparent'
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            Impostazioni Brand
          </button>
        </div>

        {/* Header Actions */}
        <div className="flex gap-2 items-center">
          <button
            onClick={() =>
              showToast('Archivio CSV caricato: artigiani_estratti.csv & xpart_ricambi_estratti.csv')
            }
            className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white px-3 py-1.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <FolderOpen className="w-3.5 h-3.5 text-[#facc15]" />
            Cartella CSV
          </button>
          <button
            onClick={() => {
              loadDataFromCsv();
              showToast("Dati aggiornati dall'archivio locale");
            }}
            className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white px-3 py-1.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <RotateCw className={`w-3.5 h-3.5 text-[#38bdf8] ${loading ? 'animate-spin' : ''}`} />
            Ricarica
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col px-6 py-3.5 gap-3.5 overflow-hidden">
        {/* =================================================================== */}
        {/* TAB 1: CASALAVOROPRO                                                */}
        {/* =================================================================== */}
        {activeTab === 'clp' && (
          <div className="flex flex-col flex-1 gap-3.5 overflow-hidden">
            {/* Controls Card */}
            <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-4 py-3 flex flex-col gap-2.5 shrink-0">
              <div className="flex gap-2.5 items-end flex-wrap">
                <div className="flex flex-col gap-1 flex-[1.5] min-w-[210px]">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Categoria Artigiano (6 Macro-Settori)
                  </label>
                  <select
                    value={categoria}
                    onChange={(e) => setCategoria(e.target.value)}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {Object.entries(CATEGORIE_RAGGRUPPATE).map(([group, items]) => (
                      <optgroup
                        key={group}
                        label={group}
                        className="font-extrabold text-[#fb923c] bg-[#141b2d]"
                      >
                        {items.map((item) => (
                          <option
                            key={item}
                            value={item}
                            className="font-normal text-white bg-[#0b0f19]"
                          >
                            {item}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1 min-w-[140px] max-w-[180px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Regione d&apos;Italia
                  </label>
                  <select
                    value={regione}
                    onChange={(e) => handleRegionChange(e.target.value)}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {Object.keys(ITALIA_GEO_DATABASE).map((reg) => (
                      <option key={reg} value={reg}>
                        {reg}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1 min-w-[210px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Provincia / Territorio
                  </label>
                  <select
                    value={zona}
                    onChange={(e) => setZona(e.target.value)}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {regionZones.map((z) => (
                      <option key={z} value={z}>
                        {z}
                      </option>
                    ))}
                    <option value="__custom__">✏️ Scrivi comune specifico...</option>
                  </select>
                  {zona === '__custom__' && (
                    <input
                      type="text"
                      value={cittaLibera}
                      onChange={(e) => setCittaLibera(e.target.value)}
                      placeholder="Comune specifico..."
                      className="mt-1 bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-1.5 rounded-lg text-[13px] outline-none"
                    />
                  )}
                </div>

                <div className="flex flex-col gap-1 max-w-[145px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Limite Contatti
                  </label>
                  <select
                    value={limite}
                    onChange={(e) => setLimite(Number(e.target.value))}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {[100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 20, 50].map((v) => (
                      <option key={v} value={v}>
                        {v === 1000
                          ? '1000 contatti (Max)'
                          : v === 20
                          ? '20 (Test veloce)'
                          : `${v} contatti`}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1 max-w-[130px] justify-center pb-1.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Deep Scraping
                  </span>
                  <label className="text-xs flex items-center gap-1.5 cursor-pointer mt-1">
                    <input
                      type="checkbox"
                      checked={deepScrape}
                      onChange={(e) => setDeepScrape(e.target.checked)}
                      className="accent-[#ea580c]"
                    />
                    Siti Web &amp; Email
                  </label>
                </div>

                {!isScraping ? (
                  <button
                    onClick={startPreviewScraping}
                    className="bg-gradient-to-br from-[#ea580c] to-[#f97316] hover:brightness-110 text-white px-4 h-[38px] rounded-lg text-[13px] font-bold inline-flex items-center gap-2 shadow-md shadow-orange-600/35 cursor-pointer transition-all"
                  >
                    <Search className="w-4 h-4" />
                    Avvia Ricerca Artigiani
                  </button>
                ) : (
                  <button
                    onClick={stopPreviewScraping}
                    className="bg-[#ef4444] hover:bg-[#dc2626] text-white px-4 h-[38px] rounded-lg text-[13px] font-bold inline-flex items-center gap-1.5 cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                    Interrompi
                  </button>
                )}

                <button
                  type="button"
                  onClick={clearScrapingView}
                  title="Svuota solo la tabella a schermo senza cancellare i file CSV o Supabase"
                  className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white px-3.5 h-[38px] rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer transition-colors"
                >
                  <Eraser className="w-3.5 h-3.5 text-[#94a3b8]" />
                  Pulisci Schermata
                </button>
              </div>

              {(isScraping || progressStatus) && (
                <div className="flex flex-col gap-1.5 bg-[#0b0f19] border border-[#334155] rounded-lg px-3.5 py-2.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-[#38bdf8] font-semibold">{progressStatus}</span>
                    <span className="text-[#94a3b8] font-bold">
                      {progressCount} / {progressTarget}
                    </span>
                  </div>
                  <div className="bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-[#ea580c] to-[#22c55e] h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.max(4, Math.min(100, Math.round((progressCount / Math.max(1, progressTarget)) * 100)))}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 shrink-0">
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Totale Estratti
                </span>
                <div className="text-lg font-extrabold mt-0.5">{stats.tot}</div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Da Inviare (In Attesa)
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#f97316]">{stats.todo}</div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Spunta Attiva (Già Inviati)
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#22c55e]">{stats.sent}</div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Cellulari WhatsApp
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#38bdf8]">{stats.cell}</div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">Email B2B</span>
                <div className="text-lg font-extrabold mt-0.5 text-[#c084fc]">{stats.em}</div>
              </div>
            </div>

            {/* Table Container */}
            <div className="bg-[#141b2d] border border-[#334155] rounded-xl flex flex-col flex-1 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-[#334155] flex flex-wrap justify-between items-center gap-3 shrink-0">
                <input
                  type="text"
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  placeholder="Filtra per nome ditta, comune, telefono, email..."
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-1.5 rounded-md text-xs min-w-[260px] outline-none"
                />

                <div className="flex gap-1.5 flex-wrap">
                  {(
                    [
                      ['all', `Tutti (${stats.tot})`],
                      ['todo', `⏳ Da Inviare (${stats.todo})`],
                      ['sent', `✔ Già Inviati (${stats.sent})`],
                      ['has_email', `Con Email (${stats.em})`],
                      ['has_reviews', `Con Recensioni (${stats.reviews})`],
                    ] as [ArtisanFilter, string][]
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setArtisanFilter(key)}
                      className={`px-2.5 py-1 rounded-md text-xs font-semibold cursor-pointer border transition-colors ${
                        artisanFilter === key
                          ? 'bg-[#1e293b] border-[#334155] text-white'
                          : 'bg-transparent border-transparent text-[#94a3b8] hover:text-white'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 overflow-auto">
                <table className="w-full border-collapse text-[12.5px] text-left">
                  <thead>
                    <tr>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10 min-w-[155px]">
                        Controllo Anti-Doppio Invio
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Ditta / Professionista
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Categoria &amp; Città
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Recapito Telefonico
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Email B2B
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Recensioni Web
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Stato Supabase
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Outreach Interattivo
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredArtisans.map((a) => {
                      const isCell = a.tipo_telefono === 'cellulare';
                      return (
                        <tr key={a.id} className="hover:bg-[#1c263c] border-b border-[#1e293b]">
                          <td className="px-3 py-2 align-middle">
                            <label
                              className="inline-flex items-center gap-2 cursor-pointer"
                              title="Spunta per segnare il contatto come già inviato ed evitare doppi invii"
                            >
                              <input
                                type="checkbox"
                                checked={a.is_contacted}
                                onChange={(e) => updateContactedState(a, e.target.checked)}
                                className="w-4 h-4 accent-[#22c55e] cursor-pointer"
                              />
                              <span
                                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${
                                  a.is_contacted
                                    ? 'bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]'
                                    : 'bg-[#eab308]/15 text-[#facc15] border-[#eab308]/40'
                                }`}
                              >
                                {a.is_contacted ? (
                                  <>
                                    <Check className="w-3 h-3" /> Inviato
                                  </>
                                ) : (
                                  <>
                                    <Clock className="w-3 h-3" /> Da inviare
                                  </>
                                )}
                              </span>
                            </label>
                          </td>
                          <td className="px-3 py-2 align-middle">
                            <strong className="text-[#f8fafc]">{a.nome_attivita}</strong>
                            {a.sito_web && (
                              <div className="mt-0.5">
                                <a
                                  href={a.sito_web}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[#38bdf8] hover:underline text-[11px] inline-flex items-center gap-1"
                                >
                                  {a.sito_web}
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-2 align-middle">
                            <div>{a.categoria}</div>
                            <div className="text-[11px] text-[#94a3b8]">{a.citta}</div>
                          </td>
                          <td className="px-3 py-2 align-middle">
                            <div>
                              {a.telefono || <span className="text-[#64748b]">N/D</span>}
                            </div>
                            <div className="mt-1">
                              <span
                                className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${
                                  isCell
                                    ? 'bg-[#22c55e]/15 text-[#4ade80] border-[#22c55e]/30'
                                    : 'bg-[#94a3b8]/15 text-[#94a3b8] border-[#94a3b8]/30'
                                }`}
                              >
                                {isCell ? 'Cellulare' : 'Fisso'}
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-2 align-middle">
                            {a.email ? (
                              <span className="text-[#38bdf8] text-xs">{a.email}</span>
                            ) : (
                              <span className="text-[#64748b]">-</span>
                            )}
                          </td>
                          <td className="px-3 py-2 align-middle">
                            {a.rating_recensioni ? (
                              <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-[#eab308]/15 text-[#facc15] border border-[#eab308]/40">
                                ⭐ {a.rating_recensioni} ({a.numero_recensioni || '0'})
                              </span>
                            ) : (
                              <span className="text-[#64748b] text-[11px]">Nessuna</span>
                            )}
                          </td>
                          <td className="px-3 py-2 align-middle">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-[#ea580c]/15 text-[#fb923c] border border-[#ea580c]/40">
                              draft_scraping
                            </span>
                          </td>
                          <td className="px-3 py-2 align-middle">
                            <div className="flex gap-1.5 items-center">
                              {isCell ? (
                                <button
                                  onClick={() => openWhatsAppComposer(a)}
                                  className={`px-2.5 py-1 rounded-md text-[11.5px] font-bold inline-flex items-center gap-1 cursor-pointer transition-all ${
                                    a.is_contacted
                                      ? 'bg-[#334155] text-[#94a3b8] hover:bg-[#475569]'
                                      : 'bg-[#22c55e] hover:bg-[#16a34a] text-white shadow-sm shadow-green-500/30'
                                  }`}
                                >
                                  <MessageCircle className="w-3.5 h-3.5" />
                                  {a.is_contacted ? 'Riapri WA' : 'Invia WhatsApp'}
                                </button>
                              ) : (
                                <span className="text-[#64748b] text-[11px] min-w-[70px]">
                                  Solo fisso
                                </span>
                              )}

                              {a.email ? (
                                <button
                                  onClick={() => openEmailComposer(a)}
                                  className={`px-2.5 py-1 rounded-md text-[11.5px] font-bold inline-flex items-center gap-1 cursor-pointer transition-all ${
                                    a.is_contacted
                                      ? 'bg-[#334155] text-[#94a3b8] hover:bg-[#475569]'
                                      : 'bg-gradient-to-br from-[#2563eb] to-[#38bdf8] hover:brightness-110 text-white shadow-sm shadow-blue-500/30'
                                  }`}
                                >
                                  <Globe className="w-3.5 h-3.5" />
                                  {a.is_contacted ? 'Riapri Email' : 'Email Chrome'}
                                </button>
                              ) : (
                                <span className="text-[#64748b] text-[11px]">No email</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* TAB 2: XPART RICAMBI AUTO                                           */}
        {/* =================================================================== */}
        {activeTab === 'xpart' && (
          <div className="flex flex-col flex-1 gap-3.5 overflow-hidden">
            <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-4 py-3 flex flex-col gap-2.5 shrink-0">
              <div className="flex gap-2.5 items-end flex-wrap">
                <div className="flex flex-col gap-1 max-w-[170px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Marca Veicolo
                  </label>
                  <select
                    value={xpartMarca}
                    onChange={(e) => setXpartMarca(e.target.value)}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {XPART_MARCHE.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1 min-w-[160px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Modello Veicolo
                  </label>
                  <input
                    type="text"
                    value={xpartModello}
                    onChange={(e) => setXpartModello(e.target.value)}
                    placeholder="es. Focus, Golf VII, Panda 319..."
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1 flex-[1.5] min-w-[220px]">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Categoria Ricambio Auto
                  </label>
                  <select
                    value={xpartCategoria}
                    onChange={(e) => setXpartCategoria(e.target.value)}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {XPART_CATEGORIE.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1 max-w-[130px] flex-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Limite Ricambi
                  </label>
                  <select
                    value={xpartLimite}
                    onChange={(e) => setXpartLimite(Number(e.target.value))}
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  >
                    {[25, 50, 100, 200].map((v) => (
                      <option key={v} value={v}>
                        {v} ricambi
                      </option>
                    ))}
                  </select>
                </div>

                {!isXpartScraping ? (
                  <button
                    onClick={startXpartPreviewScraping}
                    className="bg-gradient-to-br from-[#2563eb] to-[#38bdf8] hover:brightness-110 text-white px-4 h-[38px] rounded-lg text-[13px] font-bold inline-flex items-center gap-2 shadow-md shadow-blue-600/35 cursor-pointer transition-all"
                  >
                    <Search className="w-4 h-4" />
                    Avvia Scraping OEM XPart
                  </button>
                ) : (
                  <button
                    onClick={stopXpartPreviewScraping}
                    className="bg-[#ef4444] hover:bg-[#dc2626] text-white px-4 h-[38px] rounded-lg text-[13px] font-bold inline-flex items-center gap-1.5 cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                    Interrompi
                  </button>
                )}
              </div>

              {(isXpartScraping || xpartProgressStatus) && (
                <div className="flex flex-col gap-1.5 bg-[#0b0f19] border border-[#334155] rounded-lg px-3.5 py-2.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-[#38bdf8] font-semibold">{xpartProgressStatus}</span>
                    <span className="text-[#94a3b8] font-bold">
                      {xpartProgressCount} / {xpartLimite}
                    </span>
                  </div>
                  <div className="bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-[#2563eb] to-[#38bdf8] h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.max(4, Math.min(100, Math.round((xpartProgressCount / Math.max(1, xpartLimite)) * 100)))}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* XPart Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 shrink-0">
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Ricambi Estratti
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#38bdf8]">
                  {xpartStats.tot}
                </div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Codici OEM Unici
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#22c55e]">
                  {xpartStats.oemUnique}
                </div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Cross-References
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#c084fc]">
                  {xpartStats.crossCount}
                </div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Sincronizzati Supabase
                </span>
                <div className="text-lg font-extrabold mt-0.5 text-[#f97316]">
                  {xpartStats.tot}
                </div>
              </div>
              <div className="bg-[#141b2d] border border-[#334155] rounded-xl px-3.5 py-2">
                <span className="text-[10px] font-bold uppercase text-[#94a3b8]">
                  Stato Magazzino
                </span>
                <div className="text-sm font-extrabold mt-1.5 text-[#38bdf8]">
                  GRADO A • ATTIVO
                </div>
              </div>
            </div>

            {/* XPart Table */}
            <div className="bg-[#141b2d] border border-[#334155] rounded-xl flex flex-col flex-1 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-[#334155] flex justify-between items-center gap-3 shrink-0">
                <input
                  type="text"
                  value={xpartSearch}
                  onChange={(e) => setXpartSearch(e.target.value)}
                  placeholder="Cerca per codice OEM, marca, motore, cross-reference..."
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-1.5 rounded-md text-xs min-w-[280px] outline-none"
                />
                <div className="text-xs text-[#94a3b8]">
                  Database Ricambi: <strong className="text-white">xpart_ricambi_estratti.csv</strong>
                </div>
              </div>

              <div className="flex-1 overflow-auto">
                <table className="w-full border-collapse text-[12.5px] text-left">
                  <thead>
                    <tr>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Codice OEM
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Descrizione Ricambio
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Compatibilità Veicolo
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Motorizzazione
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Cross-Reference Aftermarket
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Prezzo Stimato
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Scaffale / Grado
                      </th>
                      <th className="sticky top-0 bg-[#182238] text-[#94a3b8] px-3 py-2.5 font-bold text-[11px] uppercase tracking-wider border-b border-[#334155] z-10">
                        Supabase
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredXpart.map((x, idx) => (
                      <tr
                        key={`${x.id_articolo}-${idx}`}
                        className="hover:bg-[#1c263c] border-b border-[#1e293b]"
                      >
                        <td className="px-3 py-2 align-middle">
                          <strong className="text-[#38bdf8] font-mono text-[13px]">
                            {x.codice_oem}
                          </strong>
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <div>
                            <strong>{x.nome_ricambio}</strong>
                          </div>
                          <div className="text-[11px] text-[#94a3b8]">{x.categoria}</div>
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <div>
                            {x.marca_veicolo} {x.modello_veicolo}
                          </div>
                          <div className="text-[11px] text-[#94a3b8]">
                            {x.anno_compatibilita || '2012-2022'}
                          </div>
                        </td>
                        <td className="px-3 py-2 align-middle text-[11.5px] text-[#cbd5e1]">
                          {x.motorizzazione || '-'}
                        </td>
                        <td className="px-3 py-2 align-middle text-[11px] text-[#a855f7]">
                          {x.cross_references || '-'}
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <strong>€ {x.prezzo || 'N/D'}</strong>
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <div>{x.scaffale || 'B-04-L2'}</div>
                          <div className="text-[10px] text-[#4ade80]">
                            {x.condizione || 'GRADO A'}
                          </div>
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/40">
                            Sincronizzato
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* TAB 3: IMPOSTAZIONI BRAND & SUPABASE                                */}
        {/* =================================================================== */}
        {activeTab === 'settings' && (
          <div className="overflow-auto flex-1">
            <div className="bg-[#141b2d] border border-[#334155] rounded-xl p-5 max-w-[800px] mx-auto flex flex-col gap-3.5">
              <h2 className="text-base font-extrabold border-b border-[#334155] pb-2">
                ⚙️ Personalizzazione Mittente (Dati Fissi), Brand e Database Supabase
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Tuo Nome / Nome Mittente
                  </label>
                  <input
                    type="text"
                    value={settings.sender_name}
                    onChange={(e) =>
                      setSettings({ ...settings, sender_name: e.target.value })
                    }
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Tuo Numero WhatsApp Mittente (Fisso)
                  </label>
                  <input
                    type="text"
                    value={settings.sender_phone}
                    onChange={(e) =>
                      setSettings({ ...settings, sender_phone: e.target.value })
                    }
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Tua Email Mittente (Fissa)
                  </label>
                  <input
                    type="text"
                    value={settings.sender_email}
                    onChange={(e) =>
                      setSettings({ ...settings, sender_email: e.target.value })
                    }
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Logo o Foto Aziendale (URL o File da PC)
                  </label>
                  <div className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={settings.logo_url}
                      onChange={(e) => {
                        setLogoVisible(true);
                        setSettings({
                          ...settings,
                          logo_url: e.target.value,
                          logo_preview_data: '',
                        });
                      }}
                      placeholder="https://casalavoropro.com/logo.png o assets/logo.png"
                      className="flex-1 min-w-0 bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                    />
                    <input
                      ref={logoFileInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/jpg,image/webp,image/gif,image/svg+xml"
                      className="hidden"
                      onChange={handleLogoFileUpload}
                    />
                    <button
                      type="button"
                      onClick={() => logoFileInputRef.current?.click()}
                      className="bg-[#1e293b] hover:bg-[#334155] border border-[#38bdf8]/45 text-[#38bdf8] px-3 py-2 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 whitespace-nowrap cursor-pointer transition-colors"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      Sfoglia / Carica Logo o Foto da PC
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Link Galleria Foto / Lavori (opzionale per messaggi)
                </label>
                <input
                  type="text"
                  value={settings.foto_allegate}
                  onChange={(e) =>
                    setSettings({ ...settings, foto_allegate: e.target.value })
                  }
                  placeholder="https://casalavoropro.com/lavori"
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                />
              </div>

              <div className="flex items-center gap-3 bg-[#0b0f19] border border-[#334155] px-3 py-2 rounded-lg text-xs">
                {(settings.logo_preview_data || settings.logo_url) && logoVisible && (
                  <img
                    src={settings.logo_preview_data || settings.logo_url}
                    alt="Anteprima Logo"
                    onError={() => setLogoVisible(false)}
                    className="max-h-[34px] max-w-[100px] object-contain"
                  />
                )}
                <span className="text-[#94a3b8]">
                  {settings.logo_url
                    ? `Logo attivo per bozze e presentazioni: ${settings.logo_url}`
                    : 'Anteprima logo mittente per email e presentazioni'}
                </span>
              </div>

              <h3 className="text-sm font-extrabold mt-2 border-b border-[#334155] pb-1.5 text-[#38bdf8]">
                Connessione Database Supabase (CasaLavoroPRO &amp; XPart)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Supabase Project URL
                  </label>
                  <input
                    type="text"
                    value={settings.supabase_url}
                    onChange={(e) =>
                      setSettings({ ...settings, supabase_url: e.target.value })
                    }
                    placeholder="https://xyzcompany.supabase.co"
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Supabase Key (Anon o Service Role)
                  </label>
                  <input
                    type="password"
                    value={settings.supabase_key}
                    onChange={(e) =>
                      setSettings({ ...settings, supabase_key: e.target.value })
                    }
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Tabella Bozze CasaLavoroPRO
                  </label>
                  <input
                    type="text"
                    value={settings.supabase_table_bozze}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        supabase_table_bozze: e.target.value,
                      })
                    }
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Tabella Ricambi XPart
                  </label>
                  <input
                    type="text"
                    value={settings.supabase_table_xpart}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        supabase_table_xpart: e.target.value,
                      })
                    }
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end mt-2">
                <button
                  onClick={handleSaveSettings}
                  className="bg-gradient-to-br from-[#ea580c] to-[#f97316] hover:brightness-110 text-white px-5 py-2.5 rounded-lg text-[13px] font-bold inline-flex items-center gap-2 shadow-md shadow-orange-600/35 cursor-pointer"
                >
                  <Save className="w-4 h-4" />
                  Salva Impostazioni
                </button>
              </div>
            </div>

            {/* =============================================================== */}
            {/* BOX INDIPENDENTE: SPAZIO TEST GENERAZIONE EMAIL (SANDBOX)       */}
            {/* =============================================================== */}
            <div className="bg-[#141b2d] border border-[#38bdf8]/40 rounded-xl p-5 max-w-[800px] mx-auto mt-4 flex flex-col gap-3.5">
              <div className="flex flex-wrap justify-between items-center gap-2 border-b border-[#334155] pb-2">
                <h2 className="text-base font-extrabold text-[#38bdf8] inline-flex items-center gap-2">
                  <FlaskConical className="w-4 h-4" />
                  Spazio Test Generazione Email
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#38bdf8]/15 text-[#38bdf8] border border-[#38bdf8]/35">
                  Sandbox Isolata • Nessun impatto su CSV/Supabase
                </span>
              </div>

              <div className="flex flex-wrap gap-2.5 items-end">
                <div className="flex flex-col gap-1 flex-[2] min-w-[240px]">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                    Email di Prova (Destinatario Test)
                  </label>
                  <input
                    type="email"
                    value={sandboxTestEmail}
                    onChange={(e) => setSandboxTestEmail(e.target.value)}
                    placeholder="la-tua-email@esempio.it"
                    className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                  />
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setSandboxBody(
                      buildSandboxPreviewBody(settings.sender_phone, settings.foto_allegate)
                    );
                    showToast('Anteprima Email Sandbox rigenerata con i dati CasaLavoroPRO');
                  }}
                  className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white px-3.5 h-[38px] rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-[#38bdf8]" />
                  Rigenera Testo
                </button>

                <a
                  href={
                    sandboxTestEmail.trim().includes('@')
                      ? `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(
                          sandboxTestEmail.trim()
                        )}&su=${encodeURIComponent(sandboxSubject)}&body=${encodeURIComponent(
                          sandboxBody
                        )}`
                      : '#sandbox-test'
                  }
                  target={sandboxTestEmail.trim().includes('@') ? '_blank' : undefined}
                  rel={sandboxTestEmail.trim().includes('@') ? 'noopener noreferrer' : undefined}
                  onClick={(e) => {
                    const target = sandboxTestEmail.trim();
                    if (!target || !target.includes('@')) {
                      e.preventDefault();
                      showToast("Inserisci un'email di prova valida prima di inviare.");
                      return;
                    }
                    const nextBody = sandboxBody.trim()
                      ? sandboxBody
                      : buildSandboxPreviewBody(settings.sender_phone, settings.foto_allegate);
                    setSandboxBody(nextBody);
                    setSandboxStatus(
                      `✔ Bozza di test generata e aperta in Google Chrome per ${target} (CSV e Supabase invariati).`
                    );
                    showToast(`Bozza email di test aperta in Chrome per ${target}`);
                  }}
                  className="bg-gradient-to-br from-[#2563eb] to-[#38bdf8] hover:brightness-110 text-white px-4 h-[38px] rounded-lg text-[13px] font-bold inline-flex items-center gap-2 shadow-md shadow-blue-600/35 no-underline cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" />
                  Genera &amp; Invia Email di Test
                </a>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Oggetto Email di Test
                </label>
                <input
                  type="text"
                  value={sandboxSubject}
                  onChange={(e) => setSandboxSubject(e.target.value)}
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Anteprima Esatta Email (Mittente: CasaLavoroPRO &lt;info@casalavoropro.com&gt;)
                </label>
                <textarea
                  rows={12}
                  value={sandboxBody}
                  onChange={(e) => setSandboxBody(e.target.value)}
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white p-3 rounded-lg text-[12.5px] leading-relaxed resize-y min-h-[210px] outline-none"
                />
              </div>

              <p
                className={`text-[11.5px] ${
                  sandboxStatus ? 'text-[#4ade80]' : 'text-[#94a3b8]'
                }`}
              >
                {sandboxStatus ||
                  'In desktop usa SMTP se configurato in .env oppure apre direttamente Google Chrome. Non registra il test nel controllo anti-doppio invio.'}
              </p>
            </div>
          </div>
        )}
      </main>

      {/* ===================================================================== */}
      {/* MODALE CONFERMA ANTI-DOPPIO INVIO                                     */}
      {/* ===================================================================== */}
      {duplicateConfirm && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex justify-center items-center z-50 p-4">
          <div className="bg-[#141b2d] border border-[#eab308]/50 rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-[#334155] flex items-center gap-2.5 text-[#facc15]">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span className="font-extrabold text-sm">
                ATTENZIONE ANTI-DOPPIO INVIO
              </span>
            </div>
            <div className="p-5 text-sm text-[#cbd5e1] leading-relaxed">
              Risulta che hai già contattato o inviato a:{' '}
              <strong className="text-white">
                {duplicateConfirm.artisan.nome_attivita}
              </strong>
              .<br />
              <br />
              Vuoi davvero procedere e inviare un messaggio duplicato?
            </div>
            <div className="px-5 py-3.5 border-t border-[#334155] flex justify-end gap-2.5">
              <button
                onClick={() => setDuplicateConfirm(null)}
                className="bg-[#334155] hover:bg-[#475569] text-white px-4 py-1.5 rounded-md text-xs font-semibold cursor-pointer"
              >
                Annulla
              </button>
              <button
                onClick={() => {
                  const target = duplicateConfirm;
                  setDuplicateConfirm(null);
                  if (target.channel === 'whatsapp') {
                    openWhatsAppComposer(target.artisan, true);
                  } else {
                    openEmailComposer(target.artisan, true);
                  }
                }}
                className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-4 py-1.5 rounded-md text-xs font-bold cursor-pointer"
              >
                Procedi comunque
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODALE COMPOSER WHATSAPP                                              */}
      {/* ===================================================================== */}
      {waModalArtisan && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex justify-center items-center z-50 p-4">
          <div className="bg-[#141b2d] border border-[#334155] rounded-2xl w-full max-w-[680px] max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#334155] flex justify-between items-center">
              <div className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-[#22c55e]" />
                <span className="text-base font-extrabold">
                  Composer WhatsApp — Personalizza Messaggio
                </span>
              </div>
              <button
                onClick={() => setWaModalArtisan(null)}
                className="text-[#94a3b8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex flex-col gap-3.5">
              <div className="bg-[#0b0f19] border border-[#334155] rounded-lg px-3.5 py-2.5 text-xs grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  Destinatario: <strong>{waModalArtisan.nome_attivita}</strong>
                </div>
                <div>
                  Cellulare WhatsApp:{' '}
                  <strong className="text-[#4ade80]">
                    {waModalArtisan.telefono || 'N/D'}
                  </strong>
                </div>
                <div>
                  Categoria &amp; Città:{' '}
                  <span className="text-[#94a3b8]">
                    {waModalArtisan.categoria} • {waModalArtisan.citta}
                  </span>
                </div>
                <div>
                  Tuo Mittente:{' '}
                  <span className="text-[#fb923c]">
                    {settings.sender_name} ({settings.sender_phone})
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Testo del Messaggio WhatsApp (Completamente Modificabile)
                </label>
                <textarea
                  rows={8}
                  value={waModalText}
                  onChange={(e) => setWaModalText(e.target.value)}
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#ea580c] text-white p-3 rounded-lg text-[13px] leading-relaxed resize-y min-h-[150px] outline-none"
                />
              </div>

              <p className="text-[11.5px] text-[#94a3b8]">
                💡{' '}
                <em>
                  Apre direttamente WhatsApp Web / Desktop. Il contatto viene contrassegnato
                  automaticamente con la <strong>Spunta Anti-Doppio Invio</strong>.
                </em>
              </p>
            </div>

            <div className="px-5 py-3.5 border-t border-[#334155] flex justify-end gap-2.5 items-center">
              <button
                onClick={() => setWaModalArtisan(null)}
                className="bg-[#334155] hover:bg-[#475569] text-white px-4 py-2 rounded-md text-[13px] font-semibold cursor-pointer"
              >
                Annulla
              </button>
              <a
                href={waHref}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => {
                  const target = waModalArtisan;
                  updateContactedState(target, true);
                  setWaModalArtisan(null);
                }}
                className="bg-[#22c55e] hover:bg-[#16a34a] text-white px-4 py-2 rounded-md text-[13px] font-bold inline-flex items-center gap-1.5 shadow-md shadow-green-500/30 no-underline"
              >
                <MessageCircle className="w-4 h-4" />
                Apri WhatsApp Desktop / Web
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODALE COMPOSER EMAIL B2B (GOOGLE CHROME INTEGRATO)                   */}
      {/* ===================================================================== */}
      {emailModalArtisan && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex justify-center items-center z-50 p-4">
          <div className="bg-[#141b2d] border border-[#334155] rounded-2xl w-full max-w-[680px] max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#334155] flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-[#38bdf8]" />
                <span className="text-base font-extrabold">
                  Composer Email B2B — Invio tramite Google Chrome
                </span>
              </div>
              <button
                onClick={() => setEmailModalArtisan(null)}
                className="text-[#94a3b8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex flex-col gap-3.5">
              <div className="bg-[#0b0f19] border border-[#334155] rounded-lg px-3.5 py-2.5 text-xs grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  Destinatario: <strong>{emailModalArtisan.nome_attivita}</strong>
                </div>
                <div>
                  Indirizzo Email:{' '}
                  <strong className="text-[#38bdf8]">{emailModalArtisan.email}</strong>
                </div>
                <div>
                  Categoria &amp; Città:{' '}
                  <span className="text-[#94a3b8]">
                    {emailModalArtisan.categoria} • {emailModalArtisan.citta}
                  </span>
                </div>
                <div>
                  Tuo Mittente:{' '}
                  <span className="text-[#fb923c]">
                    {settings.sender_name} ({settings.sender_email})
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Oggetto dell&apos;Email
                </label>
                <input
                  type="text"
                  value={emailModalSubject}
                  onChange={(e) => setEmailModalSubject(e.target.value)}
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white px-3 py-2 rounded-lg text-[13px] outline-none"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  Testo Email (con recapiti fissi e firma)
                </label>
                <textarea
                  rows={9}
                  value={emailModalBody}
                  onChange={(e) => setEmailModalBody(e.target.value)}
                  className="bg-[#0b0f19] border border-[#334155] focus:border-[#38bdf8] text-white p-3 rounded-lg text-[13px] leading-relaxed resize-y min-h-[160px] outline-none"
                />
              </div>

              <div className="bg-[#2563eb]/10 border border-[#38bdf8]/30 rounded-lg px-3 py-2.5 text-[11.5px] text-[#94a3b8] leading-relaxed">
                🚀 <strong>Integrazione Google Chrome</strong>: Cliccando sul pulsante blu, si
                aprirà la schermata di composizione Gmail precompilata con questo destinatario,
                oggetto e corpo del testo, pronta per allegare manualmente logo e foto.
              </div>
            </div>

            <div className="px-5 py-3.5 border-t border-[#334155] flex flex-wrap justify-end gap-2.5 items-center">
              <button
                onClick={() => setEmailModalArtisan(null)}
                className="bg-[#334155] hover:bg-[#475569] text-white px-4 py-2 rounded-md text-[13px] font-semibold cursor-pointer"
              >
                Annulla
              </button>
              <a
                href={gmailHref}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => {
                  const target = emailModalArtisan;
                  updateContactedState(target, true);
                  setEmailModalArtisan(null);
                }}
                className="bg-gradient-to-br from-[#2563eb] to-[#38bdf8] hover:brightness-110 text-white px-4 py-2 rounded-md text-[13px] font-bold inline-flex items-center gap-1.5 shadow-md shadow-blue-600/40 no-underline"
              >
                <Globe className="w-4 h-4" />
                Apri Bozza in Google Chrome
              </a>
              <a
                href={mailtoHref}
                onClick={() => {
                  const target = emailModalArtisan;
                  updateContactedState(target, true);
                  setEmailModalArtisan(null);
                }}
                className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white px-3.5 py-2 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 no-underline"
                title="Apri in Outlook o altro client installato"
              >
                <Mail className="w-3.5 h-3.5" />
                Client Predefinito
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-5 right-5 bg-[#1e293b] border border-[#22c55e] text-white px-4 py-2.5 rounded-lg text-[13px] font-semibold shadow-xl z-[9999]">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

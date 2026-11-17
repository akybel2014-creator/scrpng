#!/usr/bin/env python3
"""
APPLICAZIONE DESKTOP TKINTER / CUSTOMTKINTER — CASALAVOROPRO
===========================================================
Interfaccia grafica desktop nativa Windows basata su CustomTkinter/Tkinter:
- Selezione Categoria e Città/Provincia (lista rapida Veneto).
- Pulsante "Avvia Ricerca Artigiani" con thread background e progress bar.
- Tabella interattiva dei risultati con pulsanti WhatsApp dedicati.
- Persistenza automatica su CSV e storico contatti.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    BASE_DIR,
    FILE_ESTRATTI,
    FILE_REGISTRO,
    DEFAULT_CATEGORIE,
    DEFAULT_CITTA,
    DEFAULT_LIMIT_PER_SEARCH
)
from geo_data import (
    ITALIA_GEO_DATABASE,
    get_all_regions,
    get_zones_for_region,
    resolve_search_locations
)
from scraper import setup_selenium_driver, scrape_google_maps, scrape_google_maps_multi_zone
from outreach import (
    load_csv_data,
    load_contacted_registry,
    open_whatsapp_for_artisan
)


class CasaLavoroTkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CasaLavoroPRO — Lead Generation & Outreach (Desktop)")
        self.geometry("1100x700")
        self.minsize(900, 550)
        self.configure(bg="#0f172a")

        self.scraper_thread = None
        self.stop_event = threading.Event()
        self.active_driver = None
        self.artisans_list = []

        self._setup_styles()
        self._build_ui()
        self._load_existing_data()

        # Pulizia chiusura
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Configura stile Treeview
        self.style.configure(
            "Treeview",
            background="#1e293b",
            foreground="#f8fafc",
            fieldbackground="#1e293b",
            rowheight=32,
            font=("Segoe UI", 10)
        )
        self.style.configure(
            "Treeview.Heading",
            background="#0f172a",
            foreground="#94a3b8",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )
        self.style.map("Treeview", background=[("selected", "#ea580c")])

    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self, bg="#1e293b", padx=16, pady=12)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        logo_lbl = tk.Label(header_frame, text="CLP", bg="#ea580c", fg="white", font=("Segoe UI", 12, "bold"), padx=8, pady=2)
        logo_lbl.pack(side=tk.LEFT, padx=(0, 10))

        title_lbl = tk.Label(header_frame, text="CasaLavoroPRO — Outreach Console", bg="#1e293b", fg="white", font=("Segoe UI", 14, "bold"))
        title_lbl.pack(side=tk.LEFT)

        folder_btn = tk.Button(header_frame, text="📁 Apri Cartella CSV", bg="#334155", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, command=self._open_folder)
        folder_btn.pack(side=tk.RIGHT, padx=5)

        refresh_btn = tk.Button(header_frame, text="🔄 Ricarica", bg="#334155", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, command=self._load_existing_data)
        refresh_btn.pack(side=tk.RIGHT, padx=5)

        # Barra di Ricerca / Parametri
        controls_frame = tk.Frame(self, bg="#141b2d", padx=16, pady=14)
        controls_frame.pack(fill=tk.X, padx=16, pady=12)

        # Categoria
        tk.Label(controls_frame, text="CATEGORIA:", bg="#141b2d", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=4)
        self.cat_combo = ttk.Combobox(controls_frame, values=DEFAULT_CATEGORIE, width=16, font=("Segoe UI", 10))
        self.cat_combo.set("Idraulico")
        self.cat_combo.grid(row=1, column=0, padx=4, pady=4)

        # Regione
        tk.Label(controls_frame, text="REGIONE D'ITALIA:", bg="#141b2d", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=tk.W, padx=4)
        self.reg_combo = ttk.Combobox(controls_frame, values=get_all_regions(), width=16, font=("Segoe UI", 10), state="readonly")
        self.reg_combo.set("Veneto")
        self.reg_combo.grid(row=1, column=1, padx=4, pady=4)
        self.reg_combo.bind("<<ComboboxSelected>>", self._on_region_selected)

        # Provincia / Zona
        tk.Label(controls_frame, text="PROVINCIA / CITTÀ (TUTTA):", bg="#141b2d", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=tk.W, padx=4)
        self.zone_combo = ttk.Combobox(controls_frame, values=get_zones_for_region("Veneto"), width=24, font=("Segoe UI", 10))
        self.zone_combo.set("Vicenza e provincia (Tutta)")
        self.zone_combo.grid(row=1, column=2, padx=4, pady=4)

        # Limite (100 a 1000 a passi di 100)
        tk.Label(controls_frame, text="MAX CONTATTI:", bg="#141b2d", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky=tk.W, padx=4)
        limits = ["100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "20", "50"]
        self.limit_combo = ttk.Combobox(controls_frame, values=limits, width=12, font=("Segoe UI", 10))
        self.limit_combo.set("100")
        self.limit_combo.grid(row=1, column=3, padx=4, pady=4)

        # Deep Scraping
        self.deep_var = tk.BooleanVar(value=True)
        deep_chk = tk.Checkbutton(controls_frame, text="Visita siti", variable=self.deep_var, bg="#141b2d", fg="white", selectcolor="#0f172a", activebackground="#141b2d", activeforeground="white", font=("Segoe UI", 9))
        deep_chk.grid(row=1, column=4, padx=8, pady=4)

        # Pulsante Avvia
        self.btn_search = tk.Button(controls_frame, text="🔍 Avvia Ricerca", bg="#ea580c", fg="white", font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=14, pady=6, command=self._start_search)
        self.btn_search.grid(row=1, column=5, padx=6, pady=4)

        self.btn_stop = tk.Button(controls_frame, text="⏹ Interrompi", bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=12, pady=6, command=self._stop_search)
        self.btn_stop.grid(row=1, column=6, padx=4, pady=4)
        self.btn_stop.grid_remove()

        # Progress Frame
        self.progress_frame = tk.Frame(controls_frame, bg="#141b2d")
        self.progress_frame.grid(row=2, column=0, columnspan=6, sticky=tk.EW, pady=(8, 0))

        self.lbl_status = tk.Label(self.progress_frame, text="Pronto.", bg="#141b2d", fg="#38bdf8", font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode="determinate", length=300)
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(16, 0))

        # Statistiche Rapide
        stats_frame = tk.Frame(self, bg="#0f172a", padx=16)
        stats_frame.pack(fill=tk.X)

        self.stat_lbl = tk.Label(stats_frame, text="Totale contatti: 0 | Cellulari WhatsApp: 0 | Email: 0 | Già contattati: 0", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 10, "bold"))
        self.stat_lbl.pack(side=tk.LEFT, pady=4)

        # Tabella Risultati
        table_frame = tk.Frame(self, bg="#1e293b")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        columns = ("nome", "categoria", "citta", "telefono", "tipo", "email", "stato")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("nome", text="Nome Ditta / Attività")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("citta", text="Città")
        self.tree.heading("telefono", text="Telefono")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("email", text="Email B2B")
        self.tree.heading("stato", text="Stato WhatsApp")

        self.tree.column("nome", width=220)
        self.tree.column("categoria", width=120)
        self.tree.column("citta", width=120)
        self.tree.column("telefono", width=140)
        self.tree.column("tipo", width=80)
        self.tree.column("email", width=200)
        self.tree.column("stato", width=130)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Barra inferiore azioni tabella
        bottom_frame = tk.Frame(self, bg="#0f172a", padx=16, pady=8)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_wa = tk.Button(bottom_frame, text="💬 Invia WhatsApp al contatto selezionato", bg="#22c55e", fg="white", font=("Segoe UI", 11, "bold"), relief=tk.FLAT, padx=18, pady=8, command=self._send_wa_selected)
        self.btn_wa.pack(side=tk.LEFT)

        hint_lbl = tk.Label(bottom_frame, text="Fai doppio clic su una riga per aprire direttamente WhatsApp", bg="#0f172a", fg="#64748b", font=("Segoe UI", 9))
        hint_lbl.pack(side=tk.RIGHT)

        self.tree.bind("<Double-1>", lambda event: self._send_wa_selected())

    def _load_existing_data(self):
        raw = load_csv_data(FILE_ESTRATTI)
        registry = load_contacted_registry(FILE_REGISTRO)

        self.tree.delete(*self.tree.get_children())
        self.artisans_list = []

        tot = len(raw)
        cell = 0
        em_cnt = 0
        sent_cnt = 0

        for r in raw:
            nome = r.get("nome_attivita", "")
            cat = r.get("categoria", "")
            cit = r.get("citta", "")
            tel = r.get("telefono_principale", "")
            tipo = r.get("tipo_telefono", "")
            em = r.get("email", "")

            wa_key = f"WHATSAPP:{tel}"
            is_sent = wa_key in registry or f"WHATSAPP:name:{nome.lower()}" in registry
            stato = "✔ Inviato" if is_sent else "Da inviare"

            if tipo == "cellulare":
                cell += 1
            if em and "@" in em:
                em_cnt += 1
            if is_sent:
                sent_cnt += 1

            item_id = self.tree.insert("", tk.END, values=(nome, cat, cit, tel, tipo, em, stato))
            self.artisans_list.append({
                "item_id": item_id,
                "nome_attivita": nome,
                "categoria": cat,
                "citta": cit,
                "telefono": tel,
                "tipo_telefono": tipo,
                "email": em,
                "wa_contacted": is_sent
            })

        self.stat_lbl.config(text=f"Totale contatti: {tot} | Cellulari WhatsApp: {cell} | Email: {em_cnt} | Già contattati: {sent_cnt}")

    def _on_region_selected(self, event=None):
        reg = self.reg_combo.get()
        zones = get_zones_for_region(reg)
        self.zone_combo["values"] = zones
        if zones:
            self.zone_combo.set(zones[0])

    def _start_search(self):
        cat = self.cat_combo.get().strip()
        reg = self.reg_combo.get().strip()
        zone = self.zone_combo.get().strip()
        lim = int(self.limit_combo.get().strip() or "100")
        deep = self.deep_var.get()

        if not cat or not zone:
            messagebox.showwarning("Dati Mancanti", "Inserisci sia la categoria che la zona di ricerca.")
            return

        locations = resolve_search_locations(reg, zone)

        self.btn_search.grid_remove()
        self.btn_stop.grid()
        self.progress_bar["value"] = 2
        self.lbl_status.config(text=f"Avvio ricerca Google Maps: '{cat}' su '{zone}' (Target: {lim})...")

        self.stop_event.clear()

        def worker():
            driver = None
            try:
                driver = setup_selenium_driver(headless=True)
                self.active_driver = driver

                def on_progress(record, current_count, target_limit, status_msg):
                    self.after(0, lambda: self._update_progress_ui(record, current_count, target_limit, status_msg))

                total = scrape_google_maps_multi_zone(
                    driver=driver,
                    categoria=cat,
                    locations=locations,
                    target_limit=lim,
                    deep_scrape=deep,
                    progress_callback=on_progress,
                    stop_event=self.stop_event
                )
                self.after(0, lambda: self._search_finished(f"Ricerca completata: {total} nuovi contatti salvati."))
            except Exception as e:
                self.after(0, lambda: self._search_finished(f"Errore: {e}"))
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                self.active_driver = None

        self.scraper_thread = threading.Thread(target=worker, daemon=True)
        self.scraper_thread.start()

    def _update_progress_ui(self, record, current_count, target_limit, status_msg):
        self.lbl_status.config(text=status_msg)
        pct = (current_count / max(1, target_limit)) * 100
        self.progress_bar["value"] = pct

        if record:
            item_id = self.tree.insert("", 0, values=(
                record.get("nome_attivita", ""),
                record.get("categoria", ""),
                record.get("citta", ""),
                record.get("telefono_principale", ""),
                record.get("tipo_telefono", ""),
                record.get("email", ""),
                "Da inviare"
            ))
            self.artisans_list.insert(0, {
                "item_id": item_id,
                "nome_attivita": record.get("nome_attivita", ""),
                "categoria": record.get("categoria", ""),
                "citta": record.get("citta", ""),
                "telefono": record.get("telefono_principale", ""),
                "tipo_telefono": record.get("tipo_telefono", ""),
                "email": record.get("email", ""),
                "wa_contacted": False
            })

    def _stop_search(self):
        self.stop_event.set()
        if self.active_driver:
            try:
                self.active_driver.quit()
            except Exception:
                pass
        self._search_finished("Ricerca interrotta dall'utente.")

    def _search_finished(self, msg):
        self.btn_stop.grid_remove()
        self.btn_search.grid()
        self.lbl_status.config(text=msg)
        self.progress_bar["value"] = 100
        self._load_existing_data()

    def _send_wa_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("Nessuna Selezione", "Seleziona un artigiano dalla tabella per inviare il messaggio WhatsApp.")
            return

        item = selected_item[0]
        vals = self.tree.item(item, "values")
        if not vals:
            return

        nome, cat, cit, tel, tipo, em, stato = vals
        if tipo.lower() != "cellulare" or not tel:
            messagebox.showwarning("Numero Non Idoneo", f"Il numero {tel} è un fisso o non è valido per WhatsApp.")
            return

        rec = {
            "nome_attivita": nome,
            "categoria": cat,
            "citta": cit,
            "telefono": tel,
            "tipo_telefono": tipo
        }
        ok = open_whatsapp_for_artisan(rec)
        if ok:
            # Aggiorna riga
            self.tree.item(item, values=(nome, cat, cit, tel, tipo, em, "✔ Inviato"))
            messagebox.showinfo("WhatsApp Aperto", f"Chat WhatsApp aperta per:\n{nome} ({tel})\n\nIl contatto è stato registrato come inviato.")
            self._load_existing_data()

    def _open_folder(self):
        try:
            os.startfile(str(BASE_DIR))
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _on_close(self):
        self.stop_event.set()
        if self.active_driver:
            try:
                self.active_driver.quit()
            except Exception:
                pass
        self.destroy()


def main():
    app = CasaLavoroTkApp()
    app.mainloop()


if __name__ == "__main__":
    main()

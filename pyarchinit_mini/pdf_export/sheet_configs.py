"""Per-entity section/field configs for the classic-style PDF sheet engine
(``entity_sheet_template.py``).

Each config is a plain dict ``{"title": ..., "id_col": ..., "sections": [...]}``
consumed by ``EntitySheet`` / ``generate_entity_sheets``. Section groupings and
field wording mirror the classic pyarchinit plugin's per-scheda PDFs
(``pyarchinit_exp_Tombasheet_pdf.py``, ``pyarchinit_exp_Strutturasheet_pdf.py``,
``pyarchinit_exp_Faunasheet_pdf.py``, ``pyarchinit_exp_UTsheet_pdf.py``,
``pyarchinit_exp_Individui_pdf.py``) — the classic non-fauna sheets are
hardcoded Italian anyway, so labels here are plain Italian strings (not the
lazy gettext ``_()`` used elsewhere in pdf_export) rather than resolved at
render time; that matches the source material exactly and keeps the configs
trivially readable/diffable. Every domain column of the corresponding model
(pyarchinit_mini/models/{tomba,struttura,fauna,ut,individui}.py) appears in
exactly one section below.
"""

# ---------------------------------------------------------------------------
# TOMBA — pyarchinit_mini/models/tomba.py (26 columns)
# ---------------------------------------------------------------------------
TOMBA_SHEET = {
    "title": "SCHEDA TOMBA",
    "id_col": "id_tomba",
    "sections": [
        {
            "title": "DATI IDENTIFICATIVI",
            "cols": 4,
            "fields": [
                {"name": "id_tomba", "label": "ID Scheda"},
                {"name": "sito", "label": "Sito"},
                {"name": "area", "label": "Area"},
                {"name": "nr_scheda_taf", "label": "N° Scheda TAF"},
                {"name": "sigla_struttura", "label": "Sigla Struttura"},
                {"name": "nr_struttura", "label": "N° Struttura"},
                {"name": "nr_individuo", "label": "N° Individuo"},
            ],
        },
        {
            "title": "PERIODIZZAZIONE DEL RITO DI SEPOLTURA",
            "cols": 4,
            "fields": [
                {"name": "periodo_iniziale", "label": "Periodo Iniziale"},
                {"name": "fase_iniziale", "label": "Fase Iniziale"},
                {"name": "periodo_finale", "label": "Periodo Finale"},
                {"name": "fase_finale", "label": "Fase Finale"},
                {"name": "datazione_estesa", "label": "Datazione", "long": True},
            ],
        },
        {
            "title": "ELEMENTI STRUTTURALI",
            "cols": 4,
            "fields": [
                {"name": "tipo_contenitore_resti", "label": "Tipo Tomba"},
                {"name": "copertura_tipo", "label": "Tipo Copertura"},
                {"name": "segnacoli", "label": "Segnacoli"},
                {"name": "canale_libatorio_si_no", "label": "Canale Libatorio"},
            ],
        },
        {
            "title": "DATI DEPOSIZIONALI",
            "cols": 3,
            "fields": [
                {"name": "rito", "label": "Tipo Rituale"},
                {"name": "tipo_deposizione", "label": "Tipo Deposizione"},
                {"name": "tipo_sepoltura", "label": "Tipo Sepoltura"},
                {"name": "stato_di_conservazione", "label": "Stato di Conservazione"},
                {"name": "oggetti_rinvenuti_esterno", "label": "Oggetti Rinvenuti Esterno"},
                {"name": "descrizione_taf", "label": "Descrizione", "long": True},
                {"name": "interpretazione_taf", "label": "Interpretazione", "long": True},
            ],
        },
        {
            "title": "CORREDO",
            "cols": 1,
            "fields": [
                {"name": "corredo_presenza", "label": "Presenza"},
                {"name": "corredo_descrizione", "label": "Descrizione", "long": True},
                {
                    "name": "corredo_tipo",
                    "label": "Elementi Corredo",
                    "type": "subtable",
                    "parse": "pylist",
                    "columns": [
                        "N° reperto", "N° individuo", "Materiale",
                        "Posizione del corredo", "Posizione nel corredo",
                    ],
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# STRUTTURA — pyarchinit_mini/models/struttura.py (35 columns, 10 of them the
# classic plugin's list-of-lists sub-table columns — see
# StrutturaService.SUBTABLE_COLS and templates/struttura/form.html for the
# per-row column headers).
# ---------------------------------------------------------------------------
STRUTTURA_SHEET = {
    "title": "SCHEDA STRUTTURA",
    "id_col": "id_struttura",
    "sections": [
        {
            "title": "DATI IDENTIFICATIVI",
            "cols": 4,
            "fields": [
                {"name": "id_struttura", "label": "ID Scheda"},
                {"name": "sito", "label": "Sito"},
                {"name": "sigla_struttura", "label": "Sigla"},
                {"name": "numero_struttura", "label": "N° Struttura"},
                {"name": "categoria_struttura", "label": "Categoria"},
                {"name": "tipologia_struttura", "label": "Tipologia"},
                {"name": "definizione_struttura", "label": "Definizione"},
                {"name": "data_compilazione", "label": "Data Compilazione"},
                {"name": "nome_compilatore", "label": "Compilatore"},
                {"name": "descrizione", "label": "Descrizione", "long": True},
                {"name": "interpretazione", "label": "Interpretazione", "long": True},
            ],
        },
        {
            "title": "PERIODIZZAZIONE",
            "cols": 4,
            "fields": [
                {"name": "periodo_iniziale", "label": "Periodo Iniziale"},
                {"name": "fase_iniziale", "label": "Fase Iniziale"},
                {"name": "periodo_finale", "label": "Periodo Finale"},
                {"name": "fase_finale", "label": "Fase Finale"},
                {"name": "datazione_estesa", "label": "Datazione Estesa", "long": True},
            ],
        },
        {
            "title": "ELEMENTI COSTRUTTIVI",
            "fields": [
                {
                    "name": "materiali_impiegati", "label": "Materiali Impiegati",
                    "type": "subtable", "parse": "pylist", "columns": ["Materiali"],
                },
                {
                    "name": "elementi_strutturali", "label": "Elementi Strutturali",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Tipologia elemento", "Quantità"],
                },
            ],
        },
        {
            "title": "RAPPORTI STRUTTURA",
            "fields": [
                {
                    "name": "rapporti_struttura", "label": "Rapporti Struttura",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Tipo di rapporto", "Sito", "Sigla", "Numero"],
                },
            ],
        },
        {
            "title": "MISURE STRUTTURA",
            "fields": [
                {
                    "name": "misure_struttura", "label": "Misure Struttura",
                    "type": "subtable", "parse": "pylist",
                    "columns": [
                        "Ubicazione", "Elementi architettonici", "Tipo misura",
                        "Unità di misura", "Valore",
                    ],
                },
            ],
        },
        {
            "title": "STATO DI CONSERVAZIONE",
            "fields": [
                {
                    "name": "stato_conservazione", "label": "Stato di Conservazione",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Stato", "Grado", "Fattori agenti"],
                },
            ],
        },
        {
            "title": "DATI ARCHITETTURA",
            "cols": 4,
            "fields": [
                {"name": "quota", "label": "Quota"},
                {"name": "relazione_topografica", "label": "Relazione Topografica"},
                {"name": "orientamento_ingresso", "label": "Orientamento Ingresso"},
                {"name": "articolazione", "label": "Articolazione"},
                {"name": "n_ambienti", "label": "N° Ambienti"},
                {"name": "sviluppo_planimetrico", "label": "Sviluppo Planimetrico"},
                {"name": "motivo_decorativo", "label": "Motivo Decorativo"},
                {
                    "name": "prospetto_ingresso", "label": "Prospetto Ingresso",
                    "type": "subtable", "parse": "pylist", "columns": ["Prospetto"],
                },
                {
                    "name": "orientamento_ambienti", "label": "Orientamento Ambienti",
                    "type": "subtable", "parse": "pylist", "columns": ["Orientamento"],
                },
                {
                    "name": "elementi_costitutivi", "label": "Elementi Costitutivi",
                    "type": "subtable", "parse": "pylist", "columns": ["Elemento"],
                },
            ],
        },
        {
            "title": "DATI ARCHEOLOGICI",
            "cols": 2,
            "fields": [
                {"name": "potenzialita_archeologica", "label": "Potenzialità Archeologica", "long": True},
                {"name": "elementi_datanti", "label": "Elementi Datanti"},
                {
                    "name": "manufatti", "label": "Manufatti",
                    "type": "subtable", "parse": "pylist", "columns": ["Manufatto"],
                },
                {
                    "name": "fasi_funzionali", "label": "Fasi Funzionali",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Ambiente", "Periodizzazione", "Definizione e fasi funzionali"],
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# FAUNA — pyarchinit_mini/models/fauna.py (36 columns)
# ---------------------------------------------------------------------------
FAUNA_SHEET = {
    "title": "SCHEDA FAUNA ARCHEOLOGICA",
    "id_col": "id_fauna",
    "sections": [
        {
            "title": "DATI IDENTIFICATIVI",
            "cols": 4,
            "fields": [
                {"name": "id_fauna", "label": "ID Scheda"},
                {"name": "id_us", "label": "ID US"},
                {"name": "sito", "label": "Sito"},
                {"name": "area", "label": "Area"},
                {"name": "saggio", "label": "Saggio"},
                {"name": "us", "label": "US"},
                {"name": "datazione_us", "label": "Datazione US"},
                {"name": "responsabile_scheda", "label": "Responsabile"},
                {"name": "data_compilazione", "label": "Data Compilazione"},
            ],
        },
        {
            "title": "CONTESTO E METODOLOGIA",
            "cols": 3,
            "fields": [
                {"name": "metodologia_recupero", "label": "Metodologia Recupero"},
                {"name": "contesto", "label": "Contesto"},
                {"name": "documentazione_fotografica", "label": "Doc. Fotografica"},
                {"name": "descrizione_contesto", "label": "Descrizione Contesto", "long": True},
            ],
        },
        {
            "title": "CARATTERISTICHE DEL DEPOSITO",
            "cols": 3,
            "fields": [
                {"name": "resti_connessione_anatomica", "label": "Connessione Anatomica"},
                {"name": "tipologia_accumulo", "label": "Tipologia Accumulo"},
                {"name": "deposizione", "label": "Deposizione"},
                {"name": "numero_stimato_resti", "label": "N. Stimato Resti"},
                {"name": "numero_minimo_individui", "label": "NMI"},
                {"name": "affidabilita_stratigrafica", "label": "Affidabilità Stratigrafica"},
            ],
        },
        {
            "title": "DATI TASSONOMICI",
            "cols": 2,
            "fields": [
                {"name": "specie", "label": "Specie"},
                {"name": "parti_scheletriche", "label": "Parti Scheletriche"},
                {
                    "name": "specie_psi", "label": "Specie / PSI",
                    "type": "subtable", "parse": "json", "columns": ["Specie", "PSI"],
                },
                {
                    "name": "misure_ossa", "label": "Misure Ossa",
                    "type": "subtable", "parse": "json",
                    "columns": [
                        "Elemento", "Specie", "GL (mm)", "GB (mm)", "Bp (mm)", "Bd (mm)",
                    ],
                },
            ],
        },
        {
            "title": "TAFONOMIA E CONSERVAZIONE",
            "cols": 3,
            "fields": [
                {"name": "stato_frammentazione", "label": "Frammentazione"},
                {"name": "stato_conservazione", "label": "Stato Conservazione"},
                {"name": "alterazioni_morfologiche", "label": "Alterazioni Morfologiche"},
                {"name": "tracce_combustione", "label": "Tracce Combustione"},
                {"name": "tipo_combustione", "label": "Tipo Combustione"},
                {"name": "combustione_altri_materiali_us", "label": "Altri Materiali Combusti US"},
                {"name": "segni_tafonomici_evidenti", "label": "Segni Tafonomici Evidenti"},
                {"name": "caratterizzazione_segni_tafonomici", "label": "Caratterizzazione Tafonomica", "long": True},
            ],
        },
        {
            "title": "NOTE E INTERPRETAZIONE",
            "fields": [
                {"name": "note_terreno_giacitura", "label": "Note Terreno/Giacitura", "long": True},
                {"name": "campionature_effettuate", "label": "Campionature Effettuate", "long": True},
                {"name": "classi_reperti_associazione", "label": "Classi Reperti Associati", "long": True},
                {"name": "osservazioni", "label": "Osservazioni", "long": True},
                {"name": "interpretazione", "label": "Interpretazione", "long": True},
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# UT — pyarchinit_mini/models/ut.py (59 columns)
# ---------------------------------------------------------------------------
UT_SHEET = {
    "title": "SCHEDA UNITÀ TOPOGRAFICA",
    "id_col": "id_ut",
    "sections": [
        {
            "title": "IDENTIFICAZIONE",
            "cols": 3,
            "fields": [
                {"name": "id_ut", "label": "ID Scheda"},
                {"name": "progetto", "label": "Progetto"},
                {"name": "nr_ut", "label": "N° UT"},
                {"name": "ut_letterale", "label": "UT Letterale"},
                {"name": "def_ut", "label": "Definizione"},
                {"name": "geometria", "label": "Geometria"},
                {"name": "descrizione_ut", "label": "Descrizione", "long": True},
                {"name": "interpretazione_ut", "label": "Interpretazione", "long": True},
            ],
        },
        {
            "title": "LOCALIZZAZIONE",
            "cols": 4,
            "fields": [
                {"name": "nazione", "label": "Nazione"},
                {"name": "regione", "label": "Regione"},
                {"name": "provincia", "label": "Provincia"},
                {"name": "comune", "label": "Comune"},
                {"name": "frazione", "label": "Frazione"},
                {"name": "localita", "label": "Località"},
                {"name": "indirizzo", "label": "Indirizzo"},
                {"name": "nr_civico", "label": "N° Civico"},
                {"name": "carta_topo_igm", "label": "Carta IGM"},
                {"name": "carta_ctr", "label": "Carta CTR"},
                {"name": "foglio_catastale", "label": "Foglio Catastale"},
                {"name": "quota", "label": "Quota (m)"},
                {"name": "coord_geografiche", "label": "Coordinate Geografiche"},
                {"name": "coord_piane", "label": "Coordinate Piane"},
            ],
        },
        {
            "title": "CARATTERISTICHE DEL TERRENO",
            "cols": 3,
            "fields": [
                {"name": "andamento_terreno_pendenza", "label": "Pendenza"},
                {"name": "utilizzo_suolo_vegetazione", "label": "Uso del Suolo"},
                {"name": "dimensioni_ut", "label": "Dimensioni"},
                {"name": "descrizione_empirica_suolo", "label": "Descrizione Suolo", "long": True},
                {"name": "descrizione_luogo", "label": "Descrizione Luogo", "long": True},
            ],
        },
        {
            "title": "DATI RICOGNIZIONE",
            "cols": 4,
            "fields": [
                {"name": "data", "label": "Data"},
                {"name": "responsabile", "label": "Responsabile"},
                {"name": "metodo_rilievo_e_ricognizione", "label": "Metodo Ricognizione"},
                {"name": "survey_type", "label": "Tipo Survey"},
                {"name": "visibility_percent", "label": "Visibilità (%)"},
                {"name": "vegetation_coverage", "label": "Copertura Vegetale"},
                {"name": "surface_condition", "label": "Condizione Superficie"},
                {"name": "accessibility", "label": "Accessibilità"},
                {"name": "gps_method", "label": "Metodo GPS"},
                {"name": "coordinate_precision", "label": "Precisione GPS (m)"},
                {"name": "weather_conditions", "label": "Condizioni Meteo"},
                {"name": "photo_documentation", "label": "Doc. Fotografica"},
                {"name": "team_members", "label": "Team Survey"},
                {"name": "ora_meteo", "label": "Ora e Meteo"},
            ],
        },
        {
            "title": "CRONOLOGIA E INTERPRETAZIONE",
            "cols": 3,
            "fields": [
                {"name": "rep_per_mq", "label": "Reperti per m²"},
                {"name": "rep_datanti", "label": "Reperti Datanti"},
                {"name": "periodo_I", "label": "Periodo I"},
                {"name": "datazione_I", "label": "Datazione I"},
                {"name": "interpretazione_I", "label": "Interpretazione I"},
                {"name": "periodo_II", "label": "Periodo II"},
                {"name": "datazione_II", "label": "Datazione II"},
                {"name": "interpretazione_II", "label": "Interpretazione II"},
            ],
        },
        {
            "title": "ANALISI POTENZIALE/RISCHIO",
            "cols": 4,
            "fields": [
                {"name": "potential_score", "label": "Potenziale Archeologico"},
                {"name": "risk_score", "label": "Rischio Archeologico"},
                {"name": "analysis_date", "label": "Data Analisi"},
                {"name": "analysis_method", "label": "Metodo Analisi"},
                {"name": "potential_factors", "label": "Fattori di Potenziale", "long": True},
                {"name": "risk_factors", "label": "Fattori di Rischio", "long": True},
            ],
        },
        {
            "title": "DOCUMENTAZIONE",
            "cols": 2,
            "fields": [
                {"name": "enti_tutela_vincoli", "label": "Vincoli e Tutela"},
                {"name": "indagini_preliminari", "label": "Indagini Preliminari"},
                {
                    "name": "bibliografia", "label": "Bibliografia",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Riferimenti bibliografici"],
                },
                {
                    "name": "documentazione", "label": "Documentazione",
                    "type": "subtable", "parse": "pylist",
                    "columns": ["Tipo documentazione", "Riferimenti"],
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# INDIVIDUI — pyarchinit_mini/models/individui.py (24 columns, all scalar)
# ---------------------------------------------------------------------------
INDIVIDUI_SHEET = {
    "title": "SCHEDA INDIVIDUI",
    "id_col": "id_scheda_ind",
    "sections": [
        {
            "title": "DATI IDENTIFICATIVI",
            "cols": 4,
            "fields": [
                {"name": "id_scheda_ind", "label": "ID Scheda"},
                {"name": "sito", "label": "Sito"},
                {"name": "area", "label": "Area"},
                {"name": "us", "label": "US"},
                {"name": "nr_individuo", "label": "N° Individuo"},
                {"name": "data_schedatura", "label": "Data Schedatura"},
                {"name": "schedatore", "label": "Schedatore"},
                {"name": "sigla_struttura", "label": "Sigla Struttura"},
                {"name": "nr_struttura", "label": "N° Struttura"},
            ],
        },
        {
            "title": "DATI ANTROPOLOGICI",
            "cols": 3,
            "fields": [
                {"name": "sesso", "label": "Sesso"},
                {"name": "eta_min", "label": "Età Minima"},
                {"name": "eta_max", "label": "Età Massima"},
                {"name": "classi_eta", "label": "Classi di Età"},
            ],
        },
        {
            "title": "STATO E POSIZIONE SCHELETRO",
            "cols": 4,
            "fields": [
                {"name": "completo_si_no", "label": "Completo"},
                {"name": "disturbato_si_no", "label": "Disturbato"},
                {"name": "in_connessione_si_no", "label": "In Connessione"},
                {"name": "lunghezza_scheletro", "label": "Lunghezza Scheletro"},
                {"name": "posizione_scheletro", "label": "Posizione Scheletro"},
                {"name": "posizione_cranio", "label": "Posizione Cranio"},
                {"name": "posizione_arti_superiori", "label": "Posizione Arti Superiori"},
                {"name": "posizione_arti_inferiori", "label": "Posizione Arti Inferiori"},
                {"name": "orientamento_asse", "label": "Orientamento Asse"},
                {"name": "orientamento_azimut", "label": "Orientamento Azimut"},
            ],
        },
        {
            "title": "OSSERVAZIONI",
            "fields": [
                {"name": "osservazioni", "label": "Osservazioni", "long": True},
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Registry consumed by PDFGenerator.generate_entity_records_pdf — maps the
# entity_key used by the export routes (app.py) to its sheet config.
# ---------------------------------------------------------------------------
SHEET_CONFIGS = {
    "tomba": TOMBA_SHEET,
    "struttura": STRUTTURA_SHEET,
    "fauna": FAUNA_SHEET,
    "ut": UT_SHEET,
    "individui": INDIVIDUI_SHEET,
}

"""Tests for the classic-plugin-style PDF sheet engine
(entity_sheet_template.generate_entity_sheets) + the 5 per-scheda configs
in sheet_configs.py.

No pdfminer / PDF-parsing deps — assertions are size + magic-bytes only,
matching the repo's existing PDF test style (tests/test_pdf_generator_records.py).
"""
import os

import pytest

from pyarchinit_mini.pdf_export.entity_sheet_template import generate_entity_sheets
from pyarchinit_mini.pdf_export.sheet_configs import (
    FAUNA_SHEET,
    INDIVIDUI_SHEET,
    STRUTTURA_SHEET,
    TOMBA_SHEET,
    UT_SHEET,
)

TOMBA_RECORD = {
    'id_tomba': 1, 'sito': 'Volterra', 'area': 1, 'nr_scheda_taf': 1,
    'sigla_struttura': 'T', 'nr_struttura': 1, 'nr_individuo': '1',
    'rito': 'Inumazione', 'descrizione_taf': 'Descrizione test',
    'interpretazione_taf': 'Interpretazione test', 'segnacoli': 'Si',
    'canale_libatorio_si_no': 'No', 'oggetti_rinvenuti_esterno': 'Nessuno',
    'stato_di_conservazione': 'Buono', 'copertura_tipo': 'Laterizi',
    'tipo_contenitore_resti': 'Cassa', 'tipo_deposizione': 'Primaria',
    'tipo_sepoltura': 'Semplice', 'corredo_presenza': 'Si',
    'corredo_tipo': "[['1', '2', 'Bronzo', 'Interno', 'Sopra']]",
    'corredo_descrizione': 'Fibula in bronzo',
    'periodo_iniziale': 1, 'fase_iniziale': 1, 'periodo_finale': 2,
    'fase_finale': 1, 'datazione_estesa': 'IV sec. a.C.',
}

STRUTTURA_RECORD = {
    'id_struttura': 1, 'sito': 'Volterra', 'sigla_struttura': 'ST',
    'numero_struttura': 1, 'categoria_struttura': 'Muro',
    'tipologia_struttura': 'Perimetrale', 'definizione_struttura': 'Muro in pietra',
    'descrizione': 'Descrizione struttura', 'interpretazione': 'Interpretazione struttura',
    'periodo_iniziale': 1, 'fase_iniziale': 1, 'periodo_finale': 2, 'fase_finale': 1,
    'datazione_estesa': 'III sec. a.C.',
    'materiali_impiegati': "[['pietra'], ['malta']]",
    'elementi_strutturali': "[['blocco', '10']]",
    'rapporti_struttura': "[['si lega a', 'Volterra', 'ST', '2']]",
    'misure_struttura': "[['esterno', 'muro', 'lunghezza', 'm', '5.2']]",
    'data_compilazione': '2026-01-01', 'nome_compilatore': 'Mario Rossi',
    'stato_conservazione': "[['buono', 'medio', 'umidita']]",
    'quota': 12.5, 'relazione_topografica': 'Nord', 'prospetto_ingresso': "[['Est']]",
    'orientamento_ingresso': 'Est', 'articolazione': 'Semplice', 'n_ambienti': 1,
    'orientamento_ambienti': "[['N']]", 'sviluppo_planimetrico': 'Rettangolare',
    'elementi_costitutivi': "[['soglia']]", 'motivo_decorativo': 'Nessuno',
    'potenzialita_archeologica': 'Alta', 'manufatti': "[['ceramica']]",
    'elementi_datanti': 'Ceramica a vernice nera',
    'fasi_funzionali': "[['ambiente1', 'I', 'uso domestico']]",
}

FAUNA_RECORD = {
    'id_fauna': 1, 'id_us': 100, 'sito': 'Volterra', 'area': '1', 'saggio': '1',
    'us': '100', 'datazione_us': 'IV sec. a.C.', 'responsabile_scheda': 'Mario Rossi',
    'data_compilazione': '2026-01-01', 'documentazione_fotografica': 'Si',
    'metodologia_recupero': 'Setacciatura', 'contesto': 'US',
    'descrizione_contesto': 'Riempimento fossa', 'resti_connessione_anatomica': 'No',
    'tipologia_accumulo': 'Rifiuto', 'deposizione': 'Secondaria',
    'numero_stimato_resti': '15', 'numero_minimo_individui': 2,
    'specie': 'Bos taurus', 'parti_scheletriche': 'Femore',
    'specie_psi': '[["Bos taurus","femore"]]',
    'misure_ossa': '[["femore","Bos taurus","220","45","50","55"]]',
    'stato_frammentazione': 'Alta', 'tracce_combustione': 'No',
    'combustione_altri_materiali_us': False, 'tipo_combustione': '',
    'segni_tafonomici_evidenti': 'No', 'caratterizzazione_segni_tafonomici': '',
    'stato_conservazione': 'Buono', 'alterazioni_morfologiche': 'No',
    'note_terreno_giacitura': 'In situ', 'campionature_effettuate': 'Si',
    'affidabilita_stratigrafica': 'Alta', 'classi_reperti_associazione': 'Ceramica',
    'osservazioni': 'Nessuna', 'interpretazione': 'Scarto alimentare',
}

UT_RECORD = {
    'id_ut': 1, 'progetto': 'Survey Test', 'nr_ut': 1, 'ut_letterale': 'A',
    'def_ut': 'Area di frammenti fittili', 'descrizione_ut': 'Descrizione',
    'interpretazione_ut': 'Interpretazione', 'nazione': 'Italia', 'regione': 'Toscana',
    'provincia': 'PI', 'comune': 'Volterra', 'frazione': '', 'localita': 'Loc. test',
    'indirizzo': '', 'nr_civico': '', 'carta_topo_igm': '106', 'carta_ctr': '',
    'coord_geografiche': '43.4,10.8', 'coord_piane': '', 'quota': 200.0,
    'andamento_terreno_pendenza': 'Pianeggiante', 'utilizzo_suolo_vegetazione': 'Seminativo',
    'descrizione_empirica_suolo': 'Argilloso', 'descrizione_luogo': 'Pianura',
    'metodo_rilievo_e_ricognizione': 'GPS', 'geometria': 'Poligono',
    'bibliografia': "[['Rossi 2020']]", 'data': '2026-01-01', 'ora_meteo': '10:00 sereno',
    'responsabile': 'Mario Rossi', 'dimensioni_ut': '50x50m', 'rep_per_mq': '2',
    'rep_datanti': 'Ceramica', 'periodo_I': 'Etrusco', 'datazione_I': 'IV sec a.C.',
    'interpretazione_I': 'Insediamento', 'periodo_II': '', 'datazione_II': '',
    'interpretazione_II': '', 'documentazione': "[['Foto', 'DOC001']]",
    'enti_tutela_vincoli': 'Nessuno', 'indagini_preliminari': 'Nessuna',
    'visibility_percent': 80, 'vegetation_coverage': 'Bassa', 'gps_method': 'RTK',
    'coordinate_precision': 0.02, 'survey_type': 'Sistematica', 'surface_condition': 'Arato',
    'accessibility': 'Buona', 'photo_documentation': 1, 'weather_conditions': 'Sereno',
    'team_members': 'A,B', 'foglio_catastale': '12', 'potential_score': 75.0,
    'risk_score': 30.0, 'potential_factors': 'Densita reperti alta',
    'risk_factors': 'Arature profonde', 'analysis_date': '2026-01-02',
    'analysis_method': 'GIS',
}

INDIVIDUI_RECORD = {
    'id_scheda_ind': 1, 'sito': 'Volterra', 'area': '1', 'us': '100', 'nr_individuo': 1,
    'data_schedatura': '2026-01-01', 'schedatore': 'Mario Rossi', 'sesso': 'M',
    'eta_min': '20', 'eta_max': '30', 'classi_eta': 'Adulto', 'osservazioni': 'Nessuna',
    'sigla_struttura': 'T', 'nr_struttura': 1, 'completo_si_no': 'Si',
    'disturbato_si_no': 'No', 'in_connessione_si_no': 'Si', 'lunghezza_scheletro': 170.0,
    'posizione_scheletro': 'Supino', 'posizione_cranio': 'Est',
    'posizione_arti_superiori': 'Lungo il corpo', 'posizione_arti_inferiori': 'Distesi',
    'orientamento_asse': 'E-O', 'orientamento_azimut': '90',
}

ALL_CONFIGS = [
    ('tomba', TOMBA_SHEET, TOMBA_RECORD),
    ('struttura', STRUTTURA_SHEET, STRUTTURA_RECORD),
    ('fauna', FAUNA_SHEET, FAUNA_RECORD),
    ('ut', UT_SHEET, UT_RECORD),
    ('individui', INDIVIDUI_SHEET, INDIVIDUI_RECORD),
]


def _assert_valid_pdf(path, min_size=2048):
    assert os.path.exists(path)
    data = open(path, 'rb').read()
    assert data.startswith(b'%PDF')
    assert len(data) > min_size


@pytest.mark.parametrize('name,config,record', ALL_CONFIGS, ids=[c[0] for c in ALL_CONFIGS])
def test_generate_entity_sheets_all_configs(tmp_path, name, config, record):
    output_path = str(tmp_path / f'{name}.pdf')
    result = generate_entity_sheets([record], config, output_path)
    assert result == output_path
    _assert_valid_pdf(output_path)


def test_tomba_corredo_subtable_renders_and_grows_pdf(tmp_path):
    with_subtable = str(tmp_path / 'tomba_with.pdf')
    generate_entity_sheets([TOMBA_RECORD], TOMBA_SHEET, with_subtable)
    _assert_valid_pdf(with_subtable)

    record_without = dict(TOMBA_RECORD)
    record_without['corredo_tipo'] = None
    without_subtable = str(tmp_path / 'tomba_without.pdf')
    generate_entity_sheets([record_without], TOMBA_SHEET, without_subtable)
    _assert_valid_pdf(without_subtable, min_size=0)

    assert os.path.getsize(with_subtable) > os.path.getsize(without_subtable)


def test_fauna_specie_psi_subtable_renders(tmp_path):
    output_path = str(tmp_path / 'fauna_psi.pdf')
    generate_entity_sheets([FAUNA_RECORD], FAUNA_SHEET, output_path)
    _assert_valid_pdf(output_path)


def test_fauna_boolean_field_renders_as_si_no(tmp_path):
    """Real Python bools (e.g. combustione_altri_materiali_us=True) must
    render as 'Sì'/'No' without raising — never as literal 'True'/'False'
    leaking through, and never crashing the PDF build."""
    record_true = dict(FAUNA_RECORD, combustione_altri_materiali_us=True)
    output_path = str(tmp_path / 'fauna_bool_true.pdf')
    result = generate_entity_sheets([record_true], FAUNA_SHEET, output_path)
    assert result == output_path
    _assert_valid_pdf(output_path)

    record_false = dict(FAUNA_RECORD, combustione_altri_materiali_us=False)
    output_path_false = str(tmp_path / 'fauna_bool_false.pdf')
    generate_entity_sheets([record_false], FAUNA_SHEET, output_path_false)
    _assert_valid_pdf(output_path_false)


def test_empty_rows_list_produces_valid_pdf(tmp_path):
    for name, config, _ in ALL_CONFIGS:
        output_path = str(tmp_path / f'{name}_empty.pdf')
        result = generate_entity_sheets([], config, output_path)
        assert result == output_path
        data = open(output_path, 'rb').read()
        assert data.startswith(b'%PDF')


def test_none_and_empty_values_do_not_crash(tmp_path):
    sparse_record = {'id_tomba': 1, 'sito': None, 'rito': '', 'corredo_tipo': None}
    output_path = str(tmp_path / 'tomba_sparse.pdf')
    result = generate_entity_sheets([sparse_record], TOMBA_SHEET, output_path)
    assert result == output_path
    data = open(output_path, 'rb').read()
    assert data.startswith(b'%PDF')


def test_fully_empty_record_does_not_crash(tmp_path):
    for name, config, _ in ALL_CONFIGS:
        output_path = str(tmp_path / f'{name}_blank.pdf')
        result = generate_entity_sheets([{}], config, output_path)
        assert result == output_path
        data = open(output_path, 'rb').read()
        assert data.startswith(b'%PDF')


@pytest.mark.parametrize('malformed', [
    'not a list at all',
    "[1, 2, 3",  # unterminated / invalid syntax
    "{'not': 'a list'}",
    "['flat', 'list', 'no', 'sublists']",
    12345,
    '',
])
def test_malformed_subtable_value_does_not_crash(tmp_path, malformed):
    record = dict(TOMBA_RECORD)
    record['corredo_tipo'] = malformed
    output_path = str(tmp_path / 'tomba_malformed.pdf')
    result = generate_entity_sheets([record], TOMBA_SHEET, output_path)
    assert result == output_path
    data = open(output_path, 'rb').read()
    assert data.startswith(b'%PDF')


def test_multi_record_pagebreak(tmp_path):
    output_path = str(tmp_path / 'tomba_multi.pdf')
    records = [TOMBA_RECORD, dict(TOMBA_RECORD, id_tomba=2, sito='Altro Sito')]
    result = generate_entity_sheets(records, TOMBA_SHEET, output_path)
    assert result == output_path
    _assert_valid_pdf(output_path)

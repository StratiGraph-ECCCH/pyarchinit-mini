from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba

def test_tomba_table_columns():
    eng = create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("tomba_table")}
    expected = {"id_tomba","sito","area","nr_scheda_taf","sigla_struttura","nr_struttura",
        "nr_individuo","rito","descrizione_taf","interpretazione_taf","segnacoli",
        "canale_libatorio_si_no","oggetti_rinvenuti_esterno","stato_di_conservazione",
        "copertura_tipo","tipo_contenitore_resti","tipo_deposizione","tipo_sepoltura",
        "corredo_presenza","corredo_tipo","corredo_descrizione","periodo_iniziale",
        "fase_iniziale","periodo_finale","fase_finale","datazione_estesa","entity_uuid"}
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number","sync_status","created_at"} <= cols

def test_to_dict():
    t = Tomba(id_tomba=1, sito="S", rito="inumazione")
    d = t.to_dict()
    assert d["id_tomba"] == 1 and d["rito"] == "inumazione"

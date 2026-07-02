from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.struttura import Struttura

def test_struttura_table_columns():
    eng = create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("struttura_table")}
    expected = {"id_struttura","sito","sigla_struttura","numero_struttura","categoria_struttura",
        "tipologia_struttura","definizione_struttura","descrizione","interpretazione",
        "periodo_iniziale","fase_iniziale","periodo_finale","fase_finale","datazione_estesa",
        "materiali_impiegati","elementi_strutturali","rapporti_struttura","misure_struttura",
        "data_compilazione","nome_compilatore","stato_conservazione","quota","relazione_topografica",
        "prospetto_ingresso","orientamento_ingresso","articolazione","n_ambienti",
        "orientamento_ambienti","sviluppo_planimetrico","elementi_costitutivi","motivo_decorativo",
        "potenzialita_archeologica","manufatti","elementi_datanti","fasi_funzionali","entity_uuid"}
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number","sync_status","created_at"} <= cols

def test_to_dict():
    s = Struttura(id_struttura=1, sito="S", categoria_struttura="muratura", quota=42.5)
    d = s.to_dict()
    assert d["id_struttura"] == 1 and d["categoria_struttura"] == "muratura" and d["quota"] == 42.5

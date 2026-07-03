from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.fauna import Fauna

def test_fauna_table_columns():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("fauna_table")}
    expected = {
        "id_fauna", "id_us", "sito", "area", "saggio", "us", "datazione_us",
        "responsabile_scheda", "data_compilazione", "documentazione_fotografica",
        "metodologia_recupero", "contesto", "descrizione_contesto",
        "resti_connessione_anatomica", "tipologia_accumulo", "deposizione",
        "numero_stimato_resti", "numero_minimo_individui", "specie",
        "parti_scheletriche", "specie_psi", "misure_ossa", "stato_frammentazione",
        "tracce_combustione", "combustione_altri_materiali_us", "tipo_combustione",
        "segni_tafonomici_evidenti", "caratterizzazione_segni_tafonomici",
        "stato_conservazione", "alterazioni_morfologiche", "note_terreno_giacitura",
        "campionature_effettuate", "affidabilita_stratigrafica",
        "classi_reperti_associazione", "osservazioni", "interpretazione",
        "entity_uuid"
    }
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number", "sync_status", "created_at"} <= cols

def test_fauna_id_fauna_type():
    """Assert id_fauna is BigInteger type"""
    assert Fauna.__table__.c.id_fauna.type.__class__.__name__ == 'BigInteger'

def test_fauna_data_compilazione_type():
    """Assert data_compilazione is Date type"""
    assert Fauna.__table__.c.data_compilazione.type.__class__.__name__ == 'Date'

def test_fauna_combustione_altri_materiali_us_type():
    """Assert combustione_altri_materiali_us is Boolean type"""
    assert Fauna.__table__.c.combustione_altri_materiali_us.type.__class__.__name__ == 'Boolean'

def test_fauna_to_dict():
    """Assert to_dict() round-trips a couple fields"""
    f = Fauna(
        id_fauna=1,
        sito="Volterra",
        numero_minimo_individui=3,
        combustione_altri_materiali_us=True
    )
    d = f.to_dict()
    assert d["id_fauna"] == 1
    assert d["sito"] == "Volterra"
    assert d["numero_minimo_individui"] == 3
    assert d["combustione_altri_materiali_us"] is True

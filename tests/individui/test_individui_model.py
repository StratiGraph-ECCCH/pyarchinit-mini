from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.individui import Individui


def test_individui_table_columns():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("individui_table")}
    expected = {
        "id_scheda_ind", "sito", "area", "us", "nr_individuo", "data_schedatura",
        "schedatore", "sesso", "eta_min", "eta_max", "classi_eta", "osservazioni",
        "sigla_struttura", "nr_struttura", "completo_si_no", "disturbato_si_no",
        "in_connessione_si_no", "lunghezza_scheletro", "posizione_scheletro",
        "posizione_cranio", "posizione_arti_superiori", "posizione_arti_inferiori",
        "orientamento_asse", "orientamento_azimut"
    }
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number", "sync_status", "created_at", "entity_uuid"} <= cols


def test_individui_lunghezza_scheletro_type():
    """Assert lunghezza_scheletro is Numeric type"""
    assert Individui.__table__.c.lunghezza_scheletro.type.__class__.__name__ == 'Numeric'


def test_individui_nr_individuo_type():
    """Assert nr_individuo is Integer type"""
    assert Individui.__table__.c.nr_individuo.type.__class__.__name__ == 'Integer'


def test_individui_unique_constraint():
    """Assert the unique constraint ID_individuo_unico exists on (sito, nr_individuo)"""
    constraint_names = {c.name for c in Individui.__table__.constraints if hasattr(c, 'name')}
    assert 'ID_individuo_unico' in constraint_names


def test_individui_to_dict():
    """Assert to_dict() round-trips a couple fields"""
    ind = Individui(
        id_scheda_ind=1,
        sito="Volterra",
        nr_individuo=42,
        sesso="M",
        lunghezza_scheletro=175.50
    )
    d = ind.to_dict()
    assert d["id_scheda_ind"] == 1
    assert d["sito"] == "Volterra"
    assert d["nr_individuo"] == 42
    assert d["sesso"] == "M"

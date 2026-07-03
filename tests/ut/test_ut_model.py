from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.ut import Ut


def test_ut_table_columns():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("ut_table")}
    expected = {
        "id_ut", "progetto", "nr_ut", "ut_letterale", "def_ut", "descrizione_ut",
        "interpretazione_ut", "nazione", "regione", "provincia", "comune", "frazione",
        "localita", "indirizzo", "nr_civico", "carta_topo_igm", "carta_ctr",
        "coord_geografiche", "coord_piane", "quota", "andamento_terreno_pendenza",
        "utilizzo_suolo_vegetazione", "descrizione_empirica_suolo", "descrizione_luogo",
        "metodo_rilievo_e_ricognizione", "geometria", "bibliografia", "data", "ora_meteo",
        "responsabile", "dimensioni_ut", "rep_per_mq", "rep_datanti", "periodo_I",
        "datazione_I", "interpretazione_I", "periodo_II", "datazione_II",
        "interpretazione_II", "documentazione", "enti_tutela_vincoli", "indagini_preliminari",
        "visibility_percent", "vegetation_coverage", "gps_method", "coordinate_precision",
        "survey_type", "surface_condition", "accessibility", "photo_documentation",
        "weather_conditions", "team_members", "foglio_catastale", "potential_score",
        "risk_score", "potential_factors", "risk_factors", "analysis_date", "analysis_method",
        "entity_uuid"
    }
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number", "sync_status", "created_at"} <= cols


def test_numeric_types():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    assert Ut.__table__.c.potential_score.type.__class__.__name__ == 'Numeric'
    assert Ut.__table__.c.risk_score.type.__class__.__name__ == 'Numeric'
    assert Ut.__table__.c.quota.type.__class__.__name__ == 'Float'
    assert Ut.__table__.c.coordinate_precision.type.__class__.__name__ == 'Float'


def test_to_dict():
    u = Ut(id_ut=1, nr_ut=5, progetto="P1", quota=42.5, potential_score=7.50)
    d = u.to_dict()
    assert d["id_ut"] == 1
    assert d["nr_ut"] == 5
    assert d["progetto"] == "P1"
    assert d["quota"] == 42.5
    assert d["potential_score"] == 7.50

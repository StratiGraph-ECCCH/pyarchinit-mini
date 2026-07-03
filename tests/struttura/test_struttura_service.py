import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.struttura import Struttura  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle
from pyarchinit_mini.services.struttura_service import StrutturaService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)

@pytest.fixture
def svc():
    e=create_engine("sqlite:///:memory:"); Base.metadata.create_all(e)
    return StrutturaService(_DBM(e))

def test_crud(svc):
    sid = svc.create_struttura({"sito":"Volterra","categoria_struttura":"muratura","sigla_struttura":"ST1"})
    assert sid and svc.get_struttura(sid)["categoria_struttura"]=="muratura"
    assert svc.update_struttura(sid, {"categoria_struttura":"crollo"}) is True
    assert svc.get_struttura(sid)["categoria_struttura"]=="crollo"
    assert [r["id_struttura"] for r in svc.list_struttura()]==[sid]
    assert svc.count_struttura()==1
    assert svc.get_distinct_sites()==["Volterra"]
    assert svc.delete_struttura(sid) is True and svc.get_struttura(sid) is None

def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope")==[]


def test_get_thesaurus_values_reads_plugin_shared_pyarchinit_thesaurus_sigle(svc):
    """Mini's thesaurus combos must read the SAME pyarchinit_thesaurus_sigle
    source the classic plugin fills, so vocab is shared on the festos DB."""
    session = svc.db_manager.connection.get_session()
    session.add(ThesaurusSigle(
        nome_tabella="struttura_table", tipologia_sigla="6.2",
        sigla="MUR", sigla_estesa="Muro", lingua="it",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("categoria_struttura")
    assert {"value": "Muro", "code": "MUR"} in values


def test_get_thesaurus_values_falls_back_to_seed_when_db_empty(svc):
    """A THESAURUS_MAP field with no rows in either pyarchinit_thesaurus_sigle
    or thesaurus_field must still return the in-memory THESAURUS_MAPPINGS seed."""
    from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
    values = svc.get_thesaurus_values("tipologia_struttura")
    expected = THESAURUS_MAPPINGS["struttura_table"]["tipologia_struttura"]
    assert values == [{"value": v, "code": ""} for v in expected]


def test_get_thesaurus_values_truly_unknown_field_returns_empty(svc):
    assert svc.get_thesaurus_values("this_field_does_not_exist_anywhere") == []

def test_search_matches_text_fields(svc):
    svc.create_struttura({"sito": "Volterra", "categoria_struttura": "muratura", "sigla_struttura": "ST1"})
    svc.create_struttura({"sito": "Cerveteri", "categoria_struttura": "crollo"})
    assert len(svc.list_struttura(search="mura")) == 1
    assert svc.count_struttura(search="mura") == 1
    assert svc.list_struttura(search="zzz") == []


def test_create_struttura_ignores_mass_assignment_of_managed_fields(svc):
    """A crafted POST injecting id_struttura/version_number/entity_uuid/sync_status
    must not be able to force those values — they are BaseModel-managed or
    the PK, and must be assigned by the DB/model defaults only."""
    sid = svc.create_struttura({
        "sito": "S",
        "id_struttura": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
    })
    assert sid is not None
    assert sid != 999
    row = svc.get_struttura(sid)
    assert row["id_struttura"] == sid
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"


def test_update_struttura_ignores_mass_assignment_of_managed_fields(svc):
    sid = svc.create_struttura({"sito": "S"})
    original = svc.get_struttura(sid)
    ok = svc.update_struttura(sid, {
        "id_struttura": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
        "sito": "Updated",
    })
    assert ok is True
    row = svc.get_struttura(sid)
    assert row["id_struttura"] == sid  # unchanged, not 999
    assert row["sito"] == "Updated"  # legitimate field still writable
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"
    assert row["entity_uuid"] == original["entity_uuid"]


def test_create_struttura_coerces_integer_string(svc):
    sid = svc.create_struttura({"sito": "S", "numero_struttura": "7"})
    row = svc.get_struttura(sid)
    assert row["numero_struttura"] == 7
    assert isinstance(row["numero_struttura"], int)


def test_create_struttura_coerces_float_string(svc):
    sid = svc.create_struttura({"sito": "S", "numero_struttura": "7", "quota": "1.5"})
    row = svc.get_struttura(sid)
    assert row["numero_struttura"] == 7
    assert isinstance(row["numero_struttura"], int)
    assert row["quota"] == 1.5
    assert isinstance(row["quota"], float)


def test_create_struttura_unparseable_numbers_become_none(svc):
    sid = svc.create_struttura({"sito": "S", "quota": "abc", "n_ambienti": "xx"})
    row = svc.get_struttura(sid)
    assert row["quota"] is None
    assert row["n_ambienti"] is None


def test_update_struttura_coerces_integer_string(svc):
    sid = svc.create_struttura({"sito": "S"})
    assert svc.update_struttura(sid, {"numero_struttura": "12"}) is True
    row = svc.get_struttura(sid)
    assert row["numero_struttura"] == 12

    assert svc.update_struttura(sid, {"numero_struttura": "xyz"}) is True
    row = svc.get_struttura(sid)
    assert row["numero_struttura"] is None


def test_update_struttura_coerces_float_string(svc):
    sid = svc.create_struttura({"sito": "S"})
    assert svc.update_struttura(sid, {"quota": "3.25"}) is True
    row = svc.get_struttura(sid)
    assert row["quota"] == 3.25

    assert svc.update_struttura(sid, {"quota": "notafloat"}) is True
    row = svc.get_struttura(sid)
    assert row["quota"] is None

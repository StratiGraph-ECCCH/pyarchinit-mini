import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle
from pyarchinit_mini.services.tomba_service import TombaService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)

@pytest.fixture
def svc():
    e=create_engine("sqlite:///:memory:"); Base.metadata.create_all(e)
    return TombaService(_DBM(e))

def test_crud(svc):
    tid = svc.create_tomba({"sito":"Volterra","rito":"inumazione","nr_scheda_taf":"3"})
    assert tid and svc.get_tomba(tid)["rito"]=="inumazione"
    assert svc.update_tomba(tid, {"rito":"cremazione"}) is True
    assert svc.get_tomba(tid)["rito"]=="cremazione"
    assert [r["id_tomba"] for r in svc.list_tomba()]==[tid]
    assert svc.count_tomba()==1
    assert svc.get_distinct_sites()==["Volterra"]
    assert svc.delete_tomba(tid) is True and svc.get_tomba(tid) is None

def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope")==[]


def test_get_thesaurus_values_reads_plugin_shared_pyarchinit_thesaurus_sigle(svc):
    """Mini's thesaurus combos must read the SAME pyarchinit_thesaurus_sigle
    source the classic plugin fills, so vocab is shared on the festos DB."""
    session = svc.db_manager.connection.get_session()
    session.add(ThesaurusSigle(
        nome_tabella="tomba_table", tipologia_sigla="7.1",
        sigla="INU", sigla_estesa="Inumazione", lingua="it",
    ))
    session.add(ThesaurusSigle(
        nome_tabella="tomba_table", tipologia_sigla="7.1",
        sigla="CRM", sigla_estesa="Cremazione", lingua="it",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("rito")
    assert {"value": "Inumazione", "code": "INU"} in values
    assert {"value": "Cremazione", "code": "CRM"} in values


def test_get_thesaurus_values_falls_back_to_seed_when_db_empty(svc):
    """A THESAURUS_MAP field with no rows in either pyarchinit_thesaurus_sigle
    or thesaurus_field must still return the in-memory THESAURUS_MAPPINGS seed."""
    values = svc.get_thesaurus_values("corredo_presenza")
    assert values == [{"value": v, "code": ""} for v in ["Sì", "No", "Parziale"]]


def test_get_thesaurus_values_truly_unknown_field_returns_empty(svc):
    assert svc.get_thesaurus_values("this_field_does_not_exist_anywhere") == []

def test_search_matches_text_fields(svc):
    svc.create_tomba({"sito": "Volterra", "rito": "inumazione", "sigla_struttura": "TB"})
    svc.create_tomba({"sito": "Cerveteri", "rito": "cremazione"})
    assert len(svc.list_tomba(search="inum")) == 1
    assert svc.count_tomba(search="inum") == 1
    assert svc.list_tomba(search="zzz") == []


def test_create_tomba_ignores_mass_assignment_of_managed_fields(svc):
    """A crafted POST injecting id_tomba/version_number/entity_uuid/sync_status
    must not be able to force those values — they are BaseModel-managed or
    the PK, and must be assigned by the DB/model defaults only."""
    tid = svc.create_tomba({
        "sito": "S",
        "id_tomba": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
    })
    assert tid is not None
    assert tid != 999
    row = svc.get_tomba(tid)
    assert row["id_tomba"] == tid
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"


def test_update_tomba_ignores_mass_assignment_of_managed_fields(svc):
    tid = svc.create_tomba({"sito": "S"})
    original = svc.get_tomba(tid)
    ok = svc.update_tomba(tid, {
        "id_tomba": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
        "sito": "Updated",
    })
    assert ok is True
    row = svc.get_tomba(tid)
    assert row["id_tomba"] == tid  # unchanged, not 999
    assert row["sito"] == "Updated"  # legitimate field still writable
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"
    assert row["entity_uuid"] == original["entity_uuid"]


def test_create_tomba_coerces_integer_string(svc):
    tid = svc.create_tomba({"sito": "S", "area": "5"})
    row = svc.get_tomba(tid)
    assert row["area"] == 5
    assert isinstance(row["area"], int)


def test_create_tomba_unparseable_integer_becomes_none(svc):
    tid = svc.create_tomba({"sito": "S", "area": "abc"})
    row = svc.get_tomba(tid)
    assert row["area"] is None


def test_update_tomba_coerces_integer_string(svc):
    tid = svc.create_tomba({"sito": "S"})
    assert svc.update_tomba(tid, {"area": "12"}) is True
    row = svc.get_tomba(tid)
    assert row["area"] == 12

    assert svc.update_tomba(tid, {"area": "xyz"}) is True
    row = svc.get_tomba(tid)
    assert row["area"] is None

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.fauna import Fauna  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle
from pyarchinit_mini.services.fauna_service import FaunaService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)

@pytest.fixture
def svc():
    e=create_engine("sqlite:///:memory:"); Base.metadata.create_all(e)
    return FaunaService(_DBM(e))

def test_crud(svc):
    fid = svc.create_fauna({"sito":"Volterra","specie":"Bos taurus","us":"12"})
    assert fid and svc.get_fauna(fid)["specie"]=="Bos taurus"
    assert svc.update_fauna(fid, {"specie":"Ovis aries"}) is True
    assert svc.get_fauna(fid)["specie"]=="Ovis aries"
    assert [r["id_fauna"] for r in svc.list_fauna()]==[fid]
    assert svc.count_fauna()==1
    assert svc.get_distinct_sites()==["Volterra"]
    assert svc.delete_fauna(fid) is True and svc.get_fauna(fid) is None

def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope")==[]


def test_get_thesaurus_values_reads_plugin_shared_pyarchinit_thesaurus_sigle(svc):
    """Mini's thesaurus combos must read the SAME pyarchinit_thesaurus_sigle
    source the classic plugin fills, so vocab is shared on the festos DB."""
    session = svc.db_manager.connection.get_session()
    session.add(ThesaurusSigle(
        nome_tabella="fauna_table", tipologia_sigla="13.11",
        sigla="BOSTAU", sigla_estesa="Bos taurus", lingua="it",
    ))
    session.add(ThesaurusSigle(
        nome_tabella="fauna_table", tipologia_sigla="13.11",
        sigla="OVIARI", sigla_estesa="Ovis aries", lingua="it",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("specie")
    assert {"value": "Bos taurus", "code": "BOSTAU"} in values
    assert {"value": "Ovis aries", "code": "OVIARI"} in values


def test_get_thesaurus_values_falls_back_to_seed_when_db_empty(svc):
    """A THESAURUS_MAP field with no rows in either pyarchinit_thesaurus_sigle
    or thesaurus_field must still return the in-memory THESAURUS_MAPPINGS seed."""
    values = svc.get_thesaurus_values("specie")
    from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
    expected = THESAURUS_MAPPINGS["fauna_table"]["specie"]
    assert values == [{"value": v, "code": ""} for v in expected]


def test_get_thesaurus_values_truly_unknown_field_returns_empty(svc):
    assert svc.get_thesaurus_values("this_field_does_not_exist_anywhere") == []

def test_search_matches_text_fields(svc):
    svc.create_fauna({"sito": "Volterra", "specie": "Bos taurus", "contesto": "strato"})
    svc.create_fauna({"sito": "Cerveteri", "specie": "Ovis aries"})
    assert len(svc.list_fauna(search="Bos")) == 1
    assert svc.count_fauna(search="Bos") == 1
    assert svc.list_fauna(search="zzz") == []


def test_create_fauna_ignores_mass_assignment_of_managed_fields(svc):
    """A crafted POST injecting id_fauna/version_number/entity_uuid/sync_status
    must not be able to force those values — they are BaseModel-managed or
    the PK, and must be assigned by the DB/model defaults only."""
    fid = svc.create_fauna({
        "sito": "S",
        "id_fauna": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
    })
    assert fid is not None
    assert fid != 999
    row = svc.get_fauna(fid)
    assert row["id_fauna"] == fid
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"


def test_update_fauna_ignores_mass_assignment_of_managed_fields(svc):
    fid = svc.create_fauna({"sito": "S"})
    original = svc.get_fauna(fid)
    ok = svc.update_fauna(fid, {
        "id_fauna": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
        "sito": "Updated",
    })
    assert ok is True
    row = svc.get_fauna(fid)
    assert row["id_fauna"] == fid  # unchanged, not 999
    assert row["sito"] == "Updated"  # legitimate field still writable
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"
    assert row["entity_uuid"] == original["entity_uuid"]


def test_create_fauna_coerces_integer_string(svc):
    fid = svc.create_fauna({"sito": "S", "numero_minimo_individui": "3"})
    row = svc.get_fauna(fid)
    assert row["numero_minimo_individui"] == 3
    assert isinstance(row["numero_minimo_individui"], int)


def test_create_fauna_coerces_boolean_string(svc):
    fid = svc.create_fauna({"sito": "S", "combustione_altri_materiali_us": "sì"})
    row = svc.get_fauna(fid)
    assert row["combustione_altri_materiali_us"] is True

    fid2 = svc.create_fauna({"sito": "S", "combustione_altri_materiali_us": "no"})
    row2 = svc.get_fauna(fid2)
    assert row2["combustione_altri_materiali_us"] is False


def test_create_fauna_coerces_date_string(svc):
    fid = svc.create_fauna({"sito": "S", "data_compilazione": "2024-05-01"})
    row = svc.get_fauna(fid)
    assert row["data_compilazione"] == datetime.date(2024, 5, 1)


def test_create_fauna_bad_date_becomes_none(svc):
    fid = svc.create_fauna({"sito": "S", "data_compilazione": "bad"})
    row = svc.get_fauna(fid)
    assert row["data_compilazione"] is None


def test_update_fauna_coerces_integer_string(svc):
    fid = svc.create_fauna({"sito": "S"})
    assert svc.update_fauna(fid, {"numero_minimo_individui": "5"}) is True
    row = svc.get_fauna(fid)
    assert row["numero_minimo_individui"] == 5

    assert svc.update_fauna(fid, {"numero_minimo_individui": "xyz"}) is True
    row = svc.get_fauna(fid)
    assert row["numero_minimo_individui"] is None


def test_create_fauna_retries_on_id_collision(svc, monkeypatch):
    """fauna_table is a plugin-shared table with a BigInteger id_fauna —
    SQLite has no native autoincrement for it, so FaunaService allocates
    ids explicitly via max(id)+1 (mirroring MediaService._next_id). A
    same-value collision from a concurrent writer must self-heal via retry
    rather than failing the whole create."""
    first = svc.create_fauna({"sito": "S"})
    assert first == 1
    real_next_id = svc._next_id
    calls = {"n": 0}

    def flaky_next_id(session):
        if calls["n"] == 0:
            calls["n"] += 1
            return 1  # collides with the existing row
        return real_next_id(session)

    monkeypatch.setattr(svc, "_next_id", flaky_next_id)
    second = svc.create_fauna({"sito": "S2"})
    assert calls["n"] == 1
    assert second == 2
    assert svc.count_fauna() == 2

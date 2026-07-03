import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.ut import Ut  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle
from pyarchinit_mini.services.ut_service import UtService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)

@pytest.fixture
def svc():
    e=create_engine("sqlite:///:memory:"); Base.metadata.create_all(e)
    return UtService(_DBM(e))

def test_crud(svc):
    uid = svc.create_ut({"progetto":"P1","def_ut":"muro","ut_letterale":"US1"})
    assert uid and svc.get_ut(uid)["def_ut"]=="muro"
    assert svc.update_ut(uid, {"def_ut":"crollo"}) is True
    assert svc.get_ut(uid)["def_ut"]=="crollo"
    assert [r["id_ut"] for r in svc.list_ut()]==[uid]
    assert svc.count_ut()==1
    assert svc.delete_ut(uid) is True and svc.get_ut(uid) is None


def test_get_distinct_projects(svc):
    svc.create_ut({"progetto":"P1","def_ut":"muro"})
    assert svc.get_distinct_projects()==["P1"]


def test_list_ut_filters_by_progetto(svc):
    svc.create_ut({"progetto":"P1","def_ut":"muro"})
    svc.create_ut({"progetto":"P2","def_ut":"crollo"})
    assert len(svc.list_ut(progetto="P1")) == 1
    assert svc.list_ut(progetto="P1")[0]["progetto"] == "P1"
    assert len(svc.list_ut()) == 2


def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope")==[]


def test_get_thesaurus_values_reads_plugin_shared_pyarchinit_thesaurus_sigle(svc):
    """Mini's thesaurus combos must read the SAME pyarchinit_thesaurus_sigle
    source the classic plugin fills, so vocab is shared on the festos DB."""
    session = svc.db_manager.connection.get_session()
    session.add(ThesaurusSigle(
        nome_tabella="ut_table", tipologia_sigla="12.1",
        sigla="SIST", sigla_estesa="Sistematica", lingua="it",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("survey_type")
    assert {"value": "Sistematica", "code": "SIST"} in values


def test_get_thesaurus_values_falls_back_to_seed_when_db_empty(svc):
    """A THESAURUS_MAP field with no rows in either pyarchinit_thesaurus_sigle
    or thesaurus_field must still return the in-memory THESAURUS_MAPPINGS seed."""
    from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
    values = svc.get_thesaurus_values("def_ut")
    expected = THESAURUS_MAPPINGS["ut_table"]["def_ut"]
    assert values == [{"value": v, "code": ""} for v in expected]


def test_get_thesaurus_values_truly_unknown_field_returns_empty(svc):
    assert svc.get_thesaurus_values("this_field_does_not_exist_anywhere") == []


def test_search_matches_text_fields(svc):
    svc.create_ut({"progetto": "P1", "def_ut": "muratura", "localita": "Volterra"})
    svc.create_ut({"progetto": "P2", "def_ut": "crollo", "localita": "Cerveteri"})
    assert len(svc.list_ut(search="mura")) == 1
    assert svc.count_ut(search="mura") == 1
    assert len(svc.list_ut(search="Volterra")) == 1
    assert svc.list_ut(search="zzz") == []


def test_create_ut_ignores_mass_assignment_of_managed_fields(svc):
    """A crafted POST injecting id_ut/version_number/entity_uuid/sync_status
    must not be able to force those values — they are BaseModel-managed or
    the PK, and must be assigned by the DB/model defaults only."""
    uid = svc.create_ut({
        "progetto": "P",
        "id_ut": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
    })
    assert uid is not None
    assert uid != 999
    row = svc.get_ut(uid)
    assert row["id_ut"] == uid
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"


def test_update_ut_ignores_mass_assignment_of_managed_fields(svc):
    uid = svc.create_ut({"progetto": "P"})
    original = svc.get_ut(uid)
    ok = svc.update_ut(uid, {
        "id_ut": 999,
        "version_number": 42,
        "entity_uuid": "x",
        "sync_status": "hacked",
        "progetto": "Updated",
    })
    assert ok is True
    row = svc.get_ut(uid)
    assert row["id_ut"] == uid  # unchanged, not 999
    assert row["progetto"] == "Updated"  # legitimate field still writable
    assert row["version_number"] != 42
    assert row["entity_uuid"] != "x"
    assert row["sync_status"] != "hacked"
    assert row["entity_uuid"] == original["entity_uuid"]


def test_create_ut_coerces_integer_float_and_numeric_strings(svc):
    uid = svc.create_ut({"progetto": "P", "nr_ut": "5", "quota": "1.5", "potential_score": "3.25"})
    row = svc.get_ut(uid)
    assert row["nr_ut"] == 5
    assert isinstance(row["nr_ut"], int)
    assert row["quota"] == 1.5
    assert isinstance(row["quota"], float)
    # potential_score is a Numeric(5,2, asdecimal=False) column: both the
    # write-side coerce_types() and the column's own asdecimal=False keep
    # the round-tripped value a Python float, not a Decimal (see
    # test_potential_score_and_risk_score_round_trip_as_float below).
    assert row["potential_score"] == 3.25


def test_create_ut_unparseable_numeric_becomes_none(svc):
    uid = svc.create_ut({"progetto": "P", "potential_score": "bad"})
    row = svc.get_ut(uid)
    assert row["potential_score"] is None


def test_update_ut_coerces_integer_string(svc):
    uid = svc.create_ut({"progetto": "P"})
    assert svc.update_ut(uid, {"nr_ut": "12"}) is True
    row = svc.get_ut(uid)
    assert row["nr_ut"] == 12

    assert svc.update_ut(uid, {"nr_ut": "xyz"}) is True
    row = svc.get_ut(uid)
    assert row["nr_ut"] is None


def test_update_ut_coerces_numeric_string(svc):
    uid = svc.create_ut({"progetto": "P"})
    assert svc.update_ut(uid, {"potential_score": "4.75"}) is True
    row = svc.get_ut(uid)
    assert row["potential_score"] == 4.75

    assert svc.update_ut(uid, {"potential_score": "notanumber"}) is True
    row = svc.get_ut(uid)
    assert row["potential_score"] is None


def test_potential_score_and_risk_score_round_trip_as_float(svc):
    """potential_score/risk_score are Numeric(5,2, asdecimal=False) columns:
    a JSON endpoint returning a ut record must not choke on a
    non-JSON-serializable Decimal, so a read-back must come back as float,
    not Decimal."""
    from decimal import Decimal

    uid = svc.create_ut({"progetto": "P", "potential_score": "3.25", "risk_score": "1.50"})
    row = svc.get_ut(uid)

    assert row["potential_score"] == 3.25
    assert isinstance(row["potential_score"], float)
    assert not isinstance(row["potential_score"], Decimal)

    assert row["risk_score"] == 1.50
    assert isinstance(row["risk_score"], float)
    assert not isinstance(row["risk_score"], Decimal)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.ut import Ut  # noqa
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
    # potential_score is a Numeric(5,2) column: coerce_types() produces a
    # Python float (see tests/services/test_coercion.py), but SQLAlchemy's
    # Numeric type defaults to asdecimal=True on SELECT, so the round-tripped
    # value comes back as Decimal('3.25') — equal to 3.25, not `is` a float.
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

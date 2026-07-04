import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle, ThesaurusField
from pyarchinit_mini.services.tomba_service import TombaService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)


class _PoisonableSessionWrapper:
    """Wraps a real Session and simulates PostgreSQL's aborted-transaction
    behavior: once `execute` raises, any further `execute` raises too until
    `rollback()` is called. Used to prove get_thesaurus_values() rolls back
    after the sigle query fails, so the thesaurus_field fallback still runs."""
    def __init__(self, real_session):
        self._real = real_session
        self.poisoned = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._real.close()
        return False

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if 'pyarchinit_thesaurus_sigle' in sql:
            self.poisoned = True
            raise RuntimeError("simulated failure: sigle table unavailable")
        if self.poisoned:
            raise RuntimeError("simulated InFailedSqlTransaction: current transaction is aborted")
        return self._real.execute(stmt, params) if params is not None else self._real.execute(stmt)

    def rollback(self):
        self.poisoned = False
        self._real.rollback()

    def __getattr__(self, name):
        return getattr(self._real, name)


class _PoisonConn:
    def __init__(s, e): s._S = sessionmaker(bind=e)
    def get_session(s): return _PoisonableSessionWrapper(s._S())
class _PoisonDBM:
    def __init__(s, e): s.connection = _PoisonConn(e)

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
        sigla="INU", sigla_estesa="Inumazione", lingua="IT",
    ))
    session.add(ThesaurusSigle(
        nome_tabella="tomba_table", tipologia_sigla="7.1",
        sigla="CRM", sigla_estesa="Cremazione", lingua="IT",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("rito")
    assert {"value": "Inumazione", "code": "INU"} in values
    assert {"value": "Cremazione", "code": "CRM"} in values


def test_get_thesaurus_values_filters_by_ui_language_dedupes_and_falls_back_to_it(svc):
    """Shared production DB carries 7 languages for the same sigla (911 IT
    rows + 34 each of en_US/fr_FR/de_DE/es_ES/ca_ES/ar_LB) — the dropdown
    must show only the UI's language, deduped, and fall back to the Italian
    catalog (not an empty or mixed-language list) when the UI language has
    no rows of its own."""
    session = svc.db_manager.connection.get_session()
    session.add_all([
        ThesaurusSigle(nome_tabella="tomba_table", tipologia_sigla="7.1",
                       sigla="INU1", sigla_estesa="Inumazione", lingua="IT"),
        ThesaurusSigle(nome_tabella="tomba_table", tipologia_sigla="7.1",
                       sigla="INU2", sigla_estesa="Inumazione", lingua="IT"),
        ThesaurusSigle(nome_tabella="tomba_table", tipologia_sigla="7.1",
                       sigla="BURIAL", sigla_estesa="Burial", lingua="en_US"),
        ThesaurusSigle(nome_tabella="tomba_table", tipologia_sigla="7.1",
                       sigla="INHUM", sigla_estesa="Inhumation", lingua="fr_FR"),
    ])
    session.commit()
    session.close()

    it_values = [v["value"] for v in svc.get_thesaurus_values("rito", lang="it")]
    assert it_values == ["Inumazione"]

    en_values = [v["value"] for v in svc.get_thesaurus_values("rito", lang="en")]
    assert en_values == ["Burial"]

    # No 'de' rows exist at all -> falls back to the Italian catalog.
    de_values = [v["value"] for v in svc.get_thesaurus_values("rito", lang="de")]
    assert de_values == ["Inumazione"]


def test_get_thesaurus_values_falls_back_to_seed_when_db_empty(svc):
    """A THESAURUS_MAP field with no rows in either pyarchinit_thesaurus_sigle
    or thesaurus_field must still return the in-memory THESAURUS_MAPPINGS seed."""
    values = svc.get_thesaurus_values("corredo_presenza")
    assert values == [{"value": v, "code": ""} for v in ["Sì", "No", "Parziale"]]


def test_get_thesaurus_values_truly_unknown_field_returns_empty(svc):
    assert svc.get_thesaurus_values("this_field_does_not_exist_anywhere") == []


def test_get_thesaurus_values_rolls_back_after_sigle_failure_pg_simulation():
    """On PostgreSQL, a failed pyarchinit_thesaurus_sigle query aborts the
    transaction; without a rollback() the thesaurus_field fallback query
    would then also fail (InFailedSqlTransaction), silently losing the
    fallback layer. SQLite doesn't reproduce that aborted-transaction
    behavior naturally, so this test simulates it via a session wrapper
    and asserts get_thesaurus_values() still returns the fallback values."""
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    svc = TombaService(_PoisonDBM(e))

    session = sessionmaker(bind=e)()
    session.add(ThesaurusField(
        table_name="tomba_table", field_name="rito",
        value="Inumazione", label="INU",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("rito")
    assert {"value": "Inumazione", "code": "INU"} in values

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

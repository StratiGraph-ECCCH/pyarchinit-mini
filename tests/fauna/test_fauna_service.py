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
        sigla="BOSTAU", sigla_estesa="Bos taurus", lingua="IT",
    ))
    session.add(ThesaurusSigle(
        nome_tabella="fauna_table", tipologia_sigla="13.11",
        sigla="OVIARI", sigla_estesa="Ovis aries", lingua="IT",
    ))
    session.commit()
    session.close()

    values = svc.get_thesaurus_values("specie")
    assert {"value": "Bos taurus", "code": "BOSTAU"} in values
    assert {"value": "Ovis aries", "code": "OVIARI"} in values


def test_get_thesaurus_values_filters_by_ui_language_dedupes_and_falls_back_to_it(svc):
    """Shared production DB carries 7 languages for the same sigla (911 IT
    rows + 34 each of en_US/fr_FR/de_DE/es_ES/ca_ES/ar_LB) — the dropdown
    must show only the UI's language, deduped, and fall back to the Italian
    catalog (not an empty or mixed-language list) when the UI language has
    no rows of its own."""
    session = svc.db_manager.connection.get_session()
    session.add_all([
        ThesaurusSigle(nome_tabella="fauna_table", tipologia_sigla="13.11",
                       sigla="BOV1", sigla_estesa="Bovino", lingua="IT"),
        ThesaurusSigle(nome_tabella="fauna_table", tipologia_sigla="13.11",
                       sigla="BOV2", sigla_estesa="Bovino", lingua="IT"),
        ThesaurusSigle(nome_tabella="fauna_table", tipologia_sigla="13.11",
                       sigla="CATTLE", sigla_estesa="Cattle", lingua="en_US"),
        ThesaurusSigle(nome_tabella="fauna_table", tipologia_sigla="13.11",
                       sigla="BOVIN", sigla_estesa="Bovin", lingua="fr_FR"),
    ])
    session.commit()
    session.close()

    it_values = [v["value"] for v in svc.get_thesaurus_values("specie", lang="it")]
    assert it_values == ["Bovino"]

    en_values = [v["value"] for v in svc.get_thesaurus_values("specie", lang="en")]
    assert en_values == ["Cattle"]

    # No 'de' rows exist at all -> falls back to the Italian catalog.
    de_values = [v["value"] for v in svc.get_thesaurus_values("specie", lang="de")]
    assert de_values == ["Bovino"]


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
    # species now live in specie_psi JSON (flat specie column is deprecated/empty),
    # so search targets specie_psi.
    svc.create_fauna({"sito": "Volterra", "specie_psi": '[["Bos taurus", "femore"]]', "contesto": "strato"})
    svc.create_fauna({"sito": "Cerveteri", "specie_psi": '[["Ovis aries", "omero"]]'})
    assert len(svc.list_fauna(search="Bos")) == 1
    assert svc.count_fauna(search="Bos") == 1
    assert svc.list_fauna(search="zzz") == []


def test_list_fauna_derives_specie_display_from_specie_psi(svc):
    svc.create_fauna({"sito": "S", "specie_psi": '[["Bos taurus", "femore"], ["Bos taurus", "tibia"], ["Ovis aries", "omero"]]'})
    row = svc.list_fauna()[0]
    # deduped, in order, joined — derived from the JSON, not the deprecated flat column
    assert row["specie_display"] == "Bos taurus, Ovis aries"
    svc.create_fauna({"sito": "S2"})  # no specie_psi
    assert svc.list_fauna(sito="S2")[0]["specie_display"] == ""


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


# --------------------------------------------------------------------------
# specie_psi / misure_ossa JSON normalization (plugin-compatible format)
# --------------------------------------------------------------------------

def test_create_fauna_normalizes_specie_psi_to_plugin_json(svc):
    """specie_psi must round-trip as a list of [specie, psi] string pairs —
    the SAME shape the classic pyarchinit_fauna plugin writes."""
    import json
    fid = svc.create_fauna({
        "sito": "S",
        "specie_psi": '[["Bos taurus","femore"],["Ovis aries","omero"]]',
    })
    row = svc.get_fauna(fid)
    assert json.loads(row["specie_psi"]) == [["Bos taurus", "femore"], ["Ovis aries", "omero"]]


def test_create_fauna_normalizes_misure_ossa_to_plugin_json(svc):
    """misure_ossa must round-trip as a list of 6-element string lists
    (elemento, specie, GL, GB, Bp, Bd) — blank measures stay '' not 0."""
    import json
    fid = svc.create_fauna({
        "sito": "S",
        "misure_ossa": '[["femore","Bos taurus","120","","45",""]]',
    })
    row = svc.get_fauna(fid)
    assert json.loads(row["misure_ossa"]) == [["femore", "Bos taurus", "120", "", "45", ""]]


def test_create_fauna_malformed_specie_psi_becomes_empty_list(svc):
    fid = svc.create_fauna({"sito": "S", "specie_psi": "not-json{{{"})
    row = svc.get_fauna(fid)
    assert row["specie_psi"] == "[]"


def test_create_fauna_malformed_misure_ossa_becomes_empty_list(svc):
    fid = svc.create_fauna({"sito": "S", "misure_ossa": "{broken"})
    row = svc.get_fauna(fid)
    assert row["misure_ossa"] == "[]"


def test_create_fauna_specie_psi_non_list_json_becomes_empty_list(svc):
    """A JSON value that parses but isn't a list (e.g. a bare object) must
    still normalize to '[]' — the plugin format is always a list."""
    fid = svc.create_fauna({"sito": "S", "specie_psi": '{"not":"a list"}'})
    row = svc.get_fauna(fid)
    assert row["specie_psi"] == "[]"


def test_update_fauna_normalizes_specie_psi_to_plugin_json(svc):
    import json
    fid = svc.create_fauna({"sito": "S"})
    assert svc.update_fauna(fid, {
        "specie_psi": '[["Sus scrofa","mandibola"]]',
    }) is True
    row = svc.get_fauna(fid)
    assert json.loads(row["specie_psi"]) == [["Sus scrofa", "mandibola"]]


def test_update_fauna_malformed_misure_ossa_becomes_empty_list(svc):
    fid = svc.create_fauna({"sito": "S"})
    assert svc.update_fauna(fid, {"misure_ossa": "nope"}) is True
    row = svc.get_fauna(fid)
    assert row["misure_ossa"] == "[]"


def test_get_thesaurus_values_elemento_anatomico_uses_13_13_map(svc):
    """elemento_anatomico has no fauna_table column of its own — it's used
    only by the misure_ossa widget's per-cell datalist — but THESAURUS_MAP
    must still resolve it to sigla 13.13 and return a (possibly empty) list
    without crashing on a DB with no matching thesaurus rows."""
    assert svc.THESAURUS_MAP["elemento_anatomico"] == "13.13"
    values = svc.get_thesaurus_values("elemento_anatomico")
    assert isinstance(values, list)

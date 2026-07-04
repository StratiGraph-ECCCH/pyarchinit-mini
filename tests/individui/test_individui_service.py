import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.individui import Individui  # noqa
from pyarchinit_mini.models.thesaurus import ThesaurusSigle
from pyarchinit_mini.services.individui_service import IndividuiService


class _Conn:
    def __init__(s, e): s._S = sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s, e): s.connection = _Conn(e)


@pytest.fixture
def svc():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return IndividuiService(_DBM(e))


def test_crud(svc):
    iid = svc.create_individui({"sito": "Volterra", "sesso": "F", "nr_individuo": 1})
    assert iid and svc.get_individui(iid)["sesso"] == "F"
    assert svc.update_individui(iid, {"sesso": "M"}) is True
    assert svc.get_individui(iid)["sesso"] == "M"
    assert [r["id_scheda_ind"] for r in svc.list_individui()] == [iid]
    assert svc.count_individui() == 1
    assert svc.get_distinct_sites() == ["Volterra"]
    assert svc.delete_individui(iid) is True and svc.get_individui(iid) is None


def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope") == []


def test_get_thesaurus_values_filters_by_ui_language_dedupes_and_falls_back_to_it(svc):
    """Shared production DB carries multiple languages for the same sigla —
    the dropdown must show only the UI's language, deduped, and fall back
    to the Italian catalog (not an empty or mixed-language list) when the
    UI language has no rows of its own."""
    session = svc.db_manager.connection.get_session()
    session.add_all([
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="8.1",
                       sigla="SUP1", sigla_estesa="Supino", lingua="IT"),
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="8.1",
                       sigla="SUP2", sigla_estesa="Supino", lingua="IT"),
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="8.1",
                       sigla="SUPINE", sigla_estesa="Supine", lingua="en_US"),
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="8.1",
                       sigla="SUPIN", sigla_estesa="Supin", lingua="fr_FR"),
    ])
    session.commit()
    session.close()

    it_values = [v["value"] for v in svc.get_thesaurus_values("posizione_cranio", lang="it")]
    assert it_values == ["Supino"]

    en_values = [v["value"] for v in svc.get_thesaurus_values("posizione_cranio", lang="en")]
    assert en_values == ["Supine"]

    # No 'de' rows exist at all -> falls back to the Italian catalog.
    de_values = [v["value"] for v in svc.get_thesaurus_values("posizione_cranio", lang="de")]
    assert de_values == ["Supino"]


def test_get_thesaurus_values_uses_sigla_not_estesa_for_yes_no_fields(svc):
    """completo_si_no/disturbato_si_no/in_connessione_si_no store the SHORT
    sigla code as their value (mirroring the classic plugin's storage of
    these three yes/no fields), NOT the extended form used by every other
    thesaurus-backed field."""
    session = svc.db_manager.connection.get_session()
    session.add_all([
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="801.801",
                       sigla="SI", sigla_estesa="Sì, presente", lingua="IT"),
        ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="801.801",
                       sigla="NO", sigla_estesa="No, assente", lingua="IT"),
    ])
    session.commit()
    session.close()

    values = [v["value"] for v in svc.get_thesaurus_values("completo_si_no", lang="it")]
    assert sorted(values) == ["NO", "SI"]
    assert "Sì, presente" not in values
    assert "No, assente" not in values

    # A non-yes/no 8.x-mapped field still returns the extended form.
    session = svc.db_manager.connection.get_session()
    session.add(ThesaurusSigle(nome_tabella="individui_table", tipologia_sigla="8.1",
                                sigla="SUP", sigla_estesa="Supino", lingua="IT"))
    session.commit()
    session.close()
    cranio_values = [v["value"] for v in svc.get_thesaurus_values("posizione_cranio", lang="it")]
    assert cranio_values == ["Supino"]


def test_search_matches_text_fields(svc):
    svc.create_individui({"sito": "Volterra", "sesso": "F", "schedatore": "Rossi"})
    svc.create_individui({"sito": "Cerveteri", "sesso": "M"})
    assert len(svc.list_individui(search="Rossi")) == 1
    assert svc.count_individui(search="Rossi") == 1
    assert svc.list_individui(search="zzz") == []


def test_create_individui_ignores_mass_assignment_of_managed_fields(svc):
    """A crafted POST injecting id_scheda_ind/version_number must not be
    able to force those values — they are BaseModel-managed or the PK, and
    must be assigned by the DB/model defaults only."""
    iid = svc.create_individui({
        "sito": "S",
        "id_scheda_ind": 999,
        "version_number": 42,
    })
    assert iid is not None
    assert iid != 999
    row = svc.get_individui(iid)
    assert row["id_scheda_ind"] == iid
    assert row["version_number"] != 42


def test_update_individui_ignores_mass_assignment_of_managed_fields(svc):
    iid = svc.create_individui({"sito": "S"})
    ok = svc.update_individui(iid, {
        "id_scheda_ind": 999,
        "version_number": 42,
        "sito": "Updated",
    })
    assert ok is True
    row = svc.get_individui(iid)
    assert row["id_scheda_ind"] == iid  # unchanged, not 999
    assert row["sito"] == "Updated"  # legitimate field still writable
    assert row["version_number"] != 42


def test_create_individui_coerces_integer_string(svc):
    iid = svc.create_individui({"sito": "S", "nr_individuo": "7"})
    row = svc.get_individui(iid)
    assert row["nr_individuo"] == 7
    assert isinstance(row["nr_individuo"], int)


def test_create_individui_coerces_float_string(svc):
    iid = svc.create_individui({"sito": "S", "lunghezza_scheletro": "165.5"})
    row = svc.get_individui(iid)
    assert row["lunghezza_scheletro"] == 165.5
    assert isinstance(row["lunghezza_scheletro"], float)

    iid2 = svc.create_individui({"sito": "S", "lunghezza_scheletro": "abc"})
    row2 = svc.get_individui(iid2)
    assert row2["lunghezza_scheletro"] is None


def test_get_nr_individui(svc):
    svc.create_individui({"sito": "S", "sigla_struttura": "TB", "nr_struttura": 1, "nr_individuo": 1})
    svc.create_individui({"sito": "S", "sigla_struttura": "TB", "nr_struttura": 1, "nr_individuo": 3})
    svc.create_individui({"sito": "S", "sigla_struttura": "XX", "nr_struttura": 2, "nr_individuo": 9})
    svc.create_individui({"sito": "T", "sigla_struttura": "TB", "nr_struttura": 1, "nr_individuo": 5})

    assert svc.get_nr_individui("S", "TB", 1) == [1, 3]
    assert svc.get_nr_individui("S") == [1, 3, 9]
    # Unparseable nr_struttura is ignored rather than raising or filtering
    # everything out.
    assert svc.get_nr_individui("S", "TB", "not-a-number") == [1, 3]
    assert svc.get_nr_individui("") == []

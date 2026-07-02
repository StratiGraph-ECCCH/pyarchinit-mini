import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba  # noqa
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

def test_search_matches_text_fields(svc):
    svc.create_tomba({"sito": "Volterra", "rito": "inumazione", "sigla_struttura": "TB"})
    svc.create_tomba({"sito": "Cerveteri", "rito": "cremazione"})
    assert len(svc.list_tomba(search="inum")) == 1
    assert svc.count_tomba(search="inum") == 1
    assert svc.list_tomba(search="zzz") == []

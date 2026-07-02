import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.services.storage_config_service import StorageConfigService

class _Conn:
    def __init__(s, e): s._S = sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s, e): s.connection = _Conn(e)

@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", Fernet.generate_key().decode())
    eng = create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    return StorageConfigService(_DBM(eng))

def test_save_then_get_roundtrips_and_encrypts(svc):
    svc.save("s3://bucket/media", "s3://bucket/thumb", "s3://bucket/resize",
             {"s3": {"access_key": "AK", "secret_key": "SK"}})
    got = svc.get()
    assert got["media_root"] == "s3://bucket/media"
    assert got["credentials"]["s3"]["access_key"] == "AK"
    # stored form is encrypted
    with svc.db_manager.connection.get_session() as s:
        from pyarchinit_mini.models.storage_config import StorageConfig
        row = s.get(StorageConfig, 1)
        assert "AK" not in (row.credentials_encrypted or "")

def test_build_manager_feeds_credentials(svc):
    svc.save("s3://b/m", "s3://b/t", "s3://b/r", {"s3": {"access_key": "AK", "secret_key": "SK"}})
    mgr = svc.build_manager()
    from pyarchinit_mini.storage.base_backend import StorageType
    assert mgr.credentials_manager.get_credentials(StorageType.S3).get("access_key") == "AK"

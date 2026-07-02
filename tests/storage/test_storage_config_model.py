# tests/storage/test_storage_config_model.py
from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.storage_config import StorageConfig

def test_table_shape():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("storage_config")}
    assert {"id","media_root","thumb_path","thumb_resize","credentials_encrypted","updated_at"} <= cols

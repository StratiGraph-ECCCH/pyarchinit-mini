from pyarchinit_mini.storage.credentials import CredentialsManager
from pyarchinit_mini.storage.base_backend import StorageType


def test_set_and_get(monkeypatch):
    monkeypatch.delenv("PYARCHINIT_S3_ACCESS_KEY", raising=False)
    cm = CredentialsManager()
    cm.set_credentials(StorageType.S3, {"access_key": "AK", "secret_key": "SK"})
    assert cm.get_credentials(StorageType.S3)["access_key"] == "AK"


def test_env_fallback(monkeypatch):
    monkeypatch.setenv("PYARCHINIT_S3_ACCESS_KEY", "ENVAK")
    cm = CredentialsManager()
    assert cm.get_credentials(StorageType.S3).get("access_key") == "ENVAK"


def test_no_qgis_import():
    import pyarchinit_mini.storage.credentials as m
    src = open(m.__file__).read()
    assert "QgsSettings" not in src and "from qgis" not in src

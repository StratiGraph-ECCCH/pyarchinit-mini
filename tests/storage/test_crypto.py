import pytest
from pyarchinit_mini.storage import crypto

def test_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", Fernet.generate_key().decode())
    tok = crypto.encrypt_dict({"password": "s3cr3t", "user": "u"})
    assert isinstance(tok, str) and "s3cr3t" not in tok
    assert crypto.decrypt_dict(tok) == {"password": "s3cr3t", "user": "u"}

def test_no_key(monkeypatch):
    monkeypatch.delenv("PYARCHINIT_SECRET_KEY", raising=False)
    assert crypto.has_key() is False
    with pytest.raises(RuntimeError):
        crypto.encrypt_dict({"a": 1})

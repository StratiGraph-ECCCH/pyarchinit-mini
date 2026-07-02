"""Symmetric encryption for storage credentials at rest (Fernet)."""
import os
import json
from cryptography.fernet import Fernet

def has_key() -> bool:
    return bool(os.environ.get("PYARCHINIT_SECRET_KEY"))

def get_fernet():
    key = os.environ.get("PYARCHINIT_SECRET_KEY")
    return Fernet(key.encode()) if key else None

def encrypt_dict(d: dict) -> str:
    f = get_fernet()
    if f is None:
        raise RuntimeError("PYARCHINIT_SECRET_KEY not set; cannot encrypt credentials")
    return f.encrypt(json.dumps(d).encode()).decode()

def decrypt_dict(token: str) -> dict:
    f = get_fernet()
    if f is None:
        raise RuntimeError("PYARCHINIT_SECRET_KEY not set; cannot decrypt credentials")
    return json.loads(f.decrypt(token.encode()).decode())

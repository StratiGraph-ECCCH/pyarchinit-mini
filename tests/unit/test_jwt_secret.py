"""The JWT signing key: refused when absent, and refused AT USE.

`utils/auth.py` used to declare

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", <a literal>)

which reads as careful code — it consults the environment — and is the same
defect as a key written in the source, because the fallback is what almost
everybody gets.

THE ONE CONSTRAINT THAT SHAPES THIS, and the first test is about nothing else:
this module is imported by the WEB APPLICATION. `services/user_service.py:9`
and `web_interface/oidc_routes.py:612` take `hash_password` / `verify_password`
from it, so it executes on every Flask boot — verified in the running container,
where `pyarchinit_mini.utils.auth` is in `sys.modules` after `create_app()`.

So a refusal at import would stop the application everybody uses in order to
repair a path nobody uses. The refusal belongs where a token is signed.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys

import pytest

from pyarchinit_mini.utils import auth

LONG = "k" * 64
VARIABLE = auth.JWT_KEY_VARIABLE


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    """Nothing configured, unless a test says otherwise."""
    monkeypatch.delenv(VARIABLE, raising=False)


# ── 1 · the constraint ───────────────────────────────────────────────────────

def test_importing_this_module_without_a_key_is_harmless():
    """The web application must keep starting.

    Run in a SEPARATE interpreter with the variable removed, because this one
    has already imported the module and a fresh import is the thing being
    measured. `-c` rather than a reload: `importlib.reload` would not catch a
    failure that happens at first import only.
    """
    environment = dict(os.environ)
    environment.pop(VARIABLE, None)
    finished = subprocess.run(
        [sys.executable, "-c",
         "import pyarchinit_mini.utils.auth as a; "
         "print('imported', a.ALGORITHM)"],
        capture_output=True, text=True, env=environment)
    assert finished.returncode == 0, (
        f"importing utils.auth without {VARIABLE} failed, which would stop the "
        f"web application from starting:\n{finished.stderr}")
    assert "imported HS256" in finished.stdout


def test_the_functions_the_web_application_actually_uses_still_work():
    """`hash_password` and `verify_password` are why this module is imported.

    They have nothing to do with JWTs, and a JWT refusal must not touch them.
    """
    hashed = auth.hash_password("una password qualunque")
    assert auth.verify_password("una password qualunque", hashed) is True
    assert auth.verify_password("un'altra", hashed) is False


# ── 2 · the refusal, where a token is signed ─────────────────────────────────

def test_signing_a_token_without_a_key_refuses_and_names_the_variable():
    with pytest.raises(auth.JWTKeyMissing) as refusal:
        auth.create_access_token({"sub": "chiunque"})
    said = str(refusal.value)
    assert VARIABLE in said
    assert "secrets.token_urlsafe" in said, (
        "a refusal that does not say how to fix it makes somebody search")
    assert "starts without it" in said, (
        "the sentence should also say that the WEB interface does not need "
        "this variable — otherwise somebody sets it in a panic")


def test_reading_a_token_without_a_key_refuses_rather_than_returning_None():
    """`decode_access_token` returns None for an INVALID token.

    «No key is configured» is not an invalid token, it is an unconfigured
    server, and collapsing the two would report a configuration mistake as a
    failed login. `JWTKeyMissing` is a `RuntimeError` and not a `JWTError`, so
    it travels through that `except` clause untouched — asserted here because
    that is a property of the exception hierarchy and somebody could change it.
    """
    with pytest.raises(auth.JWTKeyMissing):
        auth.decode_access_token("qualunque.cosa.qui")

    from jose import JWTError
    assert not issubclass(auth.JWTKeyMissing, JWTError)


def test_an_empty_variable_is_refused_not_ignored(monkeypatch):
    monkeypatch.setenv(VARIABLE, "   ")
    with pytest.raises(auth.JWTKeyMissing) as refusal:
        auth.jwt_secret()
    assert VARIABLE in str(refusal.value)


def test_a_short_key_is_refused(monkeypatch):
    monkeypatch.setenv(VARIABLE, "k" * (auth.MINIMUM_KEY_LENGTH - 1))
    with pytest.raises(auth.JWTKeyMissing) as refusal:
        auth.jwt_secret()
    assert str(auth.MINIMUM_KEY_LENGTH) in str(refusal.value)

    monkeypatch.setenv(VARIABLE, "k" * auth.MINIMUM_KEY_LENGTH)
    assert auth.jwt_secret() == "k" * auth.MINIMUM_KEY_LENGTH


# ── 3 · and with a key, the path works ───────────────────────────────────────

def test_a_token_round_trips_when_the_variable_is_set(monkeypatch):
    monkeypatch.setenv(VARIABLE, LONG)
    token = auth.create_access_token({"sub": "0000-0002-1825-0097"})
    assert token and token.count(".") == 2

    claims = auth.decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == "0000-0002-1825-0097"
    assert "exp" in claims


def test_a_token_signed_with_one_key_does_not_verify_under_another(monkeypatch):
    """The property the whole patch is about.

    With the old literal, every installation shared a key and therefore every
    installation accepted every other's tokens. Two different keys must not.
    """
    monkeypatch.setenv(VARIABLE, LONG)
    token = auth.create_access_token({"sub": "qualcuno"})

    monkeypatch.setenv(VARIABLE, "z" * 64)
    assert auth.decode_access_token(token) is None, (
        "a token signed with a different key verified: the key is not being "
        "read where the token is read")


# ── 4 · the name that used to hold the key ───────────────────────────────────

def test_the_old_module_attribute_answers_with_the_refusal():
    """`auth.SECRET_KEY` is gone, and reaching for it says why.

    PEP 562. Kept answerable rather than simply deleted because anybody
    reaching for that name is asking for the signing key, and the honest answer
    is the refusal rather than `AttributeError: SECRET_KEY`.
    """
    with pytest.raises(auth.JWTKeyMissing) as refusal:
        auth.SECRET_KEY
    assert "jwt_secret()" in str(refusal.value)
    assert VARIABLE in str(refusal.value)


def test_importing_the_old_name_also_refuses():
    """`from pyarchinit_mini.utils.auth import SECRET_KEY`.

    Which is what a caller elsewhere would have written. Measured before it was
    removed: nobody did, and no test exercised the JWT path — but the fork is
    somebody else's living project, so the name answers instead of vanishing.
    """
    with pytest.raises(auth.JWTKeyMissing):
        importlib.import_module("pyarchinit_mini.utils.auth").SECRET_KEY

    # …and a name that never existed still behaves like a normal absence
    with pytest.raises(AttributeError):
        auth.una_cosa_che_non_esiste


def test_no_literal_remains_as_a_fallback_in_this_module():
    """Read off the code, comments and docstrings stripped.

    The narrow claim of this patch, so that a future `os.getenv(NAME, "…")`
    here fails locally as well as through the package-wide detector in
    `test_session_key.py`.
    """
    import pathlib
    import re
    import tokenize

    kept, previous = [], tokenize.INDENT
    with open(auth.__file__) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type == tokenize.COMMENT:
                continue
            if token.type == tokenize.STRING and previous in (
                    tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT):
                continue
            kept.append(token.string)
            previous = token.type
    code = " ".join(kept)

    # `os.getenv(X)` with ONE argument is fine; with a second it is a default,
    # and a default for a signing key is the defect.
    defaults = re.findall(r"getenv \( \w+ , ", code) + \
        re.findall(r"""getenv \( ['"][^'"]*['"] , """, code)
    assert not defaults, (
        f"a fallback was reintroduced for an environment read in "
        f"{pathlib.Path(auth.__file__).name}: {defaults}")

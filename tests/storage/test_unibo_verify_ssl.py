"""Regression test: the `verify_ssl` storage credential (and the
`/settings/storage` checkbox backed by it) must actually control the SSL
context used for Unibo File Manager requests.

Previously, `unibo_filemanager_backend.py` hard-coded a module-level
`SSL_CONTEXT` with `verify_mode = ssl.CERT_NONE`, so the credential was a
no-op. The DEFAULT must stay unverified (the Unibo server uses a
self-signed certificate — verifying by default would break existing
deployments); only an explicit `verify_ssl` opt-in should enable
verification.
"""
import ssl

from pyarchinit_mini.storage.backends.unibo_filemanager_backend import (
    UniboFileManagerBackend,
)


def test_verify_ssl_true_enables_certificate_verification():
    backend = UniboFileManagerBackend("proj", {"verify_ssl": True})
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_verify_ssl_string_true_enables_certificate_verification():
    backend = UniboFileManagerBackend("proj", {"verify_ssl": "true"})
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_verify_ssl_string_one_enables_certificate_verification():
    backend = UniboFileManagerBackend("proj", {"verify_ssl": "1"})
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_default_stays_unverified():
    backend = UniboFileManagerBackend("proj", {})
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_NONE


def test_verify_ssl_false_stays_unverified():
    backend = UniboFileManagerBackend("proj", {"verify_ssl": False})
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_NONE


def test_no_credentials_stays_unverified():
    backend = UniboFileManagerBackend("proj", None)
    ctx = backend.ssl_context
    assert ctx.verify_mode == ssl.CERT_NONE

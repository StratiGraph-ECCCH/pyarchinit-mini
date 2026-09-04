"""Holding a bearer without giving it to the browser.

THE MEASUREMENT THAT SHAPED THE MODULE, restated because a test is where it
stays true: `app.session_interface` in this application is
`SecureCookieSessionInterface`. There is no server-side session. So
`session["access_token"] = …` puts the token in the cookie, signed but not
encrypted, and anything holding that cookie reads it back verbatim.

`test_a_token_in_the_flask_session_would_reach_the_browser` reproduces exactly
that, so the reason this module exists cannot quietly stop being true.
"""

from __future__ import annotations

import time

import pytest

from pyarchinit_mini.web_interface import oidc_tokens

ORCID = "0000-0002-1825-0097"
OTHER = "0000-0001-5109-3700"


@pytest.fixture(autouse=True)
def empty_store():
    """No bearer survives a test — the store is module state."""
    with oidc_tokens._LOCK:
        oidc_tokens._STORE.clear()
    yield
    with oidc_tokens._LOCK:
        oidc_tokens._STORE.clear()


def answer(access="a" * 40, refresh="r" * 40, expires_in=900,
           refresh_expires_in=1800):
    """The shape Keycloak's token endpoint returns."""
    out = {"access_token": access, "expires_in": expires_in,
           "token_type": "Bearer", "scope": "openid profile email"}
    if refresh is not None:
        out["refresh_token"] = refresh
    if refresh_expires_in is not None:
        out["refresh_expires_in"] = refresh_expires_in
    return out


class Realm:
    """A token endpoint that answers without a network.

    `client_id` and `token_endpoint` are the two attributes `_refresh` reads off
    `OidcSettings`, so this stands in for one without importing Flask.
    """

    client_id = "em-console"
    token_endpoint = "http://keycloak:8080/auth/realms/em-dev/protocol/openid-connect/token"


# ── 1 · the reason this module is not one line ───────────────────────────────

def test_a_token_in_the_flask_session_would_reach_the_browser():
    """THE GUARD OF THIS CHAPTER, demonstrated rather than asserted.

    Flask's cookie session is SIGNED, which stops a browser editing it, and is
    not ENCRYPTED, which stops nothing from reading it. If this ever becomes
    false — somebody installs Flask-Session, or Flask starts encrypting — this
    test fails and the module's whole justification should be re-read.
    """
    from flask.json.tag import TaggedJSONSerializer
    from itsdangerous import URLSafeTimedSerializer

    secret = "the-real-session-key-of-this-server-0123456789"
    token = "eyJhbGciOiJSUzI1NiJ9." + "Zm9vYmFy" * 170 + ".c2ln"

    server = URLSafeTimedSerializer(secret, salt="cookie-session",
                                    serializer=TaggedJSONSerializer())
    cookie = server.dumps({"_user_id": "1", "access_token": token})

    # Somebody with the cookie and WITHOUT the key.
    thief = URLSafeTimedSerializer("not-the-key", salt="cookie-session",
                                   serializer=TaggedJSONSerializer())
    signature_ok, recovered = thief.loads_unsafe(cookie)

    assert signature_ok is False, "the wrong key should not verify"
    assert recovered["access_token"] == token, (
        "the token was NOT recovered from the cookie without the key — if "
        "Flask's session became encrypted, `oidc_tokens` can be simplified")


def test_the_handle_is_all_that_could_go_into_a_cookie():
    """What `remember` hands back is opaque and short: not a token."""
    handle = oidc_tokens.remember(answer(), ORCID)
    assert "a" * 40 not in handle
    assert "r" * 40 not in handle
    assert len(handle) < 64
    assert oidc_tokens.held(handle)


def test_the_store_never_hands_the_token_to_a_page():
    """`status()` is what the template gets, and it has no way to leak one."""
    handle = oidc_tokens.remember(answer(), ORCID)
    shown = oidc_tokens.status(handle)
    assert set(shown) == {"held", "fingerprint", "expires_in", "renewable",
                          "refresh_expires_in"}
    for value in shown.values():
        assert "a" * 40 != value and "r" * 40 != value
    assert shown["fingerprint"] == oidc_tokens.fingerprint("a" * 40)
    assert len(shown["fingerprint"]) == 12


def test_status_of_nothing_says_so_rather_than_raising():
    assert oidc_tokens.status(None) == {"held": False}
    assert oidc_tokens.status("un-handle-che-non-esiste") == {"held": False}


# ── 2 · handing the bearer back ──────────────────────────────────────────────

def test_a_fresh_bearer_comes_back_unchanged():
    handle = oidc_tokens.remember(answer(), ORCID)
    assert oidc_tokens.bearer(handle, ORCID, Realm()) == "a" * 40


def test_no_handle_refuses_and_says_what_to_do():
    with pytest.raises(oidc_tokens.SignInAgain) as refusal:
        oidc_tokens.bearer(None, ORCID, Realm())
    assert "ORCID" in str(refusal.value)


def test_a_handle_the_process_does_not_know_refuses_and_names_the_reason():
    """The `-w 2` case, and the restart case, in the sentence the user sees."""
    with pytest.raises(oidc_tokens.SignInAgain) as refusal:
        oidc_tokens.bearer("mai-visto", ORCID, Realm())
    assert "riavvio" in str(refusal.value)


def test_a_handle_is_not_redeemable_under_another_identity():
    """A cookie replayed under a different account must not borrow the bearer.

    And the handle is DESTROYED rather than merely refused: a handle that has
    been presented by the wrong identity is a handle that has leaked.
    """
    handle = oidc_tokens.remember(answer(), ORCID)
    with pytest.raises(oidc_tokens.SignInAgain) as refusal:
        oidc_tokens.bearer(handle, OTHER, Realm())
    assert "identità" in str(refusal.value)
    assert not oidc_tokens.held(handle), "the handle survived being misused"


def test_an_account_with_no_orcid_cannot_redeem_a_bearer():
    handle = oidc_tokens.remember(answer(), ORCID)
    with pytest.raises(oidc_tokens.SignInAgain):
        oidc_tokens.bearer(handle, "", Realm())


# ── 3 · expiry, and the margin ───────────────────────────────────────────────

def test_a_response_without_expires_in_is_treated_as_already_expired():
    """The pessimistic reading, on purpose.

    Optimism here costs a 401 from the room reported as the room's fault; the
    pessimistic reading costs one refresh.
    """
    handle = oidc_tokens.remember(answer(expires_in=None), ORCID)
    with oidc_tokens._LOCK:
        kept = oidc_tokens._STORE[handle]
    assert not kept.access_is_usable(time.time())


def test_the_margin_renews_before_the_token_actually_dies(monkeypatch):
    """A token valid for less than `REFRESH_MARGIN` is refreshed, not used."""
    handle = oidc_tokens.remember(
        answer(expires_in=oidc_tokens.REFRESH_MARGIN - 1), ORCID)

    asked = {}

    def fake_refresh(h, kept, settings):
        asked["yes"] = True
        renewed = oidc_tokens._Bearer(
            access_token="nuovo", refresh_token="r2",
            expires_at=time.time() + 900, refresh_expires_at=time.time() + 1800,
            orcid=kept.orcid)
        with oidc_tokens._LOCK:
            oidc_tokens._STORE[h] = renewed
        return renewed

    monkeypatch.setattr(oidc_tokens, "_refresh", fake_refresh)
    assert oidc_tokens.bearer(handle, ORCID, Realm()) == "nuovo"
    assert asked, "a token inside the margin was used instead of renewed"


def test_an_expired_bearer_with_no_refresh_token_refuses():
    handle = oidc_tokens.remember(
        answer(expires_in=None, refresh=None, refresh_expires_in=None), ORCID)
    with pytest.raises(oidc_tokens.SignInAgain) as refusal:
        oidc_tokens.bearer(handle, ORCID, Realm())
    assert "scaduta" in str(refusal.value)
    assert not oidc_tokens.held(handle), (
        "a bearer with nothing left to try should not stay in the store")


def test_a_refresh_token_of_unknown_lifetime_is_believed():
    """No `refresh_expires_in` means the realm did not say.

    Refusing on our own guess would turn a working refresh into a sign-in; the
    realm's own refusal is a better answer than one we invented.
    """
    handle = oidc_tokens.remember(
        answer(expires_in=None, refresh_expires_in=None), ORCID)
    with oidc_tokens._LOCK:
        kept = oidc_tokens._STORE[handle]
    assert kept.refresh_is_usable(time.time())


# ── 4 · the refresh, against a stand-in realm ────────────────────────────────

def test_a_refresh_replaces_both_tokens_and_keeps_the_identity(monkeypatch):
    """Keycloak reissues the refresh token; keeping the old one would break the
    day `revokeRefreshToken` is turned on — on somebody else's node."""
    handle = oidc_tokens.remember(answer(expires_in=None), ORCID)

    sent = {}

    class Answer:
        def read(self):
            return (b'{"access_token":"nuovo-access","refresh_token":'
                    b'"nuovo-refresh","expires_in":900,'
                    b'"refresh_expires_in":1800}')

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(request_, timeout=None):
        sent["url"] = request_.full_url
        sent["body"] = request_.data.decode()
        return Answer()

    monkeypatch.setattr(oidc_tokens.urllib.request, "urlopen", fake_urlopen)

    assert oidc_tokens.bearer(handle, ORCID, Realm()) == "nuovo-access"
    assert sent["url"] == Realm.token_endpoint, (
        "the refresh must go to the endpoint derived from OIDC_JWKS_URI — "
        "inside the network, not through our own proxy")
    assert "grant_type=refresh_token" in sent["body"]
    assert "client_id=em-console" in sent["body"]
    assert "client_secret" not in sent["body"], (
        "em-console is a PUBLIC client: a secret here would be a secret "
        "invented for a client that has none")

    with oidc_tokens._LOCK:
        kept = oidc_tokens._STORE[handle]
    assert kept.refresh_token == "nuovo-refresh"
    assert kept.orcid == ORCID, "a refresh must not change whose bearer this is"


def test_a_refused_refresh_drops_the_bearer_and_says_to_sign_in(monkeypatch):
    """`invalid_grant` — the refresh token expired or was revoked."""
    import io
    import urllib.error

    handle = oidc_tokens.remember(answer(expires_in=None), ORCID)

    def fake_urlopen(request_, timeout=None):
        raise urllib.error.HTTPError(
            request_.full_url, 400, "Bad Request", {},
            io.BytesIO(b'{"error":"invalid_grant"}'))

    monkeypatch.setattr(oidc_tokens.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(oidc_tokens.SignInAgain) as refusal:
        oidc_tokens.bearer(handle, ORCID, Realm())
    said = str(refusal.value)
    assert "invalid_grant" in said and "400" in said
    assert "non tento un giro di autenticazione dentro questa richiesta" in said
    assert not oidc_tokens.held(handle)


def test_an_unreachable_realm_keeps_the_bearer(monkeypatch):
    """A blip is not a revocation.

    Dropping the bearer because the network hiccuped would turn a retry into a
    sign-in, and the token may well still be perfectly good.
    """
    handle = oidc_tokens.remember(answer(expires_in=None), ORCID)

    def fake_urlopen(request_, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(oidc_tokens.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(oidc_tokens.SignInAgain):
        oidc_tokens.bearer(handle, ORCID, Realm())
    assert oidc_tokens.held(handle), (
        "an unreachable realm dropped a bearer that may still be valid")


# ── 5 · what may be logged ───────────────────────────────────────────────────

def test_the_loggable_line_carries_durations_and_never_a_token():
    line = oidc_tokens.durations(answer())
    assert "900s" in line and "1800s" in line
    assert "a" * 40 not in line
    assert "r" * 40 not in line
    assert oidc_tokens.fingerprint("a" * 40) in line


def test_a_response_with_no_refresh_token_says_absent_rather_than_None():
    line = oidc_tokens.durations(answer(refresh=None, refresh_expires_in=None))
    assert "refresh assente" in line


def test_the_fingerprint_is_a_digest_and_not_a_prefix():
    """A truncated secret is still a secret."""
    token = "eyJhbGciOiJSUzI1NiJ9.qualcosa.firma"
    print_ = oidc_tokens.fingerprint(token)
    assert print_ not in token
    assert token[:12] != print_
    assert oidc_tokens.fingerprint(None) == "—"


# ── 6 · the store is bounded ─────────────────────────────────────────────────

def test_expired_entries_are_pruned_on_every_write():
    dead = oidc_tokens.remember(
        answer(expires_in=None, refresh=None, refresh_expires_in=None), ORCID)
    assert oidc_tokens.held(dead)
    oidc_tokens.remember(answer(), OTHER)
    assert not oidc_tokens.held(dead), (
        "a bearer with nothing left to try survived a later write")


def test_the_store_cannot_grow_without_end(monkeypatch):
    monkeypatch.setattr(oidc_tokens, "MAX_ENTRIES", 8)
    for n in range(40):
        oidc_tokens.remember(answer(access=f"token-{n}"), ORCID)
    with oidc_tokens._LOCK:
        assert len(oidc_tokens._STORE) <= 8


def test_forget_says_whether_there_was_anything_to_forget():
    handle = oidc_tokens.remember(answer(), ORCID)
    assert oidc_tokens.forget(handle) is True
    assert oidc_tokens.forget(handle) is False
    assert oidc_tokens.forget(None) is False

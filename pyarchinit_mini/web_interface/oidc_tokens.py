"""The bearer this server holds ON THE USER'S BEHALF — and where it is kept.

Step 02 decided the opposite, and said so in `oidc_routes.oidc_callback`:

    THE TOKEN IS NOT KEPT. […] pyarchinit-mini calls no service on the user's
    behalf yet, so it has no reason to hold a bearer, and a token in a session
    is a token that outlives the reason it was issued.

That was right while it was true. It is no longer true: pyarchinit-mini now
delivers a site's stratigraphy into a StratiGraph room, and a room asks who is
writing. That is the case the pattern «server-side web application keeps the
token in its own session» exists for, so the decision is reversed WITH its
reason, not quietly.

════════════════════════════════════════════════════════════════════════════════
## AND HERE IS THE MEASUREMENT THAT DECIDED THE SHAPE OF THIS FILE

The obvious implementation is one line — `session["access_token"] = …`. **In
THIS application that line hands the token to the browser.** Measured in the
running container, 4 September 2026:

    app.session_interface  →  flask.sessions.SecureCookieSessionInterface
    SESSION_TYPE           →  None

There is no Flask-Session, no server-side store, nothing: the Flask session in
pyarchinit-mini IS the cookie. And a Flask cookie is **signed, not encrypted** —
the signature stops a browser EDITING it, and stops nothing at all from READING
it. Measured, with a serializer holding the wrong key:

    access token stand-in      : 1414 caratteri (a real em-dev token: 1414)
    cookie risultante          : 1550 byte (limite del browser: 4096)
    firma verificata dal ladro : False
    contenuto letto lo stesso  : ['_user_id', 'access_token']
    access_token recuperato    : eyJhbGciOiJSUzI1NiJ9.Iu8...
    identico all'originale     : True

So the token survives the round trip through the browser in plain text, readable
by anything with the cookie — an extension, a shared machine, a proxy that logs,
a screenshot of devtools. It also fits, which is the trap: nothing would fail,
and the leak would be silent.

**Therefore the cookie carries a HANDLE and the process carries the token.**
32 bytes of urandom go into the session; the bearer lives in `_STORE`, in this
worker's memory, and is looked up by that handle. The browser never receives
the token and no disk ever does either — a token on disk is a token that leaks.

## THE LIMITS OF A PROCESS-LOCAL STORE, declared rather than discovered

* **One worker.** Measured in the container (`/proc/*/cmdline`): a master and
  ONE worker, `-w 1 --threads 4` — which is what `railway.toml`, the `Procfile`
  and the Dockerfile's CMD all say. Four threads share one process, so a dict
  under a lock is the right amount of machinery. Run with `-w 2` and a handle
  minted by one worker is unknown to the other: the delivery then refuses with
  «sign in again» instead of silently misbehaving. A degradation, stated here,
  and the reason `SignInAgain` says what it says.
* **A restart forgets.** The next delivery asks the user to sign in again. That
  is the correct behaviour for a credential nobody chose to persist.
* **Bounded.** Expired entries are pruned on every write, and `_MAX_ENTRIES`
  caps the rest — an unbounded dict keyed by a value a caller can cause to be
  minted is a memory leak with a login form in front of it.

## AND WHAT IS NEVER DONE HERE: reading the token

`oidc_routes._identity_claims` states the rule, and it stands:

    an access token is addressed to `em-server`, not to us. A client that
    inspects a token issued for somebody else has stopped being a client.

Delivering a token to the service it is addressed to is not inspecting it. So
this module never decodes the JWT — not even for the expiry. **The expiry comes
from `expires_in`**, which is a number the token endpoint gave to US, in a
response addressed to us. That is the difference, and it is the whole reason
this file can hold a bearer without contradicting that comment.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

#: The ONLY thing that goes into the cookie: a handle, meaning nothing to anyone
#: who does not hold this process's memory.
HANDLE_KEY = "oidc_bearer_handle"

#: Renew this many seconds BEFORE the token actually expires. A token that is
#: valid when checked and expired when it arrives is the classic race, and the
#: margin is the cheap fix. Ten seconds would do for a call inside one network;
#: sixty covers a slow batch behind it.
REFRESH_MARGIN = 60.0

#: How many live bearers this worker will hold. One per signed-in person, and a
#: cap so that a stream of sign-ins cannot grow the dict without end.
MAX_ENTRIES = 512


class SignInAgain(RuntimeError):
    """There is no usable bearer, and no way to get one without the user.

    Deliberately NOT recoverable inside a request: a silent OIDC round trip
    inside a POST is how a request disappears. The user is told, in the sentence
    this carries, to sign in again.
    """


@dataclass
class _Bearer:
    """What the token endpoint gave us, minus everything we were not given.

    `orcid` is here so a handle cannot be redeemed under a different account —
    see `bearer()`. Nothing in this object is ever logged, returned to a
    template, or written anywhere.
    """

    access_token: str
    refresh_token: Optional[str]
    expires_at: float
    refresh_expires_at: Optional[float]
    orcid: str

    def access_is_usable(self, now: float) -> bool:
        return self.access_token and now < (self.expires_at - REFRESH_MARGIN)

    def refresh_is_usable(self, now: float) -> bool:
        if not self.refresh_token:
            return False
        if self.refresh_expires_at is None:
            # The endpoint declared no lifetime for it. Believing it is alive is
            # the only option that can succeed, and a refusal from the realm is
            # a better answer than a refusal we invented.
            return True
        return now < (self.refresh_expires_at - REFRESH_MARGIN)

    def dead(self, now: float) -> bool:
        """Nothing left to try: the access token is past AND the refresh is."""
        return not self.access_is_usable(now) and not self.refresh_is_usable(now)


_STORE: Dict[str, _Bearer] = {}
_LOCK = threading.Lock()


def fingerprint(token: Optional[str]) -> str:
    """Which token, without the token.

    The same device `session_key.fingerprint` uses, and for the same reason: a
    log line has to be able to say «still the one from the sign-in» or «a
    different one now», and a truncated secret is still a secret.
    """
    if not token:
        return "—"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def durations(answer: Dict[str, Any]) -> str:
    """The loggable half of a token response: how long, never what.

    Numbers, and the presence or absence of a refresh token. Every one of these
    is something the realm told US about our own session.
    """
    access = answer.get("expires_in")
    refresh = answer.get("refresh_expires_in")
    return (f"access {access}s (fp {fingerprint(answer.get('access_token'))}), "
            f"refresh {'assente' if not answer.get('refresh_token') else f'{refresh}s'}, "
            f"token_type={answer.get('token_type')!r}, "
            f"scope={answer.get('scope')!r}")


def _drop_the_dead(now: float) -> None:
    """Bearers with nothing left to try. Called with `_LOCK` held."""
    for handle in [h for h, b in _STORE.items() if b.dead(now)]:
        _STORE.pop(handle, None)


def _enforce_cap() -> None:
    """Oldest first, until the store fits. Called with `_LOCK` held.

    SEPARATE from `_drop_the_dead`, and the two calls sit on either side of the
    insert for a reason each test found. Both together BEFORE the insert left
    the store at `MAX_ENTRIES + 1`; both together AFTER it pruned the bearer
    just remembered, when that bearer arrived already expired — which is a real
    case (`expires_in` absent) and which must be REFUSED with «the session
    expired», not with «the server restarted».
    """
    while len(_STORE) > MAX_ENTRIES:
        _STORE.pop(next(iter(_STORE)), None)


def remember(answer: Dict[str, Any], orcid: str) -> str:
    """Keep the bearer, return the handle to put in the session.

    `answer` is the token endpoint's response, verbatim. Only four of its fields
    are read; the rest is not stored, because storing what we do not use is how
    a refresh token ends up somewhere nobody meant to put one.
    """
    access = answer.get("access_token")
    if not access:
        raise SignInAgain("il realm non ha restituito un access token.")

    now = time.time()
    # A MISSING `expires_in` is treated as ALREADY EXPIRED rather than as
    # eternal. The pessimistic reading costs one refresh; the optimistic one
    # sends a dead token to a room and reports a 401 as if the room were at
    # fault.
    lifetime = answer.get("expires_in")
    refresh_lifetime = answer.get("refresh_expires_in")
    kept = _Bearer(
        access_token=access,
        refresh_token=answer.get("refresh_token"),
        expires_at=now + float(lifetime) if lifetime else now,
        refresh_expires_at=(now + float(refresh_lifetime)
                            if refresh_lifetime else None),
        orcid=orcid,
    )

    handle = secrets.token_urlsafe(32)
    with _LOCK:
        _drop_the_dead(now)
        _STORE[handle] = kept
        _enforce_cap()
    return handle


def forget(handle: Optional[str]) -> bool:
    """Drop a bearer. True when there was one — which is what a test asserts."""
    if not handle:
        return False
    with _LOCK:
        return _STORE.pop(handle, None) is not None


def held(handle: Optional[str]) -> bool:
    """Is there a bearer behind this handle? For the page, and for tests.

    Says nothing about whether it is still valid — `bearer()` answers that, and
    answering it here would mean two places deciding one thing.
    """
    if not handle:
        return False
    with _LOCK:
        return handle in _STORE


def status(handle: Optional[str]) -> Dict[str, Any]:
    """What a page may say about the bearer: durations and a fingerprint.

    Never the token. This is what makes «which token is active» answerable in
    the interface without putting one on a screen.
    """
    with _LOCK:
        kept = _STORE.get(handle or "")
    if kept is None:
        return {"held": False}
    now = time.time()
    return {
        "held": True,
        "fingerprint": fingerprint(kept.access_token),
        "expires_in": max(0, int(kept.expires_at - now)),
        "renewable": kept.refresh_is_usable(now),
        "refresh_expires_in": (None if kept.refresh_expires_at is None
                               else max(0, int(kept.refresh_expires_at - now))),
    }


def _refresh(handle: str, kept: _Bearer, settings: Any) -> _Bearer:
    """One refresh, against the realm's token endpoint.

    `settings` is an `oidc_routes.OidcSettings`, and `token_endpoint` is
    REUSED rather than rebuilt: it is derived from `OIDC_JWKS_URI`, so it points
    inside the network, needs no internal CA, and does not put our own proxy in
    the path of our own refresh. That docstring was paid for once already.

    `client_id` and no secret: `em-console` is a PUBLIC client — measured in
    `realm-em-dev.json`, `publicClient: true` — so the refresh grant is
    authenticated by possession of the refresh token alone.
    """
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": kept.refresh_token,
        "client_id": settings.client_id,
    }).encode("utf-8")
    request_ = urllib.request.Request(
        settings.token_endpoint, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request_, timeout=10.0) as answer:
            fresh = json.loads(answer.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The realm's own word — `invalid_grant` for a refresh token that has
        # expired or been revoked — is the diagnosis, so it is passed on. The
        # BODY is read but only its `error` field is repeated: a token endpoint
        # error body can echo what was sent.
        detail = "?"
        try:
            detail = (json.loads(exc.read().decode("utf-8", "replace"))
                      .get("error") or "?")
        except Exception:                                        # noqa: BLE001
            pass
        forget(handle)
        raise SignInAgain(
            f"Il realm ha rifiutato il rinnovo della sessione ({exc.code} "
            f"{detail}). Rientra con ORCID e riprova: non tento un giro di "
            f"autenticazione dentro questa richiesta.") from exc
    except Exception as exc:                                  # network, DNS, TLS
        # NOT forgotten: the bearer may be perfectly good and the realm merely
        # unreachable. Dropping it here would turn a blip into a sign-in.
        raise SignInAgain(
            f"Non ho potuto raggiungere il realm per rinnovare la sessione "
            f"({exc}). Il token che ho non è più utilizzabile: riprova, o "
            f"rientra con ORCID.") from exc

    now = time.time()
    lifetime = fresh.get("expires_in")
    refresh_lifetime = fresh.get("refresh_expires_in")
    renewed = _Bearer(
        access_token=fresh.get("access_token") or "",
        # Keycloak reissues the refresh token on every use. Keeping the OLD one
        # when the response carries a new one would work until
        # `revokeRefreshToken` is turned on in the realm, and then it would fail
        # in production on somebody else's node.
        refresh_token=fresh.get("refresh_token") or kept.refresh_token,
        expires_at=now + float(lifetime) if lifetime else now,
        refresh_expires_at=(now + float(refresh_lifetime)
                            if refresh_lifetime else None),
        orcid=kept.orcid,
    )
    if not renewed.access_token:
        forget(handle)
        raise SignInAgain("Il rinnovo è tornato senza access token: rientra "
                          "con ORCID.")

    with _LOCK:
        _STORE[handle] = renewed
    log.info("[OIDC] bearer renewed for orcid=%s: %s → %s, %s",
             kept.orcid, fingerprint(kept.access_token),
             fingerprint(renewed.access_token), durations(fresh))
    return renewed


def bearer(handle: Optional[str], orcid: str, settings: Any) -> str:
    """The access token to put in an `Authorization` header, renewed if needed.

    Raises `SignInAgain` rather than returning None: a caller that forgets to
    check a None sends `Authorization: Bearer None`, and the room answers 401
    with nobody the wiser about why.

    THE ORCID CHECK. A handle is redeemable only under the identity it was
    minted for. Without this, a session cookie replayed under another account
    would borrow that account's bearer — and the whole point of holding one is
    that the room learns who is writing.
    """
    if not handle:
        raise SignInAgain(
            "Questa sessione non ha un token per il server delle stanze: è un "
            "accesso locale, oppure il server è stato riavviato. Rientra con "
            "ORCID.")
    with _LOCK:
        kept = _STORE.get(handle)
    if kept is None:
        raise SignInAgain(
            "Il token di questa sessione non c'è più: succede a ogni riavvio "
            "del server, perché non viene scritto da nessuna parte. Rientra "
            "con ORCID.")
    if not secrets.compare_digest(kept.orcid, orcid or ""):
        # Not a refusal about expiry: this is the wrong person.
        log.warning("[OIDC] a bearer handle presented under orcid=%s was "
                    "minted for somebody else: refusing", orcid)
        forget(handle)
        raise SignInAgain(
            "Il token di questa sessione appartiene a un'altra identità: l'ho "
            "scartato. Rientra con ORCID.")

    now = time.time()
    if kept.access_is_usable(now):
        return kept.access_token
    if not kept.refresh_is_usable(now):
        forget(handle)
        raise SignInAgain(
            "La sessione con il realm è scaduta e non ho un refresh token "
            "utilizzabile. Rientra con ORCID e riprova la consegna.")
    return _refresh(handle, kept, settings).access_token


# ── the bearer falls with the session ────────────────────────────────────────

def _on_logout(_sender: Any, **_extra: Any) -> None:
    """`logout_user()` fired. Drop the bearer AND the handle.

    Both, and not just the handle: a handle removed from the cookie with the
    bearer left in `_STORE` is a token nothing can reach and nothing will ever
    clean up until it expires — a leak in the plainest sense.
    """
    from flask import session

    handle = session.pop(HANDLE_KEY, None)
    if forget(handle):
        log.info("[OIDC] bearer dropped at logout")


def _on_login(_sender: Any, **extra: Any) -> None:
    """Somebody logged in. Drop whatever bearer this browser was carrying.

    The case this exists for: sign in with ORCID, log out, sign in LOCALLY as
    somebody else in the same browser. Without this the stale handle survives
    in the cookie — `bearer()` would refuse it on the ORCID check, which is
    correct but late, and the refusal would be about the wrong thing. The
    OIDC callback stores its own handle immediately after `login_user`, so this
    never removes a bearer that belongs to the login now happening.
    """
    from flask import session

    handle = session.pop(HANDLE_KEY, None)
    if forget(handle):
        log.info("[OIDC] a previous session's bearer dropped at login")


def configure(app: Any) -> None:
    """Attach the two hooks. Called once from `create_app`.

    SIGNALS AND NOT AN EDIT TO `auth_routes.logout()`. This is a fork of a
    living project, and every line changed in a file upstream also edits is a
    merge conflict for as long as the fork lives. `flask_login` publishes real
    blinker signals — measured in the image: `blinker 1.9.0`, `flask_login
    0.6.3`, `user_logged_out` is a `blinker.base.NamedSignal` and not a stub —
    so the bearer can fall with the session while Enzo's function stays
    untouched.

    The receivers are connected with `weak=False`: module-level functions
    referenced only by the signal would otherwise be collectable, and a hook
    that silently stops running is worse than one that was never added.
    """
    from flask_login import user_logged_in, user_logged_out

    user_logged_out.connect(_on_logout, app, weak=False)
    user_logged_in.connect(_on_login, app, weak=False)

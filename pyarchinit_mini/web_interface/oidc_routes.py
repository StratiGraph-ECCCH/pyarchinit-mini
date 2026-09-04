"""Entering with an ORCID — the identity the StratiGraph ecosystem speaks.

pyarchinit-mini knows who you are for ITSELF: a local `users` table, a hashed
password, three roles. In the StratiGraph ecosystem an identity is one thing and
it has a precise name — the **ORCID iD** — because that is the key a room's
access list is indexed by (`PUT /rooms/{room_id}/members/{orcid}`).

This module is one door, added beside the door that exists. It does NOT make
pyarchinit-mini enter a room; it makes it able to say its own name in the
ecosystem's language, which is what everything after this step needs:

    no_author = 'I cannot write without knowing who you are: a verified
                 identity is required.'   — the connector contract

## THE RULE THAT GOVERNS EVERYTHING HERE

pyarchinit-mini is and remains Enzo's program, running for his users on Railway,
with no Keycloak and no StratiGraph. Therefore:

* **OIDC absent → today's behaviour, identical.** No OIDC variable in the
  environment means no OIDC door, the local login exactly as it is, and no
  visible difference anywhere. Not «a disabled button»: nothing.
* **OIDC half-configured → an explicit refusal at startup**, naming the missing
  variable. That is the house rule, and `stratigraph-server/app/auth.py` states
  it at length: an application that starts with authentication half on is worse
  than one that does not start.

## WHY A SEPARATE MODULE

This is a fork of somebody's living project (886 commits upstream). Every line
changed in a file Enzo also edits is a merge conflict for as long as the fork
lives. So the flow lives here, in a file upstream does not have, and
`auth_routes.py` gains ONE import line — which is what attaches these two routes
to the blueprint it already owns.

## NO NEW DEPENDENCIES, and this was measured rather than assumed

The plan for this step said to use `requests` for the three HTTP calls and
`python-jose` for the verification, and to measure both inside the container
first. Measured, 12 September 2026:

    python-jose  3.5.0     present
    requests               ModuleNotFoundError

`requests` is NOT declared in `requirements.txt` and is NOT in the image. (Two
modules import it lazily inside a function — `storage/backends/http_backend.py:69`
and `cloudinary_backend.py:202` — so they load and would only fail if that
storage backend were used. A latent break, reported, not repaired here.)

So the three calls use `urllib.request` from the standard library. That is not a
compromise: they are one POST and one GET of JSON, and adding a dependency to a
fork is a divergence to reconcile with upstream forever.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from flask import current_app, flash, redirect, request, session, url_for
from flask_login import login_user

from . import oidc_tokens
from .auth_routes import User, auth_bp

log = logging.getLogger(__name__)

#: Keycloak's fixed suffixes. Named once, because the two endpoints this module
#: needs are derived and a typo in a derivation is worse than a typo in a
#: variable: it fails at the third step of a browser round trip.
_CERTS_SUFFIX = "/protocol/openid-connect/certs"
_AUTH_SUFFIX = "/protocol/openid-connect/auth"
_TOKEN_SUFFIX = "/protocol/openid-connect/token"
_USERINFO_SUFFIX = "/protocol/openid-connect/userinfo"

#: Where the transient halves of one round trip live, and nowhere else.
_STATE_KEY = "oidc_state"
_VERIFIER_KEY = "oidc_code_verifier"
_NONCE_KEY = "oidc_nonce"


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


class OidcSettings:
    """What this application needs in order to have an OIDC door at all.

    `issuer` is a NAME (it is what the token says about itself, and what `iss`
    is compared against); `jwks_uri` is a MACHINE (it is fetched). They are
    deliberately different variables and in the dev stack they are deliberately
    different hosts — `https://em.localhost:8443/auth/realms/em-dev` against
    `http://keycloak:8080/auth/realms/em-dev/…`. Routing the key fetch through
    our own proxy would make the ability to VALIDATE depend on the proxy in front
    of us. That comment was paid for with a bug; it is copied here for the same
    reason it was written there.
    """

    def __init__(self) -> None:
        self.issuer = _env("OIDC_ISSUER").rstrip("/")
        self.client_id = _env("OIDC_CLIENT_ID")
        # NO `audience`. The other services in this stack all read
        # `OIDC_AUDIENCE`, and this one deliberately does not — see
        # `configuration_error()` for the measurement that removed it.
        jwks = _env("OIDC_JWKS_URI")
        # DERIVED, not asked for twice — the same choice `app/auth.py` makes:
        # Keycloak's certs endpoint is the issuer plus a fixed suffix, so one
        # variable configures both and they cannot disagree. The dev stack sets
        # it explicitly anyway, because there it must point INSIDE.
        self.jwks_uri = jwks or (f"{self.issuer}{_CERTS_SUFFIX}" if self.issuer else "")

    @property
    def declared(self) -> bool:
        """Has anybody said anything about OIDC at all?

        `OIDC_AUDIENCE` is NOT counted: nothing here reads it, so a stale one
        left in an environment must not be able to refuse a boot on its own.
        """
        return any((self.issuer, self.client_id, _env("OIDC_JWKS_URI")))

    @property
    def enforcing(self) -> bool:
        return bool(self.issuer and self.client_id and self.jwks_uri)

    @property
    def authorization_endpoint(self) -> str:
        """The BROWSER's destination, so it comes from the public issuer."""
        return f"{self.issuer}{_AUTH_SUFFIX}"

    @property
    def token_endpoint(self) -> str:
        """The SERVER's destination, so it comes from the same base as the JWKS.

        This is the one derivation `stratigraph-server` has no precedent for: it
        validates tokens and never exchanges a code, so it needs no token
        endpoint at all. The reasoning is its own, applied one step further —
        `OIDC_JWKS_URI` is the variable that names «the machine that answers»,
        and a code exchange is the same kind of server-to-server call as a key
        fetch. Going out through the public issuer would put our own proxy in the
        path of our own login.

        `configuration_error()` refuses a JWKS URI that is not shaped like
        Keycloak's, so this replacement cannot quietly produce nonsense.
        """
        return self.jwks_uri[: -len(_CERTS_SUFFIX)] + _TOKEN_SUFFIX

    @property
    def userinfo_endpoint(self) -> str:
        """Where a claim that is not in the id_token is asked for.

        Same base as the JWKS and the token endpoint, and for the same reason:
        this is a call this server makes, not a place a browser is sent.
        """
        return self.jwks_uri[: -len(_CERTS_SUFFIX)] + _USERINFO_SUFFIX


def settings() -> OidcSettings:
    return OidcSettings()


#: The variables that must ALL be present for the door to exist. Declared here
#: rather than spelled out in three places, so that the refusal, the settings
#: and the tests cannot disagree about what is required.
#:
#: `OIDC_JWKS_URI` is not among them because it is DERIVED from the issuer.
#:
#: AND NEITHER IS `OIDC_AUDIENCE`, which every other service in this stack has.
#: That divergence was forced by a measurement — see `configuration_error()`.
REQUIRED_VARIABLES = ("OIDC_ISSUER", "OIDC_CLIENT_ID")


def configuration_error() -> Optional[str]:
    """The sentence to refuse to start with, or None.

    THE SHAPE IS `stratigraph-server/app/auth.py`'s, deliberately: something set
    and something missing is a refusal, nothing set is today's behaviour, and
    everything set is the door. What is added here is `OIDC_CLIENT_ID`, which
    that server does not need — it only ever validates a token somebody else
    obtained, while this application performs the browser flow itself and so has
    to say which client it is.

    ## WHY `OIDC_AUDIENCE` IS NOT REQUIRED HERE

    Because nothing reads it, and a variable required for nothing is a claim
    that it matters. The plan for this step asked for four variables including
    that one, and the first live round trip refused a perfectly good token with
    `Invalid audience`. Measured in the realm afterwards:

        em-console · mapper audience · included.client.audience = em-server
                                     · id.token.claim = FALSE

    The audience mapper writes `em-server` into the ACCESS token, never into
    the id_token — and that is not a gap in the realm. **An id_token's `aud` is
    the client that requested it**, by OpenID Connect Core; `em-server` is the
    audience of the access token a resource server validates.
    `stratigraph-server` is that resource server and is right to demand
    `em-server`. This application is a CLIENT reading its own id_token, so the
    audience it must insist on is its own `client_id`.

    Requiring `OIDC_AUDIENCE` while checking `client_id` would be a variable
    kept for the shape of the others. When the next step gives pyarchinit-mini a
    room to enter it will hold an access token, and `OIDC_AUDIENCE` will come
    back with a reader.
    """
    it = settings()
    if not it.declared:
        return None                      # nobody asked for OIDC: nothing to say
    present = {"OIDC_ISSUER": bool(it.issuer),
               "OIDC_CLIENT_ID": bool(it.client_id),
               "OIDC_JWKS_URI (or OIDC_ISSUER to derive it)": bool(it.jwks_uri)}
    if not all(present.values()):
        missing = ", ".join(k for k, v in present.items() if not v)
        # What is LISTED as given is what the ENVIRONMENT holds, not what was
        # derived from it. Measured on the first run of this refusal: with only
        # `OIDC_ISSUER` set, the sentence reported `OIDC_JWKS_URI` as set too —
        # true of the settings and misleading to the person reading, who would
        # go looking for a variable they never wrote.
        given = ", ".join(n for n in REQUIRED_VARIABLES + ("OIDC_JWKS_URI",)
                          if _env(n)) or "one OIDC_* variable"
        return (f"OIDC is half-configured: {given} set, {missing} missing. "
                f"Refusing to start rather than falling back to the local login "
                f"alone — an application that boots with authentication half on "
                f"is worse than one that will not boot. Set all of them, or unset "
                f"every OIDC_* variable for the behaviour pyarchinit-mini has "
                f"always had.")
    if not it.jwks_uri.endswith(_CERTS_SUFFIX):
        return (f"OIDC_JWKS_URI does not look like a Keycloak certs endpoint "
                f"(expected it to end with {_CERTS_SUFFIX!r}): {it.jwks_uri!r}. "
                f"The token endpoint is derived from it, so a URI of another "
                f"shape would send the code exchange somewhere nobody chose.")
    return None


def normalize_orcid(orcid: Any) -> Optional[str]:
    """One spelling for an identity.

    REPLICATED, NOT INVENTED: this is `stratigraph-server/app/access.py:178`
    `_norm`, line for line, and it is copied rather than approximated because an
    ORCID written in two forms is two people. That divergence is the kind found
    six months later, when permissions do not add up.

    ORCIDs travel as bare iDs and as URLs, and a table holding both would match
    one and miss the other.
    """
    if orcid in (None, ""):
        return None
    text = str(orcid).strip()
    for prefix in ("https://orcid.org/", "http://orcid.org/", "orcid.org/"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
            break
    return text.strip("/") or None


def _get_json(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as answer:
        return json.loads(answer.read().decode("utf-8"))


def _post_form(url: str, form: Dict[str, str], timeout: float = 10.0) -> Dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as answer:
        return json.loads(answer.read().decode("utf-8"))


def _verify_id_token(id_token: str, it: OidcSettings, nonce: str) -> Dict[str, Any]:
    """Signature, issuer, audience, expiry and nonce — all of them, every time.

    NO SHORTCUT. Not `verify_signature=False`, not «for now»: a token accepted
    without its signature is a claim anybody can write, and this one decides who
    somebody is.

    The key is chosen by the token's `kid` against the realm's JWKS. A realm
    rotates keys, so picking the first key would work until the day it did not.
    """
    from jose import jwk, jwt
    from jose.utils import base64url_decode

    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    keys = (_get_json(it.jwks_uri).get("keys") or [])
    chosen = next((k for k in keys if k.get("kid") == kid), None)
    if chosen is None:
        raise ValueError(
            f"the realm's JWKS has no key {kid!r}: it has "
            f"{[k.get('kid') for k in keys]!r}. A rotated key is the usual "
            f"reason, and the remedy is to sign in again.")

    # The signature, by hand, because `jose.jwt.decode` wants the key material
    # and this is the material the realm published.
    message, _, signature = id_token.rpartition(".")
    if not jwk.construct(chosen).verify(message.encode("utf-8"),
                                        base64url_decode(signature.encode("utf-8"))):
        raise ValueError("the id_token's signature does not verify against the "
                         "realm's published key")

    claims = jwt.decode(
        id_token, chosen, algorithms=[chosen.get("alg", header.get("alg", "RS256"))],
        # THE CLIENT ID, not a resource audience — see `configuration_error()`
        # for the round trip that taught this the hard way. An id_token is
        # addressed to whoever asked for it.
        audience=it.client_id, issuer=it.issuer,
        options={"verify_signature": True, "verify_aud": True,
                 "verify_iss": True, "verify_exp": True,
                 # THE ONE CHECK TURNED OFF, and it is off by the
                 # specification and not for convenience. `at_hash` binds an
                 # id_token to the access token it came with, and OpenID
                 # Connect Core requires validating it only when the id_token
                 # is issued from the AUTHORIZATION endpoint — the implicit and
                 # hybrid flows, where the two travel through the browser and
                 # one could be swapped for another. This is the authorization
                 # CODE flow: the pair is fetched by this server, over TLS,
                 # straight from the token endpoint, in one response. There is
                 # no third party in that exchange for `at_hash` to catch.
                 "verify_at_hash": False})

    if not secrets.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise ValueError("the id_token's nonce is not the one this session sent: "
                         "refusing a token that answers somebody else's request")
    return claims


@auth_bp.app_context_processor
def _oidc_in_templates() -> Dict[str, Any]:
    """Tell every template whether this server has an ORCID door.

    `app_context_processor` (not `context_processor`) because the variable is
    needed in `auth/login.html` and in `base.html`, and `base.html` renders
    under every blueprint. Registered from HERE so that the templates' one
    condition costs Enzo's Python files nothing.

    A server with no OIDC gets `False` and therefore renders nothing at all —
    not a disabled button, which would advertise a door this installation does
    not have.
    """
    return {"oidc_available": settings().enforcing}


# ── the two routes ───────────────────────────────────────────────────────────

@auth_bp.route("/oidc/login")
def oidc_login():
    """Send the browser to the realm — Authorization Code with PKCE (S256)."""
    it = settings()
    if not it.enforcing:
        flash("Questo server non ha una porta ORCID configurata.", "error")
        return redirect(url_for("auth.login"))

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    # THE VERIFIER STAYS IN THE FLASK SESSION and nowhere else — not a cookie of
    # its own, not a database row, not a module global. A module global would be
    # shared by four threads (`--threads 4`) and two people signing in at once
    # would overwrite each other's round trip.
    session[_VERIFIER_KEY] = verifier
    session[_STATE_KEY] = state
    session[_NONCE_KEY] = nonce

    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": it.client_id,
        "redirect_uri": url_for("auth.oidc_callback", _external=True),
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return redirect(f"{it.authorization_endpoint}?{query}")


@auth_bp.route("/oidc/callback")
def oidc_callback():
    """Come back from the realm, and find out who this is — and keep the bearer.

    ## THE TOKEN IS NOW KEPT, AND STEP 02 SAID THE OPPOSITE

    What used to be written here, and it was right when it was written:

        THE TOKEN IS NOT KEPT. […] pyarchinit-mini calls no service on the
        user's behalf yet, so it has no reason to hold a bearer, and a token in
        a session is a token that outlives the reason it was issued.

    The clause that carried it was «calls no service on the user's behalf YET».
    It now does: `room_client` delivers a site's stratigraphy into a StratiGraph
    room, and the room asks who is writing. A token that outlives its reason is
    a risk with no return; this one has a reason that outlives the round trip.

    **Nothing else about the reasoning changed**, and in particular the token is
    still not READ here. The access token is addressed to `em-server`; we hand
    it to `em-server`. Its expiry is taken from `expires_in`, a number the token
    endpoint gave to us — see `oidc_tokens`, which also carries the measurement
    proving that «the Flask session» in this application is the browser's
    cookie, and therefore why the cookie gets a handle and not a bearer.
    """
    it = settings()
    if not it.enforcing:
        return redirect(url_for("auth.login"))

    # The three transient halves are POPPED: one round trip, one use.
    verifier = session.pop(_VERIFIER_KEY, None)
    expected_state = session.pop(_STATE_KEY, None)
    nonce = session.pop(_NONCE_KEY, None)

    error = request.args.get("error")
    if error:
        # The realm's own words, which say more than «login failed».
        detail = request.args.get("error_description") or error
        log.warning("[OIDC] the realm refused: %s", detail)
        flash(f"Il realm ha rifiutato l'accesso: {detail}", "error")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    given_state = request.args.get("state")
    if not code or not verifier or not expected_state or not nonce:
        log.warning("[OIDC] a callback with no round trip in progress in this session")
        flash("Questo browser non ha un accesso ORCID in corso: riprova dal "
              "bottone.", "error")
        return redirect(url_for("auth.login"))
    if not secrets.compare_digest(str(given_state), str(expected_state)):
        # The one check that makes the round trip mean anything: a code delivered
        # with somebody else's state is a code this session did not ask for.
        log.warning("[OIDC] state mismatch: refusing a code this session did not ask for")
        flash("Lo stato dell'accesso non corrisponde: rifiuto un codice che "
              "questa sessione non ha chiesto.", "error")
        return redirect(url_for("auth.login"))

    try:
        answer = _post_form(it.token_endpoint, {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": url_for("auth.oidc_callback", _external=True),
            "client_id": it.client_id,
            "code_verifier": verifier,
        })
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        log.warning("[OIDC] the token exchange failed: %s %s", exc.code, body)
        flash(f"Scambio del codice rifiutato dal realm ({exc.code}).", "error")
        return redirect(url_for("auth.login"))
    except Exception as exc:                                  # network, DNS, TLS
        log.warning("[OIDC] the token endpoint could not be reached: %s", exc)
        flash("Non ho potuto raggiungere il realm per completare l'accesso.", "error")
        return redirect(url_for("auth.login"))

    id_token = answer.get("id_token")
    if not id_token:
        log.warning("[OIDC] the realm answered without an id_token")
        flash("Il realm ha risposto senza id_token.", "error")
        return redirect(url_for("auth.login"))

    try:
        claims = _verify_id_token(id_token, it, str(nonce))
    except Exception as exc:
        log.warning("[OIDC] the id_token did not verify: %s", exc)
        flash(f"Il token non è valido: {exc}", "error")
        return redirect(url_for("auth.login"))
    # …and here the token USED to go out of scope. It is kept now — see this
    # function's docstring for why the decision reversed, and `oidc_tokens` for
    # where it is kept, which is deliberately not `session`.

    # THE ORCID IS NOT IN THE ID_TOKEN, and that too was learnt from a live
    # round trip rather than assumed. See `_identity_claims`.
    try:
        identity = _identity_claims(claims, answer.get("access_token"), it)
    except Exception as exc:
        log.warning("[OIDC] could not establish the identity's claims: %s", exc)
        flash(f"Identità non stabilita: {exc}", "error")
        return redirect(url_for("auth.login"))

    orcid = normalize_orcid(identity.get("orcid"))
    email = (identity.get("email") or "").strip().lower()
    label = (identity.get("name") or identity.get("preferred_username")
             or identity.get("sub") or "")

    if not orcid:
        # `stratigraph-server/app/main.py:573` falls back to
        # `preferred_username` when a token carries no ORCID, and it is right to
        # for a service that must attribute SOMETHING. Here the whole point of
        # the door is the ORCID: without one there is nothing this login adds
        # over the local one, and inventing a local identity from a username
        # would put a person in the table under a name the ecosystem does not
        # index.
        log.warning("[OIDC] a verified token with no `orcid` claim (sub=%s)",
                    claims.get("sub"))
        flash("Questo token non porta un ORCID: il realm lo espone con un "
              "protocol mapper `orcid`, e senza quello non c'è l'identità che "
              "serve. Il login locale resta disponibile.", "error")
        return redirect(url_for("auth.login"))

    try:
        user_dict = _local_user_for(orcid, email, label)
    except _OrcidConflict as clash:
        log.warning("[OIDC] refused: %s", clash)
        flash(str(clash), "error")
        return redirect(url_for("auth.login"))
    except Exception as exc:
        log.error("[OIDC] could not attach the identity to a local user: %s", exc)
        flash("Identità verificata, ma non ho potuto collegarla a un utente "
              "locale.", "error")
        return redirect(url_for("auth.login"))

    user = User(user_dict)
    login_user(user)

    # THE BEARER, kept for the room and for nothing else.
    #
    # AFTER `login_user`, deliberately: `login_user` writes `_user_id` into the
    # session and, with `session_protection`, can regenerate it — a handle
    # stored before that could be dropped on the way, and the delivery would
    # refuse with «sign in again» right after a successful sign-in.
    #
    # It is stored under the ORCID that was just verified, so the handle is only
    # redeemable by this identity. Failing to keep it is NOT a failed login: the
    # person is signed in and everything except the room works, so it is logged
    # and the flow continues.
    try:
        session[oidc_tokens.HANDLE_KEY] = oidc_tokens.remember(answer, orcid)
        log.info("[OIDC] bearer kept for orcid=%s: %s",
                 orcid, oidc_tokens.durations(answer))
    except Exception as exc:                                     # noqa: BLE001
        session.pop(oidc_tokens.HANDLE_KEY, None)
        log.warning("[OIDC] signed in, but no bearer kept for orcid=%s: %s",
                    orcid, exc)

    log.info("[OIDC] %s entered as %s (orcid=%s)", label, user.username, orcid)
    flash(f"Benvenuto, {user.username} · ORCID {orcid}", "success")
    return redirect(url_for("index"))


def _identity_claims(claims: Dict[str, Any], access_token: Optional[str],
                     it: OidcSettings) -> Dict[str, Any]:
    """The verified claims, plus whatever only `/userinfo` will say.

    ## WHY THIS FUNCTION EXISTS

    The first live sign-in came back with a token that verified perfectly and
    carried no `orcid`. Measured in the realm:

        em-console · mapper orcid · claim.name = orcid
                                  · access.token.claim   = true
                                  · userinfo.token.claim = true
                                  · id.token.claim       = FALSE

    So the ORCID is in the ACCESS token and at `/userinfo`, and not in the
    id_token. Three ways out, and the choice is not arbitrary:

    * flip `id.token.claim` to true in the realm — smallest change, but it
      changes a file the whole stack imports, and on the institutional node the
      realm belongs to somebody else. A door that only opens when a third party
      sets a flag is a door that will be shut one day without warning.
    * parse the ACCESS token — it is a JWT here, and reading it is the classic
      mistake: an access token is addressed to `em-server`, not to us. A client
      that inspects a token issued for somebody else has stopped being a
      client.
    * ask `/userinfo`, which is the place OpenID Connect puts claims that are
      not in the id_token, and which THIS REALM ALREADY DECLARES for `orcid`.

    So: `/userinfo`. The id_token stays authoritative — if a realm does put the
    claim there, that value is used and no second call is made.

    ## THE CHECK THAT MAKES IT SAFE

    `sub` must be the same in both. Without that, a `/userinfo` answer is just
    a document arriving from the network: attaching its claims to this
    id_token's identity would be trusting the two to be about the same person
    because they arrived close together.
    """
    if claims.get("orcid"):
        return claims                    # the realm put it where a client looks

    if not access_token:
        raise ValueError(
            "the id_token carries no `orcid` and the realm returned no access "
            "token to ask /userinfo with")

    request_ = urllib.request.Request(
        it.userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}",
                 "Accept": "application/json"})
    with urllib.request.urlopen(request_, timeout=5.0) as answer:
        info = json.loads(answer.read().decode("utf-8"))

    if not secrets.compare_digest(str(info.get("sub") or ""),
                                  str(claims.get("sub") or "")):
        raise ValueError(
            f"/userinfo answered about {info.get('sub')!r} while the id_token "
            f"is about {claims.get('sub')!r}: refusing to mix two identities")

    # The id_token WINS on every key it has: it is signed and verified, and the
    # userinfo answer is here only to fill what it does not say.
    merged = dict(info)
    merged.update(claims)
    return merged


# ── attaching a verified identity to a local account ─────────────────────────

class _OrcidConflict(Exception):
    """One local account, two ORCIDs — refused rather than overwritten."""


def _unverifiable_password() -> str:
    """A password nobody can present, for an account that has none.

    `users.hashed_password` is `nullable=False`, and an account that enters only
    with OIDC has no password. The two obvious ways out are not equivalent, and
    THE MEASUREMENT DECIDED between them (12 September 2026):

      · make the column nullable → a migration altering an existing column on
        third parties' databases;
      · write a value nothing can verify → no schema change.

    The second looked right, and the plan for this step said so. Then
    `utils/auth.py:43` was measured, and it has a FALLBACK: when the stored hash
    is not recognised by passlib it compares the plain text directly
    («Hash not recognized (e.g. plain text from PyArchInit sync)»). So:

        verify_password('!oidc-only!', '!oidc-only!')  →  True

    A sentinel IS a password. Whoever typed the sentinel string would log in as
    that account — a login bypass, in the name of avoiding a migration.

    So neither: what is written is a REAL bcrypt hash of a random secret that is
    then discarded. The hash parses, so the plain-text fallback never runs, and
    the only string that would verify is 32 bytes of urandom nobody kept.
    Measured on the same day: every probe returns False, including the hash
    itself. No schema change, and nothing to guess.
    """
    from pyarchinit_mini.utils.auth import hash_password
    return hash_password(secrets.token_urlsafe(32))


def _local_user_for(orcid: str, email: str, label: str) -> Dict[str, Any]:
    """The three steps, in this order, and the order is the policy.

    1. the ORCID is already on an account → that is the person, let them in;
    2. otherwise the email matches an account with NO ORCID → link, and let them
       in. An account with a DIFFERENT ORCID is a conflict: refuse, never
       overwrite — the second identity would silently take over the first
       person's account;
    3. otherwise create an account, with role VIEWER.

    STEP 3 IS DELIBERATELY THE POOREST: arriving from Keycloak inherits no
    powers. The local roles stay the authority over pyarchinit's tables, no realm
    role is mapped onto `UserRole`, no correspondence table is invented, and
    `load_pyarchinit_permissions` is not touched. Owner and admin are
    facilitators and managers; it is not a token that decides who is one.
    """
    from sqlalchemy import func

    from pyarchinit_mini.models.user import User as UserModel

    # MEASURED rather than guessed: `UserService` keeps a `db_manager`, and each
    # of its own twelve methods opens `self.db_manager.connection.get_session()`.
    # This module borrows the same handle instead of building an engine of its
    # own, so it sees the database the application is actually using.
    connection = current_app.user_service.db_manager.connection

    # The conflict is DECIDED inside the session and RAISED after it closes.
    # Measured on the first run: raising through the `with` made
    # `database/connection.py` log `ERROR … Session error: L'utente locale …`,
    # so a deliberate policy refusal appeared in the log as a database failure.
    # The rollback that context manager performs is right and is kept; what is
    # moved is the shouting.
    refusal: Optional[str] = None

    with connection.get_session() as db:
        # 1 · the ORCID we already know
        row = db.query(UserModel).filter(UserModel.orcid == orcid).first()
        if row is not None:
            return _as_dict(row)

        # 2 · the same person, by email, not yet carrying an iD
        if email:
            row = db.query(UserModel).filter(
                func.lower(UserModel.email) == email).first()
            if row is not None:
                existing = normalize_orcid(row.orcid)
                if existing and existing != orcid:
                    refusal = (
                        f"L'utente locale «{row.username}» ha già l'ORCID "
                        f"{existing}, e questo token porta {orcid}. Sono due "
                        f"persone diverse sullo stesso account: rifiuto invece "
                        f"di sovrascrivere. Chi amministra questo server può "
                        f"separare i due account.")
                if refusal is None:
                    row.orcid = orcid
                    db.commit()
                    db.refresh(row)
                    log.info("[OIDC] linked orcid=%s to the existing user %s",
                             orcid, row.username)
                    return _as_dict(row)

        if refusal is not None:
            # nothing written, and the session closes without an error of its own
            attached = None
        else:
            # 3 · somebody new, with the least power there is
            attached = _create_viewer(db, label, email, orcid)

    if refusal is not None:
        raise _OrcidConflict(refusal)
    return attached


def _create_viewer(db: Any, label: str, email: str, orcid: str) -> Dict[str, Any]:
    """Step 3, on its own so the three branches above read as three branches."""
    from pyarchinit_mini.models.user import User as UserModel, UserRole

    username = _free_username(db, label, email, orcid)
    fresh = UserModel(
        username=username,
        email=email or f"{username}@orcid.invalid",
        full_name=label or username,
        hashed_password=_unverifiable_password(),
        role=UserRole.VIEWER,
        is_active=True,
        is_superuser=False,
        orcid=orcid,
    )
    db.add(fresh)
    db.commit()
    db.refresh(fresh)
    log.info("[OIDC] created %s as VIEWER for orcid=%s", username, orcid)
    return _as_dict(fresh)


def _as_dict(row: Any) -> Dict[str, Any]:
    """The shape `auth_routes.User` wants.

    Built here rather than through `user_service._user_to_dict`, because that
    helper is private, is Enzo's, and reaching into it from a new file is the
    kind of coupling a merge breaks. The keys are exactly the ones
    `auth_routes.User.__init__` reads, plus `orcid`.

    `_user_to_dict` still needs the `orcid` key of its own, and NOT for
    symmetry: `load_user` rebuilds the Flask-Login user from
    `get_user_by_id` on every request, so an ORCID present only here would be
    on screen once and gone from the request after.
    """
    from pyarchinit_mini.models.user import UserRole
    return {
        "id": row.id,
        "username": row.username,
        "email": row.email,
        "full_name": row.full_name,
        "role": row.role.value if isinstance(row.role, UserRole) else row.role,
        "is_active": row.is_active,
        "is_superuser": row.is_superuser,
        "orcid": getattr(row, "orcid", None),
    }


def _free_username(db: Any, label: str, email: str, orcid: str) -> str:
    """A username nobody has yet, derived from what the token said.

    Derived and then made unique, rather than asked for: this flow has no form,
    and a collision must not fail the login of somebody who did nothing wrong.
    """
    from pyarchinit_mini.models.user import User as UserModel

    seed = (label or email.split("@")[0] or f"orcid-{orcid[-4:]}").strip()
    base = "".join(c if (c.isalnum() or c in "._-") else "-"
                   for c in seed.lower()).strip("-") or f"orcid-{orcid[-4:]}"
    base = base[:40]
    candidate, suffix = base, 1
    while db.query(UserModel).filter(UserModel.username == candidate).first():
        suffix += 1
        candidate = f"{base}-{suffix}"[:50]
    return candidate

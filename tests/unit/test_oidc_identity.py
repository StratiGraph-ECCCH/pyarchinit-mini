"""What must stay true about the ORCID door.

Three rules, and each one is written to READ THE OTHER SIDE rather than to
restate it — a test that repeats a value in prose passes for ever while the
thing it guards rots.

    1. `normalize_orcid` is a COPY of stratigraph-server's `_norm`. A copy is the
       thing that drifts, so the test compares against the original's source
       when the sibling checkout is there.
    2. The id_token verification has no shortcut. Derived by stripping comments
       from the module — because the module's own prose says
       `verify_signature=False` in order to forbid it, and a naive grep
       therefore finds the forbidden thing inside the sentence that forbids it.
    3. The configuration is all-or-nothing. The variable names are read off the
       module, not typed here, so a fifth variable added tomorrow is covered by
       this test on the day it is added.
"""

import importlib
import re
import tokenize
from pathlib import Path

import pytest

MODULE = "pyarchinit_mini.web_interface.oidc_routes"

# Imported at collection time so `parametrize` can be driven by the module's own
# list instead of a copy typed here: a fourth required variable added tomorrow
# is covered by these tests on the day it is added, and one removed stops being
# asserted without anybody having to remember.
from pyarchinit_mini.web_interface.oidc_routes import REQUIRED_VARIABLES


@pytest.fixture()
def oidc(monkeypatch):
    """The module, with every OIDC_* variable cleared.

    Cleared because `configuration_error()` reads the ENVIRONMENT, and a
    developer who happens to have OIDC set in their shell would otherwise get
    different results from CI — the kind of test that fails on one machine only.
    """
    for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_CLIENT_ID",
                 "OIDC_JWKS_URI"):
        monkeypatch.delenv(name, raising=False)
    return importlib.import_module(MODULE)


def _code_without_prose(path: Path) -> str:
    """The module's CODE, with comments and docstrings removed.

    `NL` is deliberately NOT treated as the start of a logical line: inside
    brackets it is just a line break, and counting it made the first version of
    this stripper drop `"verify_iss"` and `"verify_at_hash"` and then report
    them as absent — a test that passed by not looking.
    """
    kept, previous = [], tokenize.INDENT
    with open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type == tokenize.COMMENT:
                continue
            if token.type == tokenize.STRING and previous in (
                    tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT):
                continue
            kept.append(token.string)
            previous = token.type
    return " ".join(kept)


# ── 1 · the copy must not drift from the original ────────────────────────────

def test_normalize_orcid_matches_the_room_servers_norm(oidc):
    """One spelling for one identity, and the SAME one on both sides.

    A room's access list is keyed on the ORCID
    (`PUT /rooms/{room_id}/members/{orcid}`). If this side normalises
    `https://orcid.org/0000-…` and that side does not, one person is two
    people and the permissions stop adding up — six months later, quietly.

    The sibling checkout is not a dependency of this project, so its absence
    SKIPS rather than fails. What is refused is a disagreement, never a missing
    neighbour.
    """
    access = (Path(__file__).resolve().parents[2].parent
              / "stratigraph-server" / "app" / "access.py")
    if not access.exists():
        pytest.skip(f"stratigraph-server not checked out beside this repo "
                    f"({access}) — nothing to compare against")

    source = access.read_text()
    body = re.search(r"^def _norm\(.*?\n(?=^\S|\Z)", source,
                     re.S | re.M)
    assert body, f"`_norm` is no longer in {access} — find where it moved"

    # `_norm`'s signature is annotated `(orcid: Any) -> Optional[str]`, and
    # without `from __future__ import annotations` those are evaluated when the
    # `def` runs — so the real typing objects have to be in scope, not stand-ins.
    from typing import Any, Optional
    namespace: dict = {"Any": Any, "Optional": Optional}
    exec(compile(body.group(0), str(access), "exec"), namespace)
    theirs = namespace["_norm"]

    # The inputs an ORCID actually arrives as, including the ones that differ
    # between a careful and a careless implementation.
    for probe in ("0000-0002-1825-0097",
                  "https://orcid.org/0000-0002-1825-0097",
                  "http://orcid.org/0000-0002-1825-0097",
                  "orcid.org/0000-0002-1825-0097",
                  "ORCID.ORG/0000-0002-1825-0097",
                  "https://orcid.org/0000-0002-1825-0097/",
                  "  0000-0002-1825-0097  ",
                  "", None, "/", "https://orcid.org/"):
        assert oidc.normalize_orcid(probe) == theirs(probe), (
            f"the two sides disagree about {probe!r}: this repo says "
            f"{oidc.normalize_orcid(probe)!r}, stratigraph-server says "
            f"{theirs(probe)!r}")


# ── 2 · no shortcut in the verification ──────────────────────────────────────

def test_the_id_token_verification_has_no_shortcut(oidc):
    """Every check on, except the one that is off BY THE SPECIFICATION.

    `at_hash` binds an id_token to the access token it came with, and OpenID
    Connect Core requires it only for tokens issued from the authorization
    endpoint (implicit and hybrid). This is the code flow, so it is off — and
    this test pins it as the ONLY one that may be, so turning off a second
    check has to come through here.
    """
    options = dict(re.findall(r'"(verify_[a-z_]+)"\s*:\s*(True|False)',
                              _code_without_prose(Path(oidc.__file__))))
    assert options, "no verification options found in the module at all"

    assert options.get("verify_signature") == "True", (
        "the id_token's signature is not being verified: an unverified token "
        "is a claim anybody can write, and this one decides who somebody is")
    for check in ("verify_aud", "verify_iss", "verify_exp"):
        assert options.get(check) == "True", f"{check} is not enforced"

    off = sorted(name for name, value in options.items() if value == "False")
    assert off == ["verify_at_hash"], (
        f"a check was turned off without passing through this test: {off}. "
        f"`verify_at_hash` is off by the specification (code flow); anything "
        f"else needs a reason written where it is disabled and a line here.")


def test_the_nonce_is_compared(oidc):
    """A token that answers somebody else's request must be refused.

    Read off the code rather than asserted in prose: the comparison has to be
    against the value the SESSION sent, and it has to be constant-time.
    """
    code = _code_without_prose(Path(oidc.__file__))
    assert "compare_digest" in code, (
        "state and nonce must be compared with secrets.compare_digest")
    assert code.count("compare_digest") >= 2, (
        "both the state and the nonce need comparing — one call means one of "
        "them is being trusted")


# ── 3 · all of it, or none of it ─────────────────────────────────────────────

def test_no_oidc_variable_means_no_door_and_no_complaint(oidc):
    """The ordinary case, and the one this fork must never break.

    pyarchinit-mini runs for Enzo's users with no Keycloak anywhere. No
    variable set must mean: starts, says nothing, shows nothing.
    """
    assert oidc.configuration_error() is None
    assert oidc.settings().enforcing is False
    assert oidc.settings().declared is False


#: A plausible value for each required variable, so a test can set "all but one".
PLAUSIBLE = {
    "OIDC_ISSUER": "https://em.localhost:8443/auth/realms/em-dev",
    "OIDC_CLIENT_ID": "em-console",
    "OIDC_AUDIENCE": "em-server",
}


def test_every_required_variable_has_a_value_to_test_with():
    """The guard on the two tests below.

    If `REQUIRED_VARIABLES` grows a name `PLAUSIBLE` has no value for, those
    tests would silently stop covering it — a parametrized test that skips the
    new case is the quietest way to lose a rule.
    """
    absent = [name for name in REQUIRED_VARIABLES if name not in PLAUSIBLE]
    assert not absent, (
        f"add a plausible value for {absent} to PLAUSIBLE in this file")


@pytest.mark.parametrize("missing", REQUIRED_VARIABLES)
def test_one_variable_missing_is_a_refusal_that_names_it(oidc, monkeypatch,
                                                         missing):
    """Half-configured authentication refuses, and says which piece is absent.

    `OIDC_JWKS_URI` is not among the required names because it is DERIVED from
    the issuer, which is the whole point of that derivation. Neither is
    `OIDC_AUDIENCE`: nothing in the module reads it — see
    `test_the_id_token_audience_is_the_client_not_a_resource`.
    """
    complete = {name: PLAUSIBLE[name] for name in REQUIRED_VARIABLES}
    for name, value in complete.items():
        if name != missing:
            monkeypatch.setenv(name, value)

    problem = oidc.configuration_error()
    assert problem, f"{missing} absent and the application starts anyway"
    assert missing in problem, (
        f"the refusal does not name {missing}, so whoever reads it has to "
        f"guess: {problem!r}")
    # …and it must not blame a variable that IS set.
    for name in complete:
        if name != missing:
            assert f"{name} missing" not in problem
            assert not re.search(rf"missing.*\b{name}\b", problem)


def test_all_of_them_set_opens_the_door(oidc, monkeypatch):
    for name in REQUIRED_VARIABLES:
        monkeypatch.setenv(name, PLAUSIBLE[name])
    assert oidc.configuration_error() is None
    it = oidc.settings()
    assert it.enforcing
    # the JWKS URI derived from the issuer, and the three endpoints from those
    assert it.jwks_uri.endswith("/protocol/openid-connect/certs")
    assert it.authorization_endpoint.startswith(it.issuer)
    assert it.token_endpoint.endswith("/protocol/openid-connect/token")
    assert it.userinfo_endpoint.endswith("/protocol/openid-connect/userinfo")
    # the browser is sent to the PUBLIC issuer; the server dials the INTERNAL one
    assert it.authorization_endpoint.startswith(it.issuer)


def test_a_stale_audience_alone_does_not_refuse_a_boot(oidc, monkeypatch):
    """A variable nothing reads must not be able to stop the application.

    `OIDC_AUDIENCE` left over in an environment — from a copied compose file,
    from the other services in this stack — means nothing here. If it counted
    as «OIDC was asked for», it would refuse a boot in the name of a variable
    with no reader.
    """
    monkeypatch.setenv("OIDC_AUDIENCE", "em-server")
    assert oidc.configuration_error() is None
    assert oidc.settings().enforcing is False


def test_the_id_token_audience_is_the_client_not_a_resource(oidc):
    """The bug the first live sign-in found, pinned so it cannot come back.

    An id_token's `aud` is the client that requested it (OpenID Connect Core).
    `em-server` is the audience of the ACCESS token, which is what
    stratigraph-server validates and what the realm's audience mapper writes —
    with `id.token.claim = false`. Checking the id_token against a resource
    audience refuses every good token with «Invalid audience», which is exactly
    what happened.
    """
    code = _code_without_prose(Path(oidc.__file__))
    assert "audience = it . client_id" in code, (
        "the id_token's audience must be verified against OIDC_CLIENT_ID; "
        "checking it against a resource audience refuses every valid token")
    assert "it . audience" not in code, (
        "nothing in this module may read an OIDC_AUDIENCE: an id_token is not "
        "addressed to a resource server")


def test_userinfo_is_only_trusted_when_the_subject_matches(oidc):
    """The claim that fills in for the id_token needs binding to it.

    `/userinfo` is a document arriving from the network. Without comparing
    `sub`, attaching its `orcid` to this id_token's identity would be trusting
    two answers to be about the same person because they arrived together.
    """
    code = _code_without_prose(Path(oidc.__file__))
    assert "userinfo" in code, "the /userinfo fallback is gone"
    subject_check = re.search(
        r'compare_digest \( str \( info \. get \( "sub".*?claims \. get \( "sub"',
        code, re.S)
    assert subject_check, (
        "the /userinfo answer's `sub` is not compared with the id_token's")


def test_a_jwks_uri_of_the_wrong_shape_is_refused(oidc, monkeypatch):
    """Because the token endpoint is DERIVED from it.

    A URI of another shape would send the code exchange to an address nobody
    chose, which is worse than not starting.
    """
    monkeypatch.setenv("OIDC_ISSUER",
                       "https://em.localhost:8443/auth/realms/em-dev")
    monkeypatch.setenv("OIDC_AUDIENCE", "em-server")
    monkeypatch.setenv("OIDC_CLIENT_ID", "em-console")
    monkeypatch.setenv("OIDC_JWKS_URI", "http://keycloak:8080/whatever")
    problem = oidc.configuration_error()
    assert problem and "OIDC_JWKS_URI" in problem


# ── and the password that cannot be presented ────────────────────────────────

def test_an_oidc_only_account_has_no_password_anybody_can_type(oidc):
    """The measurement that chose this over a sentinel string.

    `utils/auth.py` falls back to comparing PLAIN TEXT when the stored hash is
    not one passlib recognises — a concession to PyArchInit's own sync. So a
    sentinel like `!oidc-only!` stored as the hash would verify against itself,
    and typing the sentinel would be a login. This asserts the property that
    made the difference, not the implementation.
    """
    from pyarchinit_mini.utils.auth import verify_password

    stored = oidc._unverifiable_password()

    # the property: nothing verifies, INCLUDING the stored value itself, which
    # is what a sentinel would have failed
    for probe in ("", "!oidc-only!", "oidc", "admin", "password", stored,
                  stored[:29]):
        assert verify_password(probe, stored) is False, (
            f"{probe!r} verifies against an OIDC-only account's stored "
            f"password — that is a login bypass")

    # …and two accounts do not share it
    assert stored != oidc._unverifiable_password()

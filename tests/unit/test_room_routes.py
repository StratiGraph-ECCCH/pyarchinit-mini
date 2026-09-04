"""The two routes, the menu entry, and the bearer falling with the session.

These need an application, so they build one — and building one is itself part
of what is asserted: with no `STRATIGRAPH_*` variables the blueprint is not
registered, the two URLs are a 404 and the template flag is undefined.

MEASURED on the running container, 4 September 2026:

    senza le variabili : 277 rotte, nessuna /stratigraph/*
    con le variabili   : 279 rotte, ['/stratigraph/', '/stratigraph/deliver']

Two more routes and not one more. The tests below hold that.
"""

from __future__ import annotations

import contextlib
import io

import pytest

from pyarchinit_mini.web_interface import oidc_tokens, room_client

ORCID = "0000-0002-1825-0097"


def build(monkeypatch, *, room=True):
    """An application, quietly. `create_app` prints a great deal at boot."""
    if room:
        monkeypatch.setenv(room_client.SERVER_URL_VARIABLE,
                           "http://stratigraph-server:8000")
        monkeypatch.setenv(room_client.ROOM_ID_VARIABLE, "una-stanza")
    else:
        monkeypatch.delenv(room_client.SERVER_URL_VARIABLE, raising=False)
        monkeypatch.delenv(room_client.ROOM_ID_VARIABLE, raising=False)

    from pyarchinit_mini.web_interface.app import create_app

    with contextlib.redirect_stdout(io.StringIO()):
        made = create_app()
    app = made[0] if isinstance(made, tuple) else made
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def an_orcid_user(app) -> str:
    """An account carrying an iD, CREATED rather than assumed.

    A fresh database holds exactly one user — `admin`, with no ORCID; measured
    in a clean container. Two tests first borrowed a `dev-user` that exists only
    in the developer's own volume, and both failed the same way and for a reason
    that had nothing to do with what they were testing: `load_user` returned
    nothing, `@login_required` redirected to the login page, and the assertions
    were made against that page. A test that depends on somebody's local data is
    a test that measures the machine it runs on.
    """
    from pyarchinit_mini.models.user import User as UserModel, UserRole
    from pyarchinit_mini.utils.auth import hash_password

    connection = app.user_service.db_manager.connection
    with connection.get_session() as db:
        row = db.query(UserModel).filter(UserModel.orcid == ORCID).first()
        if row is None:
            row = UserModel(username="con-orcid", email="con-orcid@example.invalid",
                            full_name="Con ORCID",
                            hashed_password=hash_password("non-usata-mai"),
                            role=UserRole.VIEWER, is_active=True,
                            is_superuser=False, orcid=ORCID)
            db.add(row)
            db.commit()
            db.refresh(row)
        return str(row.id)


# ── 1 · absent means the feature does not exist ──────────────────────────────

def test_without_the_variables_the_routes_do_not_exist(monkeypatch):
    app = build(monkeypatch, room=False)
    paths = {str(r) for r in app.url_map.iter_rules()}
    assert not [p for p in paths if p.startswith("/stratigraph")]
    assert "stratigraph_room" not in app.blueprints

    client = app.test_client()
    assert client.get("/stratigraph/").status_code == 404
    assert client.post("/stratigraph/deliver").status_code == 404


def test_without_the_variables_no_template_sees_the_flag(monkeypatch):
    """Not «false»: UNDEFINED, so the menu entry cannot render at all."""
    app = build(monkeypatch, room=False)
    with app.test_request_context("/"):
        from flask import render_template_string
        assert render_template_string(
            "{{ stratigraph_room is defined }}") == "False"


def test_with_the_variables_exactly_two_routes_appear(monkeypatch):
    app = build(monkeypatch)
    paths = sorted(p for p in (str(r) for r in app.url_map.iter_rules())
                   if p.startswith("/stratigraph"))
    assert paths == ["/stratigraph/", "/stratigraph/deliver"]
    with app.test_request_context("/"):
        from flask import render_template_string
        assert render_template_string("{{ stratigraph_room }}") == "una-stanza"


# ── 2 · both routes need a login ─────────────────────────────────────────────

@pytest.mark.parametrize("method, path", [("get", "/stratigraph/"),
                                          ("post", "/stratigraph/deliver")])
def test_both_routes_refuse_an_anonymous_caller(monkeypatch, method, path):
    app = build(monkeypatch)
    answer = getattr(app.test_client(), method)(path)
    assert answer.status_code == 302
    assert "/auth/login" in answer.headers["Location"]


# ── 3 · THE BEARER FALLS WITH THE SESSION ────────────────────────────────────

def test_logging_out_drops_the_bearer_and_the_handle(monkeypatch):
    """`logout_user()` fires `user_logged_out`, and `oidc_tokens` listens.

    A SIGNAL and not an edit to `auth_routes.logout()`: that function is
    upstream's, and a line added there is a merge conflict for as long as this
    fork lives.

    BOTH halves are asserted. A handle removed from the cookie with the bearer
    left behind in the store is a token nothing can reach and nothing will
    clean up — a leak in the plainest sense.
    """
    app = build(monkeypatch)
    with oidc_tokens._LOCK:
        oidc_tokens._STORE.clear()

    handle = oidc_tokens.remember(
        {"access_token": "x" * 40, "expires_in": 900,
         "refresh_token": "y" * 40, "refresh_expires_in": 1800}, ORCID)

    client = app.test_client()
    with client.session_transaction() as s:
        s["_user_id"] = an_orcid_user(app)
        s["_fresh"] = True
        s[oidc_tokens.HANDLE_KEY] = handle

    assert oidc_tokens.held(handle)
    answer = client.get("/auth/logout")
    assert answer.status_code == 302

    assert not oidc_tokens.held(handle), (
        "the bearer survived a logout: it is now unreachable and uncollectable")
    with client.session_transaction() as s:
        assert oidc_tokens.HANDLE_KEY not in s


def test_that_logout_check_would_notice_a_missing_hook(monkeypatch):
    """A guard that cannot fire proves nothing.

    So the hook is disconnected and the same logout run again: the bearer must
    then SURVIVE. If it does not, the test above is passing for some other
    reason and is not testing the signal at all.
    """
    from flask_login import user_logged_out

    app = build(monkeypatch)
    with oidc_tokens._LOCK:
        oidc_tokens._STORE.clear()
    user_logged_out.disconnect(oidc_tokens._on_logout, app)
    try:
        handle = oidc_tokens.remember(
            {"access_token": "x" * 40, "expires_in": 900}, ORCID)
        client = app.test_client()
        with client.session_transaction() as s:
            s["_user_id"] = an_orcid_user(app)
            s["_fresh"] = True
            s[oidc_tokens.HANDLE_KEY] = handle
        client.get("/auth/logout")
        assert oidc_tokens.held(handle), (
            "the bearer disappeared with the hook DISCONNECTED, so the test "
            "above is not measuring the hook")
    finally:
        user_logged_out.connect(oidc_tokens._on_logout, app, weak=False)


def test_signing_in_drops_a_previous_session_s_bearer(monkeypatch):
    """ORCID, then out, then a LOCAL login in the same browser."""
    app = build(monkeypatch)
    with oidc_tokens._LOCK:
        oidc_tokens._STORE.clear()
    handle = oidc_tokens.remember(
        {"access_token": "x" * 40, "expires_in": 900}, ORCID)

    with app.test_request_context("/"):
        from flask import session
        from flask_login import login_user

        from pyarchinit_mini.web_interface.auth_routes import User

        session[oidc_tokens.HANDLE_KEY] = handle
        login_user(User(app.user_service.get_user_by_id(1)))   # admin, local
        assert oidc_tokens.HANDLE_KEY not in session
    assert not oidc_tokens.held(handle)


# ── 4 · no identity, no delivery, no traffic ─────────────────────────────────

def test_a_user_without_an_orcid_gets_the_contract_s_sentence(monkeypatch):
    """And nothing is sent: `urlopen` is a tripwire for the whole request."""
    app = build(monkeypatch)

    def explode(*_a, **_k):
        raise AssertionError("a network call was made")

    monkeypatch.setattr(room_client.urllib.request, "urlopen", explode)

    client = app.test_client()
    with client.session_transaction() as s:
        s["_user_id"] = "1"          # admin: no ORCID
        s["_fresh"] = True

    answer = client.post("/stratigraph/deliver",
                         data={"sito": "Scavo archeologico"},
                         follow_redirects=True)
    assert answer.status_code == 200
    assert room_client.NO_AUTHOR in answer.get_data(as_text=True)


def test_a_user_with_an_orcid_but_no_bearer_is_told_to_sign_in(monkeypatch):
    """The `-w 2` case and the restart case, as the person sees them."""
    app = build(monkeypatch)

    def explode(*_a, **_k):
        raise AssertionError("a network call was made")

    monkeypatch.setattr(room_client.urllib.request, "urlopen", explode)

    who = an_orcid_user(app)
    client = app.test_client()
    with client.session_transaction() as s:
        s["_user_id"] = who          # has an ORCID, holds no bearer
        s["_fresh"] = True

    answer = client.post("/stratigraph/deliver",
                         data={"sito": "Scavo archeologico"},
                         follow_redirects=True)
    page = answer.get_data(as_text=True)
    assert "ORCID" in page
    assert room_client.NO_AUTHOR not in page, (
        "an account that HAS an iD was refused as if it had none")

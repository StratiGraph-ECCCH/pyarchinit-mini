"""Integration tests for the fauna web routes (Fauna Record Type — Task 5).

Mirrors ``tests/struttura/test_struttura_routes.py`` (itself mirroring
``tests/tomba/test_tomba_routes.py``): the real route bodies live nested
inside app.py's monolithic ``create_app()`` factory, so invoking it directly
in a focused test is impractical. This builds a minimal Flask app, hand-copies
the migrated route bodies (kept in lockstep with app.py's fauna implementation,
``app.py`` "===== Fauna =====" block) and reuses the real ``auth_routes``
decorators (``login_required``/``write_permission_required``) and login
manager for authenticity, so a write-permission-gated POST is exercised the
same way it would be in production.

Unlike struttura/tomba, fauna has NO media — there is no
``/fauna/<id>/media/upload`` route and no media tab in the form template, so
this suite does not wire up MediaService/MediaHandler at all.

Covers the behaviors requested for Task 5:
  1. Authenticated GET /fauna -> 200
  2. POST /fauna/new with {sito, specie} -> redirect (302) and the record is
     retrievable via fauna_service
  3. GET /fauna/<id> -> 200, shows the specie (write-permission user)
  4. GET /api/fauna/thesaurus/specie -> 200 JSON list
  5. POST /fauna/<id>/delete -> record gone
  6. GET  /fauna/<id> as a VIEWER -> redirect, form not shown
  7. POST /fauna/<id> as a VIEWER -> redirect, record left unmutated
"""
import os

import pytest
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, login_user
from jinja2 import ChoiceLoader, FileSystemLoader

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.fauna_service import FaunaService
from pyarchinit_mini.web_interface.auth_routes import (
    init_login_manager, write_permission_required, User as AuthUser,
)

_HERE = os.path.dirname(__file__)
_APP_TEMPLATES = os.path.join(_HERE, "..", "..", "pyarchinit_mini", "web_interface", "templates")
_TEST_TEMPLATES = os.path.join(_HERE, "..", "templates")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "fauna_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def fauna_service(db_manager):
    return FaunaService(db_manager)


@pytest.fixture
def flask_app(db_manager, fauna_service, user_service):
    """Minimal Flask app mounting the migrated fauna routes.

    Route bodies below are hand-copied verbatim from pyarchinit_mini/web_interface/app.py
    (fauna_list, fauna_create, fauna_edit, fauna_delete, fauna_thesaurus) so
    this test exercises the same logic the real app registers, without
    paying for the full create_app() factory. There is deliberately NO
    media route here — fauna has no media.
    """
    app = Flask(
        __name__,
        template_folder=_APP_TEMPLATES,
        static_folder=os.path.join(_HERE, "..", "..", "pyarchinit_mini", "web_interface", "static"),
    )
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["WTF_CSRF_ENABLED"] = False
    app.db_manager = db_manager
    app.fauna_service = fauna_service

    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(os.path.abspath(_TEST_TEMPLATES)),
        FileSystemLoader(os.path.abspath(_APP_TEMPLATES)),
    ])
    app.jinja_env.globals.setdefault("get_locale", lambda: "it")
    app.jinja_env.globals.setdefault("_", lambda s: s)
    app.jinja_env.globals.setdefault("csrf_token", lambda: "test-csrf-token")

    init_login_manager(app, user_service)

    @app.route("/")
    def index():
        return ""

    # Test-only helper to establish a real flask-login session (mirrors what
    # the real /auth/login route does after password verification).
    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    # Stub SP4 export endpoints (app.py "SP4 export helpers" block) — only
    # needed here so fauna/list.html's export button url_for() calls
    # resolve; the export behavior itself is covered by
    # tests/fauna/test_fauna_export_routes.py.
    @app.route('/export/fauna/excel')
    @login_required
    def export_fauna_excel():
        return ""

    @app.route('/export/fauna/csv')
    @login_required
    def export_fauna_csv():
        return ""

    @app.route('/export/fauna/pdf')
    @login_required
    def export_fauna_pdf():
        return ""

    # ---- /fauna (mirrors app.py's fauna_list) ----
    @app.route('/fauna')
    @login_required
    def fauna_list():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        sito_filter = request.args.get('sito', '').strip()
        try:
            fauna_list_data = fauna_service.list_fauna(page=page, size=per_page,
                                                         search=search, sito=sito_filter)
            total = fauna_service.count_fauna(search=search, sito=sito_filter)
            sites = fauna_service.get_distinct_sites()
            import math
            total_pages = max(math.ceil(total / per_page), 1)
            return render_template('fauna/list.html', fauna_list=fauna_list_data,
                                   total=total, page=page, total_pages=total_pages,
                                   search=search, sito_filter=sito_filter, sites=sites)
        except Exception as e:
            flash(f'Errore Fauna: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ---- /fauna/new (mirrors app.py's fauna_create) ----
    @app.route('/fauna/new', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def fauna_create():
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            fauna_id = fauna_service.create_fauna(data)
            if fauna_id:
                flash('Fauna creata', 'success')
                return redirect(url_for('fauna_edit', fauna_id=fauna_id))
            flash('Errore creazione Fauna', 'error')
        return render_template('fauna/form.html', fauna={})

    # ---- /fauna/<id> (mirrors app.py's fauna_edit) ----
    @app.route('/fauna/<int:fauna_id>', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def fauna_edit(fauna_id):
        fauna = fauna_service.get_fauna(fauna_id)
        if not fauna:
            flash('Fauna non trovata', 'error')
            return redirect(url_for('fauna_list'))
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            if fauna_service.update_fauna(fauna_id, data):
                flash('Fauna aggiornata', 'success')
            else:
                flash('Errore aggiornamento', 'error')
            return redirect(url_for('fauna_edit', fauna_id=fauna_id))
        return render_template('fauna/form.html', fauna=fauna)

    # ---- /fauna/<id>/delete (mirrors app.py's fauna_delete) ----
    @app.route('/fauna/<int:fauna_id>/delete', methods=['POST'])
    @login_required
    @write_permission_required
    def fauna_delete(fauna_id):
        if fauna_service.delete_fauna(fauna_id):
            flash('Fauna eliminata', 'success')
        else:
            flash('Errore eliminazione', 'error')
        return redirect(url_for('fauna_list'))

    # ---- /api/fauna/thesaurus/<field> (mirrors app.py's fauna_thesaurus) ----
    @app.route('/api/fauna/thesaurus/<field>')
    @login_required
    def fauna_thesaurus(field):
        try:
            values = fauna_service.get_thesaurus_values(field)
            return jsonify(values)
        except Exception as e:
            return jsonify({'error': str(e), 'values': []}), 500

    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def write_user(user_service):
    """An OPERATOR-role user (has write/create permission)."""
    user = user_service.create_user(
        username="operator1", email="operator1@example.com", password="secret123",
        full_name="Operator One", role=UserRole.OPERATOR,
    )
    return user  # dict — see UserService.create_user / _user_to_dict


@pytest.fixture
def logged_in_client(client, write_user):
    """Test client with a real flask-login session for a write-permission user."""
    r = client.get(f"/_test/login/{write_user['id']}")
    assert r.status_code == 200
    return client


@pytest.fixture
def viewer_user(user_service):
    """A VIEWER-role user (read-only, no write/create permission)."""
    user = user_service.create_user(
        username="viewer1", email="viewer1@example.com", password="secret123",
        full_name="Viewer One", role=UserRole.VIEWER,
    )
    return user  # dict — see UserService.create_user / _user_to_dict


@pytest.fixture
def viewer_client(client, viewer_user):
    """Test client with a real flask-login session for a no-write-permission user."""
    r = client.get(f"/_test/login/{viewer_user['id']}")
    assert r.status_code == 200
    return client


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_list_page_returns_200(logged_in_client):
    r = logged_in_client.get("/fauna")
    assert r.status_code == 200


def test_create_post_inserts_record_retrievable_via_service(logged_in_client, fauna_service):
    r = logged_in_client.post(
        "/fauna/new",
        data={"sito": "Volterra", "specie": "Bos taurus"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = fauna_service.list_fauna()
    assert len(items) == 1
    assert items[0]["sito"] == "Volterra"
    assert items[0]["specie"] == "Bos taurus"


def test_edit_page_shows_specie(logged_in_client, fauna_service):
    """The flat specie column is deprecated (the classic plugin always
    writes it empty and stores species in specie_psi instead), so the form
    no longer renders a flat specie input — the edit page must instead
    surface the stored specie_psi JSON for the repeatable-row widget to
    render client-side (via the window.SPECIE_PSI script variable)."""
    fid = fauna_service.create_fauna({
        "sito": "Volterra",
        "specie_psi": '[["Ovis aries","omero"]]',
    })
    r = logged_in_client.get(f"/fauna/{fid}")
    assert r.status_code == 200
    assert b"Ovis aries" in r.data


def test_edit_post_by_viewer_is_denied_and_does_not_mutate(viewer_client, fauna_service):
    """A VIEWER (no write permission) must not be able to mutate a fauna record
    via POST /fauna/<id> — write_permission_required should redirect the
    request away before fauna_service.update_fauna() is ever called."""
    fid = fauna_service.create_fauna({"sito": "Volterra", "specie": "Ovis aries"})
    r = viewer_client.post(
        f"/fauna/{fid}",
        data={"sito": "Volterra", "specie": "Bos taurus"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    # The record must be unchanged - the write attempt was blocked, not applied.
    assert fauna_service.get_fauna(fid)["specie"] == "Ovis aries"


def test_edit_get_by_viewer_is_denied(viewer_client, fauna_service):
    """GET /fauna/<id> is gated the same way as struttura_edit/tomba_edit in
    app.py: @write_permission_required sits on the whole view, so a VIEWER is
    redirected away even for read access to the edit form."""
    fid = fauna_service.create_fauna({"sito": "Volterra", "specie": "Ovis aries"})
    r = viewer_client.get(f"/fauna/{fid}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_thesaurus_api_returns_200_json_list(logged_in_client):
    r = logged_in_client.get("/api/fauna/thesaurus/specie")
    assert r.status_code == 200
    values = r.get_json()
    assert isinstance(values, list)


def test_delete_removes_record(logged_in_client, fauna_service):
    fid = fauna_service.create_fauna({"sito": "Volterra", "specie": "Bos taurus"})
    r = logged_in_client.post(f"/fauna/{fid}/delete", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert fauna_service.get_fauna(fid) is None


def test_no_media_upload_route_exists(flask_app):
    """Fauna has no media — confirm the route the URL map would need for a
    media upload endpoint was never registered."""
    rules = {r.rule for r in flask_app.url_map.iter_rules()}
    assert not any('/media/upload' in r for r in rules if r.startswith('/fauna'))


def test_create_post_specie_psi_json_round_trips(logged_in_client, fauna_service):
    """POST /fauna/new with a specie_psi JSON string (as the form's hidden
    input would send it) must round-trip through FaunaService's
    plugin-format normalization — same shape the classic pyarchinit_fauna
    plugin writes: a list of [specie, psi] string pairs."""
    import json
    r = logged_in_client.post(
        "/fauna/new",
        data={"sito": "Volterra", "specie_psi": '[["x","y"]]'},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = fauna_service.list_fauna()
    assert len(items) == 1
    assert json.loads(items[0]["specie_psi"]) == [["x", "y"]]

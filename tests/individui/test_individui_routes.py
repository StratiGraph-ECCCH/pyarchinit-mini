"""Integration tests for the individui web routes (Individui Record Type — Task 5).

Mirrors ``tests/fauna/test_fauna_routes.py``: the real route bodies live nested
inside app.py's monolithic ``create_app()`` factory, so invoking it directly
in a focused test is impractical. This builds a minimal Flask app, hand-copies
the migrated route bodies (kept in lockstep with app.py's individui
implementation, ``app.py`` "===== Individui =====" block) and reuses the real
``auth_routes`` decorators (``login_required``/``write_permission_required``)
and login manager for authenticity, so a write-permission-gated POST is
exercised the same way it would be in production.

Like fauna, individui has NO media — there is no
``/individui/<id>/media/upload`` route and no media tab in the form template,
so this suite does not wire up MediaService/MediaHandler at all.

Covers the behaviors requested for Task 5:
  1. Authenticated GET /individui -> 200
  2. POST /individui/new with {sito, nr_individuo, sesso} -> redirect (302) and
     the record is retrievable via individui_service
  3. GET /individui/<id> -> 200, shows the sesso (write-permission user)
  4. GET /api/individui/thesaurus/posizione_cranio -> 200 JSON list
  5. POST /individui/<id>/delete -> record gone
  6. GET  /individui/<id> as a VIEWER -> redirect, form not shown
  7. POST /individui/<id> as a VIEWER -> redirect, record left unmutated
  8. No /individui/<id>/media/upload rule registered in the URL map
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
from pyarchinit_mini.services.individui_service import IndividuiService
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
    db = tmp_path / "individui_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def individui_service(db_manager):
    return IndividuiService(db_manager)


@pytest.fixture
def flask_app(db_manager, individui_service, user_service):
    """Minimal Flask app mounting the migrated individui routes.

    Route bodies below are hand-copied verbatim from
    pyarchinit_mini/web_interface/app.py (individui_list, individui_create,
    individui_edit, individui_delete, individui_thesaurus) so this test
    exercises the same logic the real app registers, without paying for the
    full create_app() factory. There is deliberately NO media route here —
    individui has no media.
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
    app.individui_service = individui_service

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

    # Stub export endpoints (app.py "Individui export" block) — only needed
    # here so individui/list.html's export button url_for() calls resolve;
    # the export behavior itself is covered by
    # tests/individui/test_individui_export_routes.py.
    @app.route('/export/individui/excel')
    @login_required
    def export_individui_excel():
        return ""

    @app.route('/export/individui/csv')
    @login_required
    def export_individui_csv():
        return ""

    @app.route('/export/individui/pdf')
    @login_required
    def export_individui_pdf():
        return ""

    # ---- /individui (mirrors app.py's individui_list) ----
    @app.route('/individui')
    @login_required
    def individui_list():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        sito_filter = request.args.get('sito', '').strip()
        try:
            individui_list_data = individui_service.list_individui(page=page, size=per_page,
                                                                     search=search, sito=sito_filter)
            total = individui_service.count_individui(search=search, sito=sito_filter)
            sites = individui_service.get_distinct_sites()
            import math
            total_pages = max(math.ceil(total / per_page), 1)
            return render_template('individui/list.html', individui_list=individui_list_data,
                                   total=total, page=page, total_pages=total_pages,
                                   search=search, sito_filter=sito_filter, sites=sites)
        except Exception as e:
            flash(f'Errore Individui: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ---- /individui/new (mirrors app.py's individui_create) ----
    @app.route('/individui/new', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def individui_create():
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            individui_id = individui_service.create_individui(data)
            if individui_id:
                flash('Individuo creato', 'success')
                return redirect(url_for('individui_edit', individui_id=individui_id))
            flash('Errore creazione Individuo', 'error')
        return render_template('individui/form.html', individui={})

    # ---- /individui/<id> (mirrors app.py's individui_edit) ----
    @app.route('/individui/<int:individui_id>', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def individui_edit(individui_id):
        individui = individui_service.get_individui(individui_id)
        if not individui:
            flash('Individuo non trovato', 'error')
            return redirect(url_for('individui_list'))
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            if individui_service.update_individui(individui_id, data):
                flash('Individuo aggiornato', 'success')
            else:
                flash('Errore aggiornamento', 'error')
            return redirect(url_for('individui_edit', individui_id=individui_id))
        return render_template('individui/form.html', individui=individui)

    # ---- /individui/<id>/delete (mirrors app.py's individui_delete) ----
    @app.route('/individui/<int:individui_id>/delete', methods=['POST'])
    @login_required
    @write_permission_required
    def individui_delete(individui_id):
        if individui_service.delete_individui(individui_id):
            flash('Individuo eliminato', 'success')
        else:
            flash('Errore eliminazione', 'error')
        return redirect(url_for('individui_list'))

    # ---- /api/individui/thesaurus/<field> (mirrors app.py's individui_thesaurus) ----
    @app.route('/api/individui/thesaurus/<field>')
    @login_required
    def individui_thesaurus(field):
        try:
            values = individui_service.get_thesaurus_values(field)
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
    r = logged_in_client.get("/individui")
    assert r.status_code == 200


def test_create_post_inserts_record_retrievable_via_service(logged_in_client, individui_service):
    r = logged_in_client.post(
        "/individui/new",
        data={"sito": "Volterra", "nr_individuo": "1", "sesso": "Maschio"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = individui_service.list_individui()
    assert len(items) == 1
    assert items[0]["sito"] == "Volterra"
    assert items[0]["nr_individuo"] == 1
    assert items[0]["sesso"] == "Maschio"


def test_edit_page_shows_sesso(logged_in_client, individui_service):
    iid = individui_service.create_individui({
        "sito": "Volterra", "nr_individuo": 1, "sesso": "Femmina",
    })
    r = logged_in_client.get(f"/individui/{iid}")
    assert r.status_code == 200
    assert b"Femmina" in r.data


def test_edit_post_by_viewer_is_denied_and_does_not_mutate(viewer_client, individui_service):
    """A VIEWER (no write permission) must not be able to mutate an individui
    record via POST /individui/<id> — write_permission_required should
    redirect the request away before individui_service.update_individui() is
    ever called."""
    iid = individui_service.create_individui({"sito": "Volterra", "nr_individuo": 1, "sesso": "Maschio"})
    r = viewer_client.post(
        f"/individui/{iid}",
        data={"sito": "Volterra", "nr_individuo": "1", "sesso": "Femmina"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    # The record must be unchanged - the write attempt was blocked, not applied.
    assert individui_service.get_individui(iid)["sesso"] == "Maschio"


def test_edit_get_by_viewer_is_denied(viewer_client, individui_service):
    """GET /individui/<id> is gated the same way as fauna_edit in app.py:
    @write_permission_required sits on the whole view, so a VIEWER is
    redirected away even for read access to the edit form."""
    iid = individui_service.create_individui({"sito": "Volterra", "nr_individuo": 1, "sesso": "Maschio"})
    r = viewer_client.get(f"/individui/{iid}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_thesaurus_api_returns_200_json_list(logged_in_client):
    r = logged_in_client.get("/api/individui/thesaurus/posizione_cranio")
    assert r.status_code == 200
    values = r.get_json()
    assert isinstance(values, list)


def test_delete_removes_record(logged_in_client, individui_service):
    iid = individui_service.create_individui({"sito": "Volterra", "nr_individuo": 1, "sesso": "Maschio"})
    r = logged_in_client.post(f"/individui/{iid}/delete", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert individui_service.get_individui(iid) is None


def test_no_media_upload_route_exists(flask_app):
    """Individui has no media — confirm the route the URL map would need for
    a media upload endpoint was never registered."""
    rules = {r.rule for r in flask_app.url_map.iter_rules()}
    assert not any('/media/upload' in r for r in rules if r.startswith('/individui'))

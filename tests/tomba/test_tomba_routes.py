"""Integration tests for the tomba (burial) web routes (SP2 Task 5).

The real route bodies live nested inside app.py's monolithic ``create_app()``
factory (~5000+ lines, starts a backup-scheduler thread, writes to the real
``~/.pyarchinit_mini`` via ConnectionManager, imports many blueprints...), so
invoking it directly in a focused test is impractical — this mirrors the
established pattern already used by ``tests/media/test_web_media_routes.py``:
build a minimal Flask app, hand-copy the migrated route bodies (kept in
lockstep with app.py's tomba implementation, ``app.py`` "===== Tomba -
Sepolture =====" block) and reuse the real ``auth_routes`` decorators
(``login_required``/``write_permission_required``) and login manager for
authenticity, so a write-permission-gated POST is exercised the same way it
would be in production.

Covers the behaviors requested for Task 5:
  1. Authenticated GET /tomba -> 200
  2. POST /tomba/new with {sito, rito} -> redirect (302) and the record is
     retrievable via tomba_service
  3. GET /tomba/<id> -> 200, shows the rito
  4. GET /api/tomba/thesaurus/rito -> 200 JSON list
  5. POST /tomba/<id>/delete -> record gone

Not covered (documented, not asserted): media upload end-to-end (already
covered generically for the 'tomba' entity_map key by
tests/media/test_web_media_routes.py's upload/list/serve/delete flow for
'us'; a tomba-specific repeat would just re-exercise the same MediaHandler
code path with a different entity_type string) and unauthenticated/
non-write-permission 403 behavior (write_permission_required's exact
rejection semantics are already unit/integration-tested elsewhere, e.g.
tests/media/test_web_media_routes.py and auth_routes tests).
"""
import os
import tempfile

import pytest
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, login_user
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.utils import secure_filename

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.media_service import MediaService
from pyarchinit_mini.services.tomba_service import TombaService
from pyarchinit_mini.media_manager.media_handler import MediaHandler
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
    db = tmp_path / "tomba_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def media_handler(tmp_path):
    return MediaHandler(
        media_root=str(tmp_path / "media"),
        thumb_path=str(tmp_path / "media" / "thumb"),
        thumb_resize=str(tmp_path / "media" / "thumb_resize"),
    )


@pytest.fixture
def media_service(db_manager, media_handler):
    return MediaService(db_manager, media_handler)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def tomba_service(db_manager):
    return TombaService(db_manager)


@pytest.fixture
def flask_app(db_manager, media_service, tomba_service, user_service):
    """Minimal Flask app mounting the migrated tomba routes.

    Route bodies below are hand-copied verbatim from pyarchinit_mini/web_interface/app.py
    (tomba_list, tomba_create, tomba_edit, tomba_delete, tomba_media_upload,
    tomba_thesaurus) so this test exercises the same logic the real app
    registers, without paying for the full create_app() factory.
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
    app.media_service = media_service
    app.tomba_service = tomba_service

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

    def _media_gallery(entity_key, id_entity):
        items = media_service.get_media_for_entity(entity_key, id_entity)
        return [{
            'id_media': m.id_media,
            'media_name': m.filename,
            'media_type': m.mediatype,
            'description': m.descrizione,
            'filepath': m.filepath,
            'url': media_service.public_url(m.filepath),
            'thumb_url': media_service.thumb_url(m.id_media),
        } for m in items]

    # ---- /tomba (mirrors app.py's tomba_list) ----
    @app.route('/tomba')
    @login_required
    def tomba_list():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        sito_filter = request.args.get('sito', '').strip()
        try:
            tomba_list_data = tomba_service.list_tomba(page=page, size=per_page,
                                                        search=search, sito=sito_filter)
            total = tomba_service.count_tomba(search=search, sito=sito_filter)
            sites = tomba_service.get_distinct_sites()
            import math
            total_pages = max(math.ceil(total / per_page), 1)
            return render_template('tomba/list.html', tomba_list=tomba_list_data,
                                   total=total, page=page, total_pages=total_pages,
                                   search=search, sito_filter=sito_filter, sites=sites)
        except Exception as e:
            flash(f'Errore Tomba: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ---- /tomba/new (mirrors app.py's tomba_create) ----
    @app.route('/tomba/new', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def tomba_create():
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            tomba_id = tomba_service.create_tomba(data)
            if tomba_id:
                flash('Tomba creata', 'success')
                return redirect(url_for('tomba_edit', tomba_id=tomba_id))
            flash('Errore creazione Tomba', 'error')
        return render_template('tomba/form.html', tomba={}, media=[])

    # ---- /tomba/<id> (mirrors app.py's tomba_edit) ----
    @app.route('/tomba/<int:tomba_id>', methods=['GET', 'POST'])
    @login_required
    def tomba_edit(tomba_id):
        tomba = tomba_service.get_tomba(tomba_id)
        if not tomba:
            flash('Tomba non trovata', 'error')
            return redirect(url_for('tomba_list'))
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            if tomba_service.update_tomba(tomba_id, data):
                flash('Tomba aggiornata', 'success')
            else:
                flash('Errore aggiornamento', 'error')
            return redirect(url_for('tomba_edit', tomba_id=tomba_id))
        media_items = []
        try:
            media_items = _media_gallery('tomba', tomba_id)
        except Exception:
            pass
        return render_template('tomba/form.html', tomba=tomba, media=media_items)

    # ---- /tomba/<id>/delete (mirrors app.py's tomba_delete) ----
    @app.route('/tomba/<int:tomba_id>/delete', methods=['POST'])
    @login_required
    @write_permission_required
    def tomba_delete(tomba_id):
        if tomba_service.delete_tomba(tomba_id):
            flash('Tomba eliminata', 'success')
        else:
            flash('Errore eliminazione', 'error')
        return redirect(url_for('tomba_list'))

    # ---- /tomba/<id>/media/upload (mirrors app.py's tomba_media_upload) ----
    @app.route('/tomba/<int:tomba_id>/media/upload', methods=['POST'])
    @login_required
    @write_permission_required
    def tomba_media_upload(tomba_id):
        try:
            f = request.files.get('file')
            if not f or not f.filename:
                flash('Nessun file', 'error')
                return redirect(url_for('tomba_edit', tomba_id=tomba_id))
            filename = secure_filename(f.filename)
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            f.save(tmp_path)
            media_service.add_media(tmp_path, 'tomba', tomba_id)
            flash('Media caricato', 'success')
            os.unlink(tmp_path)
        except Exception as e:
            flash(f'Errore upload: {e}', 'error')
        return redirect(url_for('tomba_edit', tomba_id=tomba_id))

    # ---- /api/tomba/thesaurus/<field> (mirrors app.py's tomba_thesaurus) ----
    @app.route('/api/tomba/thesaurus/<field>')
    @login_required
    def tomba_thesaurus(field):
        try:
            values = tomba_service.get_thesaurus_values(field)
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


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_list_page_returns_200(logged_in_client):
    r = logged_in_client.get("/tomba")
    assert r.status_code == 200


def test_create_post_inserts_record_retrievable_via_service(logged_in_client, tomba_service):
    r = logged_in_client.post(
        "/tomba/new",
        data={"sito": "Volterra", "rito": "Inumazione"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = tomba_service.list_tomba()
    assert len(items) == 1
    assert items[0]["sito"] == "Volterra"
    assert items[0]["rito"] == "Inumazione"


def test_edit_page_shows_rito(logged_in_client, tomba_service):
    tid = tomba_service.create_tomba({"sito": "Volterra", "rito": "Cremazione"})
    r = logged_in_client.get(f"/tomba/{tid}")
    assert r.status_code == 200
    assert b"Cremazione" in r.data


def test_thesaurus_api_returns_200_json_list(logged_in_client):
    r = logged_in_client.get("/api/tomba/thesaurus/rito")
    assert r.status_code == 200
    values = r.get_json()
    assert isinstance(values, list)


def test_delete_removes_record(logged_in_client, tomba_service):
    tid = tomba_service.create_tomba({"sito": "Volterra", "rito": "Inumazione"})
    r = logged_in_client.post(f"/tomba/{tid}/delete", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert tomba_service.get_tomba(tid) is None

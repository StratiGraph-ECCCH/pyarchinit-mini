"""Integration tests for the struttura web routes (SP2 Task 5).

The real route bodies live nested inside app.py's monolithic ``create_app()``
factory (~5000+ lines, starts a backup-scheduler thread, writes to the real
``~/.pyarchinit_mini`` via ConnectionManager, imports many blueprints...), so
invoking it directly in a focused test is impractical — this mirrors the
established pattern already used by ``tests/tomba/test_tomba_routes.py``:
build a minimal Flask app, hand-copy the migrated route bodies (kept in
lockstep with app.py's struttura implementation, ``app.py`` "===== Struttura
=====" block) and reuse the real ``auth_routes`` decorators
(``login_required``/``write_permission_required``) and login manager for
authenticity, so a write-permission-gated POST is exercised the same way it
would be in production.

Covers the behaviors requested for Task 5:
  1. Authenticated GET /struttura -> 200
  2. POST /struttura/new with {sito, categoria_struttura} -> redirect (302)
     and the record is retrievable via struttura_service
  3. GET /struttura/<id> -> 200, shows the categoria (write-permission user)
  4. GET /api/struttura/thesaurus/categoria_struttura -> 200 JSON list
  5. POST /struttura/<id>/delete -> record gone

Mirrors tomba's write-permission convention: struttura_edit (GET/POST
/struttura/<id>) is gated with @write_permission_required on the whole
view, so a VIEWER (no write permission) is redirected away for both the GET
(edit form) and the POST (mutation) branch:
  6. GET  /struttura/<id> as a VIEWER -> redirect, form not shown
  7. POST /struttura/<id> as a VIEWER -> redirect, record left unmutated

Not covered (documented, not asserted): media upload end-to-end (already
covered generically for entity_map keys by
tests/media/test_web_media_routes.py's upload/list/serve/delete flow; a
struttura-specific repeat would just re-exercise the same MediaHandler code
path with a different entity_type string) and non-write-permission behavior
on struttura_create/struttura_delete/struttura_media_upload specifically
(write_permission_required's rejection semantics are already exercised
above for struttura_edit and elsewhere).
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
from pyarchinit_mini.services.struttura_service import StrutturaService
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
    db = tmp_path / "struttura_routes.db"
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
def struttura_service(db_manager):
    return StrutturaService(db_manager)


@pytest.fixture
def flask_app(db_manager, media_service, struttura_service, user_service):
    """Minimal Flask app mounting the migrated struttura routes.

    Route bodies below are hand-copied verbatim from pyarchinit_mini/web_interface/app.py
    (struttura_list, struttura_create, struttura_edit, struttura_delete,
    struttura_media_upload, struttura_thesaurus) so this test exercises the
    same logic the real app registers, without paying for the full
    create_app() factory.
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
    app.struttura_service = struttura_service

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

    # ---- /struttura (mirrors app.py's struttura_list) ----
    @app.route('/struttura')
    @login_required
    def struttura_list():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        sito_filter = request.args.get('sito', '').strip()
        try:
            struttura_list_data = struttura_service.list_struttura(page=page, size=per_page,
                                                                     search=search, sito=sito_filter)
            total = struttura_service.count_struttura(search=search, sito=sito_filter)
            sites = struttura_service.get_distinct_sites()
            import math
            total_pages = max(math.ceil(total / per_page), 1)
            return render_template('struttura/list.html', struttura_list=struttura_list_data,
                                   total=total, page=page, total_pages=total_pages,
                                   search=search, sito_filter=sito_filter, sites=sites)
        except Exception as e:
            flash(f'Errore Struttura: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ---- /struttura/new (mirrors app.py's struttura_create) ----
    @app.route('/struttura/new', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def struttura_create():
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            struttura_id = struttura_service.create_struttura(data)
            if struttura_id:
                flash('Struttura creata', 'success')
                return redirect(url_for('struttura_edit', struttura_id=struttura_id))
            flash('Errore creazione Struttura', 'error')
        return render_template('struttura/form.html', struttura={}, media=[])

    # ---- /struttura/<id> (mirrors app.py's struttura_edit) ----
    @app.route('/struttura/<int:struttura_id>', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def struttura_edit(struttura_id):
        struttura = struttura_service.get_struttura(struttura_id)
        if not struttura:
            flash('Struttura non trovata', 'error')
            return redirect(url_for('struttura_list'))
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            if struttura_service.update_struttura(struttura_id, data):
                flash('Struttura aggiornata', 'success')
            else:
                flash('Errore aggiornamento', 'error')
            return redirect(url_for('struttura_edit', struttura_id=struttura_id))
        media_items = []
        try:
            media_items = _media_gallery('struttura', struttura_id)
        except Exception:
            pass
        return render_template('struttura/form.html', struttura=struttura, media=media_items)

    # ---- /struttura/<id>/delete (mirrors app.py's struttura_delete) ----
    @app.route('/struttura/<int:struttura_id>/delete', methods=['POST'])
    @login_required
    @write_permission_required
    def struttura_delete(struttura_id):
        if struttura_service.delete_struttura(struttura_id):
            flash('Struttura eliminata', 'success')
        else:
            flash('Errore eliminazione', 'error')
        return redirect(url_for('struttura_list'))

    # ---- /struttura/<id>/media/upload (mirrors app.py's struttura_media_upload) ----
    @app.route('/struttura/<int:struttura_id>/media/upload', methods=['POST'])
    @login_required
    @write_permission_required
    def struttura_media_upload(struttura_id):
        try:
            f = request.files.get('file')
            if not f or not f.filename:
                flash('Nessun file', 'error')
                return redirect(url_for('struttura_edit', struttura_id=struttura_id))
            filename = secure_filename(f.filename)
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            f.save(tmp_path)
            media_service.add_media(tmp_path, 'struttura', struttura_id)
            flash('Media caricato', 'success')
            os.unlink(tmp_path)
        except Exception as e:
            flash(f'Errore upload: {e}', 'error')
        return redirect(url_for('struttura_edit', struttura_id=struttura_id))

    # ---- /api/struttura/thesaurus/<field> (mirrors app.py's struttura_thesaurus) ----
    @app.route('/api/struttura/thesaurus/<field>')
    @login_required
    def struttura_thesaurus(field):
        try:
            values = struttura_service.get_thesaurus_values(field)
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
    r = logged_in_client.get("/struttura")
    assert r.status_code == 200


def test_create_post_inserts_record_retrievable_via_service(logged_in_client, struttura_service):
    r = logged_in_client.post(
        "/struttura/new",
        data={"sito": "Volterra", "categoria_struttura": "Muro"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = struttura_service.list_struttura()
    assert len(items) == 1
    assert items[0]["sito"] == "Volterra"
    assert items[0]["categoria_struttura"] == "Muro"


def test_edit_page_shows_categoria(logged_in_client, struttura_service):
    sid = struttura_service.create_struttura({"sito": "Volterra", "categoria_struttura": "Fondazione"})
    r = logged_in_client.get(f"/struttura/{sid}")
    assert r.status_code == 200
    assert b"Fondazione" in r.data


def test_edit_post_by_viewer_is_denied_and_does_not_mutate(viewer_client, struttura_service):
    """A VIEWER (no write permission) must not be able to mutate a struttura via
    POST /struttura/<id> — write_permission_required should redirect the request
    away before struttura_service.update_struttura() is ever called."""
    sid = struttura_service.create_struttura({"sito": "Volterra", "categoria_struttura": "Fondazione"})
    r = viewer_client.post(
        f"/struttura/{sid}",
        data={"sito": "Volterra", "categoria_struttura": "Muro"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    # The record must be unchanged - the write attempt was blocked, not applied.
    assert struttura_service.get_struttura(sid)["categoria_struttura"] == "Fondazione"


def test_edit_get_by_viewer_is_denied(viewer_client, struttura_service):
    """GET /struttura/<id> is gated the same way as tomba_edit in app.py:
    @write_permission_required sits on the whole view, so a VIEWER is
    redirected away even for read access to the edit form."""
    sid = struttura_service.create_struttura({"sito": "Volterra", "categoria_struttura": "Fondazione"})
    r = viewer_client.get(f"/struttura/{sid}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_thesaurus_api_returns_200_json_list(logged_in_client):
    r = logged_in_client.get("/api/struttura/thesaurus/categoria_struttura")
    assert r.status_code == 200
    values = r.get_json()
    assert isinstance(values, list)


def test_delete_removes_record(logged_in_client, struttura_service):
    sid = struttura_service.create_struttura({"sito": "Volterra", "categoria_struttura": "Muro"})
    r = logged_in_client.post(f"/struttura/{sid}/delete", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert struttura_service.get_struttura(sid) is None

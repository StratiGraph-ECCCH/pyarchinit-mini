"""Integration tests for the ut web routes (Task 5).

The real route bodies live nested inside app.py's monolithic ``create_app()``
factory (~5000+ lines, starts a backup-scheduler thread, writes to the real
``~/.pyarchinit_mini`` via ConnectionManager, imports many blueprints...), so
invoking it directly in a focused test is impractical — this mirrors the
established pattern already used by ``tests/struttura/test_struttura_routes.py``:
build a minimal Flask app, hand-copy the migrated route bodies (kept in
lockstep with app.py's ut implementation, ``app.py`` "===== UT ..."
block) and reuse the real ``auth_routes`` decorators
(``login_required``/``write_permission_required``) and login manager for
authenticity, so a write-permission-gated POST is exercised the same way it
would be in production.

Covers the behaviors requested for Task 5:
  1. Authenticated GET /ut -> 200
  2. POST /ut/new with {progetto, def_ut} -> redirect (302) and the record
     is retrievable via ut_service
  3. GET /ut/<id> -> 200, shows the def_ut (write-permission user)
  4. GET /api/ut/thesaurus/def_ut -> 200 JSON list
  5. POST /ut/<id>/delete -> record gone
  6. GET/POST /ut/<id> as a VIEWER (no write permission) -> redirected away,
     record left unmutated (mirrors struttura's write-permission convention:
     ut_edit is gated with @write_permission_required on the whole view)
  7. /ut/<id>/media/upload route IS registered (URL-map smoke check) —
     end-to-end media upload behavior is already covered generically for
     entity_map keys by tests/media/test_web_media_routes.py.

UT is project-scoped (filters by ``progetto``, not ``sito``) — unlike
Struttura/Tomba/Fauna.
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
from pyarchinit_mini.services.ut_service import UtService
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
    db = tmp_path / "ut_routes.db"
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
def ut_service(db_manager):
    return UtService(db_manager)


@pytest.fixture
def flask_app(db_manager, media_service, ut_service, user_service):
    """Minimal Flask app mounting the migrated ut routes.

    Route bodies below are hand-copied verbatim from pyarchinit_mini/web_interface/app.py
    (ut_list, ut_create, ut_edit, ut_delete, ut_media_upload, ut_thesaurus) so
    this test exercises the same logic the real app registers, without
    paying for the full create_app() factory.
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
    app.ut_service = ut_service

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

    # ---- /ut (mirrors app.py's ut_list) ----
    @app.route('/ut')
    @login_required
    def ut_list():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        progetto_filter = request.args.get('progetto', '').strip()
        try:
            ut_list_data = ut_service.list_ut(page=page, size=per_page,
                                               search=search, progetto=progetto_filter)
            total = ut_service.count_ut(search=search, progetto=progetto_filter)
            projects = ut_service.get_distinct_projects()
            import math
            total_pages = max(math.ceil(total / per_page), 1)
            return render_template('ut/list.html', ut_list=ut_list_data,
                                   total=total, page=page, total_pages=total_pages,
                                   search=search, progetto_filter=progetto_filter, projects=projects)
        except Exception as e:
            flash(f'Errore UT: {str(e)}', 'error')
            return redirect(url_for('index'))

    # ---- /ut/new (mirrors app.py's ut_create) ----
    @app.route('/ut/new', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def ut_create():
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            ut_id = ut_service.create_ut(data)
            if ut_id:
                flash('UT creata', 'success')
                return redirect(url_for('ut_edit', ut_id=ut_id))
            flash('Errore creazione UT', 'error')
        return render_template('ut/form.html', ut={}, media=[])

    # ---- /ut/<id> (mirrors app.py's ut_edit) ----
    @app.route('/ut/<int:ut_id>', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def ut_edit(ut_id):
        ut = ut_service.get_ut(ut_id)
        if not ut:
            flash('UT non trovata', 'error')
            return redirect(url_for('ut_list'))
        if request.method == 'POST':
            data = {k: v for k, v in request.form.items()}
            if ut_service.update_ut(ut_id, data):
                flash('UT aggiornata', 'success')
            else:
                flash('Errore aggiornamento', 'error')
            return redirect(url_for('ut_edit', ut_id=ut_id))
        media_items = []
        try:
            media_items = _media_gallery('ut', ut_id)
        except Exception:
            pass
        return render_template('ut/form.html', ut=ut, media=media_items)

    # ---- /ut/<id>/delete (mirrors app.py's ut_delete) ----
    @app.route('/ut/<int:ut_id>/delete', methods=['POST'])
    @login_required
    @write_permission_required
    def ut_delete(ut_id):
        if ut_service.delete_ut(ut_id):
            flash('UT eliminata', 'success')
        else:
            flash('Errore eliminazione', 'error')
        return redirect(url_for('ut_list'))

    # ---- /ut/<id>/media/upload (mirrors app.py's ut_media_upload) ----
    @app.route('/ut/<int:ut_id>/media/upload', methods=['POST'])
    @login_required
    @write_permission_required
    def ut_media_upload(ut_id):
        try:
            f = request.files.get('file')
            if not f or not f.filename:
                flash('Nessun file', 'error')
                return redirect(url_for('ut_edit', ut_id=ut_id))
            filename = secure_filename(f.filename)
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            f.save(tmp_path)
            media_service.add_media(tmp_path, 'ut', ut_id)
            flash('Media caricato', 'success')
            os.unlink(tmp_path)
        except Exception as e:
            flash(f'Errore upload: {e}', 'error')
        return redirect(url_for('ut_edit', ut_id=ut_id))

    # ---- /api/ut/thesaurus/<field> (mirrors app.py's ut_thesaurus) ----
    @app.route('/api/ut/thesaurus/<field>')
    @login_required
    def ut_thesaurus(field):
        try:
            values = ut_service.get_thesaurus_values(field)
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
    r = logged_in_client.get("/ut")
    assert r.status_code == 200


def test_create_post_inserts_record_retrievable_via_service(logged_in_client, ut_service):
    r = logged_in_client.post(
        "/ut/new",
        data={"progetto": "ScavoAlpha", "def_ut": "Strato"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    items = ut_service.list_ut()
    assert len(items) == 1
    assert items[0]["progetto"] == "ScavoAlpha"
    assert items[0]["def_ut"] == "Strato"


def test_edit_page_shows_def_ut(logged_in_client, ut_service):
    uid = ut_service.create_ut({"progetto": "ScavoAlpha", "def_ut": "Buca"})
    r = logged_in_client.get(f"/ut/{uid}")
    assert r.status_code == 200
    assert b"Buca" in r.data


def test_list_filters_by_progetto_not_sito(logged_in_client, ut_service):
    """UT is project-scoped: the list filter dropdown/query param is
    ``progetto``, not ``sito`` like struttura/tomba/fauna."""
    ut_service.create_ut({"progetto": "ScavoAlpha", "def_ut": "Buca"})
    ut_service.create_ut({"progetto": "ScavoBeta", "def_ut": "Muro"})

    r = logged_in_client.get("/ut", query_string={"progetto": "ScavoAlpha"})
    assert r.status_code == 200
    assert b"ScavoAlpha" in r.data
    assert b"Muro" not in r.data


def test_edit_post_by_viewer_is_denied_and_does_not_mutate(viewer_client, ut_service):
    """A VIEWER (no write permission) must not be able to mutate a ut via
    POST /ut/<id> — write_permission_required should redirect the request
    away before ut_service.update_ut() is ever called."""
    uid = ut_service.create_ut({"progetto": "ScavoAlpha", "def_ut": "Buca"})
    r = viewer_client.post(
        f"/ut/{uid}",
        data={"progetto": "ScavoAlpha", "def_ut": "Muro"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    # The record must be unchanged - the write attempt was blocked, not applied.
    assert ut_service.get_ut(uid)["def_ut"] == "Buca"


def test_edit_get_by_viewer_is_denied(viewer_client, ut_service):
    """GET /ut/<id> is gated the same way as struttura_edit in app.py:
    @write_permission_required sits on the whole view, so a VIEWER is
    redirected away even for read access to the edit form."""
    uid = ut_service.create_ut({"progetto": "ScavoAlpha", "def_ut": "Buca"})
    r = viewer_client.get(f"/ut/{uid}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_thesaurus_api_returns_200_json_list(logged_in_client):
    r = logged_in_client.get("/api/ut/thesaurus/def_ut")
    assert r.status_code == 200
    values = r.get_json()
    assert isinstance(values, list)


def test_delete_removes_record(logged_in_client, ut_service):
    uid = ut_service.create_ut({"progetto": "ScavoAlpha", "def_ut": "Muro"})
    r = logged_in_client.post(f"/ut/{uid}/delete", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert ut_service.get_ut(uid) is None


def test_media_upload_route_is_registered(flask_app):
    """UT HAS media (unlike Fauna) — confirm the upload endpoint the media
    tab posts to was registered. End-to-end upload behavior is covered
    generically by tests/media/test_web_media_routes.py."""
    rules = {r.rule for r in flask_app.url_map.iter_rules()}
    assert '/ut/<int:ut_id>/media/upload' in rules

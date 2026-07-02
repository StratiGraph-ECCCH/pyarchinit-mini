"""Integration tests for the plugin-schema media web routes (Task 8).

The real route bodies live nested inside app.py's monolithic ``create_app()``
factory (~5800 lines, starts a backup-scheduler thread, writes to the real
``~/.pyarchinit_mini`` via ConnectionManager, imports many blueprints...), so
invoking it directly in a focused test is impractical — this mirrors the
established pattern already used by ``tests/integration/test_admin_backup_routes.py``
and ``tests/integration/test_pottery_routes.py``: build a minimal Flask app,
hand-copy the migrated route bodies (kept in lockstep with app.py's
post-Task-8 implementation) and reuse the real ``MediaUploadForm`` and
``auth_routes`` decorators/login-manager for authenticity.

Covers the four behaviors requested for Task 8:
  1. POST an image upload for us id=1 -> 302
  2. GET /media/list -> 200, filename appears
  3. GET /media/serve?p=<abs path> -> 200, image bytes
  4. POST /media/delete/<id> -> media gone from /media/list

Also covers the /media/serve local-path guard (CWE-22 prefix-without-boundary
fix): a sibling directory that merely shares the media root's string prefix
(e.g. "<media_root>_backup") must be rejected (403), a path genuinely under a
root that doesn't exist on disk must 404, and an unregistered remote scheme
(e.g. sftp://) must 403 ("forbidden"). Registered remote schemes
(unibo/webdav/s3/r2/gdrive/dropbox) are proxied instead of erroring — see
serve_decision() in pyarchinit_mini/web_interface/media_serve.py and its
dedicated unit coverage in tests/storage/test_media_serve_backends.py.
"""
import os
import tempfile

import pytest
from PIL import Image
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file, abort,
)
from flask_login import login_required, login_user
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.utils import secure_filename

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.site_service import SiteService
from pyarchinit_mini.services.us_service import USService
from pyarchinit_mini.services.inventario_service import InventarioService
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.media_service import MediaService
from pyarchinit_mini.media_manager.media_handler import MediaHandler
from pyarchinit_mini.web_interface.app import MediaUploadForm
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
    db = tmp_path / "media_routes.db"
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
def site_service(db_manager):
    return SiteService(db_manager)


@pytest.fixture
def us_service(db_manager):
    return USService(db_manager)


@pytest.fixture
def inventario_service(db_manager):
    return InventarioService(db_manager)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def flask_app(db_manager, media_service, media_handler, site_service, us_service,
              inventario_service, user_service):
    """Minimal Flask app mounting the migrated (post-Task-8) media routes.

    Route bodies below are hand-copied verbatim from pyarchinit_mini/web_interface/app.py
    (upload_media, media_list, media_serve, delete_media) so this test exercises the
    same logic the real app registers, without paying for the full create_app() factory.
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

    # ---- /media/upload (mirrors app.py's upload_media post-Task-8) ----
    @app.route('/media/upload', methods=['GET', 'POST'])
    @login_required
    @write_permission_required
    def upload_media():
        form = MediaUploadForm()
        sites = site_service.get_all_sites(size=1000)
        site_choices = [('', '-- Seleziona Sito --')] + [(str(s.id_sito), s.sito) for s in sites]
        form.site_id.choices = [(int(v) if v else 0, n) for v, n in site_choices if v]
        form.us_site.choices = [('', '-- Seleziona Sito --')] + [(s.sito, s.sito) for s in sites]
        form.inv_site.choices = [('', '-- Seleziona Sito --')] + [(s.sito, s.sito) for s in sites]

        if form.validate_on_submit():
            try:
                entity_type = form.entity_type.data
                entity_id = None

                if entity_type == 'site':
                    entity_id = form.site_id.data
                elif entity_type == 'us':
                    site_name = form.us_site.data
                    area = form.us_area.data
                    us_number = form.us_number.data
                    if not all([site_name, us_number]):
                        flash('For US, Site and US Number are required', 'error')
                        return render_template('media/upload.html', form=form)
                    us_filters = {'sito': site_name, 'us': us_number}
                    if area:
                        us_filters['area'] = area
                    us_list = us_service.get_all_us(size=1000, filters=us_filters)
                    if not us_list:
                        flash(f'US not found: {site_name} - Area {area or "N/A"} - US {us_number}', 'error')
                        return render_template('media/upload.html', form=form)
                    entity_id = us_list[0].id_us
                elif entity_type == 'inventario':
                    site_name = form.inv_site.data
                    inv_number = form.inv_number.data
                    if not all([site_name, inv_number]):
                        flash('For Inventory, Site and Inventory Number are required', 'error')
                        return render_template('media/upload.html', form=form)
                    inv_list = inventario_service.get_all_inventario(
                        size=1000, filters={'sito': site_name, 'numero_inventario': inv_number})
                    if not inv_list:
                        flash(f'Inventory not found: {site_name} - Inv. {inv_number}', 'error')
                        return render_template('media/upload.html', form=form)
                    entity_id = inv_list[0].id_invmat

                if not entity_id:
                    flash('Error: unable to determine associated entity', 'error')
                    return render_template('media/upload.html', form=form)

                uploaded_file = form.file.data
                if uploaded_file and uploaded_file.filename:
                    filename = secure_filename(uploaded_file.filename)
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    uploaded_file.save(temp_path)

                    media = media_service.add_media(
                        temp_path, entity_type, entity_id,
                        descrizione=form.description.data or "", tags="",
                    )
                    media_id = media.id_media

                    os.remove(temp_path)

                    flash(f'File uploaded successfully! (ID: {media_id})', 'success')
                    return redirect(url_for('media_list'))
            except Exception as e:
                flash(f'File upload error: {str(e)}', 'error')

        return render_template('media/upload.html', form=form)

    # ---- /media/list (mirrors app.py's media_list post-Task-8) ----
    @app.route('/media/list')
    @login_required
    def media_list():
        try:
            from sqlalchemy import func, or_
            from pyarchinit_mini.models.media import Media, MediaToEntity
            from pyarchinit_mini.media_manager.entity_map import resolve_entity

            search_term = request.args.get('search', '').strip()
            media_type_filter = request.args.get('type', '').strip()
            entity_type_filter = request.args.get('entity', '').strip()
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))

            with db_manager.connection.get_session() as session:
                query = session.query(Media)
                if search_term:
                    like = f"%{search_term}%"
                    query = query.filter(or_(Media.filename.ilike(like),
                                              Media.descrizione.ilike(like)))
                if media_type_filter:
                    query = query.filter(Media.mediatype == media_type_filter)
                if entity_type_filter:
                    try:
                        resolved_entity_type, _, _ = resolve_entity(entity_type_filter)
                    except KeyError:
                        resolved_entity_type = entity_type_filter
                    query = (query.join(MediaToEntity, MediaToEntity.id_media == Media.id_media)
                                  .filter(MediaToEntity.entity_type == resolved_entity_type))

                total = query.count()
                rows = (query.order_by(Media.id_media.desc())
                              .offset((page - 1) * per_page)
                              .limit(per_page)
                              .all())

                type_counts = dict(
                    session.query(Media.mediatype, func.count(Media.id_media))
                           .group_by(Media.mediatype).all()
                )

                media_items = []
                for m in rows:
                    link = (session.query(MediaToEntity)
                                    .filter(MediaToEntity.id_media == m.id_media)
                                    .first())
                    entity_type = link.entity_type if link else None
                    entity_id = link.id_entity if link else None
                    entity_name = f'{entity_type} ID {entity_id}' if entity_type else 'Unknown'
                    try:
                        if entity_type == 'SITE':
                            site = site_service.get_site_by_id(entity_id)
                            entity_name = site.sito if site else entity_name
                        elif entity_type == 'US':
                            us = us_service.get_us_by_id(entity_id)
                            entity_name = f"{us.sito} - US {us.us}" if us else entity_name
                        elif entity_type == 'REPERTO':
                            inv = inventario_service.get_inventario_by_id(entity_id)
                            entity_name = f"{inv.sito} - {inv.numero_inventario}" if inv else entity_name
                    except Exception:
                        pass
                    media_items.append({
                        'id_media': m.id_media,
                        'media_name': m.filename,
                        'media_type': m.mediatype,
                        'description': m.descrizione,
                        'url': media_service.public_url(m.filepath),
                        'thumb_url': media_service.thumb_url(m.id_media),
                        'entity_type': entity_type,
                        'entity_name': entity_name,
                    })

            stats = {
                'total_media': total,
                'type_distribution': type_counts,
                'total_storage_mb': 0,
            }

            return render_template('media/list.html',
                                 media_list=media_items,
                                 stats=stats,
                                 search_term=search_term,
                                 media_type_filter=media_type_filter,
                                 entity_type_filter=entity_type_filter,
                                 page=page,
                                 per_page=per_page)
        except Exception as e:
            flash(f'Error loading media list: {str(e)}', 'error')
            return render_template('media/list.html', media_list=[], stats={})

    # ---- /media/serve (mirrors app.py's media_serve post-Task-8) ----
    # Scheme classification is delegated to the REAL serve_decision() (see
    # pyarchinit_mini/web_interface/media_serve.py) rather than hand-rolled
    # here, so this mirror can't drift stale again like its predecessor did
    # (which asserted a since-removed 501-for-remote-schemes behavior).
    @app.route('/media/serve')
    @login_required
    def media_serve():
        from pyarchinit_mini.web_interface.media_serve import serve_decision
        p = request.args.get('p', '')
        if not p:
            abort(404)
        kind, value = serve_decision(p)

        if kind == 'redirect':
            return redirect(value)

        if kind == 'proxy':
            from pyarchinit_mini.services.storage_config_service import StorageConfigService
            mgr = StorageConfigService(db_manager).build_manager()
            data = mgr.read(p)
            if data is None:
                abort(404)
            import io
            import mimetypes
            mimetype = mimetypes.guess_type(p)[0] or 'application/octet-stream'
            return send_file(io.BytesIO(data), mimetype=mimetype)

        if kind == 'forbidden':
            abort(403)

        # kind == 'file': local absolute path, restrict to the configured
        # media/thumb roots (existing CWE-22 guard).
        roots = [str(media_handler.media_root), str(media_handler.thumb_path),
                 str(media_handler.thumb_resize)]
        real = os.path.realpath(value)
        def _under(root):
            rr = os.path.realpath(root)
            return real == rr or real.startswith(rr + os.sep)
        if not any(_under(r) for r in roots):
            abort(403)
        if not os.path.isfile(real):
            abort(404)
        return send_file(real)

    # ---- /media/delete/<id> (mirrors app.py's delete_media post-Task-8) ----
    @app.route('/media/delete/<int:media_id>', methods=['POST'])
    @login_required
    @write_permission_required
    def delete_media(media_id):
        try:
            media = media_service.get_media_by_id(media_id)
            if not media:
                flash('Media file not found', 'error')
                return redirect(url_for('media_list'))

            success = media_service.delete_media(media_id)

            if success:
                flash('Media file deleted successfully', 'success')
            else:
                flash('Error deleting media file', 'error')

            referrer = request.referrer
            if referrer and ('edit_site' in referrer or 'edit_us' in referrer or 'edit_inventario' in referrer):
                return redirect(referrer)
            return redirect(url_for('media_list'))
        except Exception as e:
            flash(f'Error deleting media: {str(e)}', 'error')
            return redirect(url_for('media_list'))

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
def test_image(tmp_path):
    path = tmp_path / "upload_test.png"
    Image.new("RGB", (64, 64), color=(200, 30, 30)).save(path)
    return path


@pytest.fixture
def us_row(us_service, site_service):
    """A real 'us' row with id_us == 1 for the upload target."""
    site_service.create_site({"sito": "Test Site", "nazione": "Italia"})
    us = us_service.create_us({"sito": "Test Site", "area": "1", "us": "1"})
    assert us.id_us == 1
    return us


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_upload_list_serve_delete_flow(logged_in_client, us_row, test_image):
    """End-to-end: upload an image for us id=1, see it in the list, serve its
    bytes, then delete it and confirm it's gone from the list."""
    client = logged_in_client

    # 1. POST an image upload for us id=1.
    with open(test_image, "rb") as fh:
        resp = client.post(
            "/media/upload",
            data={
                "entity_type": "us",
                "us_site": "Test Site",
                "us_area": "1",
                "us_number": "1",
                "description": "A test photo",
                "file": (fh, "upload_test.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert resp.status_code in (302, 303), resp.data
    assert "media/list" in resp.location

    # 2. GET the media list -> 200, filename appears.
    resp = client.get("/media/list")
    assert resp.status_code == 200
    assert b"upload_test.png" in resp.data

    # Scrape the uploaded media's id + /media/serve?p=<path> URL out of the
    # rendered list page (keeps the test independent of internal service
    # plumbing and only assumes the route/template contract).
    media_id, serve_path = _find_uploaded_media(client)

    # 3. GET /media/serve?p=<abs path> -> 200, image bytes.
    resp = client.get(f"/media/serve?p={serve_path}")
    assert resp.status_code == 200
    assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

    # 4. POST delete -> media gone from /media/list.
    resp = client.post(f"/media/delete/{media_id}", follow_redirects=False)
    assert resp.status_code in (302, 303)

    resp = client.get("/media/list")
    assert resp.status_code == 200
    assert b"upload_test.png" not in resp.data


def test_media_serve_rejects_sibling_path_sharing_root_prefix(logged_in_client, media_handler):
    """CWE-22 regression: a path outside the media/thumb roots that merely
    shares the root's *string* prefix (e.g. "<media_root>_backup/...") must
    be rejected with 403, not accepted by a naive str.startswith() check."""
    client = logged_in_client

    evil_dir = str(media_handler.media_root) + "_backup"
    os.makedirs(evil_dir, exist_ok=True)
    evil_path = os.path.join(evil_dir, "secret.txt")
    with open(evil_path, "w") as fh:
        fh.write("should not be servable")

    resp = client.get(f"/media/serve?p={evil_path}")
    assert resp.status_code == 403


def test_media_serve_missing_file_under_root_is_404(logged_in_client, media_handler):
    """A path that IS genuinely under an allowed root but doesn't exist on
    disk must 404 (guard passes, existence check fails)."""
    client = logged_in_client

    os.makedirs(media_handler.media_root, exist_ok=True)
    missing_path = os.path.join(media_handler.media_root, "does_not_exist.txt")

    resp = client.get(f"/media/serve?p={missing_path}")
    assert resp.status_code == 404


def test_media_serve_unregistered_remote_scheme_is_forbidden(logged_in_client):
    """A remote scheme we recognize but don't know how to proxy (sftp://)
    is rejected with 403 via serve_decision()'s 'forbidden' outcome — NOT
    501; registered schemes (unibo/webdav/s3/r2/gdrive/dropbox) proxy
    instead. Pure serve_decision() classification (incl. the proxy cases)
    is unit-tested in tests/storage/test_media_serve_backends.py; this is
    the route-integration check that the real wiring returns 403."""
    client = logged_in_client

    resp = client.get("/media/serve?p=sftp://x/y")
    assert resp.status_code == 403


def _find_uploaded_media(client):
    """Scrape the /media/serve?p=<path> URL and the numeric media id for the
    single uploaded row out of the rendered /media/list HTML."""
    import re
    resp = client.get("/media/list")
    html = resp.data.decode("utf-8")
    m = re.search(r"/media/serve\?p=([^\"&]+)", html)
    assert m, html
    from urllib.parse import unquote
    serve_path = unquote(m.group(1))
    m2 = re.search(r"/media/delete/(\d+)", html)
    assert m2, html
    media_id = int(m2.group(1))
    return media_id, serve_path

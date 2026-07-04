"""Integration tests for the /settings/branding web route (custom PDF logo).

Mirrors the established harness pattern used by
tests/storage/test_settings_storage_route.py: build a minimal Flask app,
hand-copy the route body from app.py (reusing the real admin_required so
this exercises the same auth logic the real app registers) rather than
paying for the full create_app() factory.

Covers:
  1. GET /settings/branding -> 200 for an authenticated admin user.
  2. Non-admin (viewer) / anonymous users are redirected away.
  3. POST a valid PNG replaces static/images/logo.png and backs up the
     previous file to logo.default.png (only on the FIRST replacement).
  4. POST a non-image file (bad extension, and a text file disguised with a
     .png extension) is rejected and does not touch the logo file.
  5. POST action=reset restores logo.default.png -> logo.png.
  6. The uploaded logo actually renders correctly through
     entity_sheet_template._get_logo_flowable (end-to-end with the PDF
     sizing fix — regression guard for the header-cell overflow bug).
"""
import io
import os
import shutil

import pytest
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_user
from jinja2 import ChoiceLoader, FileSystemLoader
from PIL import Image as PILImage
from werkzeug.utils import secure_filename

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.web_interface.auth_routes import (
    init_login_manager, admin_required, User as AuthUser,
)

_HERE = os.path.dirname(__file__)
_APP_TEMPLATES = os.path.join(_HERE, "..", "..", "pyarchinit_mini", "web_interface", "templates")
_TEST_TEMPLATES = os.path.join(_HERE, "..", "templates")
_ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}


def _make_png_bytes(size=(64, 64), color=(255, 0, 0)):
    buf = io.BytesIO()
    PILImage.new("RGB", size, color).save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "branding_settings_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def static_dir(tmp_path):
    """A throwaway static/images dir seeded with a default logo.png, so
    tests never touch the real repo's static assets."""
    images_dir = tmp_path / "static" / "images"
    images_dir.mkdir(parents=True)
    (images_dir / "logo.png").write_bytes(_make_png_bytes(color=(0, 0, 255)))
    return str(tmp_path / "static")


@pytest.fixture
def flask_app(db_manager, user_service, static_dir):
    app = Flask(
        __name__,
        template_folder=_APP_TEMPLATES,
        static_folder=static_dir,
    )
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["WTF_CSRF_ENABLED"] = False
    app.db_manager = db_manager

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

    @app.route("/auth/login", endpoint="auth.login")
    def _auth_login():
        return ""

    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    _LOGO_PATH = os.path.join(app.static_folder, 'images', 'logo.png')
    _LOGO_DEFAULT_BACKUP_PATH = os.path.join(app.static_folder, 'images', 'logo.default.png')

    # ---- /settings/branding (mirrors app.py's settings_branding) ----
    @app.route("/settings/branding", methods=["GET", "POST"])
    @admin_required
    def settings_branding():
        if request.method == "POST":
            action = request.form.get("action", "upload")

            if action == "reset":
                if os.path.exists(_LOGO_DEFAULT_BACKUP_PATH):
                    shutil.copyfile(_LOGO_DEFAULT_BACKUP_PATH, _LOGO_PATH)
                    flash("Logo ripristinato al valore predefinito.", "success")
                else:
                    flash("Nessun logo predefinito salvato da ripristinare.", "error")
                return redirect(url_for("settings_branding"))

            file = request.files.get("logo")
            if not file or file.filename == "":
                flash("Nessun file selezionato.", "error")
                return redirect(url_for("settings_branding"))

            ext = os.path.splitext(secure_filename(file.filename))[1].lower()
            if ext not in _ALLOWED_EXTENSIONS:
                flash("Formato non supportato. Usa PNG o JPG.", "error")
                return redirect(url_for("settings_branding"))

            import tempfile
            fd, tmp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)
            try:
                file.save(tmp_path)
                try:
                    with PILImage.open(tmp_path) as img:
                        img.verify()
                except Exception:
                    flash("Il file caricato non è un'immagine valida.", "error")
                    return redirect(url_for("settings_branding"))

                if os.path.exists(_LOGO_PATH) and not os.path.exists(_LOGO_DEFAULT_BACKUP_PATH):
                    shutil.copyfile(_LOGO_PATH, _LOGO_DEFAULT_BACKUP_PATH)

                shutil.copyfile(tmp_path, _LOGO_PATH)
                flash("Logo aggiornato con successo.", "success")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            return redirect(url_for("settings_branding"))

        return render_template(
            "settings/branding.html",
            logo_exists=os.path.exists(_LOGO_PATH),
            has_default_backup=os.path.exists(_LOGO_DEFAULT_BACKUP_PATH),
            logo_mtime=int(os.path.getmtime(_LOGO_PATH)) if os.path.exists(_LOGO_PATH) else 0,
        )

    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def admin_user(user_service):
    return user_service.create_user(
        username="admin1", email="admin1@example.com", password="secret123",
        full_name="Admin One", role=UserRole.ADMIN,
    )


@pytest.fixture
def viewer_user(user_service):
    return user_service.create_user(
        username="viewer1", email="viewer1@example.com", password="secret123",
        full_name="Viewer One", role=UserRole.VIEWER,
    )


@pytest.fixture
def admin_client(client, admin_user):
    r = client.get(f"/_test/login/{admin_user['id']}")
    assert r.status_code == 200
    return client


@pytest.fixture
def viewer_client(client, viewer_user):
    r = client.get(f"/_test/login/{viewer_user['id']}")
    assert r.status_code == 200
    return client


def _logo_path(static_dir):
    return os.path.join(static_dir, "images", "logo.png")


def _backup_path(static_dir):
    return os.path.join(static_dir, "images", "logo.default.png")


def test_get_returns_200_for_admin(admin_client):
    resp = admin_client.get("/settings/branding")
    assert resp.status_code == 200


def test_viewer_is_redirected_not_shown_form(viewer_client):
    resp = viewer_client.get("/settings/branding", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_anonymous_is_redirected_to_login(client):
    resp = client.get("/settings/branding", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_upload_replaces_logo_and_backs_up_default_once(admin_client, static_dir):
    original_bytes = open(_logo_path(static_dir), "rb").read()
    assert not os.path.exists(_backup_path(static_dir))

    new_bytes = _make_png_bytes(color=(0, 255, 0))
    resp = admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(new_bytes), "custom_logo.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    # New logo is in place; original was backed up as the resettable default.
    assert open(_logo_path(static_dir), "rb").read() != original_bytes
    assert os.path.exists(_backup_path(static_dir))
    assert open(_backup_path(static_dir), "rb").read() == original_bytes

    # A SECOND upload must not clobber the already-saved default backup.
    another_bytes = _make_png_bytes(color=(255, 255, 0))
    admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(another_bytes), "another.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert open(_backup_path(static_dir), "rb").read() == original_bytes


def test_upload_rejects_disallowed_extension(admin_client, static_dir):
    original_bytes = open(_logo_path(static_dir), "rb").read()
    resp = admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(b"not an image"), "logo.gif")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    # Untouched — extension check runs before any file is written.
    assert open(_logo_path(static_dir), "rb").read() == original_bytes


def test_upload_rejects_corrupt_file_with_png_extension(admin_client, static_dir):
    """A non-image file renamed to .png must be caught by the PIL
    verify() step, not silently accepted as a broken logo."""
    original_bytes = open(_logo_path(static_dir), "rb").read()
    resp = admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(b"this is definitely not a png"), "fake.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert open(_logo_path(static_dir), "rb").read() == original_bytes
    with admin_client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("immagine valida" in msg for _cat, msg in flashes)


def test_reset_restores_original_default(admin_client, static_dir):
    original_bytes = open(_logo_path(static_dir), "rb").read()

    admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(_make_png_bytes(color=(9, 9, 9))), "custom.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert open(_logo_path(static_dir), "rb").read() != original_bytes

    resp = admin_client.post(
        "/settings/branding", data={"action": "reset"}, follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert open(_logo_path(static_dir), "rb").read() == original_bytes


def test_reset_without_prior_upload_flashes_error(admin_client, static_dir):
    resp = admin_client.post(
        "/settings/branding", data={"action": "reset"}, follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with admin_client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("predefinito" in msg for _cat, msg in flashes)


def test_uploaded_logo_renders_within_header_box_via_pdf_engine(admin_client, static_dir):
    """End-to-end regression guard tying this feature to the sizing fix in
    entity_sheet_template._get_logo_flowable: a freshly uploaded (large,
    square) custom logo must scale DOWN to fit the ~2.2cm header cell,
    never render at some larger hard-coded size that overflows it."""
    from pyarchinit_mini.pdf_export.entity_sheet_template import (
        _get_logo_flowable, _get_styles,
    )

    big_logo_bytes = _make_png_bytes(size=(1024, 1024), color=(1, 2, 3))
    admin_client.post(
        "/settings/branding",
        data={"action": "upload", "logo": (io.BytesIO(big_logo_bytes), "big_logo.png")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    styles = _get_styles()
    box = 54.35  # matches _header_table's logo_box (logo_width - 8)
    flowable = _get_logo_flowable(_logo_path(static_dir), styles, max_width=box, max_height=box)
    assert flowable.drawWidth <= box
    assert flowable.drawHeight <= box

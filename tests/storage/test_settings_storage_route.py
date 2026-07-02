"""Integration tests for the /settings/storage web routes (Task 10).

Mirrors the established harness pattern already used by
tests/media/test_web_media_routes.py and tests/integration/test_admin_ai_settings_routes.py:
build a minimal Flask app, hand-copy the route bodies from app.py (reusing the
real STORAGE_BACKEND_DEFS / helper / admin_required so this exercises the same
logic the real app registers) rather than paying for the full create_app()
factory (~5900 lines, background threads, real ~/.pyarchinit_mini DB, ...).

Covers:
  1. GET /settings/storage -> 200 for an authenticated admin user.
  2. POST /settings/storage persists via StorageConfigService (re-get() shows
     the saved media_root + credentials).
  3. A blank credential field on a second POST keeps the previously-saved
     value instead of wiping it (never re-rendered, so blank == "unchanged").
  4. POST /settings/storage/test/<backend> returns JSON with an "ok" key and
     never raises even for bogus credentials / an unreachable host.
  5. Non-admin (viewer) users are redirected away, not shown the form.
  6. Missing PYARCHINIT_SECRET_KEY -> save() raises RuntimeError -> route
     catches it, flashes, and does NOT 500.
"""
import os

import pytest
from cryptography.fernet import Fernet
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, login_user
from jinja2 import ChoiceLoader, FileSystemLoader

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.storage_config_service import StorageConfigService
from pyarchinit_mini.web_interface.auth_routes import (
    init_login_manager, admin_required, User as AuthUser,
)
from pyarchinit_mini.web_interface.app import (
    STORAGE_BACKEND_DEFS, STORAGE_TESTABLE_BACKENDS, _storage_merge_backend_fields,
)

_HERE = os.path.dirname(__file__)
_APP_TEMPLATES = os.path.join(_HERE, "..", "..", "pyarchinit_mini", "web_interface", "templates")
_TEST_TEMPLATES = os.path.join(_HERE, "..", "templates")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    """A real Fernet key so StorageConfigService.save()/get() can encrypt/decrypt.
    Individual tests that need the "no key set" path delete it explicitly."""
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", Fernet.generate_key().decode())


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "storage_settings_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def storage_service(db_manager):
    return StorageConfigService(db_manager)


@pytest.fixture
def flask_app(db_manager, user_service, storage_service):
    """Minimal Flask app mounting the /settings/storage routes, hand-copied
    from pyarchinit_mini/web_interface/app.py (post-Task-10) but reusing the
    real STORAGE_BACKEND_DEFS / _storage_merge_backend_fields / admin_required
    so the test exercises the same logic the real app registers."""
    app = Flask(
        __name__,
        template_folder=_APP_TEMPLATES,
        static_folder=os.path.join(_HERE, "..", "..", "pyarchinit_mini", "web_interface", "static"),
    )
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["WTF_CSRF_ENABLED"] = False
    app.db_manager = db_manager
    app.storage_service = storage_service

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

    # login_manager.login_view = "auth.login" (set inside init_login_manager)
    # needs a buildable endpoint for the @login_required redirect to work.
    @app.route("/auth/login", endpoint="auth.login")
    def _auth_login():
        return ""

    # Test-only helper to establish a real flask-login session (mirrors what
    # the real /auth/login route does after password verification).
    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    # ---- /settings/storage (mirrors app.py's settings_storage post-Task-10) ----
    @app.route("/settings/storage", methods=["GET", "POST"])
    @admin_required
    def settings_storage():
        cfg = storage_service.get()
        existing_creds = cfg.get("credentials") or {}

        if request.method == "POST":
            media_root = request.form.get("media_root", "").strip()
            thumb_path = request.form.get("thumb_path", "").strip()
            thumb_resize = request.form.get("thumb_resize", "").strip()

            credentials_out = dict(existing_creds)
            for backend_key, defn in STORAGE_BACKEND_DEFS.items():
                merged = _storage_merge_backend_fields(
                    request.form, existing_creds.get(backend_key, {}),
                    backend_key, defn["fields"], defn["checkboxes"],
                )
                credentials_out[backend_key] = merged
                for alias in defn.get("mirror_to", []):
                    credentials_out[alias] = merged

            try:
                storage_service.save(media_root, thumb_path, thumb_resize, credentials_out)
                flash("Storage settings saved.", "success")
            except RuntimeError:
                flash("Set PYARCHINIT_SECRET_KEY to store credentials.", "error")
            return redirect(url_for("settings_storage"))

        configured = {k: bool(v) for k, v in existing_creds.items()}
        return render_template(
            "settings/storage.html",
            media_root=cfg.get("media_root") or "",
            thumb_path=cfg.get("thumb_path") or "",
            thumb_resize=cfg.get("thumb_resize") or "",
            backends=STORAGE_BACKEND_DEFS,
            configured=configured,
        )

    # ---- /settings/storage/test/<backend> (mirrors app.py post-Task-10) ----
    @app.route("/settings/storage/test/<backend>", methods=["POST"])
    @admin_required
    def settings_storage_test(backend):
        from pyarchinit_mini.storage.base_backend import StorageType
        from pyarchinit_mini.storage.storage_manager import StorageManager

        if backend not in STORAGE_TESTABLE_BACKENDS:
            return jsonify({"ok": False, "message": f"Unknown backend '{backend}'"}), 400

        prefix = "s3" if backend == "r2" else backend
        defn = STORAGE_BACKEND_DEFS.get(prefix, STORAGE_BACKEND_DEFS["s3"])

        fields = {}
        for field in defn["fields"]:
            form_key = f"{prefix}_{field}"
            if field in defn["checkboxes"]:
                fields[field] = "true" if request.form.get(form_key) else "false"
            else:
                val = (request.form.get(form_key) or "").strip()
                if val:
                    fields[field] = val

        try:
            storage_type = StorageType(backend)
            mgr = StorageManager()
            mgr.credentials_manager.set_credentials(storage_type, fields)

            probe_path = request.form.get("media_root", "").strip()
            if not probe_path.lower().startswith(f"{backend}://"):
                probe_path = f"{backend}://probe"

            backend_obj = mgr.get_backend(probe_path, connect=True)
            ok = bool(getattr(backend_obj, "_connected", False))
            message = "Connected successfully." if ok else "Connection failed - check credentials."
            return jsonify({"ok": ok, "message": message})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

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


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_get_returns_200_for_admin(admin_client):
    resp = admin_client.get("/settings/storage")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    # Per-backend fieldsets with the exact spec field names should be present.
    assert 'name="unibo_server_url"' in body
    assert 'name="s3_secret_key"' in body
    assert 'name="webdav_username"' in body


def test_viewer_is_redirected_not_shown_form(viewer_client):
    resp = viewer_client.get("/settings/storage", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_anonymous_is_redirected_to_login(client):
    resp = client.get("/settings/storage", follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_post_persists_media_root_and_credentials(admin_client, storage_service):
    resp = admin_client.post(
        "/settings/storage",
        data={
            "media_root": "s3://my-bucket/media",
            "thumb_path": "s3://my-bucket/thumb",
            "thumb_resize": "s3://my-bucket/thumb_resize",
            "s3_access_key": "AKIA_TEST",
            "s3_secret_key": "shh-secret",
            "s3_region": "eu-west-1",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    got = storage_service.get()
    assert got["media_root"] == "s3://my-bucket/media"
    assert got["thumb_path"] == "s3://my-bucket/thumb"
    assert got["credentials"]["s3"]["access_key"] == "AKIA_TEST"
    assert got["credentials"]["s3"]["secret_key"] == "shh-secret"
    # S3 credentials are mirrored to 'r2' so r2:// media roots also work.
    assert got["credentials"]["r2"]["access_key"] == "AKIA_TEST"


def test_blank_secret_field_keeps_existing_value_on_resave(admin_client, storage_service):
    # First save: set a secret.
    admin_client.post(
        "/settings/storage",
        data={
            "media_root": "webdav://server.example.com/archive",
            "thumb_path": "", "thumb_resize": "",
            "webdav_username": "alice",
            "webdav_password": "correct-horse-battery-staple",
        },
        follow_redirects=False,
    )
    first = storage_service.get()
    assert first["credentials"]["webdav"]["password"] == "correct-horse-battery-staple"

    # Second save: change only the media_root, leave the webdav password blank.
    admin_client.post(
        "/settings/storage",
        data={
            "media_root": "webdav://server.example.com/archive2",
            "thumb_path": "", "thumb_resize": "",
            "webdav_username": "alice",
            "webdav_password": "",
        },
        follow_redirects=False,
    )
    second = storage_service.get()
    assert second["media_root"] == "webdav://server.example.com/archive2"
    # Password was left blank on the form -> the old value must survive.
    assert second["credentials"]["webdav"]["password"] == "correct-horse-battery-staple"


def test_get_never_renders_stored_secret_in_cleartext(admin_client, storage_service):
    storage_service.save(
        "webdav://server.example.com/archive", "", "",
        {"webdav": {"username": "alice", "password": "super-secret-value"}},
    )
    resp = admin_client.get("/settings/storage")
    assert resp.status_code == 200
    assert b"super-secret-value" not in resp.data


def test_test_connection_endpoint_returns_json_with_ok_key(admin_client):
    resp = admin_client.post(
        "/settings/storage/test/webdav",
        data={"webdav_username": "alice", "webdav_password": "wrong"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "ok" in data
    assert isinstance(data["ok"], bool)
    assert "message" in data


def test_test_connection_endpoint_never_raises_for_unknown_backend(admin_client):
    resp = admin_client.post("/settings/storage/test/not-a-real-backend", data={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False


def test_test_connection_endpoint_never_raises_on_bad_creds(admin_client):
    # No credentials at all - backend.connect() should fail cleanly (ok=False),
    # never raise a 500.
    resp = admin_client.post("/settings/storage/test/s3", data={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is False


def test_missing_secret_key_flashes_error_instead_of_500(admin_client, monkeypatch):
    monkeypatch.delenv("PYARCHINIT_SECRET_KEY", raising=False)
    resp = admin_client.post(
        "/settings/storage",
        data={"media_root": "/data/media", "thumb_path": "", "thumb_resize": ""},
        follow_redirects=False,
    )
    # No 500: the RuntimeError from save() (raised by crypto.encrypt_dict when
    # PYARCHINIT_SECRET_KEY is unset) is caught and turned into a redirect + flash.
    assert resp.status_code in (302, 303)

    # The test harness's minimal base.html stub doesn't render flashed
    # messages (unlike the real app's base.html), so assert on the session's
    # flash queue directly instead of scraping rendered HTML.
    with admin_client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("PYARCHINIT_SECRET_KEY" in msg for _cat, msg in flashes)

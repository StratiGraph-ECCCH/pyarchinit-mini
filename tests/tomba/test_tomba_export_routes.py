"""Route smoke tests for the SP4 tomba export endpoints
(/export/tomba/excel, /export/tomba/csv, /export/tomba/pdf).

Follows the established pattern from test_tomba_routes.py: a minimal Flask
app mounting hand-copied route bodies (kept in lockstep with app.py's
"SP4 export helpers" / "Tomba export" blocks), reusing the real
auth_routes login manager so the endpoints are exercised authenticated,
exactly as in production.

tomba's corredo_tipo is a Python-repr list-of-lists sub-table column (the
classic plugin's str(table2dict()) format), so the export routes flatten it
to a readable string first — same convention as struttura/fauna
(_flatten_tomba_row in app.py).
"""
import os

import pytest
from flask import Flask, redirect, request, send_file, url_for
from flask_login import login_required, login_user

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.tomba_service import TombaService
from pyarchinit_mini.services.struttura_service import parse_pylist as struttura_parse_pylist
from pyarchinit_mini.services.export_import_service import ExportImportService
from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser

_HERE = os.path.dirname(__file__)


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "tomba_export_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def tomba_service(db_manager):
    return TombaService(db_manager)


@pytest.fixture
def flask_app(db_manager, tomba_service, user_service):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["WTF_CSRF_ENABLED"] = False

    csv_excel_service = ExportImportService(db_manager)
    pdf_generator = PDFGenerator()

    init_login_manager(app, user_service)

    @app.route("/")
    def index():
        return ""

    # Dummy login endpoint so flask-login's unauthorized() redirect (which
    # url_for()s "auth.login") resolves in this minimal app.
    app.add_url_rule("/login", endpoint="auth.login", view_func=lambda: "")

    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    @app.route("/tomba")
    @login_required
    def tomba_list():
        return ""

    def _export_tmp_send(build_fn, suffix, download_name, mimetype):
        import tempfile
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            build_fn(tmp_path)
            return send_file(tmp_path, as_attachment=True,
                            download_name=download_name, mimetype=mimetype)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _flatten_tomba_row(d):
        """Mirrors app.py's _flatten_tomba_row (via _flatten_pylist_cols)."""
        out = dict(d)
        for col in tomba_service.SUBTABLE_COLS:
            parsed = struttura_parse_pylist(out.get(col))
            out[col] = '; '.join(
                ' / '.join(str(cell) for cell in row) for row in parsed
            ) if parsed else ''
        return out

    @app.route('/export/tomba/excel')
    @login_required
    def export_tomba_excel():
        sito = request.args.get('sito', '').strip()
        rows = tomba_service.list_tomba(page=1, size=1_000_000, sito=sito)
        data = [_flatten_tomba_row(r) for r in rows]
        filename = f'tomba_{sito}.xlsx' if sito else 'tomba.xlsx'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_excel(data, tmp, sheet_name='Tomba'),
            '.xlsx', filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/export/tomba/csv')
    @login_required
    def export_tomba_csv():
        sito = request.args.get('sito', '').strip()
        rows = tomba_service.list_tomba(page=1, size=1_000_000, sito=sito)
        data = [_flatten_tomba_row(r) for r in rows]
        filename = f'tomba_{sito}.csv' if sito else 'tomba.csv'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_csv(data, tmp),
            '.csv', filename, 'text/csv')

    @app.route('/export/tomba/pdf')
    @login_required
    def export_tomba_pdf():
        sito = request.args.get('sito', '').strip()
        rows = tomba_service.list_tomba(page=1, size=1_000_000, sito=sito)
        data = [_flatten_tomba_row(r) for r in rows]
        filename = f'tomba_{sito}.pdf' if sito else 'tomba.pdf'
        return _export_tmp_send(
            lambda tmp: pdf_generator.generate_records_pdf('Tomba', data, tmp),
            '.pdf', filename, 'application/pdf')

    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def write_user(user_service):
    return user_service.create_user(
        username="operator1", email="operator1@example.com", password="secret123",
        full_name="Operator One", role=UserRole.OPERATOR,
    )


@pytest.fixture
def logged_in_client(client, write_user):
    r = client.get(f"/_test/login/{write_user['id']}")
    assert r.status_code == 200
    return client


def test_export_csv_returns_200_csv(logged_in_client, tomba_service):
    tomba_service.create_tomba({"sito": "Volterra", "rito": "Inumazione"})
    r = logged_in_client.get("/export/tomba/csv")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"Volterra" in r.data


def test_export_excel_returns_200_xlsx(logged_in_client, tomba_service):
    tomba_service.create_tomba({"sito": "Volterra", "rito": "Inumazione"})
    r = logged_in_client.get("/export/tomba/excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.content_type


def test_export_pdf_returns_200_pdf(logged_in_client, tomba_service):
    tomba_service.create_tomba({"sito": "Volterra", "rito": "Inumazione"})
    r = logged_in_client.get("/export/tomba/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data.startswith(b"%PDF")


def test_export_requires_login(client):
    r = client.get("/export/tomba/csv", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_export_csv_flattens_corredo_tipo(logged_in_client, tomba_service):
    """The stored Python-repr corredo_tipo must be flattened to a readable
    'cell / cell / ...' string in exports — never dumped raw."""
    tomba_service.create_tomba({
        "sito": "Volterra",
        "corredo_tipo": '[["1","2","Ceramica","interno","presso il cranio"]]',
    })
    r = logged_in_client.get("/export/tomba/csv")
    assert r.status_code == 200
    body = r.data.decode()
    assert "1 / 2 / Ceramica / interno / presso il cranio" in body
    assert "[['1'" not in body

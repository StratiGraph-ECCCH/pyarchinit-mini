"""Route smoke tests for the SP4 struttura export endpoints
(/export/struttura/excel, /export/struttura/csv, /export/struttura/pdf).

struttura's 10 SUBTABLE_COLS are stored as Python-repr strings (e.g.
"[['buono', 'medio']]"). The export routes must flatten them to a readable
string via _flatten_struttura_row (hand-copied here from app.py's "SP4
export helpers" block, kept in lockstep) before handing rows to
Excel/CSV/PDF export — so a raw to_dict() dump like "[[" must NEVER appear
in the exported CSV bytes.
"""
import os
import tempfile

import pytest
from flask import Flask, request, send_file
from flask_login import login_required, login_user

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.struttura_service import StrutturaService, parse_pylist as struttura_parse_pylist
from pyarchinit_mini.services.export_import_service import ExportImportService
from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser


def _flatten_struttura_row(d):
    """Hand-copied from app.py's SP4 export helpers — kept in lockstep."""
    out = dict(d)
    for col in StrutturaService.SUBTABLE_COLS:
        parsed = struttura_parse_pylist(out.get(col))
        out[col] = '; '.join(
            ' / '.join(str(cell) for cell in row) for row in parsed
        ) if parsed else ''
    return out


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "struttura_export_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def struttura_service(db_manager):
    return StrutturaService(db_manager)


@pytest.fixture
def flask_app(db_manager, struttura_service, user_service):
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

    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    @app.route("/struttura")
    @login_required
    def struttura_list():
        return ""

    def _export_tmp_send(build_fn, suffix, download_name, mimetype):
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

    @app.route('/export/struttura/excel')
    @login_required
    def export_struttura_excel():
        sito = request.args.get('sito', '').strip()
        rows = struttura_service.list_struttura(page=1, size=1_000_000, sito=sito)
        data = [_flatten_struttura_row(r) for r in rows]
        filename = f'struttura_{sito}.xlsx' if sito else 'struttura.xlsx'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_excel(data, tmp, sheet_name='Struttura'),
            '.xlsx', filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/export/struttura/csv')
    @login_required
    def export_struttura_csv():
        sito = request.args.get('sito', '').strip()
        rows = struttura_service.list_struttura(page=1, size=1_000_000, sito=sito)
        data = [_flatten_struttura_row(r) for r in rows]
        filename = f'struttura_{sito}.csv' if sito else 'struttura.csv'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_csv(data, tmp),
            '.csv', filename, 'text/csv')

    @app.route('/export/struttura/pdf')
    @login_required
    def export_struttura_pdf():
        sito = request.args.get('sito', '').strip()
        rows = struttura_service.list_struttura(page=1, size=1_000_000, sito=sito)
        data = [_flatten_struttura_row(r) for r in rows]
        filename = f'struttura_{sito}.pdf' if sito else 'struttura.pdf'
        return _export_tmp_send(
            lambda tmp: pdf_generator.generate_records_pdf('Struttura', data, tmp),
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


def test_export_csv_flattens_repr_subtable_columns(logged_in_client, struttura_service):
    struttura_service.create_struttura({
        "sito": "Volterra",
        "sigla_struttura": "US100",
        "materiali_impiegati": "[['buono','medio']]",
    })
    r = logged_in_client.get("/export/struttura/csv")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"[[" not in r.data
    assert b"buono" in r.data and b"medio" in r.data


def test_export_excel_returns_200_xlsx(logged_in_client, struttura_service):
    struttura_service.create_struttura({
        "sito": "Volterra",
        "materiali_impiegati": "[['buono']]",
    })
    r = logged_in_client.get("/export/struttura/excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.content_type


def test_export_pdf_returns_200_pdf(logged_in_client, struttura_service):
    struttura_service.create_struttura({
        "sito": "Volterra",
        "materiali_impiegati": "[['buono']]",
    })
    r = logged_in_client.get("/export/struttura/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data.startswith(b"%PDF")

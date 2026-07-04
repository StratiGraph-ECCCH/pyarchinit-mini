"""Route smoke tests for the SP4 fauna export endpoints
(/export/fauna/excel, /export/fauna/csv, /export/fauna/pdf).

fauna's specie_psi ([[specie, psi], ...]) and misure_ossa
([[elemento, specie, GL, GB, Bd, Bp], ...]) columns are stored as JSON.
The excel/csv routes must flatten them to a readable string via
_flatten_fauna_row (hand-copied here from app.py's "SP4 export helpers"
block, kept in lockstep) — so the exported CSV must show the species name
in plain text, not the raw JSON list. The PDF route instead passes RAW
record dicts straight to the classic-style sheet engine
(PDFGenerator.generate_entity_records_pdf), which parses the JSON
sub-tables itself.
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
from pyarchinit_mini.services.fauna_service import FaunaService
from pyarchinit_mini.services.export_import_service import ExportImportService
from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser

import json


def _flatten_fauna_row(d):
    """Hand-copied from app.py's SP4 export helpers — kept in lockstep."""
    out = dict(d)

    specie_psi = out.get('specie_psi')
    try:
        specie_rows = json.loads(specie_psi) if specie_psi else []
    except (TypeError, ValueError):
        specie_rows = []
    parts = []
    for row in specie_rows if isinstance(specie_rows, list) else []:
        if not isinstance(row, (list, tuple)) or not row:
            continue
        specie = row[0]
        psi = row[1] if len(row) > 1 else None
        parts.append(f"{specie} ({psi})" if psi else str(specie))
    out['specie_psi'] = '; '.join(parts)

    misure_ossa = out.get('misure_ossa')
    try:
        misure_rows = json.loads(misure_ossa) if misure_ossa else []
    except (TypeError, ValueError):
        misure_rows = []
    mparts = []
    for row in misure_rows if isinstance(misure_rows, list) else []:
        if isinstance(row, (list, tuple)) and row:
            mparts.append(' / '.join(str(cell) for cell in row))
    out['misure_ossa'] = '; '.join(mparts)

    return out


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "fauna_export_routes.db"
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

    @app.route("/fauna")
    @login_required
    def fauna_list():
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

    @app.route('/export/fauna/excel')
    @login_required
    def export_fauna_excel():
        sito = request.args.get('sito', '').strip()
        rows = fauna_service.list_fauna(page=1, size=1_000_000, sito=sito)
        data = [_flatten_fauna_row(r) for r in rows]
        filename = f'fauna_{sito}.xlsx' if sito else 'fauna.xlsx'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_excel(data, tmp, sheet_name='Fauna'),
            '.xlsx', filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/export/fauna/csv')
    @login_required
    def export_fauna_csv():
        sito = request.args.get('sito', '').strip()
        rows = fauna_service.list_fauna(page=1, size=1_000_000, sito=sito)
        data = [_flatten_fauna_row(r) for r in rows]
        filename = f'fauna_{sito}.csv' if sito else 'fauna.csv'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_csv(data, tmp),
            '.csv', filename, 'text/csv')

    @app.route('/export/fauna/pdf')
    @login_required
    def export_fauna_pdf():
        sito = request.args.get('sito', '').strip()
        rows = fauna_service.list_fauna(page=1, size=1_000_000, sito=sito)
        filename = f'fauna_{sito}.pdf' if sito else 'fauna.pdf'
        logo = os.path.join(app.static_folder or '', 'images', 'logo.png')
        return _export_tmp_send(
            lambda tmp: pdf_generator.generate_entity_records_pdf(
                'fauna', rows, tmp, logo_path=logo if os.path.exists(logo) else None),
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


def test_export_csv_flattens_json_species_column(logged_in_client, fauna_service):
    fauna_service.create_fauna({
        "sito": "Volterra",
        "us": "100",
        "specie_psi": json.dumps([["Bos taurus", "adulto"]]),
        "misure_ossa": json.dumps([["omero", "Bos taurus", "1", "2", "3", "4"]]),
    })
    r = logged_in_client.get("/export/fauna/csv")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"Bos taurus" in r.data
    # raw JSON list markers must not leak into the export
    assert b'[["Bos' not in r.data


def test_export_excel_returns_200_xlsx(logged_in_client, fauna_service):
    fauna_service.create_fauna({
        "sito": "Volterra",
        "specie_psi": json.dumps([["Sus scrofa", None]]),
    })
    r = logged_in_client.get("/export/fauna/excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.content_type


def test_export_pdf_returns_200_pdf(logged_in_client, fauna_service):
    fauna_service.create_fauna({
        "sito": "Volterra",
        "specie_psi": json.dumps([["Sus scrofa", None]]),
    })
    r = logged_in_client.get("/export/fauna/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data.startswith(b"%PDF")

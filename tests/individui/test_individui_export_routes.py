"""Route smoke tests for the Individui export endpoints
(/export/individui/excel, /export/individui/csv, /export/individui/pdf).

Mirrors tests/fauna/test_fauna_export_routes.py. Unlike fauna, individui has
NO JSON/repr sub-table columns — every column is scalar — so no per-row
flattening helper is needed here; ``list_individui()`` already returns
plain dicts ready for csv_excel_service / pdf_generator (the PDF route
passes these raw dicts straight to
PDFGenerator.generate_entity_records_pdf, the classic-style sheet engine).
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
from pyarchinit_mini.services.individui_service import IndividuiService
from pyarchinit_mini.services.export_import_service import ExportImportService
from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "individui_export_routes.db"
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

    @app.route("/individui")
    @login_required
    def individui_list():
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

    ALL_RECORDS_SIZE = 1_000_000

    @app.route('/export/individui/excel')
    @login_required
    def export_individui_excel():
        sito = request.args.get('sito', '').strip()
        rows = individui_service.list_individui(page=1, size=ALL_RECORDS_SIZE, sito=sito)
        data = [r for r in rows]
        filename = f'individui_{sito}.xlsx' if sito else 'individui.xlsx'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_excel(data, tmp, sheet_name='Individui'),
            '.xlsx', filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/export/individui/csv')
    @login_required
    def export_individui_csv():
        sito = request.args.get('sito', '').strip()
        rows = individui_service.list_individui(page=1, size=ALL_RECORDS_SIZE, sito=sito)
        data = [r for r in rows]
        filename = f'individui_{sito}.csv' if sito else 'individui.csv'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_csv(data, tmp),
            '.csv', filename, 'text/csv')

    @app.route('/export/individui/pdf')
    @login_required
    def export_individui_pdf():
        sito = request.args.get('sito', '').strip()
        rows = individui_service.list_individui(page=1, size=ALL_RECORDS_SIZE, sito=sito)
        filename = f'individui_{sito}.pdf' if sito else 'individui.pdf'
        logo = os.path.join(app.static_folder or '', 'images', 'logo.png')
        return _export_tmp_send(
            lambda tmp: pdf_generator.generate_entity_records_pdf(
                'individui', rows, tmp, logo_path=logo if os.path.exists(logo) else None),
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


def test_export_csv_contains_created_record(logged_in_client, individui_service):
    individui_service.create_individui({
        "sito": "Volterra",
        "nr_individuo": 1,
        "sesso": "Femmina",
    })
    r = logged_in_client.get("/export/individui/csv")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"Femmina" in r.data


def test_export_excel_returns_200_xlsx(logged_in_client, individui_service):
    individui_service.create_individui({"sito": "Volterra", "nr_individuo": 1, "sesso": "Maschio"})
    r = logged_in_client.get("/export/individui/excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.content_type


def test_export_pdf_returns_200_pdf(logged_in_client, individui_service):
    individui_service.create_individui({"sito": "Volterra", "nr_individuo": 1, "sesso": "Maschio"})
    r = logged_in_client.get("/export/individui/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data.startswith(b"%PDF")


def test_export_routes_registered(flask_app):
    """Confirm the excel/csv/pdf export routes are registered in the URL map
    (guards against a route being dropped/renamed silently)."""
    rules = {r.rule for r in flask_app.url_map.iter_rules()}
    assert '/export/individui/excel' in rules
    assert '/export/individui/csv' in rules
    assert '/export/individui/pdf' in rules

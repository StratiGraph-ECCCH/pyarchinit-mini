"""Route smoke tests for the SP4 UT export endpoints
(/export/ut/excel, /export/ut/csv, /export/ut/pdf).

UT's documentazione and bibliografia are Python-repr list-of-lists
sub-table columns (the classic plugin's str(table2dict()) format). The
excel/csv routes flatten them to readable strings first — same convention
as struttura/fauna/tomba (_flatten_ut_row in app.py). The PDF route instead
passes RAW record dicts straight to the classic-style sheet engine
(PDFGenerator.generate_entity_records_pdf), which parses the pylist
sub-tables itself. UT is project-scoped (filtered by ?progetto=, not
?sito=), mirroring app.py's ut_list route.
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
from pyarchinit_mini.services.ut_service import UtService
from pyarchinit_mini.services.struttura_service import parse_pylist as struttura_parse_pylist
from pyarchinit_mini.services.export_import_service import ExportImportService
from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser


@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "ut_export_routes.db"
    conn = DatabaseConnection.from_url(f"sqlite:///{db}")
    Base.metadata.create_all(conn.engine)
    return DatabaseManager(conn)


@pytest.fixture
def user_service(db_manager):
    return UserService(db_manager)


@pytest.fixture
def ut_service(db_manager):
    return UtService(db_manager)


@pytest.fixture
def flask_app(db_manager, ut_service, user_service):
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

    @app.route("/ut")
    @login_required
    def ut_list():
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

    def _flatten_ut_row(d):
        """Mirrors app.py's _flatten_ut_row (via _flatten_pylist_cols)."""
        out = dict(d)
        for col in ut_service.SUBTABLE_COLS:
            parsed = struttura_parse_pylist(out.get(col))
            out[col] = '; '.join(
                ' / '.join(str(cell) for cell in row) for row in parsed
            ) if parsed else ''
        return out

    @app.route('/export/ut/excel')
    @login_required
    def export_ut_excel():
        progetto = request.args.get('progetto', '').strip()
        rows = ut_service.list_ut(page=1, size=1_000_000, progetto=progetto)
        data = [_flatten_ut_row(r) for r in rows]
        filename = f'ut_{progetto}.xlsx' if progetto else 'ut.xlsx'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_excel(data, tmp, sheet_name='UT'),
            '.xlsx', filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.route('/export/ut/csv')
    @login_required
    def export_ut_csv():
        progetto = request.args.get('progetto', '').strip()
        rows = ut_service.list_ut(page=1, size=1_000_000, progetto=progetto)
        data = [_flatten_ut_row(r) for r in rows]
        filename = f'ut_{progetto}.csv' if progetto else 'ut.csv'
        return _export_tmp_send(
            lambda tmp: csv_excel_service.export_to_csv(data, tmp),
            '.csv', filename, 'text/csv')

    @app.route('/export/ut/pdf')
    @login_required
    def export_ut_pdf():
        progetto = request.args.get('progetto', '').strip()
        rows = ut_service.list_ut(page=1, size=1_000_000, progetto=progetto)
        filename = f'ut_{progetto}.pdf' if progetto else 'ut.pdf'
        logo = os.path.join(app.static_folder or '', 'images', 'logo.png')
        return _export_tmp_send(
            lambda tmp: pdf_generator.generate_entity_records_pdf(
                'ut', rows, tmp, logo_path=logo if os.path.exists(logo) else None),
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


def test_export_csv_returns_200_csv(logged_in_client, ut_service):
    ut_service.create_ut({"progetto": "ProgettoX", "ut_letterale": "A"})
    r = logged_in_client.get("/export/ut/csv")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"ProgettoX" in r.data


def test_export_excel_returns_200_xlsx(logged_in_client, ut_service):
    ut_service.create_ut({"progetto": "ProgettoX", "ut_letterale": "A"})
    r = logged_in_client.get("/export/ut/excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.content_type


def test_export_pdf_returns_200_pdf(logged_in_client, ut_service):
    ut_service.create_ut({"progetto": "ProgettoX", "ut_letterale": "A"})
    r = logged_in_client.get("/export/ut/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data.startswith(b"%PDF")


def test_export_csv_flattens_documentazione_and_bibliografia(logged_in_client, ut_service):
    """The stored Python-repr sub-tables must be flattened to readable
    'cell / cell' strings in exports — never dumped raw."""
    ut_service.create_ut({
        "progetto": "P1",
        "documentazione": '[["Fotografia","DSC001.jpg"]]',
        "bibliografia": '[["Rossi 1999"]]',
    })
    r = logged_in_client.get("/export/ut/csv")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Fotografia / DSC001.jpg" in body
    assert "Rossi 1999" in body
    assert "[['Fotografia'" not in body

"""
Task 6: Tomba nr_individuo auto-populate + dashboard/AI/MCP integration tests.

Mirrors tests/fauna/test_fauna_integration.py. Covers the behaviors added
when wiring individui into:
  - the MCP data import parser tool (_get_service_for_table)
  - the AI assistant system prompts (IT/EN deep links) + _build_context_block
  - the MCP pyarchinit_sync_tool input schema (data_types enum)
  - the new GET /api/tomba/individui route (the tomba<->individui auto-populate
    link: tomba's nr_individuo multi-select is populated from this endpoint)
"""

import os

import pytest
from flask import Flask, jsonify, request
from flask_login import login_required, login_user

from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.user import UserRole
from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.services.individui_service import IndividuiService
from pyarchinit_mini.web_interface.auth_routes import init_login_manager, User as AuthUser
from pyarchinit_mini.mcp_server.tools.data_import_parser_tool import DataImportParserTool
from pyarchinit_mini.mcp_server.tools.pyarchinit_sync_tool import PyArchInitSyncTool
from pyarchinit_mini.services import ai_assistant_service as m


# --------------------------------------------------------------------------
# MCP / AI prompt / sync-tool wiring (mirrors tests/fauna/test_fauna_integration.py)
# --------------------------------------------------------------------------

def _make_import_tool():
    """DataImportParserTool's real ctor is (db_session, config) via BaseTool.

    _get_service_for_table() reads self.db_manager (not self.db_session), which
    the production wiring (mcp_server/server.py) never actually sets on this
    tool today -- a pre-existing gap unrelated to this task. We construct the
    tool normally and then attach a stub db_manager attribute, since
    IndividuiService.__init__ only stores the reference and never touches it.
    """
    tool = DataImportParserTool(db_session=None, config=None)
    tool.db_manager = None
    return tool


def test_get_service_for_table_returns_individui_service():
    tool = _make_import_tool()
    svc = tool._get_service_for_table("individui_table")
    assert isinstance(svc, IndividuiService)
    assert type(svc).__name__ == "IndividuiService"


def test_individui_table_field_mappings_present():
    tool = _make_import_tool()
    mapping = tool.FIELD_MAPPINGS.get("individui_table")
    assert mapping is not None
    for field in ("sito", "area", "us", "nr_individuo", "sesso", "classi_eta"):
        assert field in mapping
        assert isinstance(mapping[field], list) and len(mapping[field]) > 0


def test_import_tool_schema_enum_has_individui_table():
    tool = _make_import_tool()
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["target_table"]["enum"]
    assert "individui_table" in enum


def test_ai_prompt_mentions_individui_it_and_en():
    assert "/individui" in m.SYSTEM_PROMPT_IT
    assert "/individui" in m.SYSTEM_PROMPT_EN


def test_sync_tool_data_types_enum_has_individui():
    tool = PyArchInitSyncTool(db_session=None, config=None)
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["data_types"]["items"]["enum"]
    assert "individui" in enum


def test_build_context_block_individui_summary():
    block = m._build_context_block({
        'individui_summary': {'total': 2, 'by_sesso': {'Maschio': 1}},
    })
    assert "INDIVIDUI" in block
    assert "Maschio" in block


# --------------------------------------------------------------------------
# PART A.3: GET /api/tomba/individui (the tomba<->individui auto-populate link)
#
# The real route body lives nested inside app.py's monolithic create_app()
# factory, so invoking it directly in a focused test is impractical -- this
# mirrors the established pattern (tests/tomba/test_tomba_routes.py,
# tests/individui/test_individui_routes.py): build a minimal Flask app,
# hand-copy the migrated route body (kept in lockstep with app.py's
# tomba_individui implementation) and reuse the real auth_routes login
# manager for authenticity.
# --------------------------------------------------------------------------

@pytest.fixture
def db_manager(tmp_path):
    db = tmp_path / "tomba_individui_api.db"
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
    """Minimal Flask app mounting ONLY /api/tomba/individui, hand-copied
    verbatim from app.py's tomba_individui route (the "===== Tomba -
    Sepolture =====" block), the same way /api/tomba/thesaurus/<field> is
    exercised in tests/tomba/test_tomba_routes.py."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.db_manager = db_manager
    app.individui_service = individui_service

    init_login_manager(app, user_service)

    # Test-only helper to establish a real flask-login session (mirrors what
    # the real /auth/login route does after password verification).
    @app.route("/_test/login/<int:user_id>")
    def _test_login(user_id):
        user_dict = user_service.get_user_by_id(user_id)
        login_user(AuthUser(user_dict))
        return ""

    # ---- /api/tomba/individui (mirrors app.py's tomba_individui) ----
    @app.route('/api/tomba/individui')
    @login_required
    def tomba_individui():
        sito = request.args.get('sito', '').strip()
        if not sito:
            return jsonify([])
        sigla_struttura = request.args.get('sigla_struttura', '').strip() or None
        nr_struttura = request.args.get('nr_struttura', '').strip() or None
        return jsonify(individui_service.get_nr_individui(sito, sigla_struttura, nr_struttura))

    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def write_user(user_service):
    """An OPERATOR-role user (has write/create permission) -- login_required
    only needs an authenticated session, but this mirrors the fixture the
    other route-test harnesses in this suite already use."""
    user = user_service.create_user(
        username="operator1", email="operator1@example.com", password="secret123",
        full_name="Operator One", role=UserRole.OPERATOR,
    )
    return user


@pytest.fixture
def logged_in_client(client, write_user):
    r = client.get(f"/_test/login/{write_user['id']}")
    assert r.status_code == 200
    return client


def test_tomba_individui_route_returns_filtered_list(logged_in_client, individui_service):
    individui_service.create_individui({
        "sito": "Volterra", "sigla_struttura": "TB", "nr_struttura": 1,
        "nr_individuo": 3, "sesso": "Maschio",
    })
    individui_service.create_individui({
        "sito": "Volterra", "sigla_struttura": "TB", "nr_struttura": 1,
        "nr_individuo": 1, "sesso": "Femmina",
    })
    individui_service.create_individui({
        "sito": "Volterra", "sigla_struttura": "TB", "nr_struttura": 2,
        "nr_individuo": 9, "sesso": "Maschio",
    })
    individui_service.create_individui({
        "sito": "Altrosito", "nr_individuo": 5, "sesso": "Maschio",
    })

    r = logged_in_client.get("/api/tomba/individui?sito=Volterra&sigla_struttura=TB&nr_struttura=1")
    assert r.status_code == 200
    assert r.get_json() == [1, 3]


def test_tomba_individui_route_missing_sito_returns_empty_list(logged_in_client):
    r = logged_in_client.get("/api/tomba/individui")
    assert r.status_code == 200
    assert r.get_json() == []

"""
Task 6: Fauna dashboard/AI/MCP integration tests.

Mirrors tests/struttura/test_struttura_integration.py. Covers the behaviors added
when wiring fauna into:
  - the MCP data import parser tool (_get_service_for_table)
  - the AI assistant system prompts (IT/EN deep links)
  - the MCP pyarchinit_sync_tool input schema (data_types enum)
"""

from pyarchinit_mini.mcp_server.tools.data_import_parser_tool import DataImportParserTool
from pyarchinit_mini.mcp_server.tools.pyarchinit_sync_tool import PyArchInitSyncTool
from pyarchinit_mini.services import ai_assistant_service as m
from pyarchinit_mini.services.fauna_service import FaunaService


def _make_import_tool():
    """DataImportParserTool's real ctor is (db_session, config) via BaseTool.

    _get_service_for_table() reads self.db_manager (not self.db_session), which
    the production wiring (mcp_server/server.py) never actually sets on this
    tool today -- a pre-existing gap unrelated to this task. We construct the
    tool normally and then attach a stub db_manager attribute, since
    FaunaService.__init__ only stores the reference and never touches it.
    """
    tool = DataImportParserTool(db_session=None, config=None)
    tool.db_manager = None
    return tool


def test_get_service_for_table_returns_fauna_service():
    tool = _make_import_tool()
    svc = tool._get_service_for_table("fauna_table")
    assert isinstance(svc, FaunaService)
    assert type(svc).__name__ == "FaunaService"


def test_fauna_table_field_mappings_present():
    tool = _make_import_tool()
    mapping = tool.FIELD_MAPPINGS.get("fauna_table")
    assert mapping is not None
    for field in ("sito", "area", "us", "specie", "contesto", "numero_minimo_individui"):
        assert field in mapping
        assert isinstance(mapping[field], list) and len(mapping[field]) > 0


def test_import_tool_schema_enum_has_fauna_table():
    tool = _make_import_tool()
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["target_table"]["enum"]
    assert "fauna_table" in enum


def test_ai_prompt_mentions_fauna_it_and_en():
    assert "/fauna" in m.SYSTEM_PROMPT_IT
    assert "/fauna" in m.SYSTEM_PROMPT_EN


def test_sync_tool_data_types_enum_has_fauna():
    tool = PyArchInitSyncTool(db_session=None, config=None)
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["data_types"]["items"]["enum"]
    assert "fauna" in enum

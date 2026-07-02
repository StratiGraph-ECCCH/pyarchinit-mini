"""
Task 6: Tomba dashboard/AI/MCP integration tests.

Covers the behaviors added when wiring tomba into:
  - the MCP data import parser tool (_get_service_for_table)
  - the AI assistant system prompts (IT/EN deep links)
  - the MCP pyarchinit_sync_tool input schema (data_types enum)
"""

from pyarchinit_mini.mcp_server.tools.data_import_parser_tool import DataImportParserTool
from pyarchinit_mini.mcp_server.tools.pyarchinit_sync_tool import PyArchInitSyncTool
from pyarchinit_mini.services import ai_assistant_service as m
from pyarchinit_mini.services.tomba_service import TombaService


def _make_import_tool():
    """DataImportParserTool's real ctor is (db_session, config) via BaseTool.

    _get_service_for_table() reads self.db_manager (not self.db_session), which
    the production wiring (mcp_server/server.py) never actually sets on this
    tool today -- a pre-existing gap unrelated to this task. We construct the
    tool normally and then attach a stub db_manager attribute, since
    TombaService.__init__ only stores the reference and never touches it.
    """
    tool = DataImportParserTool(db_session=None, config=None)
    tool.db_manager = None
    return tool


def test_get_service_for_table_returns_tomba_service():
    tool = _make_import_tool()
    svc = tool._get_service_for_table("tomba_table")
    assert isinstance(svc, TombaService)
    assert type(svc).__name__ == "TombaService"


def test_tomba_table_field_mappings_present():
    tool = _make_import_tool()
    mapping = tool.FIELD_MAPPINGS.get("tomba_table")
    assert mapping is not None
    for field in ("sito", "area", "nr_scheda_taf", "rito", "tipo_sepoltura", "descrizione_taf"):
        assert field in mapping
        assert isinstance(mapping[field], list) and len(mapping[field]) > 0


def test_import_tool_schema_enum_has_tomba_table():
    tool = _make_import_tool()
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["target_table"]["enum"]
    assert "tomba_table" in enum


def test_ai_prompt_mentions_tomba_it_and_en():
    assert "/tomba" in m.SYSTEM_PROMPT_IT
    assert "/tomba" in m.SYSTEM_PROMPT_EN


def test_sync_tool_data_types_enum_has_tomba():
    tool = PyArchInitSyncTool(db_session=None, config=None)
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["data_types"]["items"]["enum"]
    assert "tomba" in enum

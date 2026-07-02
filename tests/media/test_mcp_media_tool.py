import asyncio

import pytest
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from pyarchinit_mini.models.base import Base
from pyarchinit_mini.mcp_server.tools.media_management_tool import MediaManagementTool


def _png(tmp_path, name="a.png"):
    p = tmp_path / name
    Image.new("RGB", (300, 300)).save(p)
    return str(p)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tool(tmp_path, monkeypatch):
    # MediaManagementTool.execute() rebuilds its DatabaseManager from
    # `self.db_session.bind.url`, so a file-backed sqlite DB (not :memory:) is
    # required for the schema created here to still be visible to that
    # second engine.
    db_path = tmp_path / "mcp_media_test.db"
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    # execute() also constructs its own MediaHandler() with no args each
    # call - point it at a temp dir via env vars for isolation (mirrors the
    # fixture pattern in test_media_service_plugin.py).
    monkeypatch.setenv("PYARCHINIT_MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("PYARCHINIT_THUMB_PATH", str(tmp_path / "thumb"))
    monkeypatch.setenv("PYARCHINIT_THUMB_RESIZE", str(tmp_path / "resize"))

    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()

    return MediaManagementTool(db_session=db_session, config=None)


def test_entity_type_enum_has_new_plugin_keys(tool):
    schema = tool.to_tool_description().input_schema
    enum = schema["properties"]["entity_type"]["enum"]
    assert "pottery" in enum
    assert "ut" in enum
    assert set(enum) == {"us", "inventario", "pottery", "struttura", "tomba", "tma", "ut", "site"}


def test_operation_enum_drops_removed_ops(tool):
    schema = tool.to_tool_description().input_schema
    ops = schema["properties"]["operation"]["enum"]
    assert set(ops) == {"upload", "get", "list", "update", "delete"}


def test_upload_get_list_update_delete_roundtrip(tool, tmp_path):
    file_path = _png(tmp_path)

    upload_result = _run(tool.execute({
        "operation": "upload",
        "entity_type": "us",
        "entity_id": 42,
        "file_path": file_path,
        "description": "test photo",
        "tags": "test,photo",
    }))

    assert upload_result["success"] is True
    media_id = upload_result["result"]["media_id"]
    assert media_id is not None
    assert upload_result["result"]["filepath"].endswith("a.png")

    # get
    get_result = _run(tool.execute({"operation": "get", "media_id": media_id}))
    assert get_result["success"] is True
    assert get_result["result"]["filename"] == "a.png"
    assert get_result["result"]["mediatype"] == "image"

    # list - carries the new field names, not the removed ones
    list_result = _run(tool.execute({
        "operation": "list",
        "entity_type": "us",
        "entity_id": 42,
    }))
    assert list_result["success"] is True
    items = list_result["result"]["media_items"]
    assert len(items) == 1
    item = items[0]
    assert item["id_media"] == media_id
    assert item["filepath"].endswith("a.png")
    assert "filename" in item and "mediatype" in item
    for old_field in ("media_name", "media_type", "media_path", "file_size", "author", "is_primary"):
        assert old_field not in item

    # update - only descrizione/tags are writable
    update_result = _run(tool.execute({
        "operation": "update",
        "media_id": media_id,
        "description": "updated description",
    }))
    assert update_result["success"] is True
    assert update_result["result"]["descrizione"] == "updated description"

    # delete
    delete_result = _run(tool.execute({"operation": "delete", "media_id": media_id}))
    assert delete_result["success"] is True

    list_after_delete = _run(tool.execute({
        "operation": "list",
        "entity_type": "us",
        "entity_id": 42,
    }))
    assert list_after_delete["result"]["media_items"] == []


def test_set_primary_and_statistics_operations_removed(tool):
    result = _run(tool.execute({"operation": "set_primary", "media_id": 1}))
    assert result["success"] is False

    result = _run(tool.execute({"operation": "statistics"}))
    assert result["success"] is False

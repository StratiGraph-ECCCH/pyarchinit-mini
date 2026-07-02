# -*- coding: utf-8 -*-
"""Test that media tables are excluded from concurrency locking."""
from pyarchinit_mini.database.concurrency_manager import ID_FIELD_MAPPINGS


def test_media_tables_not_lockable():
    """Media tables lack version_number/editing_by, so must be excluded from locking."""
    assert "media_table" not in ID_FIELD_MAPPINGS
    assert "media_thumb_table" not in ID_FIELD_MAPPINGS
    assert "media_to_entity_table" not in ID_FIELD_MAPPINGS


def test_documentation_still_lockable():
    """Verify documentation_table remains in the mapping."""
    assert ID_FIELD_MAPPINGS["documentation_table"] == "id_documentazione"

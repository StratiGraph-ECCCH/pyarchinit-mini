"""
Contract tests for PyArchInitSyncTool's reading of ImportExportService
return dicts.

The service methods (import_sites/import_us/import_inventario/export_sites/
export_us, and the future tomba/struttura/fauna/ut equivalents) all return
{'imported'|'exported': int, 'updated': int, 'skipped': int, 'errors': list}
(no 'success' key, no '<type>_imported'/'<type>_exported' keys). The tool
used to read the wrong keys (e.g. 'sites_imported', 'success') so counts
silently read as 0 and errors were swallowed. These tests pin the fixed
contract using a stub service - no real DB/ImportExportService needed.

_import_data()/_export_data() are plain sync methods (unlike execute(),
which is async and constructs its own ImportExportService), so they're the
smallest reachable unit for this contract.
"""

from pyarchinit_mini.mcp_server.tools.pyarchinit_sync_tool import PyArchInitSyncTool


def _tool():
    return PyArchInitSyncTool(db_session=None, config=None)


class _StubService:
    """Stand-in for ImportExportService; each attribute is set per-test
    to a callable returning the service-contract dict."""


def test_import_sites_reads_imported_key_and_surfaces_errors():
    tool = _tool()
    service = _StubService()
    service.import_sites = lambda **kwargs: {
        'imported': 5, 'updated': 1, 'skipped': 0, 'errors': ['boom']
    }

    result = tool._import_data(service, ['sites'], None, True)

    assert result['imported']['sites'] == 5
    assert any('boom' in e for e in result['errors'])


def test_import_us_reads_imported_and_relationships_created():
    tool = _tool()
    service = _StubService()
    service.import_us = lambda **kwargs: {
        'imported': 3, 'updated': 0, 'skipped': 0,
        'relationships_created': 2, 'errors': []
    }

    result = tool._import_data(service, ['us'], None, True)

    assert result['imported']['us'] == 3
    assert result['imported']['relationships'] == 2
    assert result['errors'] == []


def test_import_inventario_branch_reads_imported_key():
    """Regression: 'inventario' is in the data_types enum but previously had
    no import branch at all in _import_data - it silently did nothing."""
    tool = _tool()
    service = _StubService()
    service.import_inventario = lambda **kwargs: {
        'imported': 7, 'updated': 0, 'skipped': 0, 'errors': []
    }

    result = tool._import_data(service, ['inventario'], None, True)

    assert result['imported']['inventario'] == 7


def test_import_backup_path_propagated_from_service():
    tool = _tool()
    service = _StubService()
    service.import_sites = lambda **kwargs: {
        'imported': 1, 'updated': 0, 'skipped': 0, 'errors': [],
        'backup_path': '/tmp/backup.db'
    }

    result = tool._import_data(service, ['sites'], None, True)

    assert result['backup_path'] == '/tmp/backup.db'


def test_export_sites_reads_exported_key_and_surfaces_errors():
    tool = _tool()
    service = _StubService()
    service.export_sites = lambda **kwargs: {
        'exported': 4, 'updated': 0, 'skipped': 0, 'errors': ['oops']
    }

    result = tool._export_data(service, 'sqlite:///target.db', ['sites'], None)

    assert result['exported']['sites'] == 4
    assert any('oops' in e for e in result['errors'])


def test_export_us_reads_exported_key():
    tool = _tool()
    service = _StubService()
    service.export_us = lambda **kwargs: {
        'exported': 6, 'updated': 0, 'skipped': 0, 'errors': []
    }

    result = tool._export_data(service, 'sqlite:///target.db', ['us'], None)

    assert result['exported']['us'] == 6
    assert result['errors'] == []

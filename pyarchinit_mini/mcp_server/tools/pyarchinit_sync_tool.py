"""
PyArchInit Sync Tool

Imports and exports data between PyArchInit (full version) and PyArchInit-Mini.
Handles sites, stratigraphic units, inventories, and thesaurus data.
"""

import logging
from typing import Dict, Any
from .base_tool import BaseTool, ToolDescription

logger = logging.getLogger(__name__)


class PyArchInitSyncTool(BaseTool):
    """PyArchInit Sync - Import/export data from/to PyArchInit full version"""

    def to_tool_description(self) -> ToolDescription:
        return ToolDescription(
            name="pyarchinit_sync",
            description=(
                "Synchronize data between PyArchInit (full version) and PyArchInit-Mini. "
                "Import sites, US, inventories from PyArchInit or export data to PyArchInit. "
                "Automatically creates backups and handles database migrations."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["import", "export"],
                        "description": "Operation: import (from PyArchInit) or export (to PyArchInit)"
                    },
                    "source_db_url": {
                        "type": "string",
                        "description": "Source database URL (e.g., 'sqlite:///path/to/pyarchinit.db' or 'postgresql://user:pass@host/dbname')"
                    },
                    "data_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["sites", "us", "inventario", "thesaurus", "tomba", "struttura", "fauna"]},
                        "description": "Types of data to sync: sites, us, inventario, thesaurus, tomba, struttura, fauna",
                        "default": ["sites", "us"]
                    },
                    "site_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: filter by site names (empty = all sites)"
                    },
                    "auto_backup": {
                        "type": "boolean",
                        "description": "Create automatic backup before operation",
                        "default": True
                    }
                },
                "required": ["operation", "source_db_url"],
            },
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PyArchInit sync operation"""
        try:
            operation = arguments.get("operation")
            source_db_url = arguments.get("source_db_url")
            data_types = arguments.get("data_types", ["sites", "us"])
            site_filter = arguments.get("site_filter")
            auto_backup = arguments.get("auto_backup", True)

            if not operation or not source_db_url:
                return self._format_error("Both operation and source_db_url are required")

            logger.info(f"PyArchInit sync: {operation} from {source_db_url}, data_types={data_types}")

            # Get current database URL
            import os
            mini_db_url = getattr(self.config, 'database_url', None) or os.getenv('DATABASE_URL', 'sqlite:///pyarchinit_mini.db')

            # Create service
            from pyarchinit_mini.services.import_export_service import ImportExportService

            if operation == "import":
                service = ImportExportService(mini_db_connection=mini_db_url, source_db_connection=source_db_url)
                result = self._import_data(service, data_types, site_filter, auto_backup)
            else:  # export
                service = ImportExportService(mini_db_connection=mini_db_url)
                result = self._export_data(service, source_db_url, data_types, site_filter)

            if result.get('success'):
                return self._format_success(result, f"Successfully completed {operation} operation")
            else:
                return self._format_error(result.get('message', f'{operation.capitalize()} failed'))

        except Exception as e:
            logger.error(f"PyArchInit sync error: {str(e)}", exc_info=True)
            return self._format_error(f"Sync failed: {str(e)}")

    def _import_data(self, service, data_types: list, site_filter: list, auto_backup: bool) -> Dict[str, Any]:
        """Import data from PyArchInit"""
        results = {'success': True, 'imported': {}, 'backup_path': None, 'errors': []}

        try:
            # Import sites
            if 'sites' in data_types:
                logger.info("Importing sites...")
                site_result = service.import_sites(sito_filter=site_filter, auto_backup=auto_backup)
                results['imported']['sites'] = site_result.get('sites_imported', 0)
                if site_result.get('backup_path'):
                    results['backup_path'] = site_result['backup_path']
                if not site_result.get('success', True):
                    results['errors'].append(f"Sites import: {site_result.get('message', 'failed')}")

            # Import US
            if 'us' in data_types:
                logger.info("Importing US...")
                us_result = service.import_us(sito_filter=site_filter, auto_backup=auto_backup)
                results['imported']['us'] = us_result.get('us_imported', 0)
                results['imported']['relationships'] = us_result.get('relationships_created', 0)
                if not results['backup_path'] and us_result.get('backup_path'):
                    results['backup_path'] = us_result['backup_path']
                if not us_result.get('success', True):
                    results['errors'].append(f"US import: {us_result.get('message', 'failed')}")

            # Import tomba (burials)
            if 'tomba' in data_types:
                logger.info("Importing tomba...")
                if hasattr(service, 'import_tomba'):
                    tomba_result = service.import_tomba(sito_filter=site_filter, auto_backup=auto_backup)
                    results['imported']['tomba'] = tomba_result.get('tomba_imported', 0)
                    if not results['backup_path'] and tomba_result.get('backup_path'):
                        results['backup_path'] = tomba_result['backup_path']
                    if not tomba_result.get('success', True):
                        results['errors'].append(f"Tomba import: {tomba_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Tomba import: not yet supported by ImportExportService")

            # Import struttura (structures)
            if 'struttura' in data_types:
                logger.info("Importing struttura...")
                if hasattr(service, 'import_struttura'):
                    struttura_result = service.import_struttura(sito_filter=site_filter, auto_backup=auto_backup)
                    results['imported']['struttura'] = struttura_result.get('struttura_imported', 0)
                    if not results['backup_path'] and struttura_result.get('backup_path'):
                        results['backup_path'] = struttura_result['backup_path']
                    if not struttura_result.get('success', True):
                        results['errors'].append(f"Struttura import: {struttura_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Struttura import: not yet supported by ImportExportService")

            # Import fauna (archaeozoology)
            if 'fauna' in data_types:
                logger.info("Importing fauna...")
                if hasattr(service, 'import_fauna'):
                    fauna_result = service.import_fauna(sito_filter=site_filter, auto_backup=auto_backup)
                    results['imported']['fauna'] = fauna_result.get('fauna_imported', 0)
                    if not results['backup_path'] and fauna_result.get('backup_path'):
                        results['backup_path'] = fauna_result['backup_path']
                    if not fauna_result.get('success', True):
                        results['errors'].append(f"Fauna import: {fauna_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Fauna import: not yet supported by ImportExportService")

            # Import thesaurus
            if 'thesaurus' in data_types:
                logger.info("Importing thesaurus...")
                thes_result = service.import_thesaurus()
                results['imported']['thesaurus'] = thes_result.get('total_imported', 0)
                if not thes_result.get('success', True):
                    results['errors'].append(f"Thesaurus import: {thes_result.get('message', 'failed')}")

            if results['errors']:
                results['success'] = len(results['errors']) < len(data_types)  # Partial success
                results['message'] = f"Import completed with {len(results['errors'])} errors"
            else:
                results['message'] = f"Successfully imported all data types"

            return results

        except Exception as e:
            return {'success': False, 'message': f'Import failed: {str(e)}'}

    def _export_data(self, service, target_db_url: str, data_types: list, site_filter: list) -> Dict[str, Any]:
        """Export data to PyArchInit"""
        results = {'success': True, 'exported': {}, 'errors': []}

        try:
            # Export sites
            if 'sites' in data_types:
                logger.info("Exporting sites...")
                site_result = service.export_sites(target_db_connection=target_db_url, sito_filter=site_filter)
                results['exported']['sites'] = site_result.get('sites_exported', 0)
                if not site_result.get('success', True):
                    results['errors'].append(f"Sites export: {site_result.get('message', 'failed')}")

            # Export US
            if 'us' in data_types:
                logger.info("Exporting US...")
                us_result = service.export_us(target_db_connection=target_db_url, sito_filter=site_filter)
                results['exported']['us'] = us_result.get('us_exported', 0)
                results['exported']['relationships'] = us_result.get('relationships_exported', 0)
                if not us_result.get('success', True):
                    results['errors'].append(f"US export: {us_result.get('message', 'failed')}")

            # Export tomba (burials)
            if 'tomba' in data_types:
                logger.info("Exporting tomba...")
                if hasattr(service, 'export_tomba'):
                    tomba_result = service.export_tomba(target_db_connection=target_db_url, sito_filter=site_filter)
                    results['exported']['tomba'] = tomba_result.get('tomba_exported', 0)
                    if not tomba_result.get('success', True):
                        results['errors'].append(f"Tomba export: {tomba_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Tomba export: not yet supported by ImportExportService")

            # Export struttura (structures)
            if 'struttura' in data_types:
                logger.info("Exporting struttura...")
                if hasattr(service, 'export_struttura'):
                    struttura_result = service.export_struttura(target_db_connection=target_db_url, sito_filter=site_filter)
                    results['exported']['struttura'] = struttura_result.get('struttura_exported', 0)
                    if not struttura_result.get('success', True):
                        results['errors'].append(f"Struttura export: {struttura_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Struttura export: not yet supported by ImportExportService")

            # Export fauna (archaeozoology)
            if 'fauna' in data_types:
                logger.info("Exporting fauna...")
                if hasattr(service, 'export_fauna'):
                    fauna_result = service.export_fauna(target_db_connection=target_db_url, sito_filter=site_filter)
                    results['exported']['fauna'] = fauna_result.get('fauna_exported', 0)
                    if not fauna_result.get('success', True):
                        results['errors'].append(f"Fauna export: {fauna_result.get('message', 'failed')}")
                else:
                    results['errors'].append("Fauna export: not yet supported by ImportExportService")

            if results['errors']:
                results['success'] = len(results['errors']) < len(data_types)
                results['message'] = f"Export completed with {len(results['errors'])} errors"
            else:
                results['message'] = f"Successfully exported all data types"

            return results

        except Exception as e:
            return {'success': False, 'message': f'Export failed: {str(e)}'}

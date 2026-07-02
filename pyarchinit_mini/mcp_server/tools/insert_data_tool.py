"""
Insert Data Tool - Database Record Insertion for MCP

This tool enables AI assistants to insert new archaeological records into the database.
Features:
- Support for all PyArchInit tables (sites, US, inventario, datazioni, relationships)
- Automatic field validation (required fields, data types, constraints)
- Foreign key validation
- Transaction safety (rollback on error)
- Works with both SQLite and PostgreSQL
- Detailed error messages for troubleshooting
- Automatic datetime conversion from ISO strings
"""

import logging
import os
from datetime import datetime, date
from sqlalchemy import Table, MetaData, inspect, DateTime, Date
from sqlalchemy.exc import IntegrityError, DataError
from typing import Dict, Any, Optional
from pyarchinit_mini.database.connection import DatabaseConnection
from pyarchinit_mini.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


def insert_data(
    table: str,
    data: Dict[str, Any],
    validate_only: bool = False
) -> dict:
    """
    Insert a new record into a PyArchInit table.

    Args:
        table: Table name to insert into.
               Supports ALL database tables including: site_table, us_table,
               inventario_materiali_table, datazioni_table, us_relationships_table,
               periodizzazione tables, media tables, thesaurus tables, users table, etc.
        data: Dictionary of field_name -> value pairs.
              Do NOT include auto-increment primary key fields (like "id").
              Example: {"sito": "Pompei", "area": 1, "us": 100, "unita_tipo": "US"}
        validate_only: If True, only validate data without inserting (dry-run mode)

    Returns:
        dict: Result with structure:
        {
            "success": True | False,
            "message": "Success/error message",
            "inserted_id": <new record ID> (only if success=True),
            "validation_errors": [...] (only if validation failed),
            "data": {...} (echoed data if validate_only=True)
        }

    Examples:
        # Insert a new site
        result = insert_data(
            table="site_table",
            data={
                "sito": "Tempio della Fortuna",
                "location": "Palestrina",
                "nazione": "Italia",
                "tipologia": "Santuario"
            }
        )

        # Insert a new US (Stratigraphic Unit)
        result = insert_data(
            table="us_table",
            data={
                "sito": "Pompei",
                "area": 1,
                "us": 150,
                "unita_tipo": "US",
                "definizione_stratigrafica": "Strato",
                "descrizione": "Strato di crollo",
                "periodo": "Romano"
            }
        )

        # Validate without inserting
        result = insert_data(
            table="us_table",
            data={"sito": "Test", "area": 1, "us": 200},
            validate_only=True
        )

    Notes:
        - Auto-increment fields (like "id") are generated automatically - do NOT include them
        - Required fields must be provided (check schema first with get_schema tool)
        - Foreign keys are validated (e.g., "sito" in us_table must exist in site_table)
        - For SQLite: INTEGER PRIMARY KEY is auto-increment
        - For PostgreSQL: SERIAL fields are auto-increment
    """
    try:
        # Get database connection - use config default if DATABASE_URL not set
        from pyarchinit_mini.mcp_server.config import _get_default_database_url
        database_url = os.getenv("DATABASE_URL") or _get_default_database_url()
        db_connection = DatabaseConnection(database_url)
        db_manager = DatabaseManager(db_connection)
        engine = db_connection.engine
        metadata = MetaData()
        inspector = inspect(engine)

        # Detect database type
        db_type = "sqlite" if "sqlite" in str(engine.url) else "postgresql"

        # Validate table exists in database
        all_tables = inspector.get_table_names()
        if table not in all_tables:
            return {
                "success": False,
                "error": "table_not_found",
                "message": f"Table '{table}' does not exist in database",
                "available_tables": all_tables
            }

        # ⚠️ BLOCK DIRECT MEDIA TABLE INSERTS - Use manage_media tool instead
        MEDIA_TABLES = ["media_table", "media_thumb_table"]
        if table in MEDIA_TABLES:
            return {
                "success": False,
                "error": "use_manage_media_tool",
                "message": (
                    f"❌ Direct insert into '{table}' is not allowed. "
                    f"Media files must be uploaded using the 'manage_media' tool "
                    f"to ensure proper file storage and path management. "
                    f"\n\n📋 How to use manage_media:\n"
                    f"1. Upload file with operation='upload'\n"
                    f"2. Provide entity_type (one of: us, inventario, pottery, struttura, tomba, tma, ut, site)\n"
                    f"3. Provide entity_id (the entity's integer primary key, e.g. id_sito, id_us, id_invmat)\n"
                    f"4. Either provide file_path on server OR file_content_base64\n"
                    f"5. The tool will copy files to ~/.pyarchinit_mini/media/ and create DB record\n\n"
                    f"Example:\n"
                    f"{{\n"
                    f"  'operation': 'upload',\n"
                    f"  'entity_type': 'site',\n"
                    f"  'entity_id': 12,\n"
                    f"  'file_content_base64': '<base64-encoded-content>',\n"
                    f"  'filename': 'site_photo.jpg',\n"
                    f"  'description': 'Site overview'\n"
                    f"}}\n\n"
                    f"This ensures files are stored permanently in the correct location, "
                    f"not in temporary directories like /tmp/ where they will be lost."
                ),
                "correct_tool": "manage_media",
                "tool_operations": ["upload", "get", "list", "update", "delete"]
            }

        # Reflect table structure
        table_obj = Table(table, metadata, autoload_with=engine)

        # Validate data
        validation_errors = []

        # Get primary key columns
        pk_constraint = inspector.get_pk_constraint(table)
        pk_columns = pk_constraint.get('constrained_columns', []) if pk_constraint else []

        # Get column information
        columns = inspector.get_columns(table)
        column_info = {col['name']: col for col in columns}

        # Check for auto-increment primary keys in data (should NOT be provided)
        for col_name in pk_columns:
            if col_name in data:
                col = column_info.get(col_name)
                if col:
                    is_autoincrement = False
                    if db_type == "sqlite":
                        # SQLite: INTEGER PRIMARY KEY is auto-increment
                        is_autoincrement = "INTEGER" in str(col['type']).upper()
                    else:  # postgresql
                        # PostgreSQL: SERIAL or has default sequence
                        is_autoincrement = (
                            col.get('autoincrement', False) or
                            'SERIAL' in str(col['type']).upper() or
                            (col.get('default', '') or '').startswith('nextval')
                        )

                    if is_autoincrement:
                        validation_errors.append({
                            "field": col_name,
                            "error": "auto_increment_field_provided",
                            "message": f"Field '{col_name}' is auto-increment - do NOT provide it in data"
                        })

        # Check required fields
        for col_name, col_info in column_info.items():
            is_required = not col_info.get('nullable', True)
            is_pk = col_name in pk_columns
            has_default = col_info.get('default') is not None

            # Skip auto-increment primary keys
            if is_pk:
                col_type = str(col_info['type'])
                is_autoincrement = False
                if db_type == "sqlite":
                    is_autoincrement = "INTEGER" in col_type.upper()
                else:  # postgresql
                    is_autoincrement = (
                        col_info.get('autoincrement', False) or
                        'SERIAL' in col_type.upper() or
                        (col_info.get('default', '') or '').startswith('nextval')
                    )

                if is_autoincrement:
                    continue

            # Field is required if: NOT NULL, no default, and not auto-increment
            if is_required and not has_default and col_name not in data:
                validation_errors.append({
                    "field": col_name,
                    "error": "required_field_missing",
                    "message": f"Required field '{col_name}' is missing"
                })

        # Check for unknown fields
        for field_name in data.keys():
            if field_name not in column_info:
                validation_errors.append({
                    "field": field_name,
                    "error": "unknown_field",
                    "message": f"Field '{field_name}' does not exist in table '{table}'"
                })

        # Check foreign key constraints
        foreign_keys = inspector.get_foreign_keys(table)
        for fk in foreign_keys:
            constrained_cols = fk.get('constrained_columns', [])
            referred_table = fk.get('referred_table')
            referred_cols = fk.get('referred_columns', [])

            for i, col_name in enumerate(constrained_cols):
                if col_name in data:
                    value = data[col_name]
                    if value is not None:  # NULL is allowed for optional foreign keys
                        # Check if referenced value exists
                        referred_col = referred_cols[i] if i < len(referred_cols) else 'id'
                        ref_table = Table(referred_table, MetaData(), autoload_with=engine)

                        with engine.connect() as conn:
                            result = conn.execute(
                                ref_table.select().where(
                                    getattr(ref_table.c, referred_col) == value
                                )
                            ).fetchone()

                            if not result:
                                validation_errors.append({
                                    "field": col_name,
                                    "error": "foreign_key_violation",
                                    "message": f"Value '{value}' for field '{col_name}' does not exist in {referred_table}.{referred_col}"
                                })

        # If validation errors, return them
        if validation_errors:
            return {
                "success": False,
                "error": "validation_failed",
                "message": f"Data validation failed with {len(validation_errors)} error(s)",
                "validation_errors": validation_errors
            }

        # If validate_only mode, return success without inserting
        if validate_only:
            return {
                "success": True,
                "message": "Data validation passed - ready to insert",
                "data": data
            }

        # Convert datetime strings to datetime objects
        # SQLAlchemy requires Python datetime objects for DateTime columns
        converted_data = {}
        for field_name, value in data.items():
            if field_name in column_info:
                col_type = column_info[field_name]['type']

                # Check if this is a DateTime column
                if isinstance(col_type, DateTime):
                    if isinstance(value, str) and value:
                        # Try to parse ISO format datetime string
                        try:
                            # Support common ISO formats
                            # 2025-11-02T10:00:00, 2025-11-02 10:00:00, 2025-11-02T10:00:00Z
                            value_clean = value.replace('Z', '').replace('T', ' ').strip()

                            # Try parsing with different formats
                            for fmt in [
                                '%Y-%m-%d %H:%M:%S.%f',  # With microseconds
                                '%Y-%m-%d %H:%M:%S',     # Without microseconds
                                '%Y-%m-%d',              # Date only
                            ]:
                                try:
                                    converted_data[field_name] = datetime.strptime(value_clean, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                # If no format matched, leave as is (will fail later with clear error)
                                converted_data[field_name] = value
                        except Exception:
                            # If conversion fails, leave as is
                            converted_data[field_name] = value
                    else:
                        # Already a datetime object or None
                        converted_data[field_name] = value

                # Handle Date fields (date only, no time)
                elif isinstance(col_type, Date):
                    if isinstance(value, str) and value:
                        try:
                            value_clean = value.strip()
                            # Try parsing as date-only string
                            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                try:
                                    converted_data[field_name] = datetime.strptime(value_clean, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                converted_data[field_name] = value
                        except Exception:
                            converted_data[field_name] = value
                    else:
                        converted_data[field_name] = value
                else:
                    # Not a datetime/date column, use as is
                    converted_data[field_name] = value
            else:
                # Unknown column (already validated), use as is
                converted_data[field_name] = value

        # Insert data with converted datetime values
        with engine.begin() as conn:  # Transaction automatically commits or rolls back
            result = conn.execute(table_obj.insert().values(**converted_data))

            # Get the inserted ID
            inserted_id = result.inserted_primary_key[0] if result.inserted_primary_key else None

            return {
                "success": True,
                "message": f"Record inserted successfully into {table}",
                "inserted_id": inserted_id,
                "data": data
            }

    except IntegrityError as e:
        # Database constraint violation (unique, foreign key, etc.)
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Integrity error inserting into {table}: {error_msg}", exc_info=True)

        return {
            "success": False,
            "error": "integrity_error",
            "message": f"Database constraint violation: {error_msg}",
            "details": "This usually means:\n"
                      "- Duplicate value in unique field\n"
                      "- Foreign key reference doesn't exist\n"
                      "- NOT NULL constraint violated"
        }

    except DataError as e:
        # Data type mismatch
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Data type error inserting into {table}: {error_msg}", exc_info=True)

        return {
            "success": False,
            "error": "data_type_error",
            "message": f"Data type mismatch: {error_msg}",
            "details": "This usually means:\n"
                      "- String provided for integer field\n"
                      "- Invalid date format\n"
                      "- Value too long for field",
            "retry_suggestion": (
                "IMPORTANT: This tool (PyArchInit manage_data) now supports automatic datetime conversion. "
                "If this error is related to timestamps, the issue has been fixed - please retry "
                "the same operation with the SAME data using this tool."
            )
        }

    except Exception as e:
        logger.error(f"Error inserting data into {table}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to insert data into {table}: {str(e)}"
        }

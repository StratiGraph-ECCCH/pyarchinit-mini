# -*- coding: utf-8 -*-
"""Concurrency management: optimistic locking + soft record locking."""
import logging
from datetime import datetime, timezone
from sqlalchemy import text

logger = logging.getLogger(__name__)

ID_FIELD_MAPPINGS = {
    'us_table': 'id_us',
    'inventario_materiali_table': 'id_invmat',
    'site_table': 'id_sito',
    'periodizzazione_table': 'id_perfas',
    'struttura_table': 'id_struttura',
    'tomba_table': 'id_tomba',
    'campioni_table': 'id_campione',
    'individui_table': 'id_individuo',
    'tafonomia_table': 'id_tafonomia',
    'documentation_table': 'id_documentazione',
    'pottery_table': 'id_rep',
}


class ConcurrencyManager:
    """Manages optimistic locking and soft record locking.

    Uses version_number for optimistic locking (conflict detection)
    and editing_by/editing_since for soft record locking.
    """

    def __init__(self, connection):
        """
        Args:
            connection: DatabaseConnection instance with get_session() method.
        """
        self.connection = connection

    def _get_id_field(self, table_name):
        return ID_FIELD_MAPPINGS.get(table_name)

    def check_version_conflict(self, table_name, record_id, expected_version):
        """Check if a record's version matches the expected version.

        Returns None if no conflict, or a dict with conflict details.
        """
        id_field = self._get_id_field(table_name)
        if not id_field:
            return None
        with self.connection.get_session() as session:
            row = session.execute(
                text(f"SELECT version_number, last_modified_by, last_modified_timestamp "
                     f"FROM {table_name} WHERE {id_field} = :rid"),
                {"rid": record_id}
            ).fetchone()
            if row is None:
                return None
            current_version = row[0] or 1
            if current_version != expected_version:
                return {
                    "current_version": current_version,
                    "expected_version": expected_version,
                    "last_modified_by": row[1],
                    "last_modified_timestamp": row[2],
                }
            return None

    def lock_record(self, table_name, record_id, username):
        """Soft-lock a record for editing.

        Returns True if lock acquired, False if already locked by another user.
        """
        id_field = self._get_id_field(table_name)
        if not id_field:
            return False
        with self.connection.get_session() as session:
            row = session.execute(
                text(f"SELECT editing_by FROM {table_name} WHERE {id_field} = :rid"),
                {"rid": record_id}
            ).fetchone()
            if row and row[0] and row[0] != username:
                return False
            session.execute(
                text(f"UPDATE {table_name} SET editing_by = :user, "
                     f"editing_since = :since WHERE {id_field} = :rid"),
                {"user": username, "since": datetime.now(timezone.utc), "rid": record_id}
            )
            session.commit()
            return True

    def unlock_record(self, table_name, record_id, username):
        """Release soft-lock on a record.

        Returns True if unlocked, False if table not recognized.
        """
        id_field = self._get_id_field(table_name)
        if not id_field:
            return False
        with self.connection.get_session() as session:
            session.execute(
                text(f"UPDATE {table_name} SET editing_by = NULL, "
                     f"editing_since = NULL WHERE {id_field} = :rid AND editing_by = :user"),
                {"rid": record_id, "user": username}
            )
            session.commit()
            return True

    def get_active_editors(self, table_name):
        """Get all currently locked records in a table.

        Returns list of dicts with record_id, user, since.
        """
        id_field = self._get_id_field(table_name)
        if not id_field:
            return []
        with self.connection.get_session() as session:
            rows = session.execute(
                text(f"SELECT {id_field}, editing_by, editing_since "
                     f"FROM {table_name} WHERE editing_by IS NOT NULL")
            ).fetchall()
            return [{"record_id": r[0], "user": r[1], "since": r[2]} for r in rows]

    def increment_version(self, table_name, record_id, username):
        """Increment version_number and update modification tracking."""
        id_field = self._get_id_field(table_name)
        if not id_field:
            return
        with self.connection.get_session() as session:
            session.execute(
                text(f"UPDATE {table_name} SET version_number = version_number + 1, "
                     f"last_modified_by = :user, last_modified_timestamp = :ts, "
                     f"sync_status = 'modified' WHERE {id_field} = :rid"),
                {"user": username, "ts": datetime.now(timezone.utc), "rid": record_id}
            )
            session.commit()

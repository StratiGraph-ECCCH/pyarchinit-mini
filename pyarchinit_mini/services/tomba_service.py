"""
Tomba Service — manages tomba_table (burial) records.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_
from sqlalchemy import Integer as _SAInteger

from pyarchinit_mini.models.tomba import Tomba

logger = logging.getLogger(__name__)


def _coerce_types(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce string values destined for Integer columns to int.

    Text form inputs feed Integer columns (area, nr_scheda_taf, ...);
    non-numeric input saves fine on SQLite (dynamic typing) but fails the
    whole INSERT/UPDATE on Postgres. Convert non-empty strings to int();
    if unparseable, fall back to None instead of raising. Generic over the
    model's Integer columns so other record types can reuse this helper.
    """
    integer_cols = {
        c.name for c in model.__table__.columns
        if isinstance(c.type, _SAInteger)
    }
    coerced = dict(data)
    for key in integer_cols:
        if key not in coerced:
            continue
        value = coerced[key]
        if value is None or isinstance(value, int):
            continue
        if isinstance(value, str):
            value = value.strip()
        if value == '':
            coerced[key] = None
            continue
        try:
            coerced[key] = int(value)
        except (TypeError, ValueError):
            coerced[key] = None
    return coerced


class TombaService:
    """Service for Tomba (burial) records."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def list_tomba(self, page: int = 1, size: int = 50, search: str = '',
                    sito: str = '') -> List[Dict[str, Any]]:
        """List Tomba records with optional filters."""
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Tomba)
                if sito:
                    q = q.filter(Tomba.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Tomba.sito.ilike(pat),
                        Tomba.rito.ilike(pat),
                        Tomba.sigla_struttura.ilike(pat),
                        Tomba.nr_individuo.ilike(pat),
                    ))
                q = q.order_by(Tomba.id_tomba.desc())
                offset = (page - 1) * size
                rows = q.offset(offset).limit(size).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            logger.error(f"list_tomba failed: {e}")
            return []

    def count_tomba(self, search: str = '', sito: str = '') -> int:
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Tomba)
                if sito:
                    q = q.filter(Tomba.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Tomba.sito.ilike(pat),
                        Tomba.rito.ilike(pat),
                        Tomba.sigla_struttura.ilike(pat),
                        Tomba.nr_individuo.ilike(pat),
                    ))
                return q.count()
        except Exception:
            return 0

    def get_tomba(self, tomba_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Tomba).filter(
                    Tomba.id_tomba == tomba_id).first()
                return row.to_dict() if row else None
        except Exception as e:
            logger.error(f"get_tomba failed: {e}")
            return None

    def create_tomba(self, data: Dict[str, Any]) -> Optional[int]:
        try:
            with self.db_manager.connection.get_session() as session:
                valid_keys = Tomba.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys and v is not None and v != ''}
                clean = _coerce_types(Tomba, clean)
                row = Tomba(**clean)
                session.add(row)
                session.flush()
                tomba_id = row.id_tomba
                session.commit()
                return tomba_id
        except Exception as e:
            logger.error(f"create_tomba failed: {e}")
            return None

    def update_tomba(self, tomba_id: int, data: Dict[str, Any]) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Tomba).filter(
                    Tomba.id_tomba == tomba_id).first()
                if not row:
                    return False
                valid_keys = Tomba.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys}
                clean = _coerce_types(Tomba, clean)
                for k, v in clean.items():
                    setattr(row, k, v if v != '' else None)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"update_tomba failed: {e}")
            return False

    def delete_tomba(self, tomba_id: int) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Tomba).filter(
                    Tomba.id_tomba == tomba_id).first()
                if row:
                    session.delete(row)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"delete_tomba failed: {e}")
            return False

    # ---------------- Thesaurus integration ----------------

    THESAURUS_TABLE = 'tomba_table'

    def get_thesaurus_values(self, field: str) -> List[Dict[str, str]]:
        """Return thesaurus values for a Tomba field as [{value, code}, ...].
        Queries Mini's thesaurus_field table keyed by field_name. Returns []
        for unknown/unmapped fields or on error."""
        from sqlalchemy import text

        results = []
        try:
            with self.db_manager.connection.get_session() as session:
                try:
                    rows = session.execute(text(
                        "SELECT value, label FROM thesaurus_field "
                        "WHERE table_name = :t AND field_name = :f "
                        "ORDER BY value"
                    ), {'t': self.THESAURUS_TABLE, 'f': field}).fetchall()
                    for r in rows:
                        results.append({'value': r[0], 'code': r[1] or ''})
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"get_thesaurus_values({field}): {e}")
        return results

    def get_distinct_sites(self) -> List[str]:
        try:
            with self.db_manager.connection.get_session() as session:
                rows = session.query(Tomba.sito).filter(
                    Tomba.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

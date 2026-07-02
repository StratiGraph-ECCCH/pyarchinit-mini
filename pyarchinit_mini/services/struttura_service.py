"""
Struttura Service — manages struttura_table (structure) records.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_
from sqlalchemy import Integer as _SAInteger
from sqlalchemy import Float as _SAFloat

from pyarchinit_mini.models.struttura import Struttura

logger = logging.getLogger(__name__)


def _coerce_types(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce string values destined for Integer/Float columns to int/float.

    Text form inputs feed numeric columns (numero_struttura, quota, ...);
    non-numeric input saves fine on SQLite (dynamic typing) but fails the
    whole INSERT/UPDATE on Postgres. Convert non-empty strings using the
    target column's Python type; if unparseable, fall back to None instead
    of raising. Generic over the model's Integer/Float columns so other
    record types can reuse this helper.
    """
    numeric_cols = {
        c.name: (int if isinstance(c.type, _SAInteger) else float)
        for c in model.__table__.columns
        if isinstance(c.type, (_SAInteger, _SAFloat))
    }
    coerced = dict(data)
    for key, caster in numeric_cols.items():
        if key not in coerced:
            continue
        value = coerced[key]
        if value is None or isinstance(value, caster):
            continue
        if caster is float and isinstance(value, int):
            # int is fine for a float column too
            continue
        if isinstance(value, str):
            value = value.strip()
        if value == '':
            coerced[key] = None
            continue
        try:
            coerced[key] = caster(value)
        except (TypeError, ValueError):
            coerced[key] = None
    return coerced


class StrutturaService:
    """Service for Struttura (structure) records."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def list_struttura(self, page: int = 1, size: int = 50, search: str = '',
                        sito: str = '') -> List[Dict[str, Any]]:
        """List Struttura records with optional filters."""
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Struttura)
                if sito:
                    q = q.filter(Struttura.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Struttura.sito.ilike(pat),
                        Struttura.sigla_struttura.ilike(pat),
                        Struttura.categoria_struttura.ilike(pat),
                        Struttura.tipologia_struttura.ilike(pat),
                        Struttura.definizione_struttura.ilike(pat),
                    ))
                q = q.order_by(Struttura.id_struttura.desc())
                offset = (page - 1) * size
                rows = q.offset(offset).limit(size).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            logger.error(f"list_struttura failed: {e}")
            return []

    def count_struttura(self, search: str = '', sito: str = '') -> int:
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Struttura)
                if sito:
                    q = q.filter(Struttura.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Struttura.sito.ilike(pat),
                        Struttura.sigla_struttura.ilike(pat),
                        Struttura.categoria_struttura.ilike(pat),
                        Struttura.tipologia_struttura.ilike(pat),
                        Struttura.definizione_struttura.ilike(pat),
                    ))
                return q.count()
        except Exception:
            return 0

    def get_struttura(self, struttura_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Struttura).filter(
                    Struttura.id_struttura == struttura_id).first()
                return row.to_dict() if row else None
        except Exception as e:
            logger.error(f"get_struttura failed: {e}")
            return None

    def create_struttura(self, data: Dict[str, Any]) -> Optional[int]:
        try:
            with self.db_manager.connection.get_session() as session:
                valid_keys = Struttura.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys and v is not None and v != ''}
                clean = _coerce_types(Struttura, clean)
                row = Struttura(**clean)
                session.add(row)
                session.flush()
                struttura_id = row.id_struttura
                session.commit()
                return struttura_id
        except Exception as e:
            logger.error(f"create_struttura failed: {e}")
            return None

    def update_struttura(self, struttura_id: int, data: Dict[str, Any]) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Struttura).filter(
                    Struttura.id_struttura == struttura_id).first()
                if not row:
                    return False
                valid_keys = Struttura.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys}
                clean = _coerce_types(Struttura, clean)
                for k, v in clean.items():
                    setattr(row, k, v if v != '' else None)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"update_struttura failed: {e}")
            return False

    def delete_struttura(self, struttura_id: int) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Struttura).filter(
                    Struttura.id_struttura == struttura_id).first()
                if row:
                    session.delete(row)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"delete_struttura failed: {e}")
            return False

    # ---------------- Thesaurus integration ----------------

    THESAURUS_TABLE = 'struttura_table'

    def get_thesaurus_values(self, field: str) -> List[Dict[str, str]]:
        """Return thesaurus values for a Struttura field as [{value, code}, ...].
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
                rows = session.query(Struttura.sito).filter(
                    Struttura.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

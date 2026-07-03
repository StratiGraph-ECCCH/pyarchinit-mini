"""
Struttura Service — manages struttura_table (structure) records.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_

from pyarchinit_mini.models.struttura import Struttura
from .coercion import coerce_types

logger = logging.getLogger(__name__)


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
                clean = coerce_types(Struttura, clean)
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
                clean = coerce_types(Struttura, clean)
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
    THESAURUS_MAP = {
        'sigla_struttura': '6.1', 'categoria_struttura': '6.2', 'tipologia_struttura': '6.3',
        'definizione_struttura': '6.4', 'sviluppo_planimetrico': '6.15',
    }

    def get_thesaurus_values(self, field: str) -> List[Dict[str, str]]:
        """Return thesaurus values for a Struttura field as [{value, code}, ...].
        Tries PyArchInit's native pyarchinit_thesaurus_sigle table first (the
        vocab shared with the classic plugin), falls back to Mini's
        thesaurus_field, then to the in-memory THESAURUS_MAPPINGS seed.
        Returns [] for unknown fields or on error."""
        from sqlalchemy import text

        results = []
        sigla = self.THESAURUS_MAP.get(field)
        try:
            with self.db_manager.connection.get_session() as session:
                if sigla:
                    try:
                        rows = session.execute(text(
                            "SELECT sigla, sigla_estesa FROM pyarchinit_thesaurus_sigle "
                            "WHERE nome_tabella = :t AND tipologia_sigla = :s "
                            "ORDER BY sigla_estesa"
                        ), {'t': self.THESAURUS_TABLE, 's': sigla}).fetchall()
                        for r in rows:
                            results.append({'value': r.sigla_estesa or r.sigla, 'code': r.sigla})
                    except Exception:
                        pass

                if not results:
                    try:
                        rows = session.execute(text(
                            "SELECT value, label FROM thesaurus_field "
                            "WHERE table_name = :t AND field_name = :f "
                            "ORDER BY value"
                        ), {'t': self.THESAURUS_TABLE, 'f': field}).fetchall()
                        for r in rows:
                            results.append({'value': r.value, 'code': r.label or ''})
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"get_thesaurus_values({field}): {e}")

        if not results:
            from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
            for v in THESAURUS_MAPPINGS.get(self.THESAURUS_TABLE, {}).get(field, []):
                results.append({'value': v, 'code': ''})

        return results

    def get_distinct_sites(self) -> List[str]:
        try:
            with self.db_manager.connection.get_session() as session:
                rows = session.query(Struttura.sito).filter(
                    Struttura.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

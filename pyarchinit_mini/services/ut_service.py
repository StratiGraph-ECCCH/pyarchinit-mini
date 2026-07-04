"""
UT Service — manages ut_table (Unita di Tracciamento / survey unit) records.

UT is project-scoped (via ``progetto``), not site-scoped like Struttura —
it has no ``sito`` column. id_ut is a plain Integer primary key with native
autoincrement, so (unlike FaunaService's BigInteger PK) no explicit
max(id)+1 allocator is needed here; the plain model constructor and the
DB's native autoincrement/SERIAL handle id assignment.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_

from pyarchinit_mini.models.ut import Ut
from .coercion import coerce_types

logger = logging.getLogger(__name__)

# Maps the UI locale code to the `lingua` value stored in
# pyarchinit_thesaurus_sigle: Italian is stored uppercase ('IT'), other
# languages use locale codes ('en_US', 'fr_FR', ...) matched as-is.
_THESAURUS_LANG_MAP = {'it': 'IT', 'en': 'en_US'}


class UtService:
    """Service for Ut (survey unit) records."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def list_ut(self, page: int = 1, size: int = 50, search: str = '',
                progetto: str = '') -> List[Dict[str, Any]]:
        """List Ut records with optional filters."""
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Ut)
                if progetto:
                    q = q.filter(Ut.progetto == progetto)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Ut.progetto.ilike(pat),
                        Ut.ut_letterale.ilike(pat),
                        Ut.def_ut.ilike(pat),
                        Ut.localita.ilike(pat),
                        Ut.comune.ilike(pat),
                        Ut.descrizione_ut.ilike(pat),
                    ))
                q = q.order_by(Ut.id_ut.desc())
                offset = (page - 1) * size
                rows = q.offset(offset).limit(size).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            logger.error(f"list_ut failed: {e}")
            return []

    def count_ut(self, search: str = '', progetto: str = '') -> int:
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Ut)
                if progetto:
                    q = q.filter(Ut.progetto == progetto)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Ut.progetto.ilike(pat),
                        Ut.ut_letterale.ilike(pat),
                        Ut.def_ut.ilike(pat),
                        Ut.localita.ilike(pat),
                        Ut.comune.ilike(pat),
                        Ut.descrizione_ut.ilike(pat),
                    ))
                return q.count()
        except Exception:
            return 0

    def get_ut(self, ut_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Ut).filter(
                    Ut.id_ut == ut_id).first()
                return row.to_dict() if row else None
        except Exception as e:
            logger.error(f"get_ut failed: {e}")
            return None

    def create_ut(self, data: Dict[str, Any]) -> Optional[int]:
        try:
            with self.db_manager.connection.get_session() as session:
                valid_keys = Ut.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys and v is not None and v != ''}
                clean = coerce_types(Ut, clean)
                row = Ut(**clean)
                session.add(row)
                session.flush()
                ut_id = row.id_ut
                session.commit()
                return ut_id
        except Exception as e:
            logger.error(f"create_ut failed: {e}")
            return None

    def update_ut(self, ut_id: int, data: Dict[str, Any]) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Ut).filter(
                    Ut.id_ut == ut_id).first()
                if not row:
                    return False
                valid_keys = Ut.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys}
                clean = coerce_types(Ut, clean)
                for k, v in clean.items():
                    setattr(row, k, v if v != '' else None)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"update_ut failed: {e}")
            return False

    def delete_ut(self, ut_id: int) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Ut).filter(
                    Ut.id_ut == ut_id).first()
                if row:
                    session.delete(row)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"delete_ut failed: {e}")
            return False

    # ---------------- Thesaurus integration ----------------

    THESAURUS_TABLE = 'ut_table'
    THESAURUS_MAP = {
        'survey_type': '12.1', 'vegetation_coverage': '12.2', 'gps_method': '12.3',
        'surface_condition': '12.4', 'accessibility': '12.5', 'weather_conditions': '12.6',
        'def_ut': '12.7',
    }

    def get_thesaurus_values(self, field: str, lang: str = 'it') -> List[Dict[str, str]]:
        """Return thesaurus values for a Ut field as [{value, code}, ...].
        Tries PyArchInit's native pyarchinit_thesaurus_sigle table first (the
        vocab shared with the classic plugin), filtered by the UI language
        (with fallback to the Italian catalog, then to no language filter at
        all), falls back to Mini's thesaurus_field, then to the in-memory
        THESAURUS_MAPPINGS seed. Returns [] for unknown fields or on error."""
        from sqlalchemy import text

        db_lang = _THESAURUS_LANG_MAP.get((lang or 'it').lower(), lang)

        results = []
        sigla = self.THESAURUS_MAP.get(field)
        try:
            with self.db_manager.connection.get_session() as session:
                if sigla:
                    sigle_rows = []
                    attempts = []
                    for lv in (db_lang, 'IT', None):
                        if lv not in attempts:
                            attempts.append(lv)
                    for lingua_value in attempts:
                        params = {'t': self.THESAURUS_TABLE, 's': sigla}
                        if lingua_value is not None:
                            params['l'] = lingua_value
                            lingua_clause = " AND lingua = :l"
                        else:
                            lingua_clause = ""
                        try:
                            sigle_rows = session.execute(text(
                                "SELECT sigla, sigla_estesa FROM pyarchinit_thesaurus_sigle "
                                "WHERE nome_tabella = :t AND tipologia_sigla = :s" + lingua_clause +
                                " ORDER BY sigla_estesa"
                            ), params).fetchall()
                        except Exception:
                            # Clear any aborted-transaction state (PostgreSQL)
                            # so the next retry / fallback query can still run.
                            session.rollback()
                            sigle_rows = []
                        if sigle_rows:
                            break

                    seen = set()
                    for r in sigle_rows:
                        value = r.sigla_estesa or r.sigla
                        if value in seen:
                            continue
                        seen.add(value)
                        results.append({'value': value, 'code': r.sigla})

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

        # Dedupe the final combined list too, preserving first-seen order.
        seen_final = set()
        deduped = []
        for r in results:
            if r['value'] in seen_final:
                continue
            seen_final.add(r['value'])
            deduped.append(r)
        return deduped

    def get_distinct_projects(self) -> List[str]:
        try:
            with self.db_manager.connection.get_session() as session:
                rows = session.query(Ut.progetto).filter(
                    Ut.progetto.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

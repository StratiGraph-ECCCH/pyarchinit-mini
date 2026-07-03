"""
Struttura Service — manages struttura_table (structure) records.
"""

import ast
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_

from pyarchinit_mini.models.struttura import Struttura
from .coercion import coerce_types

logger = logging.getLogger(__name__)


def _normalize_pylist(v) -> str:
    """Parse an incoming struttura sub-table value (the browser sends a
    JSON-serialized list-of-lists, e.g. '[["buono","medio","umidità"]]')
    with ast.literal_eval — which accepts JSON's double-quoted list/string
    syntax just fine, since it's a subset of Python literal syntax — drop
    any cell that is empty/blank (matching the classic pyarchinit plugin's
    table2dict, which appends a cell to a row's sub_list only `if
    bool(value)`, i.e. it drops ALL empty cells, not just trailing ones,
    producing a shorter positional list), drop rows that end up empty, and
    re-serialize with Python repr() — the exact str(list-of-lists) format
    the classic plugin writes and reads back with eval(). Never raises:
    malformed, non-list, or empty input becomes the string '[]'."""
    if v is None:
        return '[]'
    if isinstance(v, (list, tuple)):
        parsed = v
    else:
        try:
            parsed = ast.literal_eval(v)
        except (SyntaxError, ValueError, TypeError):
            return '[]'
    if not isinstance(parsed, (list, tuple)):
        return '[]'
    rows = []
    for row in parsed:
        if not isinstance(row, (list, tuple)):
            continue
        cells = [str(c) for c in row if str(c).strip()]
        if cells:
            rows.append(cells)
    return repr(rows)


def parse_pylist(v) -> list:
    """Parse a struttura sub-table column's stored value — Python repr,
    single-quoted, as produced by _normalize_pylist and by the classic
    pyarchinit plugin's table2dict — into a Python list-of-lists, for
    handing to the edit-form template (which passes it through `| tojson`
    for the JS widget). Returns [] for None/empty/malformed input; never
    raises."""
    if not v:
        return []
    try:
        parsed = ast.literal_eval(v)
    except (SyntaxError, ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


class StrutturaService:
    """Service for Struttura (structure) records."""

    # The 10 struttura_table columns stored as str(list-of-lists) —
    # the classic plugin's repeatable sub-table format (see
    # _normalize_pylist / parse_pylist above). Shared with the web route
    # (struttura_edit) and the form template's widget instantiation.
    SUBTABLE_COLS = [
        'materiali_impiegati', 'elementi_strutturali', 'rapporti_struttura',
        'misure_struttura', 'stato_conservazione', 'prospetto_ingresso',
        'orientamento_ambienti', 'elementi_costitutivi', 'manufatti',
        'fasi_funzionali',
    ]

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
                # Sub-table columns are always normalized to str(list-of-lists)
                # if present in the payload at all — even a blank value must
                # become the literal '[]' (not be dropped/left NULL), matching
                # the classic plugin's format.
                for key in self.SUBTABLE_COLS:
                    if key in data and key in valid_keys:
                        clean[key] = _normalize_pylist(data.get(key))
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
                for key in self.SUBTABLE_COLS:
                    if key in clean:
                        clean[key] = _normalize_pylist(clean.get(key))
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
        # Sub-table cell thesauri (see SUBTABLE_COLS / the form's repeatable
        # widgets). These are NOT struttura_table columns themselves — each
        # backs one THES cell of a repeatable sub-table row — so they are
        # named after the cell's purpose rather than a DB column name.
        'materiali_impiegati': '6.5', 'elementi_strutturali': '6.6',
        'rapporti_sigla': '6.1',  # reuses the same sigla vocab as sigla_struttura
        'misure_elementi_arch': '6.9', 'misure_tipo': '6.7', 'misure_unita': '6.8',
        'stato_fattori': '6.10', 'prospetto_ingresso': '6.11',
        'elementi_costitutivi': '6.12', 'manufatti': '6.13', 'fasi_definizione': '6.14',
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
                        # Clear any aborted-transaction state (PostgreSQL) so the
                        # thesaurus_field fallback query below can still run.
                        session.rollback()

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

"""
Tomba Service — manages tomba_table (burial) records.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_

from pyarchinit_mini.models.tomba import Tomba
from .coercion import coerce_types
from .struttura_service import _normalize_pylist

logger = logging.getLogger(__name__)

# Maps the UI locale code to the `lingua` value stored in
# pyarchinit_thesaurus_sigle: Italian is stored uppercase ('IT'), other
# languages use locale codes ('en_US', 'fr_FR', ...) matched as-is.
_THESAURUS_LANG_MAP = {'it': 'IT', 'en': 'en_US'}


class TombaService:
    """Service for Tomba (burial) records."""

    # tomba_table columns stored as str(list-of-lists) — the classic
    # plugin's repeatable sub-table format (Tomba.py serializes
    # tableWidget_corredo_tipo with str(table2dict(...))). corredo_tipo
    # rows have 5 positional cells: ID Reperto, ID Individuo, Materiale,
    # Posizione del corredo, Posizione nel corredo. Shared with the web
    # routes (tomba_create/tomba_edit) and the form template's
    # repeatable-row widget; see StrutturaService._normalize_pylist /
    # parse_pylist for the serialization helpers.
    SUBTABLE_COLS = ['corredo_tipo']

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
                clean = coerce_types(Tomba, clean)
                # Sub-table columns are always normalized to str(list-of-lists)
                # on CREATE — even a missing/blank value must become the
                # literal '[]' (not be dropped/left NULL), matching the
                # classic plugin's format. Mirrors struttura_service's
                # create_struttura, which reads the raw `data` (not the
                # value-filtered `clean`) so an absent/empty field is still
                # normalized.
                for key in self.SUBTABLE_COLS:
                    if key in valid_keys:
                        clean[key] = _normalize_pylist(data.get(key))
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
                clean = coerce_types(Tomba, clean)
                for key in self.SUBTABLE_COLS:
                    if key in clean:
                        clean[key] = _normalize_pylist(clean.get(key))
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
    THESAURUS_MAP = {
        'rito': '7.1', 'stato_di_conservazione': '7.2', 'copertura_tipo': '7.3',
        'tipo_contenitore_resti': '7.4', 'tipo_deposizione': '7.6', 'tipo_sepoltura': '7.7',
        'segnacoli': '701.701', 'canale_libatorio_si_no': '701.701', 'corredo_presenza': '702.702',
    }

    def get_thesaurus_values(self, field: str, lang: str = 'it') -> List[Dict[str, str]]:
        """Return thesaurus values for a Tomba field as [{value, code}, ...].
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

    def get_distinct_sites(self) -> List[str]:
        try:
            with self.db_manager.connection.get_session() as session:
                rows = session.query(Tomba.sito).filter(
                    Tomba.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

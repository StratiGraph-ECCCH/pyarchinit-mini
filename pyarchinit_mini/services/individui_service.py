"""
Individui Service — manages individui_table (human skeletal remains) records.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import or_

from pyarchinit_mini.models.individui import Individui
from .coercion import coerce_types

logger = logging.getLogger(__name__)

# Maps the UI locale code to the `lingua` value stored in
# pyarchinit_thesaurus_sigle: Italian is stored uppercase ('IT'), other
# languages use locale codes ('en_US', 'fr_FR', ...) matched as-is.
_THESAURUS_LANG_MAP = {'it': 'IT', 'en': 'en_US'}


class IndividuiService:
    """Service for Individui (human skeletal remains) records."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def list_individui(self, page: int = 1, size: int = 50, search: str = '',
                        sito: str = '') -> List[Dict[str, Any]]:
        """List Individui records with optional filters."""
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Individui)
                if sito:
                    q = q.filter(Individui.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Individui.sito.ilike(pat),
                        Individui.area.ilike(pat),
                        Individui.us.ilike(pat),
                        Individui.sigla_struttura.ilike(pat),
                        Individui.sesso.ilike(pat),
                        Individui.classi_eta.ilike(pat),
                        Individui.schedatore.ilike(pat),
                    ))
                q = q.order_by(Individui.id_scheda_ind.desc())
                offset = (page - 1) * size
                rows = q.offset(offset).limit(size).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            logger.error(f"list_individui failed: {e}")
            return []

    def count_individui(self, search: str = '', sito: str = '') -> int:
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Individui)
                if sito:
                    q = q.filter(Individui.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Individui.sito.ilike(pat),
                        Individui.area.ilike(pat),
                        Individui.us.ilike(pat),
                        Individui.sigla_struttura.ilike(pat),
                        Individui.sesso.ilike(pat),
                        Individui.classi_eta.ilike(pat),
                        Individui.schedatore.ilike(pat),
                    ))
                return q.count()
        except Exception:
            return 0

    def get_individui(self, individui_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Individui).filter(
                    Individui.id_scheda_ind == individui_id).first()
                return row.to_dict() if row else None
        except Exception as e:
            logger.error(f"get_individui failed: {e}")
            return None

    def create_individui(self, data: Dict[str, Any]) -> Optional[int]:
        valid_keys = Individui.writable_columns()
        clean = {k: v for k, v in data.items() if k in valid_keys and v is not None and v != ''}
        clean = coerce_types(Individui, clean)
        try:
            with self.db_manager.connection.get_session() as session:
                row = Individui(**clean)
                session.add(row)
                session.flush()
                individui_id = row.id_scheda_ind
                session.commit()
                return individui_id
        except Exception as e:
            logger.error(f"create_individui failed: {e}")
            return None

    def update_individui(self, individui_id: int, data: Dict[str, Any]) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Individui).filter(
                    Individui.id_scheda_ind == individui_id).first()
                if not row:
                    return False
                valid_keys = Individui.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys}
                clean = coerce_types(Individui, clean)
                for k, v in clean.items():
                    setattr(row, k, v if v != '' else None)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"update_individui failed: {e}")
            return False

    def delete_individui(self, individui_id: int) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Individui).filter(
                    Individui.id_scheda_ind == individui_id).first()
                if row:
                    session.delete(row)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"delete_individui failed: {e}")
            return False

    # ---------------- Thesaurus integration ----------------

    THESAURUS_TABLE = 'individui_table'
    THESAURUS_MAP = {
        'area': '8.6',
        'posizione_cranio': '8.1',
        'posizione_scheletro': '8.2',
        'orientamento_asse': '8.3',
        'posizione_arti_superiori': '8.4',
        'posizione_arti_inferiori': '8.5',
        'completo_si_no': '801.801',
        'disturbato_si_no': '801.801',
        'in_connessione_si_no': '801.801',
    }

    # These fields store the SHORT sigla code (a yes/no flag) rather than
    # the extended form, mirroring how the classic pyarchinit_individui
    # plugin persists them.
    USE_SIGLA_FIELDS = {'completo_si_no', 'disturbato_si_no', 'in_connessione_si_no'}

    def get_thesaurus_values(self, field: str, lang: str = 'it') -> List[Dict[str, str]]:
        """Return thesaurus values for an Individui field as [{value, code}, ...].
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
                        value = r.sigla if field in self.USE_SIGLA_FIELDS else (r.sigla_estesa or r.sigla)
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
                rows = session.query(Individui.sito).filter(
                    Individui.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

    # ---------------- Tomba-link helper ----------------

    def get_nr_individui(self, sito: str, sigla_struttura: Optional[str] = None,
                          nr_struttura=None) -> List[int]:
        """Return the sorted list of distinct, non-null nr_individuo values
        recorded at `sito`, optionally narrowed to a specific tomba/struttura
        (`sigla_struttura` + `nr_struttura`). Used to populate the individuo
        picker on the tomba/struttura form. Requires a non-empty `sito` (an
        empty one returns [] rather than scanning the whole table)."""
        if not sito:
            return []
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Individui.nr_individuo).filter(
                    Individui.sito == sito,
                    Individui.nr_individuo.isnot(None),
                )
                if sigla_struttura:
                    q = q.filter(Individui.sigla_struttura == sigla_struttura)
                if nr_struttura is not None and nr_struttura != '':
                    # 0 is a parseable value — don't drop it via truthiness.
                    try:
                        nr_struttura_int = int(nr_struttura)
                    except (TypeError, ValueError):
                        nr_struttura_int = None
                    if nr_struttura_int is not None:
                        q = q.filter(Individui.nr_struttura == nr_struttura_int)
                rows = q.distinct().all()
                return sorted({int(r[0]) for r in rows})
        except Exception as e:
            logger.error(f"get_nr_individui failed: {e}")
            return []

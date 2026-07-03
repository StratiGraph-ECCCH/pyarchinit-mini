"""
Fauna Service — manages fauna_table (faunal remains) records.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError

from pyarchinit_mini.models.fauna import Fauna
from .coercion import coerce_types

logger = logging.getLogger(__name__)


def _normalize_json_list(v: str) -> str:
    """Parse a specie_psi/misure_ossa JSON string and re-serialize it with
    json.dumps (Python default separators), so the stored value is valid,
    canonical JSON matching the classic pyarchinit_fauna plugin's format
    (a list of 2-element [specie, psi] or 6-element
    [elemento, specie, GL, GB, Bp, Bd] string lists). Malformed input, or
    input that doesn't parse to a list, becomes '[]'."""
    try:
        parsed = json.loads(v)
    except (TypeError, ValueError):
        return '[]'
    if not isinstance(parsed, list):
        return '[]'
    return json.dumps(parsed)


class FaunaService:
    """Service for Fauna (faunal remains) records.

    fauna_table is a plugin-shared table (see
    tests/fauna/test_fauna_migration.py): it can pre-exist on a shared DB,
    populated by the pyarchinit_fauna plugin. Its id_fauna is BigInteger —
    Postgres allocates it via BIGSERIAL, but SQLite has no native
    autoincrement for a BigInteger PK (only for a bare "INTEGER PRIMARY
    KEY" rowid alias), so id_fauna would come back NULL there. Allocate it
    explicitly via max(id)+1, mirroring MediaService._next_id, with a short
    retry loop so a same-value collision from a concurrent writer (plugin
    or mini) self-heals instead of failing the whole create.
    """

    _MAX_INSERT_ATTEMPTS = 6

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def _next_id(self, session) -> int:
        cur = session.query(func.max(Fauna.id_fauna)).scalar()
        return (cur or 0) + 1

    def list_fauna(self, page: int = 1, size: int = 50, search: str = '',
                    sito: str = '') -> List[Dict[str, Any]]:
        """List Fauna records with optional filters."""
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Fauna)
                if sito:
                    q = q.filter(Fauna.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Fauna.sito.ilike(pat),
                        Fauna.area.ilike(pat),
                        Fauna.us.ilike(pat),
                        Fauna.saggio.ilike(pat),
                        Fauna.specie_psi.ilike(pat),
                        Fauna.contesto.ilike(pat),
                    ))
                q = q.order_by(Fauna.id_fauna.desc())
                offset = (page - 1) * size
                rows = q.offset(offset).limit(size).all()
                result = []
                for r in rows:
                    d = r.to_dict()
                    d['specie_display'] = self._species_summary(d.get('specie_psi'))
                    result.append(d)
                return result
        except Exception as e:
            logger.error(f"list_fauna failed: {e}")
            return []

    @staticmethod
    def _species_summary(specie_psi) -> str:
        """Comma-joined species names from the specie_psi JSON (col0 of each row)."""
        if not specie_psi:
            return ''
        try:
            data = json.loads(specie_psi) if isinstance(specie_psi, str) else specie_psi
            names = [str(row[0]) for row in data
                     if isinstance(row, (list, tuple)) and row and row[0]]
            return ', '.join(dict.fromkeys(names))
        except Exception:
            return ''

    def count_fauna(self, search: str = '', sito: str = '') -> int:
        try:
            with self.db_manager.connection.get_session() as session:
                q = session.query(Fauna)
                if sito:
                    q = q.filter(Fauna.sito == sito)
                if search:
                    pat = f"%{search}%"
                    q = q.filter(or_(
                        Fauna.sito.ilike(pat),
                        Fauna.area.ilike(pat),
                        Fauna.us.ilike(pat),
                        Fauna.saggio.ilike(pat),
                        Fauna.specie_psi.ilike(pat),
                        Fauna.contesto.ilike(pat),
                    ))
                return q.count()
        except Exception:
            return 0

    def get_fauna(self, fauna_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Fauna).filter(
                    Fauna.id_fauna == fauna_id).first()
                return row.to_dict() if row else None
        except Exception as e:
            logger.error(f"get_fauna failed: {e}")
            return None

    def create_fauna(self, data: Dict[str, Any]) -> Optional[int]:
        valid_keys = Fauna.writable_columns()
        clean = {k: v for k, v in data.items() if k in valid_keys and v is not None and v != ''}
        clean = coerce_types(Fauna, clean)
        for key in ('specie_psi', 'misure_ossa'):
            if key in clean and isinstance(clean[key], str) and clean[key]:
                clean[key] = _normalize_json_list(clean[key])
        last = self._MAX_INSERT_ATTEMPTS - 1
        for attempt in range(self._MAX_INSERT_ATTEMPTS):
            try:
                with self.db_manager.connection.get_session() as session:
                    row = Fauna(id_fauna=self._next_id(session), **clean)
                    session.add(row)
                    session.flush()
                    fauna_id = row.id_fauna
                    session.commit()
                    return fauna_id
            except IntegrityError as e:
                if attempt == last:
                    logger.error(f"create_fauna failed: {e}")
                    return None
                time.sleep(0.02 * (attempt + 1))
                continue
            except Exception as e:
                logger.error(f"create_fauna failed: {e}")
                return None

    def update_fauna(self, fauna_id: int, data: Dict[str, Any]) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Fauna).filter(
                    Fauna.id_fauna == fauna_id).first()
                if not row:
                    return False
                valid_keys = Fauna.writable_columns()
                clean = {k: v for k, v in data.items() if k in valid_keys}
                clean = coerce_types(Fauna, clean)
                for key in ('specie_psi', 'misure_ossa'):
                    if key in clean and isinstance(clean[key], str) and clean[key]:
                        clean[key] = _normalize_json_list(clean[key])
                for k, v in clean.items():
                    setattr(row, k, v if v != '' else None)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"update_fauna failed: {e}")
            return False

    def delete_fauna(self, fauna_id: int) -> bool:
        try:
            with self.db_manager.connection.get_session() as session:
                row = session.query(Fauna).filter(
                    Fauna.id_fauna == fauna_id).first()
                if row:
                    session.delete(row)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"delete_fauna failed: {e}")
            return False

    # ---------------- Thesaurus integration ----------------

    THESAURUS_TABLE = 'fauna_table'
    THESAURUS_MAP = {
        'contesto': '13.1', 'metodologia_recupero': '13.2', 'tipologia_accumulo': '13.3',
        'deposizione': '13.4', 'stato_frammentazione': '13.5', 'stato_conservazione': '13.6',
        'affidabilita_stratigrafica': '13.7', 'tracce_combustione': '13.8', 'tipo_combustione': '13.9',
        'resti_connessione_anatomica': '13.10', 'specie': '13.11', 'parti_scheletriche': '13.12',
        'elemento_anatomico': '13.13',
        'segni_tafonomici_evidenti': '13.14', 'caratterizzazione_segni_tafonomici': '13.15',
        'numero_stimato_resti': '13.16',
    }

    def get_thesaurus_values(self, field: str) -> List[Dict[str, str]]:
        """Return thesaurus values for a Fauna field as [{value, code}, ...].
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
                rows = session.query(Fauna.sito).filter(
                    Fauna.sito.isnot(None)).distinct().all()
                return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []

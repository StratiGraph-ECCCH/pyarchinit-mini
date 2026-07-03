"""
Shared type-coercion helper for service create/update paths.

Web-form / JSON payloads arrive as strings (or already-correct Python
types when called programmatically). SQLite has dynamic typing, so a
type-mismatched value silently "works" there; Postgres does not, and a
type-mismatched value fails the whole INSERT/UPDATE. This module coerces
input to match a model column's declared SQLAlchemy type (Integer,
Float/Numeric, Boolean, Date) so writes behave the same across both
backends. Never raises: unparseable input becomes None instead.

Used by StrutturaService, TombaService, FaunaService, and UtService (and
any future record-type service with numeric/boolean/date columns fed by
form data).
"""

from datetime import date
from typing import Any, Dict

from sqlalchemy import Boolean, Date as _SADate, Integer as _SAInteger, Numeric as _SANumeric

_TRUE_WORDS = {"true", "1", "si", "sì", "on", "yes", "y"}
_FALSE_WORDS = {"false", "0", "no", "off", "n"}


def _coerce_bool(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v == '':
            return None
        if v in _TRUE_WORDS:
            return True
        if v in _FALSE_WORDS:
            return False
        return None
    return None


def _coerce_date(value: Any) -> Any:
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str):
        v = value.strip()
        if v == '':
            return None
        try:
            return date.fromisoformat(v)
        except (TypeError, ValueError):
            return None
    return None


def _coerce_int(value: Any) -> Any:
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
    if value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Any:
    if value is None or isinstance(value, (float, int)):
        return value
    if isinstance(value, str):
        value = value.strip()
    if value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_types(model, data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a NEW dict with values destined for Integer/Float/Boolean/Date
    columns of ``model`` coerced to the matching Python type.

    - Integer  -> int(v)
    - Float/Numeric -> float(v) (an already-int value is left as-is; ints
      are valid for a Float/Numeric column too). Numeric is checked so
      that DECIMAL-typed columns (e.g. Numeric(5,2)) are coerced too —
      Float IS-A Numeric in SQLAlchemy, so this branch catches both.
      Integer is NOT a Numeric subclass, so plain Integer columns are
      unaffected by this branch.
    - Boolean  -> truthy parse of a lowercased/stripped string: words in
      {"true","1","si","sì","on","yes","y"} -> True; words in
      {"false","0","no","off","n"} -> False; empty string -> None;
      anything else unrecognized -> None. Already-bool values pass through.
      A plain int (not a bool) is truthiness-coerced: 0 -> False, any
      non-zero int -> True (e.g. a spreadsheet/JSON import sending 1/0).
    - Date     -> date.fromisoformat(v) for a "YYYY-MM-DD" string; empty
      string or an invalid value -> None. Already-date values pass through.

    Any other column type (Text/String/etc.) is left untouched, as are
    keys that don't map to a model column. Never raises on bad input —
    unparseable numeric/date/bool values become None.

    IMPORTANT ordering: Boolean is checked before Integer (and Date is
    checked before Integer/Float too), since a Boolean column's type
    could in principle be an Integer subtype on some dialects — checking
    Boolean first ensures it's always handled by the Boolean branch.
    Likewise _coerce_bool itself checks isinstance(value, bool) before
    isinstance(value, int), since bool is a subclass of int in Python.
    """
    coerced = dict(data)
    for col in model.__table__.columns:
        key = col.name
        if key not in coerced:
            continue
        value = coerced[key]
        col_type = col.type
        if isinstance(col_type, Boolean):
            coerced[key] = _coerce_bool(value)
        elif isinstance(col_type, _SADate):
            coerced[key] = _coerce_date(value)
        elif isinstance(col_type, _SAInteger):
            coerced[key] = _coerce_int(value)
        elif isinstance(col_type, _SANumeric):
            coerced[key] = _coerce_float(value)
        # else: leave value untouched (Text/String/etc.)
    return coerced

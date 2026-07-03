"""
Shared type-coercion helper for service create/update paths.

Web-form / JSON payloads arrive as strings (or already-correct Python
types when called programmatically). SQLite has dynamic typing, so a
type-mismatched value silently "works" there; Postgres does not, and a
type-mismatched value fails the whole INSERT/UPDATE. This module coerces
input to match a model column's declared SQLAlchemy type (Integer,
Float, Boolean, Date) so writes behave the same across both backends.
Never raises: unparseable input becomes None instead.

Used by StrutturaService, TombaService, and FaunaService (and any future
record-type service with numeric/boolean/date columns fed by form data).
"""

from datetime import date
from typing import Any, Dict

from sqlalchemy import Boolean, Date as _SADate, Float as _SAFloat, Integer as _SAInteger

_TRUE_WORDS = {"true", "1", "si", "sì", "on", "yes", "y"}
_FALSE_WORDS = {"false", "0", "no", "off", "n"}


def _coerce_bool(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
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
    - Float    -> float(v) (an already-int value is left as-is; ints are
      valid for a Float column too)
    - Boolean  -> truthy parse of a lowercased/stripped string: words in
      {"true","1","si","sì","on","yes","y"} -> True; words in
      {"false","0","no","off","n"} -> False; empty string -> None;
      anything else unrecognized -> None. Already-bool values pass through.
    - Date     -> date.fromisoformat(v) for a "YYYY-MM-DD" string; empty
      string or an invalid value -> None. Already-date values pass through.

    Any other column type (Text/String/etc.) is left untouched, as are
    keys that don't map to a model column. Never raises on bad input —
    unparseable numeric/date/bool values become None.

    IMPORTANT ordering: Boolean is checked before Integer (and Date is
    checked before Integer/Float too), since a Boolean column's type
    could in principle be an Integer subtype on some dialects — checking
    Boolean first ensures it's always handled by the Boolean branch.
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
        elif isinstance(col_type, _SAFloat):
            coerced[key] = _coerce_float(value)
        # else: leave value untouched (Text/String/etc.)
    return coerced

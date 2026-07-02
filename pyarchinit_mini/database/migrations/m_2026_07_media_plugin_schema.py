"""One-shot: replace mini's inline media schema with the classic-plugin schema.

Safe: only runs when the existing media tables are empty (Adarte v2 / Railway have
no media). Never touches a DB that already holds media rows."""
from sqlalchemy import inspect, text
from ...models.base import Base
from ...models.media import Media, MediaThumb, MediaToEntity  # noqa: F401  (register on Base)

_MEDIA_TABLES = ("media_thumb_table", "media_to_entity_table", "media_table")


def _count(conn, table):
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def migrate(engine) -> dict:
    insp = inspect(engine)
    present = set(insp.get_table_names())
    if "media_table" in present:
        cols = {c["name"] for c in insp.get_columns("media_table")}
        if "filepath" in cols and "media_path" not in cols:
            # Already the new plugin schema — nothing to do. Guards against
            # re-running on every startup (would otherwise drop+recreate the
            # empty-but-already-migrated tables every time).
            return {"status": "already_migrated", "reason": "media_table already in plugin schema"}
    with engine.begin() as conn:
        for t in ("media_table", "media_thumb_table", "media_to_entity_table"):
            if t in present and _count(conn, t) > 0:
                return {"status": "skipped", "reason": f"{t} has rows"}
        for t in _MEDIA_TABLES:
            if t in present:
                conn.execute(text(f"DROP TABLE {t}"))
    Base.metadata.create_all(
        engine,
        tables=[Media.__table__, MediaThumb.__table__, MediaToEntity.__table__],
    )
    return {"status": "migrated", "reason": "recreated media tables from plugin schema"}

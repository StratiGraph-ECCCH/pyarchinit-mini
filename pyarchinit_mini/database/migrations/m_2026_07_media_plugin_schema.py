"""One-shot: replace mini's inline media schema with the classic-plugin schema.

Two paths, chosen automatically:
  - Empty (or not-yet-existing) media tables -> drop + recreate empty. Safe:
    nothing to lose.
  - Populated OLD-schema media_table (has media_path/media_type, not
    filepath) -> DATA-preserving conversion. The 3 old tables are renamed to
    `<name>_legacy` (never dropped — the safety backup), the 3 new
    plugin-schema tables are created, and every row is converted across:
    media rows (deduped on filepath, which is UNIQUE in the new schema) and
    media_to_entity links (via ENTITY_MAP; unmappable entity_type values keep
    the media row but skip the link). Old thumbnails stay in
    media_thumb_table_legacy — the new media_thumb_table is left empty since
    thumbnails are cheap to regenerate.

Idempotent either way: once media_table has `filepath` (new schema) or a
`media_table_legacy` backup already exists, further runs are a no-op."""
import os
import uuid
from sqlalchemy import inspect, text
from ...models.base import Base
from ...models.media import Media, MediaThumb, MediaToEntity  # noqa: F401  (register on Base)
from ...media_manager.entity_map import ENTITY_MAP

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

    if "media_table_legacy" in present:
        # A data-migration already ran to completion — the rename+create+
        # convert below happens atomically, so if the backup exists the
        # conversion is done. Never re-rename or re-convert onto it.
        return {"status": "already_migrated", "reason": "media_table_legacy backup already exists"}

    if "media_table" in present:
        cols = {c["name"] for c in insp.get_columns("media_table")}
        is_old_schema = "filepath" not in cols and ("media_path" in cols or "media_type" in cols)
        if is_old_schema:
            with engine.connect() as probe:
                row_count = _count(probe, "media_table")
            if row_count > 0:
                return _migrate_data(engine)

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


def _migrate_data(engine) -> dict:
    """Populated OLD-schema media_table: preserve every row.

    Everything happens inside one transaction so any failure rolls back the
    renames too, leaving the DB exactly as it was found.
    """
    with engine.begin() as conn:
        insp = inspect(conn)
        present = set(insp.get_table_names())

        # --- 1. Backup by rename (never drop) -----------------------------
        conn.execute(text("ALTER TABLE media_table RENAME TO media_table_legacy"))
        if "media_thumb_table" in present:
            conn.execute(text("ALTER TABLE media_thumb_table RENAME TO media_thumb_table_legacy"))
        if "media_to_entity_table" in present:
            if _count(conn, "media_to_entity_table") > 0:
                conn.execute(text("ALTER TABLE media_to_entity_table RENAME TO media_to_entity_table_legacy"))
            else:
                conn.execute(text("DROP TABLE media_to_entity_table"))

        # --- 2. Create the new plugin-schema tables ------------------------
        Base.metadata.create_all(
            conn,
            tables=[Media.__table__, MediaThumb.__table__, MediaToEntity.__table__],
        )

        # --- 3. Convert rows -------------------------------------------------
        legacy_cols = {c["name"] for c in inspect(conn).get_columns("media_table_legacy")}
        legacy_rows = [dict(r) for r in conn.execute(text("SELECT * FROM media_table_legacy")).mappings().all()]

        media_rows = []
        filepath_to_id_media = {}
        resolved_id_media = [None] * len(legacy_rows)
        media_count = 0
        for i, row in enumerate(legacy_rows):
            filepath = row.get("media_path") or None
            id_media = row.get("id_media")
            if filepath and filepath in filepath_to_id_media:
                # Duplicate filepath (UNIQUE in the new schema) — reuse the
                # id_media of the row already queued for insertion instead of
                # inserting a second media row.
                resolved_id_media[i] = filepath_to_id_media[filepath]
                continue

            filename = row.get("media_filename") or row.get("media_name")
            filetype = os.path.splitext(filename)[1].lstrip(".").lower() if filename else ""
            entity_uuid = (row.get("entity_uuid") if "entity_uuid" in legacy_cols else None) or str(uuid.uuid4())

            media_rows.append({
                "id_media": id_media,
                "mediatype": row.get("media_type"),
                "filename": filename,
                "filetype": filetype,
                "filepath": filepath,
                "descrizione": row.get("description") if "description" in legacy_cols else None,
                "tags": row.get("tags") if "tags" in legacy_cols else None,
                "entity_uuid": entity_uuid,
            })
            resolved_id_media[i] = id_media
            if filepath:
                filepath_to_id_media[filepath] = id_media
            media_count += 1

        if media_rows:
            conn.execute(Media.__table__.insert(), media_rows)

        link_rows = []
        seen_links = set()
        link_id = 1
        link_count = 0
        link_skipped = 0
        for i, row in enumerate(legacy_rows):
            entity_type_key = row.get("entity_type")
            entity_id = row.get("entity_id")

            if entity_type_key not in ENTITY_MAP or entity_id is None:
                # Either an unmappable legacy entity_type or no entity bound
                # at all — the media row is still kept, only the link isn't
                # created.
                link_skipped += 1
                continue

            entity_type, table_name, _id_col = ENTITY_MAP[entity_type_key]
            id_media = resolved_id_media[i]
            dedup_key = (entity_id, entity_type, id_media)
            if dedup_key in seen_links:
                continue  # duplicate link (UNIQUE id_entity+entity_type+id_media)
            seen_links.add(dedup_key)

            filename = row.get("media_filename") or row.get("media_name")
            filepath = row.get("media_path") or None
            link_rows.append({
                "id_mediaToEntity": link_id,
                "id_entity": entity_id,
                "entity_type": entity_type,
                "table_name": table_name,
                "id_media": id_media,
                "filepath": filepath,
                "media_name": filename,
                "entity_uuid": str(uuid.uuid4()),
            })
            link_id += 1
            link_count += 1

        if link_rows:
            conn.execute(MediaToEntity.__table__.insert(), link_rows)

        if conn.dialect.name == "postgresql":
            # We inserted explicit PK values above; bump the implicit
            # sequences so future autoincrement inserts don't collide.
            conn.execute(text(
                "SELECT setval(pg_get_serial_sequence('media_table', 'id_media'), "
                "COALESCE((SELECT MAX(id_media) FROM media_table), 1))"
            ))
            conn.execute(text(
                "SELECT setval(pg_get_serial_sequence('media_to_entity_table', 'id_mediaToEntity'), "
                "COALESCE((SELECT MAX(\"id_mediaToEntity\") FROM media_to_entity_table), 1))"
            ))

    return {
        "status": "data_migrated",
        "reason": "converted rows from old-schema media_table (backed up as *_legacy)",
        "media": media_count,
        "links": link_count,
        "links_skipped": link_skipped,
    }

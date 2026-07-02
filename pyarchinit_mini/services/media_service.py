"""
Media service - Business logic for media file management
"""

from typing import List, Dict, Any, Optional
from urllib.parse import quote
from sqlalchemy import asc, desc, or_, func
from sqlalchemy.exc import IntegrityError
from ..database.manager import DatabaseManager
from ..models.media import Media, MediaThumb, MediaToEntity, Documentation
from ..media_manager.media_handler import MediaHandler
from ..media_manager.entity_map import resolve_entity
from ..media_manager.path_resolver import resolve_media_path, is_remote_url, cloudinary_to_url
from ..utils.validators import validate_data
from ..utils.exceptions import ValidationError, RecordNotFoundError
import os
import time
from pathlib import Path

class MediaService:
    """Media operations over the classic-plugin media schema (shared DB)."""

    def __init__(self, db_manager, media_handler=None):
        self.db_manager = db_manager
        self.media_handler = media_handler or MediaHandler()

    def _next_id(self, session, model, id_col):
        cur = session.query(func.max(getattr(model, id_col))).scalar()
        return (cur or 0) + 1

    def get_media_by_id(self, media_id):
        with self.db_manager.connection.get_session() as s:
            return s.get(Media, media_id)

    # id allocation = max(id)+1, matching the classic pyarchinit plugin
    # (DB_MANAGER.max_num_id + 1). Neither tool draws media ids from the Postgres
    # sequence via nextval, so there is nothing to setval — the only shared-DB
    # hazard is two writers computing the same max+1 concurrently, which surfaces
    # as a PK IntegrityError on the loser. We retry (recomputing max+1 on a fresh
    # session each attempt) so those collisions self-heal. This is backend-agnostic:
    # works on Postgres (festos, shared with the plugin) and on SQLite (local).
    _MAX_INSERT_ATTEMPTS = 6

    def add_media(self, file_path, entity_key, id_entity, descrizione="", tags=""):
        entity_type, table_name, _ = resolve_entity(entity_key)
        stored = self.media_handler.store_original(file_path)
        dest_path, filename = stored["dest_path"], stored["filename"]
        last = self._MAX_INSERT_ATTEMPTS - 1
        for attempt in range(self._MAX_INSERT_ATTEMPTS):
            try:
                with self.db_manager.connection.get_session() as s:
                    media = s.query(Media).filter(Media.filepath == dest_path).first()
                    if media is None:
                        media = Media(
                            id_media=self._next_id(s, Media, "id_media"),
                            mediatype=stored["mediatype"], filename=filename,
                            filetype=stored["filetype"], filepath=dest_path,
                            descrizione=descrizione, tags=tags,
                        )
                        s.add(media); s.flush()
                        thumb = self.media_handler.make_thumbnails(dest_path, media.id_media, filename)
                        if thumb:
                            s.add(MediaThumb(
                                id_media_thumb=self._next_id(s, MediaThumb, "id_media_thumb"),
                                id_media=media.id_media, mediatype=stored["mediatype"],
                                media_filename=filename,
                                media_thumb_filename=thumb["media_thumb_filename"],
                                filetype=stored["filetype"], filepath=thumb["thumb_path"],
                                path_resize=thumb["resize_path"],
                            ))
                    exists = s.query(MediaToEntity).filter(
                        MediaToEntity.id_entity == id_entity,
                        MediaToEntity.entity_type == entity_type,
                        MediaToEntity.id_media == media.id_media,
                    ).first()
                    if exists is None:
                        s.add(MediaToEntity(
                            id_mediaToEntity=self._next_id(s, MediaToEntity, "id_mediaToEntity"),
                            id_entity=id_entity, entity_type=entity_type, table_name=table_name,
                            id_media=media.id_media, filepath=dest_path, media_name=filename,
                        ))
                    s.commit()
                    s.refresh(media)
                    s.expunge(media)
                    return media
            except IntegrityError:
                if attempt == last:
                    raise
                # brief backoff before recomputing max+1 and retrying
                time.sleep(0.02 * (attempt + 1))
                continue

    def get_media_for_entity(self, entity_key, id_entity):
        entity_type, table_name, _ = resolve_entity(entity_key)
        with self.db_manager.connection.get_session() as s:
            q = (s.query(Media)
                 .join(MediaToEntity, MediaToEntity.id_media == Media.id_media)
                 .filter(MediaToEntity.table_name == table_name,
                         MediaToEntity.id_entity == id_entity)
                 .order_by(Media.id_media.desc()))
            rows = q.all()
            for r in rows:
                s.expunge(r)
            return rows

    def get_media_by_entity(self, entity_key, id_entity, page=1, size=10):
        """Back-compat alias for get_media_for_entity (page/size ignored)."""
        return self.get_media_for_entity(entity_key, id_entity)

    def get_media_for_entity_ids(self, entity_key, entity_ids):
        result = {eid: [] for eid in entity_ids}
        for eid in entity_ids:
            try:
                items = self.get_media_for_entity(entity_key, eid)
            except Exception:
                items = []
            result[eid] = [{
                "id_media": m.id_media,
                "media_name": m.filename,
                "filepath": m.filepath,
                "media_type": m.mediatype,
                "url": self.public_url(m.filepath),
                "thumb_url": self.thumb_url(m.id_media),
            } for m in items]
        return result

    def public_url(self, filepath):
        """URL the browser can load for a stored media filepath."""
        if not filepath:
            return ""
        if filepath.lower().startswith("cloudinary://"):
            return cloudinary_to_url(filepath)
        if filepath.lower().startswith(("http://", "https://")):
            return filepath
        # local absolute path or unibo/other backend -> serve through mini's route
        return "/media/serve?p=" + quote(filepath)

    def thumb_url(self, id_media):
        with self.db_manager.connection.get_session() as s:
            t = s.query(MediaThumb).filter(MediaThumb.id_media == id_media).first()
            if not t or not t.filepath:
                return self.public_url(self._media_path(s, id_media))
            return self.public_url(t.filepath)

    def _media_path(self, session, id_media):
        m = session.get(Media, id_media)
        return m.filepath if m else ""

    def unlink_media(self, id_media, entity_key, id_entity):
        entity_type, _, _ = resolve_entity(entity_key)
        with self.db_manager.connection.get_session() as s:
            s.query(MediaToEntity).filter(
                MediaToEntity.id_media == id_media,
                MediaToEntity.entity_type == entity_type,
                MediaToEntity.id_entity == id_entity,
            ).delete()
            s.commit()
            return True

    def delete_media(self, id_media, delete_files=True):
        with self.db_manager.connection.get_session() as s:
            media = s.get(Media, id_media)
            if not media:
                return False
            files = []
            if delete_files:
                files.append(media.filepath)
                for t in s.query(MediaThumb).filter(MediaThumb.id_media == id_media).all():
                    files += [t.filepath, t.path_resize]
            s.delete(media)      # CASCADE removes thumbs + links
            s.commit()
        if delete_files:
            for f in files:
                try:
                    if f and not is_remote_url(f) and os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass
        return True

class DocumentationService:
    """Service class for documentation operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_documentation(self, doc_data: Dict[str, Any]) -> Documentation:
        """Create a new documentation record"""
        # Validate data
        validate_data('documentation', doc_data)

        # Create documentation
        return self.db_manager.create(Documentation, doc_data)

    def get_documentation_by_id(self, doc_id: int) -> Optional[Documentation]:
        """Get documentation by ID"""
        return self.db_manager.get_by_id(Documentation, doc_id)

    def get_documentation_by_entity(self, entity_type: str, entity_id: int,
                                   page: int = 1, size: int = 10) -> List[Documentation]:
        """Get all documentation for a specific entity"""
        filters = {'entity_type': entity_type, 'entity_id': entity_id}
        return self.get_all_documentation(page=page, size=size, filters=filters)

    def get_all_documentation(self, page: int = 1, size: int = 10,
                             filters: Optional[Dict[str, Any]] = None) -> List[Documentation]:
        """Get all documentation with pagination and filtering"""
        try:
            with self.db_manager.connection.get_session() as session:
                query = session.query(Documentation)

                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if hasattr(Documentation, key):
                            query = query.filter(getattr(Documentation, key) == value)

                # Apply ordering (final versions first, then by creation date)
                query = query.order_by(desc(Documentation.is_final), desc(Documentation.date_created))

                # Apply pagination
                offset = (page - 1) * size
                return query.offset(offset).limit(size).all()

        except Exception as e:
            from ..utils.exceptions import DatabaseError
            raise DatabaseError(f"Failed to get Documentation records: {e}")

    def update_documentation(self, doc_id: int, update_data: Dict[str, Any]) -> Documentation:
        """Update existing documentation"""
        # Validate update data
        if update_data:
            validate_data('documentation', update_data)

        return self.db_manager.update(Documentation, doc_id, update_data)

    def delete_documentation(self, doc_id: int, delete_file: bool = True) -> bool:
        """Delete documentation record and optionally the file"""
        try:
            # Get documentation record
            doc = self.get_documentation_by_id(doc_id)
            if not doc:
                raise RecordNotFoundError(f"Documentation with ID {doc_id} not found")

            # Delete file if requested
            if delete_file and doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except Exception:
                    pass  # Continue with database deletion even if file deletion fails

            # Delete database record
            return self.db_manager.delete(Documentation, doc_id)

        except Exception as e:
            from ..utils.exceptions import DatabaseError
            raise DatabaseError(f"Failed to delete documentation: {e}")

    def count_documentation(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documentation with optional filters"""
        return self.db_manager.count(Documentation, filters)

"""
Media management models — aligned to the classic pyarchinit plugin schema.
The three media tables are shared with the QGIS plugin, so they do NOT inherit
BaseModel (the plugin tables have only entity_uuid as a sync column).
"""
import uuid
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from .base import Base, BaseModel


def _uuid():
    return str(uuid.uuid4())


class Media(Base):
    """media_table — file catalog (shared with the QGIS plugin)."""
    __tablename__ = 'media_table'

    id_media = Column(BigInteger, primary_key=True, autoincrement=True)
    mediatype = Column(Text)                       # "image" | "document" | "video" | ...
    filename = Column(Text)
    filetype = Column(String(10))
    filepath = Column(Text, unique=True)           # UNIQUE natural key; absolute path or remote URI
    descrizione = Column(Text)
    tags = Column(Text)
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<Media(id_media={self.id_media}, filepath={self.filepath!r})>"


class MediaThumb(Base):
    """media_thumb_table — on-disk thumbnails (no DB blob)."""
    __tablename__ = 'media_thumb_table'

    id_media_thumb = Column(BigInteger, primary_key=True, autoincrement=True)
    id_media = Column(BigInteger, ForeignKey('media_table.id_media', ondelete='CASCADE'))
    mediatype = Column(Text)
    media_filename = Column(Text)
    media_thumb_filename = Column(Text, unique=True)
    filetype = Column(String(10))
    filepath = Column(Text)                        # 200x200 thumb file
    path_resize = Column(Text)                     # 600x600 resize file
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<MediaThumb(id_media_thumb={self.id_media_thumb}, id_media={self.id_media})>"


class MediaToEntity(Base):
    """media_to_entity_table — M:N link between a media file and an archaeological entity."""
    __tablename__ = 'media_to_entity_table'
    __table_args__ = (
        UniqueConstraint('id_entity', 'entity_type', 'id_media', name='ID_mediaToEntity_unico'),
    )

    id_mediaToEntity = Column(BigInteger, primary_key=True, autoincrement=True)
    id_entity = Column(BigInteger)
    entity_type = Column(Text)                     # 'US','REPERTO','CERAMICA',...
    table_name = Column(Text)                      # 'us_table','pottery_table',...
    id_media = Column(BigInteger, ForeignKey('media_table.id_media', ondelete='CASCADE'))
    filepath = Column(Text)                        # denormalized copy of media_table.filepath
    media_name = Column(Text)                      # denormalized filename
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<MediaToEntity({self.entity_type}:{self.id_entity} -> media {self.id_media})>"


class Documentation(BaseModel):
    """
    Documentation files and reports
    """
    __tablename__ = 'documentation_table'

    id_doc = Column(Integer, primary_key=True, autoincrement=True)

    # Entity linking
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)

    # Document info
    doc_type = Column(String(100))  # 'report', 'analysis', 'photo_log', etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # File info
    file_path = Column(String(1000))
    file_format = Column(String(20))  # 'pdf', 'doc', 'txt', etc.

    # Metadata
    author = Column(String(200))
    date_created = Column(DateTime)
    version = Column(String(20))
    language = Column(String(10))

    # Status
    is_final = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Documentation('{self.title}', {self.entity_type}:{self.entity_id})>"

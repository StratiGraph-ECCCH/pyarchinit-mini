"""Global (single-row) media storage configuration."""
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from .base import Base

class StorageConfig(Base):
    __tablename__ = "storage_config"
    id = Column(Integer, primary_key=True)          # always 1
    media_root = Column(Text)                        # upload target (may be scheme-prefixed)
    thumb_path = Column(Text)
    thumb_resize = Column(Text)
    credentials_encrypted = Column(Text)             # Fernet token of {backend: {field: val}}
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

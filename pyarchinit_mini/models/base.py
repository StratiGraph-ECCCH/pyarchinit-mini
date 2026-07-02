"""
Base model class for all PyArchInit-Mini models
"""

import uuid
from datetime import datetime, timezone
from typing import Set
from sqlalchemy import DateTime, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

def _generate_uuid():
    return str(uuid.uuid4())

# Columns managed internally by BaseModel (sync/concurrency/audit state).
# These must never be settable via mass-assignment from untrusted input
# (e.g. raw request.form data forwarded by web routes) — doing so could
# let a write-user overwrite sync/concurrency state that the plugin sync
# and optimistic-locking logic rely on.
MANAGED_COLUMNS = {
    'entity_uuid',
    'version_number',
    'sync_status',
    'editing_by',
    'editing_since',
    'last_modified_by',
    'last_modified_timestamp',
    'created_at',
    'updated_at',
}

class BaseModel(Base):
    """
    Base model class with common fields and methods
    """
    __abstract__ = True

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Concurrency / sync columns
    entity_uuid = Column(String(36), unique=True, index=True, default=_generate_uuid)
    version_number = Column(Integer, default=1, nullable=False)
    last_modified_by = Column(String(100))
    last_modified_timestamp = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='new')
    editing_by = Column(String(100))
    editing_since = Column(DateTime(timezone=True))

    @classmethod
    def writable_columns(cls) -> Set[str]:
        """Return the set of column names safe for mass-assignment from
        untrusted input (e.g. raw web-form data).

        Excludes:
          - the model's primary-key column(s), so callers can never force
            an explicit PK value (which on Postgres bypasses the SERIAL
            sequence and can cause later duplicate-key collisions).
          - the BaseModel-managed sync/concurrency/audit columns in
            MANAGED_COLUMNS, so callers can never overwrite state the
            plugin sync and optimistic-locking logic rely on.
        """
        pk_names = {c.name for c in cls.__table__.primary_key.columns}
        return {c.name for c in cls.__table__.columns} - pk_names - MANAGED_COLUMNS

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update_from_dict(self, data):
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
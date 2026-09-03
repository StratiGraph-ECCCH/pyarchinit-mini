"""
User model for authentication and authorization
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import deferred
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .base import BaseModel


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "ADMIN"           # Full access to everything
    OPERATOR = "OPERATOR"     # Can create/edit/delete data
    VIEWER = "VIEWER"         # Read-only access


class User(BaseModel):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    # Contact info for messaging (deferred to avoid errors when columns don't exist yet)
    telegram_username = deferred(Column(String(100), nullable=True))
    phone = deferred(Column(String(30), nullable=True))
    # ORCID iD — the identity the StratiGraph ecosystem indexes people by (a
    # room's ACL is keyed on it: PUT /rooms/{room}/members/{orcid}). Same
    # `deferred(...)` treatment as the two above, for the reason their comment
    # gives: a database that predates the column must keep opening.
    #
    # nullable: the great majority of pyarchinit-mini's users will never have
    # one, and requiring it would make an ecosystem's convention into a local
    # obligation. unique: two local accounts cannot be the same person.
    # String(64) for a 19-character iD: the bare form is what gets stored (see
    # `normalize_orcid` in web_interface/auth_routes.py), and the margin costs
    # nothing on either backend.
    orcid = deferred(Column(String(64), unique=True, nullable=True, index=True))

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"

    # Cache for PyArchInit granular permissions (loaded at login)
    _pa_role_perms = None  # {'can_insert': bool, 'can_update': bool, 'can_delete': bool, 'can_view': bool}
    _pa_table_perms = None  # {table_name: {'can_insert': bool, ...}}

    def load_pyarchinit_permissions(self, session):
        """Load granular permissions from pyarchinit_roles and pyarchinit_permissions.
        Call this after login when using a PostgreSQL PyArchInit DB."""
        try:
            from sqlalchemy import text
            # Get role-level permissions from pyarchinit_roles
            pa_user = session.execute(
                text("SELECT role FROM pyarchinit_users WHERE username = :u"),
                {'u': self.username}
            ).fetchone()
            if pa_user:
                role_perms = session.execute(
                    text("SELECT can_insert, can_update, can_delete, can_view "
                         "FROM pyarchinit_roles WHERE role_name = :r"),
                    {'r': pa_user[0]}
                ).fetchone()
                if role_perms:
                    self._pa_role_perms = {
                        'can_insert': role_perms[0], 'can_update': role_perms[1],
                        'can_delete': role_perms[2], 'can_view': role_perms[3]
                    }

                # Get table-level overrides from pyarchinit_permissions
                pa_id = session.execute(
                    text("SELECT id FROM pyarchinit_users WHERE username = :u"),
                    {'u': self.username}
                ).fetchone()
                if pa_id:
                    table_rows = session.execute(
                        text("SELECT table_name, can_insert, can_update, can_delete, can_view "
                             "FROM pyarchinit_permissions WHERE user_id = :uid"),
                        {'uid': pa_id[0]}
                    ).fetchall()
                    if table_rows:
                        self._pa_table_perms = {}
                        for r in table_rows:
                            self._pa_table_perms[r[0]] = {
                                'can_insert': r[1], 'can_update': r[2],
                                'can_delete': r[3], 'can_view': r[4]
                            }
        except Exception:
            pass  # Tables may not exist (SQLite), fall back to role-based

    def has_permission(self, permission: str, table_name: str = None) -> bool:
        """
        Check if user has a specific permission, optionally for a specific table.

        Args:
            permission: 'create', 'read', 'update', 'delete', 'manage_users'
            table_name: Optional table name for granular check (e.g. 'us_table')

        Returns:
            bool: True if user has permission
        """
        if self.is_superuser:
            return True

        # Map permission names to pyarchinit column names
        perm_map = {'create': 'can_insert', 'read': 'can_view',
                    'update': 'can_update', 'delete': 'can_delete'}
        pa_key = perm_map.get(permission)

        # Check table-level permissions first (most specific)
        if table_name and self._pa_table_perms and table_name in self._pa_table_perms:
            if pa_key and pa_key in self._pa_table_perms[table_name]:
                return bool(self._pa_table_perms[table_name][pa_key])

        # Check role-level PyArchInit permissions
        if self._pa_role_perms and pa_key:
            return bool(self._pa_role_perms.get(pa_key, False))

        # Fallback to Mini role-based permissions
        permissions = {
            UserRole.ADMIN: ['create', 'read', 'update', 'delete', 'manage_users'],
            UserRole.OPERATOR: ['create', 'read', 'update', 'delete'],
            UserRole.VIEWER: ['read']
        }
        return permission in permissions.get(self.role, [])

    def can_create(self, table_name: str = None) -> bool:
        """Check if user can create records"""
        return self.has_permission('create', table_name)

    def can_edit(self, table_name: str = None) -> bool:
        """Check if user can edit records"""
        return self.has_permission('update', table_name)

    def can_delete(self, table_name: str = None) -> bool:
        """Check if user can delete records"""
        return self.has_permission('delete', table_name)

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.has_permission('manage_users')

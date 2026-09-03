"""
User service for authentication and user management
"""

from typing import Optional, List
from datetime import datetime

from pyarchinit_mini.models.user import User, UserRole
from pyarchinit_mini.utils.auth import hash_password, verify_password
from pyarchinit_mini.database.manager import DatabaseManager


class UserService:
    """Service for user management and authentication"""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize user service

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        is_superuser: bool = False
    ) -> User:
        """
        Create a new user

        Args:
            username: Username
            email: Email address
            password: Plain text password (will be hashed)
            full_name: Full name (optional)
            role: User role
            is_superuser: Whether user is superuser

        Returns:
            User: Created user

        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        # Check if email exists
        if self.get_user_by_email(email):
            raise ValueError(f"Email '{email}' already exists")

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "role": role,
            "is_superuser": is_superuser,
            "is_active": True
        }

        with self.db_manager.connection.get_session() as session:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)

            # Return user dict to avoid detached instance
            return self._user_to_dict(user)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password

        Args:
            username: Username
            password: Password

        Returns:
            User or None: User if authentication successful, None otherwise
        """
        print(f"[AUTH] Authenticating user: {username}")
        user = self.get_user_by_username(username)

        if not user:
            print(f"[AUTH] User not found: {username}")
            return None

        print(f"[AUTH] User found: {user.get('username')}, checking password...")
        if not verify_password(password, user["hashed_password"]):
            print(f"[AUTH] Password verification FAILED")
            return None

        print(f"[AUTH] Password verified, checking if active...")
        if not user["is_active"]:
            print(f"[AUTH] User is INACTIVE")
            return None

        print(f"[AUTH] Authentication SUCCESSFUL for {username}")

        # Update last login
        self.update_last_login(user["id"])

        return user

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            dict or None: User data or None if not found
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            return self._user_to_dict(user) if user else None

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """
        Get user by username

        Args:
            username: Username

        Returns:
            dict or None: User data or None if not found
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            return self._user_to_dict(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """
        Get user by email

        Args:
            email: Email address

        Returns:
            dict or None: User data or None if not found
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.email == email).first()
            return self._user_to_dict(user) if user else None

    def get_all_users(self) -> List[dict]:
        """
        Get all users

        Returns:
            List[dict]: List of all users
        """
        with self.db_manager.connection.get_session() as session:
            users = session.query(User).all()
            return [self._user_to_dict(user) for user in users]

    def update_user(
        self,
        user_id: int,
        **updates
    ) -> Optional[dict]:
        """
        Update user information

        Args:
            user_id: User ID
            **updates: Fields to update

        Returns:
            dict or None: Updated user or None if not found
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return None

            # Update fields
            for key, value in updates.items():
                if key == "password":
                    # Hash password if provided
                    user.hashed_password = hash_password(value)
                elif hasattr(user, key) and key != "hashed_password":
                    setattr(user, key, value)

            session.commit()
            session.refresh(user)

            return self._user_to_dict(user)

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user

        Args:
            user_id: User ID

        Returns:
            bool: True if deleted, False if not found
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return False

            session.delete(user)
            session.commit()

            return True

    def update_last_login(self, user_id: int) -> None:
        """
        Update user's last login time

        Args:
            user_id: User ID
        """
        with self.db_manager.connection.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if user:
                user.last_login = datetime.utcnow()
                session.commit()

    def create_default_admin(self) -> Optional[dict]:
        """
        Create default admin user if no users exist

        Returns:
            dict or None: Admin user if created
        """
        # Check if any users exist
        with self.db_manager.connection.get_session() as session:
            user_count = session.query(User).count()

            if user_count > 0:
                return None

        # Create default admin
        try:
            admin = self.create_user(
                username="admin",
                email="admin@pyarchinit.local",
                password="admin",  # CHANGE THIS IN PRODUCTION!
                full_name="Administrator",
                role=UserRole.ADMIN,
                is_superuser=True
            )
            return admin
        except ValueError:
            return None

    @staticmethod
    def _user_to_dict(user: Optional[User]) -> Optional[dict]:
        """
        Convert User model to dict

        Args:
            user: User model instance

        Returns:
            dict or None: User data or None
        """
        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            # ORCID iD, when there is one. `getattr` with a default rather than
            # `user.orcid`, because this method also runs against a database
            # that predates the column: the model declares it `deferred(...)`
            # for exactly that reason, and this reader must not be the one line
            # that raises on an older schema.
            "orcid": getattr(user, "orcid", None),
            "hashed_password": user.hashed_password,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }

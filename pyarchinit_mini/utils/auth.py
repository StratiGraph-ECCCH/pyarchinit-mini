"""
Authentication utilities for JWT and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

try:
    from passlib.context import CryptContext
    from jose import JWTError, jwt
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False


# Password hashing context
if PASSLIB_AVAILABLE:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT configuration
#
# `ALGORITHM` and the expiry are settings; the KEY is not, and it used to be
# declared here beside them with a literal as its fallback. That literal was
# published in a public repository, so anybody who had read the source could
# forge a token for any installation whose administrator had not set
# `JWT_SECRET_KEY` — which is every installation that never knew it existed.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#: The variable that must hold the JWT signing key. There is no default.
JWT_KEY_VARIABLE = "JWT_SECRET_KEY"

#: The shortest key accepted. The same floor `web_interface/session_key.py`
#: applies, for the same reason and NOT by importing it: `utils` must not depend
#: on `web_interface`, and one shared constant across that boundary would be a
#: layering inversion bought for four characters.
MINIMUM_KEY_LENGTH = 32


class JWTKeyMissing(RuntimeError):
    """No signing key is configured. Raised WHERE A TOKEN IS SIGNED OR READ.

    ## WHY THIS IS RAISED AT USE AND NOT AT IMPORT

    The obvious repair — read the environment at module level and raise when it
    is absent — would stop the WEB APPLICATION from starting for everybody who
    has no `JWT_SECRET_KEY`. Measured, and this is the whole constraint of the
    change: `services/user_service.py:9` and
    `web_interface/oidc_routes.py:612` import `hash_password` /
    `verify_password` from this module, so **this file is executed on every
    Flask boot** — verified in the running container, where
    `pyarchinit_mini.utils.auth` is in `sys.modules` after `create_app()`.

    So an import-time refusal would break the application everybody uses in
    order to repair a path nobody uses. The two functions that need a key ask
    for one when they are called; importing this module stays harmless.

    ## AND WHY NOT REUSE `session_key.resolve()`

    That was the other candidate, and it was rejected on a measurement rather
    than on taste: `resolve()` **never fails to produce a key** — absent an
    environment variable it generates one and keeps it. Reusing it would hand
    the FastAPI authentication surface a WORKING signing key on every
    installation, silently. That surface is not deployed anywhere and the
    roadmap says it must not be promoted; with a key that always resolves, the
    day somebody serves it, it would authenticate with tokens signed by the
    Flask session key, with nobody having decided that.

    Refusing here turns «that API is not deployed» from an accident into a
    stated requirement: serving it means setting a variable on purpose.

    A second reason, which is a real cost rather than a principle: the two keys
    have different lifecycles. Rotating a session key logs local users out and
    is nobody else's business; rotating a JWT key invalidates bearers already
    handed to clients. One value would make either rotation break the other.
    """


def jwt_secret() -> str:
    """The JWT signing key, or a refusal that says what to set.

    A function and not a constant, so that the absence is discovered by whoever
    signs a token rather than by whoever imports this file.
    """
    raw = os.getenv(JWT_KEY_VARIABLE)
    if raw is None or not raw.strip():
        raise JWTKeyMissing(
            f"{JWT_KEY_VARIABLE} is not set, and there is no safe default: this "
            f"path signs and verifies JSON Web Tokens, and a key written into "
            f"the source would let anybody who read it forge one. Set it — "
            f"python -c 'import secrets; print(secrets.token_urlsafe(48))' — or "
            f"do not use the JWT endpoints. The Flask web interface does not "
            f"need this variable and starts without it.")
    key = raw.strip()
    if len(key) < MINIMUM_KEY_LENGTH:
        raise JWTKeyMissing(
            f"{JWT_KEY_VARIABLE} is {len(key)} characters long, and at least "
            f"{MINIMUM_KEY_LENGTH} are required. A short signing key looks "
            f"configured and is not.")
    return key


def __getattr__(name: str):
    """`auth.SECRET_KEY` no longer exists — and says so with the same sentence.

    PEP 562 module-level `__getattr__`. The name is kept ANSWERABLE rather than
    simply deleted, because anybody reaching for it is asking for the signing
    key, and the honest answer to that is the refusal above rather than
    `AttributeError: SECRET_KEY`. Measured before removing it: nothing outside
    this module read it, and no test exercises the JWT path at all.
    """
    if name == "SECRET_KEY":
        raise JWTKeyMissing(
            f"utils.auth.SECRET_KEY no longer exists: the JWT signing key is "
            f"resolved by `jwt_secret()` when a token is signed, so that a "
            f"missing {JWT_KEY_VARIABLE} does not stop the web application from "
            f"starting. Call `jwt_secret()`.")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class AuthUtils:
    """Authentication utility functions"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            bool: True if password matches
        """
        if not PASSLIB_AVAILABLE:
            raise ImportError(
                "passlib is required for password hashing. "
                "Install with: pip install 'passlib[bcrypt]'"
            )
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Hash not recognized (e.g. plain text from PyArchInit sync).
            # Try direct comparison as last resort, then re-hash if matched.
            if plain_password == hashed_password:
                return True
            return False

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        if not PASSLIB_AVAILABLE:
            raise ImportError(
                "passlib is required for password hashing. "
                "Install with: pip install 'passlib[bcrypt]'"
            )
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            str: JWT token
        """
        if not PASSLIB_AVAILABLE:
            raise ImportError(
                "python-jose is required for JWT tokens. "
                "Install with: pip install 'python-jose[cryptography]'"
            )

        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, jwt_secret(), algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode a JWT access token

        Args:
            token: JWT token

        Returns:
            Dict or None: Decoded payload or None if invalid
        """
        if not PASSLIB_AVAILABLE:
            raise ImportError(
                "python-jose is required for JWT tokens. "
                "Install with: pip install 'python-jose[cryptography]'"
            )

        try:
            payload = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None


# Convenience functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (convenience function)"""
    return AuthUtils.verify_password(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password (convenience function)"""
    return AuthUtils.hash_password(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token (convenience function)"""
    return AuthUtils.create_access_token(data, expires_delta)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode access token (convenience function)"""
    return AuthUtils.decode_access_token(token)

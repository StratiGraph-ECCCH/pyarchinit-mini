"""Where this application's Flask `SECRET_KEY` comes from.

## THE DEFECT THIS REPLACES

`app.py` used to say, in the source, on a line committed to a public
repository:

    app.config['SECRET_KEY'] = 'your-secret-key-here'

Flask signs the session cookie with that value, and the signature is the ONLY
thing the server checks before believing which user a request belongs to. A key
everybody can read is a signature anybody can produce: no password needed, no
brute force, no bug to exploit — just a cookie forged with a string published on
GitHub, and the server hands over the account it names. Flask-WTF derives its
CSRF tokens from the same key, so those were forgeable too.

Verified in the running container on 3 September 2026: the environment did NOT
override it. Every reachable installation of pyarchinit-mini shared one key.

## THE ORDER, AND WHY THERE IS NO THIRD FALLBACK

1. **`PYARCHINIT_SESSION_KEY`** from the environment. The right way for a
   deployment — Railway, a container, Ansible — because the key stays out of
   the image and out of the repository.

2. **`FLASK_SECRET_KEY`** from the environment, and this one is a repair rather
   than a convenience. `docs/3D_BUILDER_TECHNICAL_DOCUMENTATION.md:624` lists it
   under «Environment Variables», so the project's own documentation has been
   telling administrators to set it — and MEASURED: no Python file in this
   repository reads it. Somebody who did exactly what the documentation said got
   no protection at all. Honouring it makes an existing promise true.

3. **A key generated once and kept** in `$PYARCHINIT_HOME/session.key`, mode
   `0600`. This is the case that matters most in practice: Enzo's single user,
   who has never set an environment variable, gets a key of their own —
   different from everybody else's, and **stable across restarts**, so sessions
   do not fall over every time the application is restarted.

**And nothing else.** If that file can be neither read nor created, the
application REFUSES TO START and says which path it could not write.

A random key held in memory looks like the prudent fallback and is the opposite.
It would invalidate every session on every restart, and — the part that makes it
insidious — with more than one worker process each worker would hold a DIFFERENT
key, so users would be thrown out at random depending on which worker answered.
That is a defect that presents as «it logs me out sometimes» and that nobody
ever traces back to its cause. A refusal to boot is loud, immediate, and
fixable.

## WHY NOT `PYARCHINIT_SECRET_KEY`, WHICH ALREADY EXISTS

Measured before choosing a name, because reusing it was the obvious move:

    pyarchinit_mini/storage/crypto.py:10
        key = os.environ.get("PYARCHINIT_SECRET_KEY")
        return Fernet(key.encode()) if key else None

It is a **Fernet key** — 32 url-safe base64 bytes, a hard format constraint —
used to encrypt storage-backend credentials at rest. Two reasons not to share
it, and either alone would be enough:

* **key separation.** One secret serving two unrelated cryptographic purposes
  means a compromise of either is a compromise of both, and a rotation for one
  is a forced rotation for the other.
* **the formats disagree.** Flask's key has no shape requirement. An
  administrator who set `PYARCHINIT_SECRET_KEY` to a long random passphrase for
  the session would break storage encryption with a `binascii.Error` from inside
  Fernet; one who set a Fernet key would be using 32 bytes of base64 where a
  session key wants entropy of its own. And `crypto.py` treats the variable as
  OPTIONAL (`has_key()` is a real state, and the interface flashes «Set
  PYARCHINIT_SECRET_KEY to store credentials»), while a session key is not
  optional — making the session depend on it would turn a handled absence into
  a broken login.

There is also a second, unrelated Fernet key on disk —
`$PYARCHINIT_HOME/secret.key`, written by `services/app_setting_service.py:33`.
This module deliberately uses a DIFFERENT file (`session.key`) for the same
key-separation reason, and copies that module's file handling: same
`$PYARCHINIT_HOME` resolution, same `0600`.
"""

from __future__ import annotations

import logging
import os
import secrets
import stat
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger(__name__)

#: The environment variables consulted, in order. `FLASK_SECRET_KEY` is second
#: and is a repair — see the module docstring.
ENVIRONMENT_NAMES = ("PYARCHINIT_SESSION_KEY", "FLASK_SECRET_KEY")

#: The file, beside `secret.key` and deliberately not the same file.
FILE_NAME = "session.key"

#: Bytes of randomness for a generated key. 48 raw bytes → 64 url-safe
#: characters, which is comfortably above anything an attacker can search and
#: costs nothing.
GENERATED_BYTES = 48

#: The shortest key accepted FROM THE ENVIRONMENT.
#:
#: A floor and not a warning, because a deployment that set a session key
#: believes itself protected, and a four-character key is worse than the
#: default it replaced — it looks configured. 32 characters is roughly 160 bits
#: for a passphrase drawn from a keyboard, which is enough, and it is short
#: enough not to reject a key somebody generated sensibly.
MINIMUM_LENGTH = 32

#: Values that must never be accepted, whatever they are set to.
#:
#: `your-secret-key-here` is not a hypothetical: it is the string this patch
#: removes from `app.py`, AND it is what
#: `docs/3D_BUILDER_TECHNICAL_DOCUMENTATION.md:624` and
#: `docs/examples/cli_usage.rst:313` show as the example value. Somebody will
#: copy it out of the documentation, and a key from a public example is the
#: defect this module exists to end. Refused by name, with a sentence that says
#: how to make a real one.
KNOWN_PLACEHOLDERS = frozenset({
    "your-secret-key-here",
    "your-secret-key",
    "changeme",
    "change-me",
    "secret",
    "dev",
    "dev-secret",
})


class SessionKeyError(RuntimeError):
    """The application must not start. The message names what to fix."""


def _home() -> Path:
    """`$PYARCHINIT_HOME`, or `~/.pyarchinit_mini`.

    The same resolution `services/app_setting_service.py:17` uses. NOT the one
    `app.py` uses two lines above the call site, which is
    `Path.home() / '.pyarchinit_mini'` and ignores the variable — a divergence
    that does not bite in the container (its Dockerfile sets `HOME` and
    `PYARCHINIT_HOME` to agreeing values) and that is not this patch's to fix.
    """
    return Path(os.environ.get("PYARCHINIT_HOME")
                or (Path.home() / ".pyarchinit_mini"))


def key_path() -> Path:
    return _home() / FILE_NAME


def fingerprint(key: object) -> str:
    """A short, stable label for a key — for a log line, never the key itself.

    A key in a log is a key in a log aggregator, in a screenshot and in a bug
    report. This is what goes on the boot line instead, and it is also how the
    end-of measurements show «the same key» and «two different keys» without
    printing either.
    """
    import hashlib

    material = key if isinstance(key, bytes) else str(key).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:12]


def _refuse_if_unusable(value: str, source: str) -> None:
    if value.strip().lower() in KNOWN_PLACEHOLDERS:
        raise SessionKeyError(
            f"{source} is set to {value!r}, which is a placeholder from this "
            f"project's own documentation and therefore a key the whole world "
            f"knows. Flask signs the session cookie with it, and the signature "
            f"is the only thing that decides which user a request belongs to. "
            f"Generate one: "
            f"python -c 'import secrets; print(secrets.token_urlsafe(48))' "
            f"— or unset the variable and a private key will be created in "
            f"{key_path()}.")
    if len(value) < MINIMUM_LENGTH:
        raise SessionKeyError(
            f"{source} is {len(value)} characters long, and this application "
            f"requires at least {MINIMUM_LENGTH}. A short session key looks "
            f"configured and is not: it signs every login. Generate one: "
            f"python -c 'import secrets; print(secrets.token_urlsafe(48))'.")


def _from_environment() -> Optional[Tuple[str, str]]:
    for name in ENVIRONMENT_NAMES:
        raw = os.environ.get(name)
        if raw is None:
            continue
        value = raw.strip()
        if not value:
            # Set and empty is NOT the same as unset: somebody wrote the
            # variable, so they believe it is doing something. Falling through
            # to the file would leave them believing it for ever.
            raise SessionKeyError(
                f"{name} is set but empty. Either give it a value "
                f"(python -c 'import secrets; print(secrets.token_urlsafe(48))') "
                f"or remove it, and a private key will be created in "
                f"{key_path()}.")
        _refuse_if_unusable(value, name)
        return value, name
    return None


def _from_file() -> Tuple[bytes, str]:
    """Read the kept key, or make one. Refuse rather than improvise.

    The write is to a TEMPORARY name and then renamed, so two workers starting
    at the same instant cannot read a half-written file: `os.replace` is atomic
    within a filesystem. The mode is set on the temporary file BEFORE the
    rename, so the key is never briefly world-readable.
    """
    path = key_path()
    try:
        if path.exists():
            kept = path.read_bytes().strip()
            if kept:
                return kept, f"{path}"
            log.warning("[session] %s is empty; generating a new key", path)

        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = secrets.token_urlsafe(GENERATED_BYTES).encode("ascii")
        temporary = path.with_name(f"{FILE_NAME}.{os.getpid()}.new")
        temporary.write_bytes(fresh)
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)   # 0600, before the rename
        os.replace(temporary, path)
        log.info("[session] a new session key was created in %s", path)
        return fresh, f"{path}"
    except SessionKeyError:
        raise
    except OSError as exc:
        raise SessionKeyError(
            f"cannot read or create the session key at {path}: {exc}. "
            f"pyarchinit-mini refuses to start rather than sign sessions with a "
            f"key it cannot keep — a key held only in memory would be a "
            f"different key in every worker process, and users would be logged "
            f"out at random. Make that directory writable, or set "
            f"PYARCHINIT_SESSION_KEY in the environment.") from exc


def resolve() -> Tuple[object, str]:
    """The key, and where it came from. Raises `SessionKeyError` if there is none.

    Returns the value as `str` when it came from the environment and as `bytes`
    when it came from the file — Flask accepts either, and converting would only
    hide which one it was.
    """
    from_environment = _from_environment()
    if from_environment is not None:
        value, name = from_environment
        return value, f"the environment ({name})"
    key, where = _from_file()
    return key, where


def configure(app) -> str:
    """Put the key on the app and say — WITHOUT the key — where it came from.

    Returns the log line, so a caller that wants to print it differently can.
    """
    key, where = resolve()
    app.config["SECRET_KEY"] = key
    line = (f"[session] SECRET_KEY from {where} · fingerprint "
            f"{fingerprint(key)}")
    log.info(line)
    return line

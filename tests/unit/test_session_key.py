"""The key that signs every session.

A security repair without a regression test is a repair somebody can undo
without noticing, and this one is a single line in a 7000-line file. So the
first test below does not check behaviour at all: it reads the whole package and
refuses ANY literal assigned to `SECRET_KEY`, which is the shape the defect had.

The rest is the resolution order, and the three refusals — because the point of
this module is that it says no rather than improvising, and «it refuses» is a
claim that has to be measured like any other.
"""

from __future__ import annotations

import io
import os
import pathlib
import re
import stat
import tokenize

import pytest

from pyarchinit_mini.web_interface import session_key as sk

PACKAGE = pathlib.Path(sk.__file__).resolve().parents[1]


def _code_only(path: pathlib.Path) -> str:
    """A file's CODE, with comments and docstrings removed.

    Needed for the same reason it was needed twice before in this repository: a
    grep for the forbidden string finds the sentence that forbids it. This
    module NAMES `your-secret-key-here` on purpose — it is the entry in
    `KNOWN_PLACEHOLDERS` that refuses it — and its docstring quotes the old
    line, so a naive search reports the defect as still present.

    `NL` is deliberately not treated as the start of a logical line: inside
    brackets it is only a line break, and counting it drops the first string of
    every multi-line literal.
    """
    kept, previous = [], tokenize.INDENT
    with open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type == tokenize.COMMENT:
                continue
            if token.type == tokenize.STRING and previous in (
                    tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT):
                continue
            kept.append(token.string)
            previous = token.type
    return " ".join(kept)


# ── 1 · the defect cannot come back ──────────────────────────────────────────

def _literal_secret_key_assignments(path: pathlib.Path):
    """Statements in `path` that assign a STRING LITERAL to a SECRET_KEY.

    Walked over the TOKEN STREAM rather than matched with a regular expression,
    and that is the whole point of this helper.

    THE FIRST VERSION OF THIS TEST WAS A NO-OP, and it was the test defending a
    security fix. It ran a regex over `_code_only()`, which joins tokens with
    SPACES — so `app.config['SECRET_KEY'] = 'x'` becomes

        app . config [ 'SECRET_KEY' ] = 'x'

    and a pattern expecting `SECRET_KEY['"]?\]?\s*=` never matched, because a
    space sits between the quote and the bracket. Two deliberate breakages
    (reinstating the literal, and reinstating a different one) both PASSED
    before this was found. Tokens have no spacing to get wrong.
    """
    statements, current = [], []
    with open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type in (tokenize.COMMENT, tokenize.NL):
                continue
            if token.type == tokenize.NEWLINE:
                statements.append(current)
                current = []
                continue
            current.append(token)
    statements.append(current)

    offenders = []
    for statement in statements:
        names = [t.string.strip("'\"") for t in statement
                 if t.type in (tokenize.NAME, tokenize.STRING)]
        if "SECRET_KEY" not in names:
            continue
        equals = next((i for i, t in enumerate(statement)
                       if t.type == tokenize.OP and t.string == "="), None)
        if equals is None:
            continue
        assigned = [t.string for t in statement[equals + 1:]
                    if t.type == tokenize.STRING]
        if assigned:
            offenders.append(" ".join(t.string for t in statement))
    return offenders


def test_no_literal_is_assigned_to_SECRET_KEY_anywhere_in_the_package():
    """The shape of the bug, refused structurally.

    `app.config['SECRET_KEY'] = 'your-secret-key-here'` signed the session of
    every installation with a string published on GitHub. The repair is one
    line, so what defends it is this: no file in the package may assign a
    string literal to `SECRET_KEY`. A key comes from the environment or from a
    file, never from the source.
    """
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        found = _literal_secret_key_assignments(path)
        if found:
            offenders[str(path.relative_to(PACKAGE))] = found

    # THE ONE THAT IS KNOWN AND NOT REPAIRED HERE, pinned rather than excused.
    #
    # `utils/auth.py:23` signs the FastAPI application's JWTs and falls back to
    # a literal when `JWT_SECRET_KEY` is unset. It is the SAME defect as the one
    # this module fixes — a signing key in a public source — and it is left
    # alone for a measured reason: those two functions are called only from
    # `pyarchinit_mini/api/auth.py`, the FastAPI surface that is not deployed
    # and that the roadmap says must not be promoted. No Flask route mints or
    # accepts one of those tokens.
    #
    # So it is not reachable today, and it becomes reachable on the day somebody
    # serves that API — which is exactly the day nobody thinks to look. Repairing
    # it means changing when `create_access_token` refuses, which is a change to
    # somebody else's authentication and not this patch's to make.
    #
    # Pinned as an EXACT statement, so that editing that line — including
    # fixing it — fails this test and forces whoever does it to come here.
    KNOWN_AND_UNREPAIRED = {
        "utils/auth.py": [
            ' SECRET_KEY = os . getenv ( "JWT_SECRET_KEY" , '
            '"your-secret-key-change-in-production" )'],
    }

    assert offenders == KNOWN_AND_UNREPAIRED, (
        f"a literal is assigned to a signing key somewhere new.\n"
        f"  found:    {offenders}\n"
        f"  expected: {KNOWN_AND_UNREPAIRED}\n"
        f"Flask signs the session cookie with `SECRET_KEY` and the signature is "
        f"the only thing deciding which user a request belongs to, so a key in "
        f"the source is a forgeable login for every installation. Use "
        f"`session_key.configure(app)`. If you have just REPAIRED "
        f"`utils/auth.py`, remove its entry from KNOWN_AND_UNREPAIRED above.")


def test_the_flask_session_key_specifically_has_no_literal_left():
    """The narrow claim of this patch, separated from the broad one above.

    The test above tolerates one known offender in code that is not served;
    this one tolerates none at all in `web_interface/`, which is the surface
    users actually reach.
    """
    web = PACKAGE / "web_interface"
    offenders = {str(p.relative_to(PACKAGE)): found
                 for p in sorted(web.rglob("*.py"))
                 if (found := _literal_secret_key_assignments(p))}
    assert not offenders, offenders


def test_this_files_own_detector_actually_detects():
    """Because the first version of the test above did not.

    A guard that cannot fire is worse than no guard: it reports the absence of
    what it never looked for. So the detector is pointed at a file that DOES
    contain the defect, written here for the purpose.
    """
    import tempfile

    sample = ("import flask\n"
              "def make():\n"
              "    app = flask.Flask(__name__)\n"
              "    app.config['SECRET_KEY'] = 'your-secret-key-here'\n"
              "    return app\n")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(sample)
        written = pathlib.Path(handle.name)
    try:
        found = _literal_secret_key_assignments(written)
        assert len(found) == 1, f"the detector missed the defect: {found}"
        assert "your-secret-key-here" in found[0]
    finally:
        written.unlink()

    # …and it does not fire on the shape this repository now uses
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write("def make(app):\n"
                     "    app.config['SECRET_KEY'] = resolve()\n")
        clean = pathlib.Path(handle.name)
    try:
        assert _literal_secret_key_assignments(clean) == []
    finally:
        clean.unlink()


def test_the_old_literal_survives_only_as_something_this_module_refuses():
    """It IS still in the code — once, as the thing being rejected.

    Asserted rather than left to a reader's grep, because the honest answer to
    «is `your-secret-key-here` gone?» is «yes as a key, no as a word», and the
    difference is the guard.
    """
    carriers = [p for p in PACKAGE.rglob("*.py")
                if "your-secret-key-here" in _code_only(p)]
    assert [p.name for p in carriers] == ["session_key.py"], carriers
    assert "your-secret-key-here" in sk.KNOWN_PLACEHOLDERS


# ── 2 · the environment, and which variable wins ─────────────────────────────

LONG = "x" * 64
OTHER = "y" * 64


def test_the_environment_is_used_when_it_is_set(monkeypatch, tmp_path):
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", LONG)

    key, where = sk.resolve()
    assert key == LONG
    assert "PYARCHINIT_SESSION_KEY" in where
    assert not (tmp_path / sk.FILE_NAME).exists(), (
        "a key was written to disk even though the environment provided one")


def test_the_project_variable_wins_over_the_documented_one(monkeypatch, tmp_path):
    """`FLASK_SECRET_KEY` is honoured because the project's own documentation
    tells administrators to set it and nothing read it — but it is second."""
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.setenv("FLASK_SECRET_KEY", OTHER)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", LONG)
    key, where = sk.resolve()
    assert key == LONG and "PYARCHINIT_SESSION_KEY" in where

    monkeypatch.delenv("PYARCHINIT_SESSION_KEY")
    key, where = sk.resolve()
    assert key == OTHER and "FLASK_SECRET_KEY" in where


def test_it_does_not_reuse_the_fernet_variable(monkeypatch, tmp_path):
    """`PYARCHINIT_SECRET_KEY` is `storage/crypto.py`'s Fernet key.

    Sharing it would tie two unrelated cryptographic purposes together AND
    disagree about format — `Fernet(key.encode())` requires 32 url-safe base64
    bytes, a session key requires nothing. So setting it must have no effect
    here.
    """
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", LONG)

    key, where = sk.resolve()
    assert key != LONG and key.decode() != LONG
    assert str(tmp_path) in where, "it should have fallen through to the file"
    assert "PYARCHINIT_SECRET_KEY" not in sk.ENVIRONMENT_NAMES


# ── 3 · the three refusals ───────────────────────────────────────────────────

@pytest.mark.parametrize("placeholder", sorted(sk.KNOWN_PLACEHOLDERS))
def test_a_known_placeholder_is_refused_by_name(monkeypatch, tmp_path,
                                                placeholder):
    """Including the one this project's own docs used to print.

    Somebody will copy an example value out of the documentation, and a key from
    a public example is exactly the defect this module ends. The refusal names
    the value and says how to make a real one.
    """
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", placeholder)

    with pytest.raises(sk.SessionKeyError) as refusal:
        sk.resolve()
    said = str(refusal.value)
    assert placeholder in said
    assert "secrets.token_urlsafe" in said, (
        "a refusal that does not say how to fix it makes somebody search")


def test_a_short_key_is_refused(monkeypatch, tmp_path):
    """A four-character key looks configured and is worse than the default it
    replaced."""
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", "abcd")
    with pytest.raises(sk.SessionKeyError) as refusal:
        sk.resolve()
    assert str(sk.MINIMUM_LENGTH) in str(refusal.value)

    # …and one character below the floor is still refused, so the boundary is
    # where it says it is
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", "z" * (sk.MINIMUM_LENGTH - 1))
    with pytest.raises(sk.SessionKeyError):
        sk.resolve()
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", "z" * sk.MINIMUM_LENGTH)
    assert sk.resolve()[0] == "z" * sk.MINIMUM_LENGTH


def test_a_variable_that_is_set_and_empty_is_refused_not_ignored(monkeypatch,
                                                                 tmp_path):
    """Set and empty is not the same as unset.

    Somebody wrote the variable, so they believe it is doing something. Falling
    through to the file silently would leave them believing it for ever.
    """
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", "   ")
    with pytest.raises(sk.SessionKeyError) as refusal:
        sk.resolve()
    assert "empty" in str(refusal.value)


def test_a_home_that_cannot_be_written_refuses_the_boot_and_names_the_path(
        monkeypatch, tmp_path):
    """No third fallback.

    A random key in memory would be a DIFFERENT key in every worker process,
    and users would be thrown out at random depending on which worker answered
    — a defect that presents as «it logs me out sometimes» and that nobody
    traces back. A refusal to boot is loud and fixable.
    """
    if os.getuid() == 0:
        pytest.skip("running as root: a read-only directory is not read-only")
    locked = tmp_path / "locked"
    locked.mkdir()
    os.chmod(locked, stat.S_IRUSR | stat.S_IXUSR)      # r-x, no write
    monkeypatch.setenv("PYARCHINIT_HOME", str(locked))
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)
    try:
        with pytest.raises(sk.SessionKeyError) as refusal:
            sk.resolve()
        said = str(refusal.value)
        assert str(locked) in said, (
            f"the refusal does not name the path that could not be written: "
            f"{said}")
        assert "refuses to start" in said
    finally:
        os.chmod(locked, stat.S_IRWXU)                 # so tmp_path can be cleaned


# ── 4 · the kept key ─────────────────────────────────────────────────────────

def test_a_key_is_created_with_restricted_permissions(monkeypatch, tmp_path):
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)

    key, where = sk.resolve()
    path = tmp_path / sk.FILE_NAME
    assert path.exists() and str(path) in where
    assert len(key) >= 60, f"a short generated key: {len(key)} bytes"
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, (
        f"the session key is mode {oct(mode)}: it must not be readable by "
        f"anybody but its owner")
    # …and no temporary file was left behind by the atomic write
    assert sorted(p.name for p in tmp_path.iterdir()) == [sk.FILE_NAME]


def test_the_second_boot_gets_the_SAME_key(monkeypatch, tmp_path):
    """The property that keeps sessions alive across a restart.

    This is what makes the file fallback usable at all: a key regenerated on
    every boot would log everybody out on every deploy.
    """
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)
    first, _ = sk.resolve()
    second, _ = sk.resolve()
    assert first == second
    assert sk.fingerprint(first) == sk.fingerprint(second)


def test_two_installations_get_two_different_keys(monkeypatch, tmp_path):
    """The end of «every installation shares one key»."""
    one, two = tmp_path / "one", tmp_path / "two"
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("PYARCHINIT_HOME", str(one))
    key_one, _ = sk.resolve()
    monkeypatch.setenv("PYARCHINIT_HOME", str(two))
    key_two, _ = sk.resolve()

    assert key_one != key_two
    assert sk.fingerprint(key_one) != sk.fingerprint(key_two)


def test_an_emptied_key_file_is_replaced_rather_than_used(monkeypatch, tmp_path):
    """A zero-byte file would otherwise become a zero-byte signing key."""
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    for name in sk.ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)
    (tmp_path / sk.FILE_NAME).write_bytes(b"")
    key, _ = sk.resolve()
    assert key and len(key) >= 60


# ── 5 · the key never reaches a log ──────────────────────────────────────────

def test_the_boot_line_carries_a_fingerprint_and_never_the_key(monkeypatch,
                                                               tmp_path):
    """A secret in a log is a secret in a log aggregator, a screenshot and a
    bug report."""
    monkeypatch.setenv("PYARCHINIT_HOME", str(tmp_path))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("PYARCHINIT_SESSION_KEY", LONG)

    class Stand:
        config: dict = {}

    line = sk.configure(Stand())
    assert Stand.config["SECRET_KEY"] == LONG
    assert LONG not in line, f"the key is in the log line: {line}"
    assert sk.fingerprint(LONG) in line
    assert len(sk.fingerprint(LONG)) == 12

    # …and the fingerprint is stable and does not invert into the key
    assert sk.fingerprint(LONG) == sk.fingerprint(LONG)
    assert sk.fingerprint(LONG) != sk.fingerprint(OTHER)

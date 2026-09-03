"""Living behind the node's front door — and the two ways that goes wrong.

`https://em.localhost:8443/pyarchinit/` reaches this application through Caddy,
which STRIPS the prefix and hands it back in `X-Forwarded-Prefix`. Werkzeug's
`ProxyFix` turns that into WSGI's `SCRIPT_NAME`, and Flask prepends it to every
`url_for`. Two things must stay true, and neither is obvious:

1. **`ProxyFix` is off unless an environment variable turns it on.** Those
   headers arrive WITH the request: with a proxy in front the proxy writes them,
   without one the caller does. Measured on 17 September, direct port, variable
   on, hostile headers:

       redirect_uri = https://evil.example/pwned/auth/oidc/callback

   which is the whole reason the variable exists. Through Caddy the same headers
   produce the real address, because `header_up` replaces them.

2. **No template writes an absolute path by hand.** `url_for` gets the prefix
   from `SCRIPT_NAME`; a literal `href="/docs"` does not, and behind the proxy it
   leaves the prefix behind and lands on the front door's 404. That was one link
   in `base.html`, i.e. one broken link on EVERY page — found by counting the
   served HTML, not by reading.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pyarchinit_mini.web_interface import proxy

VARIABLE = proxy.BEHIND_PROXY_VARIABLE
TEMPLATES = (pathlib.Path(proxy.__file__).resolve().parent / "templates")


class Recorder:
    """The smallest thing `configure` needs: something with a `wsgi_app`.

    A real Flask app would need a database. What is being tested is whether the
    middleware is installed and what it does to the WSGI environment, and both
    are visible from here.
    """

    def __init__(self):
        self.seen = {}

        def application(environ, start_response):
            self.seen = dict(environ)
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"ok"]

        self.wsgi_app = application

    def call(self, **headers):
        environ = {
            "REQUEST_METHOD": "GET", "PATH_INFO": "/auth/login",
            "SERVER_NAME": "localhost", "SERVER_PORT": "8080",
            "SERVER_PROTOCOL": "HTTP/1.1", "wsgi.url_scheme": "http",
            "REMOTE_ADDR": "10.0.0.9", "HTTP_HOST": "localhost:8080",
        }
        environ.update(headers)
        self.wsgi_app(environ, lambda status, out: None)
        return self.seen


# ── 1 · absent means unchanged ───────────────────────────────────────────────

def test_without_the_variable_nothing_is_installed_and_nothing_is_logged(
        monkeypatch):
    """«Absent means today's behaviour» includes the log.

    Most people who run pyarchinit-mini expose it directly, and for them this
    patch must be invisible.
    """
    monkeypatch.delenv(VARIABLE, raising=False)
    app = Recorder()
    original = app.wsgi_app

    assert proxy.configure(app) is None
    assert app.wsgi_app is original, "the WSGI app was wrapped anyway"
    assert proxy.declared() is False


def test_without_the_variable_a_forwarded_prefix_is_ignored(monkeypatch):
    """THE GUARD OF THIS CHAPTER, at the level where it acts.

    A caller declaring its own prefix must not reach `SCRIPT_NAME`.
    """
    monkeypatch.delenv(VARIABLE, raising=False)
    app = Recorder()
    proxy.configure(app)

    environ = app.call(HTTP_X_FORWARDED_PREFIX="/pwned",
                       HTTP_X_FORWARDED_HOST="evil.example",
                       HTTP_X_FORWARDED_PROTO="https")
    assert environ.get("SCRIPT_NAME", "") == "", (
        f"a caller's X-Forwarded-Prefix became SCRIPT_NAME="
        f"{environ.get('SCRIPT_NAME')!r} with no proxy declared: every link this "
        f"application builds would be steerable by whoever asks")
    assert environ["HTTP_HOST"] == "localhost:8080"
    assert environ["wsgi.url_scheme"] == "http"


# ── 2 · set means the prefix arrives ─────────────────────────────────────────

def test_with_the_variable_the_prefix_becomes_SCRIPT_NAME(monkeypatch):
    """Which is what makes `url_for` emit `/pyarchinit/...` without one template
    change. If a template ever needs editing, this is the thing that stopped
    working."""
    monkeypatch.setenv(VARIABLE, "1")
    app = Recorder()
    line = proxy.configure(app)
    assert line and VARIABLE in line

    environ = app.call(HTTP_X_FORWARDED_PREFIX="/pyarchinit",
                       HTTP_X_FORWARDED_HOST="em.localhost:8443",
                       HTTP_X_FORWARDED_PROTO="https")
    assert environ["SCRIPT_NAME"] == "/pyarchinit"
    assert environ["HTTP_HOST"] == "em.localhost:8443"
    assert environ["wsgi.url_scheme"] == "https"


@pytest.mark.parametrize("yes", sorted(proxy.TRUE_VALUES))
def test_every_accepted_yes_turns_it_on(monkeypatch, yes):
    monkeypatch.setenv(VARIABLE, yes)
    assert proxy.declared() is True
    monkeypatch.setenv(VARIABLE, yes.upper())
    assert proxy.declared() is True, "the value should not be case-sensitive"


@pytest.mark.parametrize("no", sorted(v for v in proxy.FALSE_VALUES if v))
def test_every_accepted_no_leaves_it_off(monkeypatch, no):
    monkeypatch.setenv(VARIABLE, no)
    assert proxy.declared() is False


def test_a_value_that_is_neither_is_refused_rather_than_guessed(monkeypatch):
    """Because both guesses are bad.

    Read as «no», every link breaks behind the operator's proxy with nothing in
    the log to say why. Read as «yes», any caller can declare its own address.
    """
    monkeypatch.setenv(VARIABLE, "mabye")
    with pytest.raises(proxy.ProxyConfigurationError) as refusal:
        proxy.declared()
    said = str(refusal.value)
    assert "mabye" in said
    assert VARIABLE in said
    for accepted in ("1", "true", "yes", "on"):
        assert accepted in said, "the refusal should list what it accepts"


def test_only_one_hop_is_trusted():
    """A number larger than the number of real proxies lets a caller prepend a
    fake entry to `X-Forwarded-For` and have it believed. There is one proxy."""
    assert proxy.TRUSTED_HOPS == 1


# ── 3 · no template writes an absolute path by hand ──────────────────────────

def _hand_written_absolute_paths():
    """Every `href`/`action`/`src` that starts with `/` and is not a Jinja
    expression. Those are the ones `url_for` never sees, so they never get
    `SCRIPT_NAME` and never get the prefix."""
    offenders = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for match in re.finditer(r'(?:href|action|src)="(/[^"{}]*)"', line):
                offenders.setdefault(str(path.relative_to(TEMPLATES)),
                                     []).append((number, match.group(1)))
    return offenders


def test_no_template_hard_codes_a_path_from_the_origin_root():
    """The `/docs` class of bug, refused for the whole template tree.

    `base.html:115` had `href="/docs"` — a real route, and a link that worked
    for as long as this application owned the origin's root. Behind the front
    door it pointed at `https://em.localhost:8443/docs`, which is the proxy's
    404, and because it lived in the shared layout it was the one broken link on
    every page.

    Measured when it was found: 64 of the 65 links on the login page already
    carried the prefix, and this was the only hand-written absolute path in the
    whole tree. So the rule is cheap to keep.
    """
    offenders = _hand_written_absolute_paths()
    assert not offenders, (
        f"a template writes an absolute path by hand: {offenders}. "
        f"`url_for` prepends the proxy's prefix from SCRIPT_NAME and a literal "
        f"does not, so behind the node's front door that link leaves "
        f"`/pyarchinit/` behind and lands on a 404. Use "
        f"`{{{{ url_for('endpoint') }}}}`.")


def test_that_template_check_actually_detects():
    """A guard that cannot fire reports the absence of what it never looked for.

    Two proofs before, in this repository, were no-ops. So the detector is
    pointed at a template written to contain the defect.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        room = pathlib.Path(directory)
        (room / "guilty.html").write_text('<a href="/docs">aiuto</a>\n')
        (room / "innocent.html").write_text(
            '<a href="{{ url_for(\'docs\') }}">aiuto</a>\n'
            '<a href="https://orcid.org/0000-0002-1825-0097">orcid</a>\n'
            '<a href="#top">su</a>\n')

        global TEMPLATES
        kept, TEMPLATES = TEMPLATES, room
        try:
            found = _hand_written_absolute_paths()
        finally:
            TEMPLATES = kept

    assert list(found) == ["guilty.html"], found
    assert found["guilty.html"] == [(1, "/docs")]

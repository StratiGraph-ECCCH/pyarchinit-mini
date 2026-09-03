"""Living behind a reverse proxy — and only when somebody says there is one.

pyarchinit-mini serves at its own root: `/auth/login`, `/static/…`, `/us/…`.
Put behind a proxy at `https://host/pyarchinit/`, the proxy strips that prefix
before the request arrives, so the application never sees it — and every
`url_for()` and every form `action` it emits points at `/auth/login` instead of
`/pyarchinit/auth/login`. The links leave the prefix behind and 404.

The mechanism that fixes it is standard and is NOT invented here: the proxy
sends `X-Forwarded-Prefix`, Werkzeug's `ProxyFix` turns it into WSGI's
`SCRIPT_NAME`, and from that moment Flask prepends the prefix by itself. No
template is touched. **If a template ever needs touching, `SCRIPT_NAME` is not
arriving and that is the defect** — not the template.

════════════════════════════════════════════════════════════════════════════════
## WHY THIS IS OFF UNLESS AN ENVIRONMENT VARIABLE TURNS IT ON

Not house style — a real hole.

`ProxyFix(x_for, x_host, x_proto, x_prefix)` tells Werkzeug to **believe
headers that arrive with the request**. With a proxy in front, the proxy writes
them and they are trustworthy. **Without one, the caller writes them**, and then
a client can declare its own address, its own host and its own prefix — and the
application will build links, and log addresses, from what the caller said about
itself.

Turning it on by default would hand free spoofing to everybody who exposes
pyarchinit-mini directly, which is Enzo's users. So:

    PYARCHINIT_BEHIND_PROXY unset  →  today's behaviour, byte for byte
    PYARCHINIT_BEHIND_PROXY set    →  one hop of forwarded headers is trusted

It is the fourth time this shape is written in this project (the OIDC door, the
session key, the JWT key, this), and at this point it is the rule of the house:
**absent means unchanged; half-set means a refusal that says so.**

## AND WHAT THIS DELIBERATELY DOES NOT DO: declare a public address

`stratigraph-server/app/handoff.py:148` states the opposite rule for the links
IT writes, and states it well:

    Configuration, never a request header. `Host` is caller-supplied, and a link
    built from it is a link an attacker can point at their own server by asking
    for it with the right header

So the obvious move would be a `PYARCHINIT_PUBLIC_BASE` and an OIDC
`redirect_uri` built from it rather than from the request. **Measured, and it is
the wrong move here, for two reasons that do not apply to `handoff.py`:**

1. **A redirect_uri is validated downstream.** Keycloak refuses any value that
   is not in the client's registered list, so a steered one is not a redirect an
   attacker can receive — it is a flow that stops with «Invalid parameter:
   redirect_uri». `handoff.py`'s links have no such gate: they are handed to a
   person and clicked. And header injection here requires *making the request
   yourself*: a victim clicking a link cannot be made to send custom headers.

2. **There are two doors, and one declared address cannot serve both.**
   `http://localhost:8090/` stays working for development (measured as a
   requirement, not assumed), and `https://em.localhost:8443/pyarchinit/` is the
   node's front door. A single declared base would make the direct port emit the
   proxy's `redirect_uri`, the browser would return to the OTHER origin, and the
   Flask session holding `state` and the PKCE verifier would not be there —
   `localhost:8090` and `em.localhost:8443` are different cookie jars. The flow
   would fail with «this browser has no ORCID sign-in in progress», which reads
   like a bug and is a configuration that cannot be right for both.

So the `redirect_uri` stays derived from the request, and what is DECLARED is
the thing that actually needs declaring: **that there is a proxy in front worth
believing.** The residual is stated rather than hidden — the derivation is
exactly as trustworthy as that proxy, which is what the variable asserts.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

#: The variable that declares a trusted proxy in front.
BEHIND_PROXY_VARIABLE = "PYARCHINIT_BEHIND_PROXY"

#: What counts as yes and what counts as no. Anything else is a refusal rather
#: than a guess: an operator who wrote `PYARCHINIT_BEHIND_PROXY=mabye` meant
#: something, and silently reading it as «no» would leave every link in the
#: application broken behind their proxy with nothing in the log to say why.
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})

#: How many proxies are in front. ONE — Caddy — and the number matters: it is
#: how far back down `X-Forwarded-For` Werkzeug will look for the client's
#: address. A larger number than there are real hops lets a caller prepend a
#: fake entry and have it believed.
TRUSTED_HOPS = 1


class ProxyConfigurationError(RuntimeError):
    """The variable says something this module cannot read."""


def declared() -> bool:
    """Is there a proxy in front? Raises if the answer is unreadable."""
    raw = os.environ.get(BEHIND_PROXY_VARIABLE)
    if raw is None:
        return False
    value = raw.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ProxyConfigurationError(
        f"{BEHIND_PROXY_VARIABLE}={raw!r} is not something this application can "
        f"read as yes or no. Accepted: {sorted(TRUE_VALUES)} to trust one "
        f"reverse proxy in front, {sorted(v for v in FALSE_VALUES if v)} or "
        f"unset for none. It is refused rather than assumed, because reading it "
        f"as «no» would leave every link broken behind your proxy with nothing "
        f"in the log to explain it, and reading it as «yes» would let any caller "
        f"declare its own address.")


def configure(app) -> Optional[str]:
    """Wrap the WSGI app when a proxy is declared. Returns the line to log.

    `None` when there is no proxy — and nothing is logged in that case, because
    «absent means today's behaviour» includes the log.
    """
    if not declared():
        return None

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app,
                            x_for=TRUSTED_HOPS, x_proto=TRUSTED_HOPS,
                            x_host=TRUSTED_HOPS, x_prefix=TRUSTED_HOPS)
    line = (f"[proxy] {BEHIND_PROXY_VARIABLE} is set: trusting "
            f"{TRUSTED_HOPS} hop of X-Forwarded-For/Proto/Host/Prefix. "
            f"`url_for` will emit the prefix the proxy declares.")
    log.info(line)
    return line

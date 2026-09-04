"""Carrying this database's stratigraphy to a StratiGraph room. Nothing else.

**Not an app, not a service, not a thread that lives.** Given a room, an address
and an identity the ORCID door already verified, this hands the operations the
adapter produced to the door `stratigraph-server` opened for connectors.

    pyarchinit_mini/connector/us_ops.py     rows  →  operations   (pure)
    this module                             operations  →  a room (the wire)

**It does not compute the operations.** `us_ops.deliver()` does, and it is a
pure function with no session, no socket and no token — which is why it lives in
a package whose docstring forbids all three. If translation logic ever appears
in this file, it is in the wrong file.

## THE FOUR RULES, and each is a thing that could have gone the other way

**1 · Configuration is per environment; absent means the feature is off.** The
house rule for the fourth time (the OIDC door, the session key, the JWT key, the
proxy) and by now it is simply how this fork behaves: no variable, no feature,
and pyarchinit-mini is byte for byte what Enzo's users run. Half the variables
is a refusal that names the missing one.

**2 · No identity, no delivery — and no network call either.** The refusal is
the connector contract's own sentence, and it is checked BEFORE anything is
sent, not after a server rejects it. Falling back on the local username would
put a name in somebody else's graph that the ecosystem cannot resolve to a
person; a service account would attribute an excavation to a machine.

**3 · One synchronous POST, and an outcome a person can read.** No queue, no
automatic retry, no background thread. `pyarchinit_mini/stratigraph/sync_queue.py`
is still in this repository as the argument for that: a queue that retries by
itself is the reason nobody can now say whether it ever worked. If the server
does not answer, the user is told and that is the end of it.

**4 · `author` and `ts` are the server's to write.** `ws.apply_from_connector`
pops the first and defaults the second, and a client that writes either is
lying about who did what and when.

## AND A REFUSAL FROM THE ROOM IS NOT AN ERROR

A 200 carrying a populated `refused` is the normal answer to delivering the same
site twice: the operations are idempotent and the room says so. It is shown, not
retried. Retrying an idempotent CRDT operation repairs nothing and hides the
real reason — which is exactly what the endpoint's own docstring says on the
other side of the wire.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from pyarchinit_mini.connector import us_ops

log = logging.getLogger(__name__)

#: Ours, not the realm's. The SERVICE is called `stratigraph-server`; the
#: clientId inside the tokens is still literally `em-server`, and renaming that
#: would change the audience every service validates — a decision with a cost,
#: not a tidy-up. There is no link between our name for a variable and a
#: clientId the realm has frozen, so these are named properly from the start.
SERVER_URL_VARIABLE = "STRATIGRAPH_SERVER_URL"
ROOM_ID_VARIABLE = "STRATIGRAPH_ROOM_ID"
REQUIRED_VARIABLES = (SERVER_URL_VARIABLE, ROOM_ID_VARIABLE)

#: The connector contract's own words, for the case this module refuses first.
#: Copied from `s3dgraphy.contract`'s `no_author` rather than paraphrased: a
#: refusal that reads differently in two tools is two policies.
NO_AUTHOR = ("I cannot write without knowing who you are: a verified identity "
             "is required.")

#: `stratigraph-server` caps a batch at `OPS_BATCH_MAX` (1000) and answers 413
#: above it, with a measurement in the constant explaining that the limit is the
#: room's lock. This is the same number, known here so the refusal happens
#: before a wasted round trip and says something useful about paging.
BATCH_MAX = 1000

#: Long enough for a thousand operations under a room lock on a large graph
#: (measured on the server: ~2 s at ten thousand nodes), short enough that an
#: unreachable node does not hold a worker thread for a minute.
TIMEOUT = 30.0


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


class RoomSettings:
    """Where the room is, and which one."""

    def __init__(self) -> None:
        self.server_url = _env(SERVER_URL_VARIABLE).rstrip("/")
        self.room_id = _env(ROOM_ID_VARIABLE)

    @property
    def declared(self) -> bool:
        return any((self.server_url, self.room_id))

    @property
    def enforcing(self) -> bool:
        return bool(self.server_url and self.room_id)

    @property
    def ops_endpoint(self) -> str:
        """`/v1/rooms/{id}/ops` — and the `/v1` is not decoration.

        `app/main.py:210` mounts every authenticated route under a router with
        `prefix="/v1"`. The chapter's prompt writes the path without it, which
        is how everybody says it out loud; what goes on the wire has it, and a
        URL missing it is a 404 that looks like a missing feature.
        """
        return (f"{self.server_url}/v1/rooms/"
                f"{urllib.parse.quote(self.room_id, safe='')}/ops")


def settings() -> RoomSettings:
    return RoomSettings()


def configuration_error() -> Optional[str]:
    """The sentence to refuse with, or None. Same three states as everywhere."""
    it = settings()
    if not it.declared:
        return None
    present = {SERVER_URL_VARIABLE: bool(it.server_url),
               ROOM_ID_VARIABLE: bool(it.room_id)}
    if all(present.values()):
        if not (it.server_url.startswith("http://")
                or it.server_url.startswith("https://")):
            return (f"{SERVER_URL_VARIABLE}={it.server_url!r} has no scheme. "
                    f"It is the base of a server-to-server call — inside the "
                    f"network, by service name, e.g. "
                    f"`http://stratigraph-server:8000` — and urllib will not "
                    f"guess one.")
        return None
    missing = ", ".join(k for k, v in present.items() if not v)
    given = ", ".join(k for k, v in present.items() if v)
    return (f"The StratiGraph room is half-configured: {given} set, {missing} "
            f"missing. Refusing rather than guessing — a delivery needs both an "
            f"address and a room, and inventing either would send an "
            f"excavation somewhere nobody chose. Set both, or unset both for "
            f"the behaviour pyarchinit-mini has always had.")


class RoomRefusal(RuntimeError):
    """Something this module will not do, in a sentence meant for a person."""


@dataclass
class Outcome:
    """What happened, including what did not become an operation at all.

    `skipped` and `counts` come from the adapter (rows it could not read, verbs
    with no counterpart in the datamodel); `refused` comes from the room. Two
    different kinds of «did not land», kept apart, because one is this
    database's shape and the other is the graph's state.
    """

    sent: int = 0
    applied: int = 0
    refused: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    room_id: str = ""
    kept: Optional[Dict[str, Any]] = None

    @property
    def idempotent(self) -> int:
        """Refusals that mean «the room already has this», not «this is wrong».

        The two must be counted apart: the first is the normal answer to
        delivering a site twice, the second is a bug at this end.
        """
        return sum(1 for r in self.refused if r.get("reason") == "idempotent")

    @property
    def other_refusals(self) -> List[Dict[str, Any]]:
        return [r for r in self.refused if r.get("reason") != "idempotent"]

    @property
    def a_repeat(self) -> bool:
        """Did this deliver anything the room did not already have?

        MEASURED, 4 September 2026, delivering one site three times into
        `probe-pyarchinit-09-client-stanza`:

            1ª consegna : 112 inviate → 112 applicate,  0 rifiutate
            2ª consegna : 112 inviate →  41 applicate, 71 rifiutate (idempotent)
            3ª consegna : 112 inviate →  41 applicate, 71 rifiutate (idempotent)

        **The nodes are not refused on a repeat — they MERGE.** `add_node` in
        `s3dgraphy/crdt.py` is idempotent by merging and reports
        `applied: true, reason: "merged"`, while `add_edge` refuses outright
        with `"idempotent"`. So «all refused» — which is what this chapter's
        prompt expected, and what an earlier draft of this class tested for —
        NEVER happens for a delivery that carries units. It would only be true
        for a delivery of edges alone.

        And `applied` therefore cannot be read as «created»: the endpoint's
        `applied` count conflates a first write with a merge, which is an
        already-declared gap on the server's side, not something this client can
        resolve. What it CAN do is not pretend otherwise.

        So the honest test for «the room already had this» is: every operation
        either merged or was refused as idempotent, and nothing was refused for
        any other reason.
        """
        return (self.sent > 0
                and self.idempotent + self.applied == self.sent
                and self.idempotent > 0
                and not self.other_refusals)

    def summary(self) -> str:
        parts = [f"{self.applied} applicate su {self.sent}"]
        if self.idempotent:
            parts.append(f"{self.idempotent} già presenti")
        if self.other_refusals:
            parts.append(f"{len(self.other_refusals)} rifiutate")
        if self.skipped:
            parts.append(f"{len(self.skipped)} righe non tradotte")
        return ", ".join(parts)


def _post(endpoint: str, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request_ = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request_, timeout=TIMEOUT) as answer:
        return json.loads(answer.read().decode("utf-8"))


def deliver(units: Iterable[Dict[str, Any]],
            relationships: Iterable[Dict[str, Any]] = (),
            *, orcid: Optional[str], token_source: Any,
            graph_id: Optional[str] = None) -> Outcome:
    """Translate, then carry. Refusals happen in this order, and the order is the point.

    1. the feature is configured at all;
    2. **the identity** — and NOTHING has left this process by the time this is
       decided, which is the property `test_room_client` proves by handing in a
       `token_source` that records whether it was ever asked;
    3. the batch is within what the room accepts;
    4. only then a token is fetched, and only then a socket is opened.

    `token_source` is a CALLABLE, not a token. That is what puts step 4 after
    step 2: a token passed in as a string would already have been minted — and,
    in the shape this application actually has, already refreshed against the
    realm — before this function decided whether it was allowed to do anything.
    """
    it = settings()
    problem = configuration_error()
    if problem:
        raise RoomRefusal(problem)
    if not it.enforcing:
        raise RoomRefusal(
            f"Nessuna stanza configurata: {SERVER_URL_VARIABLE} e "
            f"{ROOM_ID_VARIABLE} non sono impostate, quindi questo server non "
            f"consegna a nessuno.")

    # 2 · THE IDENTITY, before anything reaches the network.
    if not (orcid or "").strip():
        raise RoomRefusal(NO_AUTHOR)

    made = us_ops.deliver(units, relationships)
    outcome = Outcome(sent=len(made.ops), skipped=list(made.skipped),
                      counts=dict(made.counts), room_id=it.room_id)
    if not made.ops:
        # Not an error and not a refusal: a site with no units produced no
        # operations, and the adapter behaved correctly. `stratigraph-server`
        # takes the same view of an empty batch and answers 200.
        return outcome
    if len(made.ops) > BATCH_MAX:
        raise RoomRefusal(
            f"{len(made.ops)} operazioni in una consegna, e la stanza ne "
            f"accetta {BATCH_MAX} per richiesta: il limite è il lock della "
            f"stanza, che resta chiuso per tutto il lotto. Consegna un'area "
            f"per volta — le operazioni sono idempotenti, quindi consegnare a "
            f"pezzi è sicuro.")

    # 4 · now, and not before.
    token = token_source()
    payload: Dict[str, Any] = {"ops": made.ops}
    if graph_id:
        payload["graph_id"] = graph_id

    try:
        answer = _post(it.ops_endpoint, payload, token)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        try:
            detail = json.loads(detail).get("detail") or detail
        except Exception:                                        # noqa: BLE001
            pass
        log.warning("[room] %s refused the batch: %s %s",
                    it.ops_endpoint, exc.code, detail)
        raise RoomRefusal(
            f"La stanza «{it.room_id}» ha rifiutato la consegna "
            f"({exc.code}): {detail}") from exc
    except Exception as exc:                                  # network, DNS, TLS
        log.warning("[room] %s could not be reached: %s", it.ops_endpoint, exc)
        raise RoomRefusal(
            f"Non ho potuto raggiungere il server delle stanze "
            f"({it.server_url}): {exc}. Non metto la consegna in coda — "
            f"riprova quando il server risponde.") from exc

    outcome.applied = int(answer.get("applied") or 0)
    outcome.refused = list(answer.get("refused") or [])
    outcome.kept = answer.get("kept")
    log.info("[room] %s → %s (orcid=%s, graph_id=%s)",
             it.room_id, outcome.summary(), orcid, graph_id)
    return outcome

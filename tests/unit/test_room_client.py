"""Carrying a site to a room: what it refuses, in what order, and what it sends.

THE ORDER IS THE POLICY, and the test that matters most is the one proving that
a delivery without an identity **never reaches the network**. It is not enough
that the room would refuse it: by then the excavation has left the building, the
token has been minted (and, in this application, possibly refreshed against the
realm), and the refusal is somebody else's to make.

So the tests hand in a `token_source` that RECORDS whether it was called, and a
`urlopen` that raises if it is reached. A refusal that lets either fire is a
refusal that happened too late.
"""

from __future__ import annotations

import json

import pytest

from pyarchinit_mini.web_interface import room_client

ORCID = "0000-0002-1825-0097"


@pytest.fixture(autouse=True)
def a_room(monkeypatch):
    """Configured, unless a test says otherwise."""
    monkeypatch.setenv(room_client.SERVER_URL_VARIABLE,
                       "http://stratigraph-server:8000")
    monkeypatch.setenv(room_client.ROOM_ID_VARIABLE, "una-stanza")


class Tripwire:
    """A token source that must not be asked, and knows whether it was."""

    def __init__(self, token="un-token"):
        self.asked = 0
        self.token = token

    def __call__(self):
        self.asked += 1
        return self.token


def no_network(monkeypatch):
    """Any socket opened from here is a test failure, not a network error."""
    def explode(*_a, **_k):
        raise AssertionError("a network call was made")
    monkeypatch.setattr(room_client.urllib.request, "urlopen", explode)


UNITS = [{"sito": "Scavo", "area": "1", "us": "1",
          "d_stratigrafica": "Strato", "unita_tipo": "US"},
         {"sito": "Scavo", "area": "1", "us": "2",
          "d_stratigrafica": "Strato", "unita_tipo": "US"}]
EDGES = [{"sito": "Scavo", "us_from": 1, "us_to": 2,
          "relationship_type": "Copre"}]


# ── 1 · configuration: three states, and the third is a refusal ──────────────

def test_no_variable_at_all_is_not_a_problem(monkeypatch):
    monkeypatch.delenv(room_client.SERVER_URL_VARIABLE, raising=False)
    monkeypatch.delenv(room_client.ROOM_ID_VARIABLE, raising=False)
    assert room_client.configuration_error() is None
    assert room_client.settings().declared is False
    assert room_client.settings().enforcing is False


def test_both_variables_is_the_feature(monkeypatch):
    assert room_client.configuration_error() is None
    assert room_client.settings().enforcing is True


@pytest.mark.parametrize("missing, named", [
    (room_client.SERVER_URL_VARIABLE, room_client.SERVER_URL_VARIABLE),
    (room_client.ROOM_ID_VARIABLE, room_client.ROOM_ID_VARIABLE),
])
def test_half_configured_refuses_and_names_the_missing_one(monkeypatch,
                                                           missing, named):
    monkeypatch.delenv(missing, raising=False)
    problem = room_client.configuration_error()
    assert problem and named in problem
    assert "missing" in problem


def test_an_address_without_a_scheme_is_refused_rather_than_guessed(monkeypatch):
    """`urllib` will not guess one, and neither will this.

    A bare `stratigraph-server:8000` looks like a host and a port to a person
    and like a URL scheme called `stratigraph-server` to urllib.
    """
    monkeypatch.setenv(room_client.SERVER_URL_VARIABLE, "stratigraph-server:8000")
    problem = room_client.configuration_error()
    assert problem and "scheme" in problem


def test_the_endpoint_carries_the_v1_prefix():
    """`app/main.py:210` mounts every authenticated route under `/v1`.

    Said out loud everybody drops it, including this chapter's own prompt. What
    goes on the wire has it, and a URL missing it is a 404 that reads like a
    missing feature.
    """
    assert (room_client.settings().ops_endpoint
            == "http://stratigraph-server:8000/v1/rooms/una-stanza/ops")


def test_a_room_id_with_awkward_characters_is_quoted(monkeypatch):
    monkeypatch.setenv(room_client.ROOM_ID_VARIABLE, "scavo/2026 nord")
    assert ("/rooms/scavo%2F2026%20nord/ops"
            in room_client.settings().ops_endpoint)


# ── 2 · THE REFUSAL THAT MUST COME BEFORE THE NETWORK ────────────────────────

@pytest.mark.parametrize("nobody", [None, "", "   "])
def test_without_an_orcid_nothing_is_sent_and_no_token_is_asked_for(
        monkeypatch, nobody):
    """THE GUARD OF THIS CHAPTER.

    Three things are asserted, and the last two are the point: the sentence is
    the contract's, no socket was opened, and **the token source was never
    called** — so nothing was minted or refreshed for a delivery that was never
    allowed to happen.
    """
    no_network(monkeypatch)
    source = Tripwire()

    with pytest.raises(room_client.RoomRefusal) as refusal:
        room_client.deliver(UNITS, EDGES, orcid=nobody, token_source=source)

    assert str(refusal.value) == room_client.NO_AUTHOR
    assert source.asked == 0, (
        "a token was fetched for a delivery that was refused for having no "
        "author: the refusal is happening after the credential, not before it")


def test_that_tripwire_actually_fires():
    """A guard that cannot fire reports the absence of what it never looked for.

    Three proofs in this repository have been no-ops. So the two instruments the
    test above relies on are pointed at a case that must trip them.
    """
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setenv(room_client.SERVER_URL_VARIABLE,
                           "http://stratigraph-server:8000")
        monkeypatch.setenv(room_client.ROOM_ID_VARIABLE, "una-stanza")
        no_network(monkeypatch)
        source = Tripwire()
        # …the SAME call, with an identity: it must get past the guard, ask for
        # the token, and then hit the network tripwire.
        #
        # The tripwire's `AssertionError` comes back wrapped in a `RoomRefusal`,
        # because `deliver` puts one `except Exception` around the POST for
        # network, DNS and TLS. That is the boundary working, not the tripwire
        # failing — the sentence carries the tripwire's own words, which is what
        # proves the socket was reached.
        with pytest.raises(room_client.RoomRefusal) as boom:
            room_client.deliver(UNITS, EDGES, orcid=ORCID, token_source=source)
        assert "a network call was made" in str(boom.value)
        assert source.asked == 1, (
            "the token source was never called even WITH an identity, so "
            "`source.asked == 0` above proves nothing")
    finally:
        monkeypatch.undo()


def test_configuration_is_refused_before_the_identity_is_even_read(monkeypatch):
    """A server with no room does not get as far as asking who you are."""
    monkeypatch.delenv(room_client.ROOM_ID_VARIABLE, raising=False)
    no_network(monkeypatch)
    source = Tripwire()
    with pytest.raises(room_client.RoomRefusal) as refusal:
        room_client.deliver(UNITS, EDGES, orcid=ORCID, token_source=source)
    assert room_client.ROOM_ID_VARIABLE in str(refusal.value)
    assert source.asked == 0


def test_a_batch_over_the_room_s_cap_is_refused_here(monkeypatch):
    """Before a round trip, and with the reason the room would have given.

    The number is the server's `OPS_BATCH_MAX`, and the sentence repeats its
    measurement: the limit is the room's lock, held for the whole batch.
    """
    no_network(monkeypatch)
    source = Tripwire()
    many = [{"sito": "Scavo", "area": "1", "us": str(n), "unita_tipo": "US"}
            for n in range(room_client.BATCH_MAX + 1)]
    with pytest.raises(room_client.RoomRefusal) as refusal:
        room_client.deliver(many, (), orcid=ORCID, token_source=source)
    said = str(refusal.value)
    assert str(room_client.BATCH_MAX) in said
    assert "idempotenti" in said, "a refusal should say why paging is safe"
    assert source.asked == 0


def test_an_empty_delivery_is_not_an_error_and_sends_nothing(monkeypatch):
    """A site with no units produced no operations, and that is correct.

    `stratigraph-server` takes the same view and answers 200 to an empty batch;
    a client that special-cased it would be the only one that thought it was
    a problem.
    """
    no_network(monkeypatch)
    source = Tripwire()
    outcome = room_client.deliver([], (), orcid=ORCID, token_source=source)
    assert outcome.sent == 0 and outcome.applied == 0
    assert source.asked == 0


# ── 3 · what actually goes on the wire ───────────────────────────────────────

class Sent:
    """Captures one POST and answers with what the room would."""

    def __init__(self, reply):
        self.reply = reply
        self.url = None
        self.headers = {}
        self.payload = None

    def __call__(self, request_, timeout=None):
        self.url = request_.full_url
        self.headers = {k.lower(): v for k, v in request_.headers.items()}
        self.payload = json.loads(request_.data.decode())
        body = json.dumps(self.reply).encode()

        class Answer:
            def read(self_inner):
                return body

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *_):
                return False

        return Answer()


def test_a_delivery_sends_the_adapter_s_operations_with_the_bearer(monkeypatch):
    wire = Sent({"applied": 3, "refused": [], "kept": {"version": 1}})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)

    outcome = room_client.deliver(UNITS, EDGES, orcid=ORCID,
                                  token_source=Tripwire("il-bearer"))

    assert wire.url == "http://stratigraph-server:8000/v1/rooms/una-stanza/ops"
    assert wire.headers["authorization"] == "Bearer il-bearer"
    assert outcome.applied == 3
    assert outcome.sent == len(wire.payload["ops"]) == 3   # two units, one edge
    assert outcome.room_id == "una-stanza"


def test_the_client_writes_neither_author_nor_ts(monkeypatch):
    """`ws.apply_from_connector` pops the one and defaults the other.

    A client that writes either is lying about who did what and when — and
    `apply_from_connector` would drop `author` anyway, so writing it would be a
    claim with no effect, which is the worst kind.
    """
    wire = Sent({"applied": 3, "refused": []})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)
    room_client.deliver(UNITS, EDGES, orcid=ORCID, token_source=Tripwire())

    for op in wire.payload["ops"]:
        assert "author" not in op, f"the client wrote an author: {op}"
        assert "ts" not in op, f"the client wrote a timestamp: {op}"


def test_graph_id_travels_only_when_it_was_given(monkeypatch):
    wire = Sent({"applied": 0, "refused": []})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)

    room_client.deliver(UNITS, (), orcid=ORCID, token_source=Tripwire())
    assert "graph_id" not in wire.payload, (
        "a null graph_id is not the same as an absent one: absent means «the "
        "active graph», and the server decides which that is")

    room_client.deliver(UNITS, (), orcid=ORCID, token_source=Tripwire(),
                        graph_id="un-grafo")
    assert wire.payload["graph_id"] == "un-grafo"


# ── 4 · a refusal is not an error ────────────────────────────────────────────

def test_the_measured_shape_of_a_second_delivery_is_read_as_a_repeat(monkeypatch):
    """NODES MERGE, EDGES REFUSE — and an earlier draft of this test was wrong.

    It asserted «a repeat means everything refused», which is what this
    chapter's prompt expected. Measured instead, delivering one real site three
    times into `probe-pyarchinit-09-client-stanza` on 4 September 2026:

        1ª : 112 inviate → 112 applicate,  0 rifiutate
        2ª : 112 inviate →  41 applicate, 71 rifiutate (idempotent)
        3ª : 112 inviate →  41 applicate, 71 rifiutate (idempotent)

    `add_node` is idempotent BY MERGING and reports itself applied; only
    `add_edge` refuses. So «all refused» never happens for a site with units,
    and a client testing for it would have reported every repeat as if it were
    a first delivery. The numbers here are the measured ones.
    """
    refused = [{"op": "add_edge", "id": f"e{n}", "reason": "idempotent"}
               for n in range(71)]
    wire = Sent({"applied": 41, "refused": refused})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)

    outcome = room_client.deliver(UNITS, EDGES, orcid=ORCID,
                                  token_source=Tripwire())
    outcome.sent = 112                      # the real batch, not this fixture's
    assert outcome.idempotent == 71
    assert outcome.a_repeat is True, (
        "a repeat in which the nodes merged was not recognised as a repeat")
    assert "già presenti" in outcome.summary()
    assert "aggiunte" not in outcome.summary(), (
        "`applied` conflates created and merged, so the wording must not claim "
        "anything was added")


def test_a_first_delivery_is_not_read_as_a_repeat(monkeypatch):
    wire = Sent({"applied": 3, "refused": []})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)
    outcome = room_client.deliver(UNITS, EDGES, orcid=ORCID,
                                  token_source=Tripwire())
    assert outcome.a_repeat is False
    assert outcome.idempotent == 0


def test_a_refusal_that_is_not_idempotency_is_kept_apart(monkeypatch):
    """«The room already has this» and «this operation is wrong» are not the
    same answer, and a client that files them together loses the second."""
    wire = Sent({"applied": 1, "refused": [
        {"op": "add_edge", "reason": "idempotent"},
        {"op": "update_field", "reason": "node is not here"}]})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)
    outcome = room_client.deliver(UNITS, EDGES, orcid=ORCID,
                                  token_source=Tripwire())
    assert outcome.idempotent == 1
    assert len(outcome.other_refusals) == 1
    assert outcome.a_repeat is False, (
        "a batch carrying a real refusal must not be reported as a quiet repeat")
    assert "1 rifiutate" in outcome.summary()


def test_a_delivery_of_edges_alone_can_still_be_wholly_refused(monkeypatch):
    """The case «all refused» DOES describe — and the only one."""
    wire = Sent({"applied": 0, "refused": [
        {"op": "add_edge", "reason": "idempotent"}]})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)
    outcome = room_client.deliver(
        [{"sito": "Scavo", "area": "1", "us": "1", "unita_tipo": "US"}],
        (), orcid=ORCID, token_source=Tripwire())
    outcome.sent = 1
    assert outcome.a_repeat is True


def test_an_http_error_becomes_a_sentence_carrying_the_room_s_own_words(
        monkeypatch):
    import io
    import urllib.error

    def refuse(request_, timeout=None):
        raise urllib.error.HTTPError(
            request_.full_url, 403, "Forbidden", {},
            io.BytesIO(b'{"detail":"writing operations into this room needs '
                       b'editor or above"}'))

    monkeypatch.setattr(room_client.urllib.request, "urlopen", refuse)
    with pytest.raises(room_client.RoomRefusal) as refusal:
        room_client.deliver(UNITS, EDGES, orcid=ORCID, token_source=Tripwire())
    said = str(refusal.value)
    assert "403" in said and "editor or above" in said


def test_an_unreachable_server_says_so_and_promises_no_queue(monkeypatch):
    def refuse(request_, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(room_client.urllib.request, "urlopen", refuse)
    with pytest.raises(room_client.RoomRefusal) as refusal:
        room_client.deliver(UNITS, EDGES, orcid=ORCID, token_source=Tripwire())
    said = str(refusal.value)
    assert "coda" in said, (
        "the sentence should say the delivery is NOT queued — `sync_queue.py` "
        "is in this repository as the reason that promise is worth making")


# ── 5 · what the adapter could not translate is carried, not swallowed ───────

def test_rows_the_adapter_skipped_reach_the_outcome(monkeypatch):
    wire = Sent({"applied": 2, "refused": []})
    monkeypatch.setattr(room_client.urllib.request, "urlopen", wire)

    outcome = room_client.deliver(
        UNITS,
        [{"sito": "Scavo", "us_from": 1, "us_to": 2,
          "relationship_type": "Sta simpatico a"}],
        orcid=ORCID, token_source=Tripwire())

    assert outcome.skipped, "an unmappable verb vanished without a word"
    assert any("Sta simpatico a" in line for line in outcome.skipped)
    assert outcome.counts, "the counts a caller decides on were dropped"
    assert "non tradotte" in outcome.summary()

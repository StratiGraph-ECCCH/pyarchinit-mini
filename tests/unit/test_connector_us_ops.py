"""What must stay true when an excavation becomes a graph.

The tests that matter here are not «does it produce operations» — it obviously
does. They are the four ways this can be wrong in a way nobody notices:

1. **an id that is not stable**, so the same unit delivered twice is two nodes;
2. **an edge type nobody's vocabulary knows**, which lands silently because
   `apply_op_to_section` does not validate `edge_type` at all;
3. **an arrow pointing the wrong way**, which draws the excavation upside down
   and is only ever caught by a person looking at a matrix;
4. **a row quietly dropped**, so a delivery reports success over an incomplete
   excavation.

The vocabulary test reads the DATAMODEL rather than restating it, so the day
`is_after` is renamed this file fails instead of the graph going quiet.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from pyarchinit_mini.connector.us_ops import (
    RELATIONSHIPS, UNIT_TYPES, DEFAULT_UNIT_TYPE, Delivery, deliver,
    edge_id, normalize_area, ops_for_units, unit_id)

SITE = "Scavo di prova"


def unit(us, *, area="1", tipo="US", **extra):
    row = {"sito": SITE, "area": area, "us": us, "unita_tipo": tipo,
           "d_stratigrafica": f"strato {us}"}
    row.update(extra)
    return row


def rel(left, right, verb, **extra):
    row = {"sito": SITE, "us_from": left, "us_to": right,
           "relationship_type": verb}
    row.update(extra)
    return row


# ── 1 · the identifiers ──────────────────────────────────────────────────────

def test_the_same_unit_gives_the_same_id_and_two_units_do_not():
    """The property the whole delivery rests on.

    `stratigraph/uuid_manager.py` mints `uuid4`, and with it the same unit
    delivered twice would be two nodes. This is why it is not used.
    """
    once = unit_id(SITE, "1", "12")
    again = unit_id(SITE, "1", "12")
    assert once == again

    assert unit_id(SITE, "1", "13") != once, "two units share an id"
    assert unit_id(SITE, "2", "12") != once, "two areas share an id"
    assert unit_id("Altro scavo", "1", "12") != once, "two sites share an id"


def test_an_absent_area_and_an_empty_one_are_the_same_unit():
    """The `area` decision, asserted rather than left in a comment.

    `us_service.create_us` compares `US.area == us_data.get('area', '')`, so for
    the service an absent area IS the empty string — while the column is
    nullable, and `area = ''` does not match `area IS NULL` in SQL. This adapter
    follows the service.

    The consequence is asserted too: a database holding both would get one node.
    """
    assert normalize_area(None) == ""
    assert normalize_area("") == ""
    assert normalize_area("   ") == ""

    assert unit_id(SITE, None, "12") == unit_id(SITE, "", "12")
    assert unit_id(SITE, None, "12") == unit_id(SITE, "  ", "12")
    # …and whitespace around a REAL area does not make a second unit either
    assert unit_id(SITE, " A ", "12") == unit_id(SITE, "A", "12")


def test_an_edge_id_is_the_triple_the_editor_also_composes():
    """Borrowed, not invented: `EMStudio/frontend/src/crdt.ts:622`.

    Same convention means an edge delivered from here and the same edge drawn by
    hand in the editor are ONE edge, so the second merges instead of doubling
    the arrow.
    """
    assert edge_id("a", "is_after", "b") == "a__is_after__b"


# ── 2 · the vocabulary is read, never remembered ─────────────────────────────

def _datamodel(name: str):
    """The datamodel from the s3Dgraphy checkout beside this repository.

    Skipped when it is not there: it is not a dependency of this project's
    tests. What is refused is a DISAGREEMENT, never a missing neighbour.
    """
    path = (pathlib.Path(__file__).resolve().parents[2].parent / "s3Dgraphy"
            / "src" / "s3dgraphy" / "JSON_config" / name)
    if not path.exists():
        pytest.skip(f"s3Dgraphy not checked out beside this repo ({path})")
    return json.loads(path.read_text())


def test_every_edge_type_this_adapter_can_emit_exists_in_the_datamodel():
    """The one that would have caught the existing converter's bug.

    `s3d_integration/s3d_converter.py:220` emits `is_before`, which is not in
    connections 1.6.13 — and nothing complains: `Graph.add_edge` degrades it to
    `generic_connection` with a warning (graph.py:208), and
    `apply_op_to_section`, which is the path a CRDT operation takes, does not
    check at all. So an invented type lands and the graph goes quiet.
    """
    known = _datamodel("s3Dgraphy_connections_datamodel.json")["edge_types"]
    mine = {pair[0] for pair in RELATIONSHIPS.values() if pair is not None}
    assert mine, "the relationship table is empty?"
    unknown = sorted(t for t in mine if t not in known)
    assert not unknown, (
        f"{unknown} are not edge types in the connections datamodel. Nothing "
        f"in the CRDT path validates this, so such an edge lands silently and "
        f"is only found by somebody reading a matrix.")
    # …and the one that is NOT there, pinned so nobody puts it back
    assert "is_before" not in known, (
        "`is_before` now exists in the datamodel: the module docstring's "
        "explanation of the converter's bug needs updating")
    assert "is_after" in known


def test_every_node_type_this_adapter_can_emit_exists_in_s3dgraphy():
    """Same rule for the nodes, read off the class definitions."""
    import re
    path = (pathlib.Path(__file__).resolve().parents[2].parent / "s3Dgraphy"
            / "src" / "s3dgraphy" / "nodes" / "stratigraphic_node.py")
    if not path.exists():
        pytest.skip("s3Dgraphy not checked out beside this repo")
    known = set(re.findall(r'node_type\s*=\s*"([^"]+)"', path.read_text()))
    mine = set(UNIT_TYPES.values()) | {DEFAULT_UNIT_TYPE}
    unknown = sorted(t for t in mine if t not in known)
    assert not unknown, (
        f"{unknown} are not stratigraphic node types in s3Dgraphy. A node with "
        f"a made-up type is worse than a node that is missing.")


def test_the_remapping_of_the_virtual_units_is_the_repositorys_own():
    """`USVA`/`USVB` → `USVs`, `USVC` → `USVn`.

    Read off `_2026_05_vocab_alignment.py` rather than typed here: it is this
    project's declared vocabulary decision, and two copies of it would diverge.
    """
    from pyarchinit_mini.database.migrations import _2026_05_vocab_alignment as v

    for old, new in v.REMAP.items():
        assert UNIT_TYPES.get(old) == new, (
            f"the migration remaps {old} → {new}; this adapter says "
            f"{UNIT_TYPES.get(old)!r}")


# ── 3 · the direction, which is the classic error ────────────────────────────

def test_copre_runs_from_the_more_recent_to_the_more_ancient():
    """`A copre B` → `A —is_after→ B`, and the reason is quoted from the source.

    connections 1.6.13 on `is_after`: «This is the canonical direction in
    Extended Matrix (from more recent to more ancient)». A unit that lies over
    another is the more recent one, so it is the source.

    Inverting this draws the excavation upside down and nothing in the pipeline
    objects.
    """
    made = deliver([unit("10"), unit("20")], [rel(10, 20, "Copre")])
    edges = [o for o in made.ops if o["op"] == "add_edge"]
    assert len(edges) == 1, made.counts
    assert edges[0]["edge_type"] == "is_after"
    assert edges[0]["source"] == unit_id(SITE, "1", "10"), \
        "the covering unit must be the source: it is the later one"
    assert edges[0]["target"] == unit_id(SITE, "1", "20")
    # the excavation's own word is kept beside the graph's
    assert edges[0]["attributes"]["pyarchinit_relationship"] == "Copre"


def test_the_table_stores_both_directions_and_only_one_edge_comes_out():
    """46 `Copre` and 46 `Coperto da` in the tutorial database.

    A naive mapping produces two arrows for one relationship. The inverse verbs
    map to `None` — skipped, and counted apart from the verbs nobody knows.
    """
    made = deliver([unit("10"), unit("20")],
                   [rel(10, 20, "Copre"), rel(20, 10, "Coperto da")])
    edges = [o for o in made.ops if o["op"] == "add_edge"]
    assert len(edges) == 1, [e["id"] for e in edges]
    assert made.counts["relationships_inverse_skipped"] == 1
    assert made.counts["relationships"] == 1


def test_a_symmetric_relation_is_one_edge_whichever_row_records_it():
    """`Uguale a` has no direction, and the table records it twice.

    The endpoints are sorted so both rows compose the same edge id and the
    second merges. Without that, the symmetric verbs would be the one place that
    still doubled.
    """
    both = deliver([unit("10"), unit("20")],
                   [rel(10, 20, "Uguale a"), rel(20, 10, "Uguale a")])
    edges = [o for o in both.ops if o["op"] == "add_edge"]
    assert len({e["id"] for e in edges}) == 1, [e["id"] for e in edges]
    assert edges[0]["edge_type"] == "is_physically_equal_to"


def test_each_physical_relation_keeps_its_own_verb():
    """`cuts`, `fills`, `abuts` — not all flattened into a chronology.

    The existing converter maps COVERS, CUTS and FILLS all to one edge type;
    the datamodel has three, and losing the distinction loses what the
    excavation observed.
    """
    made = deliver([unit(str(n)) for n in (1, 2, 3, 4)],
                   [rel(1, 2, "Taglia"), rel(3, 4, "Riempie"),
                    rel(1, 3, "Si appoggia a")])
    kinds = {o["edge_type"] for o in made.ops if o["op"] == "add_edge"}
    assert kinds == {"cuts", "fills", "abuts"}, kinds


def test_the_chronological_consequence_of_a_physical_relation_is_NOT_inferred():
    """`A taglia B` implies A is later, and this adapter does not say so.

    Both `cuts` and `is_after` exist, so emitting both would be recording an
    inference as a record. Asserted because it is a decision somebody may want
    to reverse, and reversing it should be deliberate.
    """
    made = deliver([unit("1"), unit("2")], [rel(1, 2, "Taglia")])
    kinds = [o["edge_type"] for o in made.ops if o["op"] == "add_edge"]
    assert kinds == ["cuts"], kinds


# ── 4 · nothing is dropped quietly ───────────────────────────────────────────

def test_a_verb_nobody_knows_is_counted_and_named():
    """`>>`, `<<`, `>`, `<` are in the tutorial data (25 rows) and in nobody's
    vocabulary — not in this repository's own `RELATIONSHIP_TYPES` either."""
    made = deliver([unit("1"), unit("2")],
                   [rel(1, 2, ">>"), rel(1, 2, "<")])
    assert not [o for o in made.ops if o["op"] == "add_edge"]
    assert made.counts["relationships_unknown_verb_>>"] == 1
    assert made.counts["relationships_unknown_verb_<"] == 1
    assert len(made.skipped) == 2
    assert ">>" in made.skipped[0]


def test_a_unit_type_with_no_counterpart_is_left_out_and_said():
    """`USM` is pyarchinit's masonry unit and Extended Matrix has no USM.

    Choosing `US` or `USVs` for it would be an archaeological decision this
    adapter has no standing to make.
    """
    made = ops_for_units([unit("1"), unit("2", tipo="USM")])
    assert len(made.ops) == 1
    assert made.counts["units"] == 1
    assert made.counts["units_unmappable_type_USM"] == 1
    assert "USM" in made.skipped[0] and "left out" in made.skipped[0]


def test_a_row_that_cannot_be_identified_is_refused():
    made = ops_for_units([unit("1"), {"sito": SITE, "us": None},
                          {"sito": "", "us": "9"}])
    assert made.counts["units"] == 1
    assert made.counts["units_unidentifiable"] == 2


def test_a_relationship_to_a_unit_that_was_not_delivered_is_refused():
    """An `add_edge` between ids nobody can resolve is an arrow into nothing.

    It would be APPLIED — `apply_op_to_section` does not check that an edge's
    endpoints exist — so this has to be caught here.
    """
    made = deliver([unit("1"), unit("2", tipo="USM")], [rel(1, 2, "Copre")])
    assert not [o for o in made.ops if o["op"] == "add_edge"]
    assert made.counts["relationships_dangling"] == 1
    assert "not delivered" in made.skipped[-1]


def test_a_unit_with_no_declared_type_takes_the_default_and_is_counted():
    """A row of `us_table` that does not say which subtype it is, is a plain
    stratigraphic unit — and the count says how many took that route, so the
    default is never invisible."""
    made = ops_for_units([unit("1", tipo=None), unit("2", tipo="")])
    assert [o["node"]["node_type"] for o in made.ops] == ["US", "US"]
    assert made.counts["units_typed_by_default"] == 2


# ── 5 · what the adapter must never write ────────────────────────────────────

def test_no_operation_carries_an_author_or_a_timestamp():
    """The server writes both.

    `ws.apply_from_connector` pops `author` and defaults `ts`. An adapter that
    wrote the first would be stating who did something; one that wrote the
    second would be deciding the clock a merge is judged by.
    """
    made = deliver([unit("1"), unit("2")], [rel(1, 2, "Copre")])
    assert made.ops
    for op in made.ops:
        assert "author" not in op, op
        assert "ts" not in op, op
        assert "author" not in json.dumps(op)


def test_the_node_payload_is_in_the_key_the_crdt_reads():
    """`node`, not the top level.

    `apply_op_to_section` reads `dict(op.get("node") or op.get("data") or {})`.
    An operation with `node_type` beside `op` and `id` is accepted and lands a
    node with no type and no name — measured, silently.
    """
    made = ops_for_units([unit("1")])
    op = made.ops[0]
    assert set(op) == {"op", "id", "node"}, (
        f"keys outside `node` are dropped by the CRDT: {sorted(op)}")
    assert op["node"]["node_type"] == "US"
    assert op["node"]["name"] == "1"
    assert op["node"]["data"]["origin"] == "pyarchinit-mini"


def test_the_adapter_touches_no_network_and_no_session():
    """Purity, read off the module rather than promised in a docstring."""
    import inspect
    import re

    from pyarchinit_mini.connector import us_ops

    code = re.sub(r'"""[\s\S]*?"""', '""', inspect.getsource(us_ops))
    code = re.sub(r"#[^\n]*", "", code)
    for forbidden in ("requests", "urllib", "http", "socket", "get_session",
                      "db_manager", "sqlalchemy", "Session"):
        assert forbidden not in code, (
            f"{forbidden!r} appears in the adapter: it is meant to be a "
            f"function from rows to operations, and that purity is what lets it "
            f"be tested without a database or a server")

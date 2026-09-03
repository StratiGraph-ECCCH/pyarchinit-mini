"""A row of `us_table` becomes a node; a row of `us_relationships_table`
becomes an edge. Nothing else.

Pure: rows in, CRDT operations out. No session, no socket, no token — see the
package docstring for why that matters.

════════════════════════════════════════════════════════════════════════════════
EVERYTHING BELOW WAS MEASURED, on 13 September 2026, against s3Dgraphy
1.6.0.dev17 (node datamodel 1.6.4, connections datamodel 1.6.13) and against
`data/pyarchinit_tutorial.db` (51 units and 187 relationships for one site).
The vocabulary is not remembered and not invented: where a concept of this
database has no counterpart there, it is LEFT OUT and counted, because a node
with a made-up type is worse than a node that is missing.
════════════════════════════════════════════════════════════════════════════════

## THE IDENTIFIERS — the decision everything else rests on

`pyarchinit_mini/stratigraph/uuid_manager.py` mints `str(uuid.uuid4())`. If this
adapter used that, the same unit delivered twice would be two nodes, and the
same unit seen from EMStudio and from here would be two things. **It is not
used.**

Ids are DERIVED, with `s3dgraphy.contract.core.stable_id` — `uuid5` over a
shared namespace, so two computations over the same datum give the same id, in
this process, in another tool, next year:

    stable_id("pyarchinit-mini", "us", sito, area, us)

### The natural key, and the `area` question the prompt asked about

A unit is `(sito, area, us)`. Measured:

* `models/us.py:18` — `us_table`, primary key `id_us` autoincrement, and **no
  `UniqueConstraint`** on the triple;
* `database/schemas.py:104` — a NON-unique index `idx_us_sito_area_us`;
* `services/us_service.py:60` — uniqueness is enforced BY HAND, and the line is
  the interesting one:

      US.area == us_data.get('area', '')

  It compares against `''` while the column is `Text` and nullable. So for the
  service, an absent `area` IS the empty string — and for SQLite and PostgreSQL,
  `area = ''` does **not** match a row where `area IS NULL`. The hand-written
  check therefore misses a duplicate whose stored `area` is NULL.

**What this adapter chose, and it is a choice with a consequence:** `area` is
normalised to `''` when it is NULL, empty or whitespace, so `NULL` and `''` name
the SAME node. That follows the service's own convention rather than the
column's, on the ground that the service is what users go through. The
consequence, stated: a database that somehow holds both a NULL-area and an
empty-area unit with the same number gets ONE node, and the second delivery
merges into the first. Given the service refuses to create the pair, that is
consistent — but it is an assumption, not a fact about the schema.

Measured in both sample databases: `area NULL: 0`, `area '': 0`, values `'1'`,
`'A'`, `'Port'`. So today the question is theoretical, which is exactly when to
answer it.

## THE UNIT TYPES

`us_table.unita_tipo` holds, in the tutorial database: `None`, `US`, `USM`,
`USVA`, `USVB`, `CON`, `Extractor`, `SF`.

s3Dgraphy's stratigraphic node types (`nodes/stratigraphic_node.py`):
`US`, `USVs`, `USVn`, `USD`, `SF`, `VSF`, `RSF`, `serSU`, `serUSVn`, `serUSVs`,
`serUSD`, `TSU`, `UL`, `USN`, `USNt`, `BR`, `SE`.

`USVA`/`USVB` → `USVs` and `USVC` → `USVn` are **this repository's own**
mapping, not one invented here: `database/migrations/_2026_05_vocab_alignment.py`
declares `REMAP = {"USVA": "USVs", "USVB": "USVs", "USVC": "USVn"}`.

## THE RELATIONSHIPS, AND THE DIRECTION — where the classic error lives

`us_relationships_table` (`models/harris_matrix.py:28`) stores
`(sito, us_from, us_to, relationship_type, certainty)`, and it stores **both
directions**: 46 `Copre` and 46 `Coperto da`, 17 `Taglia` and 17 `Tagliato da`.
A naive mapping produces two edges for one relationship.

So each verb pair has ONE canonical side and the inverse is skipped. Which side
is canonical is not a preference — the connections datamodel says it:

    is_after · "Indicates a temporal sequence where one item occurs after
                another. This is the canonical direction in Extended Matrix
                (from more recent to more ancient)"

`A copre B` means A lies over B, so A is the more recent: the edge runs
**A → B** with `is_after`. Inverting it would draw the excavation upside down,
and — this is why it is worth the paragraph — **nothing would complain**:
`apply_op_to_section` does not validate `edge_type` at all, and `Graph.add_edge`,
which does, is not on this path. The direction is only ever checked by a person
looking at a matrix.

`is_before` DOES NOT EXIST in connections 1.6.13. Worth stating because
`s3d_integration/s3d_converter.py:220` emits it, and the consequence was
measured: `Graph.add_edge` finds the type unallowed and **silently degrades it to
`generic_connection`** (graph.py:208-210). Running that converter over this same
site produces 51 nodes of type `Node` and 144 edges of type
`generic_connection` — an em.json with no stratigraphy left in it. That is why
that code could not be reused.

## WHAT IS NOT WRITTEN HERE, ON PURPOSE

* **`author`** — the server writes it from the token
  (`ws.apply_from_connector` pops whatever is in the payload). An adapter that
  wrote it would be stating who did something.
* **`ts`** — the server defaults it (`entry.setdefault("ts", now_iso())`). The
  consequence, declared: a second delivery therefore carries a NEWER clock than
  the first, so `update_field` operations WIN rather than being refused as
  idempotent. `add_node` merges either way and the graph does not move on the
  data this adapter produces, because it produces no `update_field` — but a
  future version that does must decide where its clock comes from.
* **the chronological consequence of a physical relation.** `cuts`, `fills` and
  `abuts` all imply «later than» to an archaeologist. Both the physical verb and
  `is_after` exist in the datamodel, and this adapter emits only the physical
  one. Emitting both would be recording an inference as a record; the inference
  belongs to whoever reads the matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# The contract's own deterministic id. Imported rather than reimplemented: the
# whole point is that another tool computing the same id gets the same answer,
# and that stops being true the moment there are two implementations.
from s3dgraphy.contract.core import stable_id

#: What this connector calls itself inside a derived id. A namespace part, so
#: two different tools deriving an id for the same excavation do not collide by
#: accident — and so that a node's id says where it was minted.
ORIGIN = "pyarchinit-mini"

#: `us_table.unita_tipo` → an s3Dgraphy `node_type`.
#:
#: `USVA`/`USVB`/`USVC` come from this repository's own vocabulary migration.
#: What is NOT here is as deliberate as what is:
#:
#:   USM       a masonry unit. pyarchinit's own concept; Extended Matrix has no
#:             USM, and choosing between `US` and `USVs` for it would be an
#:             archaeological decision this adapter has no standing to make.
#:   CON       undocumented in this repository (no constant, no vocabulary entry,
#:             no comment). An unknown three letters is not a type.
#:   Extractor `extractor` DOES exist in s3Dgraphy — but it is PARADATA, not a
#:             unit: it names the passage of a source that supports a statement.
#:             Minting one from a row of `us_table` would produce an extractor
#:             with no source document attached, which is a node that asserts a
#:             provenance nobody can follow.
UNIT_TYPES: Dict[str, str] = {
    "US": "US",
    "SF": "SF",
    "USVA": "USVs",
    "USVB": "USVs",
    "USVC": "USVn",
    "USVs": "USVs",
    "USVn": "USVn",
    "USD": "USD",
    "VSF": "VSF",
    "RSF": "RSF",
    "TSU": "TSU",
    "UL": "UL",
}

#: The type a row with no declared `unita_tipo` gets.
#:
#: A DEFAULT, which the contract normally forbids («missing slot → named, never
#: defaulted»), and the exception is argued rather than assumed: that rule is
#: about a caller's REQUEST, where a missing value means somebody did not say.
#: Here the value is a nullable column on a table called `us_table`, whose rows
#: are stratigraphic units by construction. A row that does not say which
#: subtype it is, is a plain one. The count of rows that took this default is
#: reported by `deliver`, so it is never invisible.
DEFAULT_UNIT_TYPE = "US"

#: `us_relationships_table.relationship_type` → (edge type, how to orient it).
#:
#: `"forward"` means the edge runs from `us_from` to `us_to`.
#: `"symmetric"` means the relation has no direction, so the edge is emitted
#: once with the two endpoints in a fixed order (see `_oriented`).
#: `None` means «this is the inverse of a pair already covered» — skipped, not
#: unknown, and the difference is reported separately.
RELATIONSHIPS: Dict[str, Optional[Tuple[str, str]]] = {
    # ── chronological, and the canonical direction of Extended Matrix ────────
    "Copre": ("is_after", "forward"),          # A lies over B → A is later
    "Coperto da": None,                        # …the inverse of the above
    "Posteriore a": ("is_after", "forward"),
    "Anteriore a": None,
    # ── physical relations, each with its own verb ───────────────────────────
    "Taglia": ("cuts", "forward"),
    "Tagliato da": None,
    "Riempie": ("fills", "forward"),
    "Riempito da": None,
    "Si appoggia a": ("abuts", "forward"),
    "Gli si appoggia": None,
    # ── symmetric ────────────────────────────────────────────────────────────
    "Si lega a": ("is_bonded_to", "symmetric"),
    "Uguale a": ("is_physically_equal_to", "symmetric"),
    "Contemporaneo a": ("has_same_time", "symmetric"),
}

#: The fields of a unit that travel into the node's `data`, and the name they
#: travel under. Only what a graph can be read for: the identity of the unit,
#: what it is, what it was understood to be, and when.
#:
#: The 70 columns of `us_table` are NOT all copied. A node is not a row: an
#: excavation's record lives in this database and stays there, and what goes
#: into a shared graph is what somebody else needs in order to reason about the
#: stratigraphy. The rest is available to whoever opens pyarchinit-mini.
UNIT_FIELDS: Dict[str, str] = {
    "sito": "site",
    "area": "area",
    "us": "unit",
    "d_stratigrafica": "stratigraphic_definition",
    "d_interpretativa": "interpretive_definition",
    "descrizione": "description",
    "interpretazione": "interpretation",
    "periodo_iniziale": "period_start",
    "fase_iniziale": "phase_start",
    "periodo_finale": "period_end",
    "fase_finale": "phase_end",
    "anno_scavo": "excavation_year",
    "scavato": "excavated",
}


def normalize_area(area: Any) -> str:
    """One spelling for «no area» — see the module docstring's `area` section.

    NULL, `""` and whitespace all become `""`, which is the value
    `us_service.create_us` compares against.
    """
    if area is None:
        return ""
    return str(area).strip()


def unit_id(sito: Any, area: Any, us: Any) -> str:
    """The id of a stratigraphic unit, derived from what identifies it.

    Deterministic: the same three values give the same id every time, which is
    what makes a second delivery a merge instead of a duplicate.
    """
    return stable_id(ORIGIN, "us", str(sito or "").strip(),
                     normalize_area(area), str(us or "").strip())


def edge_id(source: str, edge_type: str, target: str) -> str:
    """`source__type__target`, and the shape is borrowed rather than invented.

    `EMStudio/frontend/src/crdt.ts:622` composes exactly this when an edge
    arrives without an id. Using the same convention means an edge produced here
    and the same edge drawn by hand in the editor **are one edge**, so the
    second one merges instead of doubling the arrow.
    """
    return f"{source}__{edge_type}__{target}"


@dataclass
class Delivery:
    """The operations, and an honest account of what did not become one.

    `skipped` is prose for a person; `counts` is for a caller that wants to
    decide whether to go ahead. Both, because «12 units delivered» without «and
    3 rows I could not read» is a report that hides its own limits.
    """

    ops: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    def bump(self, key: str, by: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + by


def _oriented(source: str, target: str, how: str) -> Tuple[str, str]:
    """Which way the edge runs.

    For a symmetric relation the endpoints are SORTED, so the two rows that
    record it (`A uguale a B` and `B uguale a A`) produce the same edge id and
    the second one merges. Without this the symmetric verbs would be the one
    place that still doubled.
    """
    if how == "symmetric":
        return (source, target) if source <= target else (target, source)
    return source, target


def _node_data(row: Dict[str, Any]) -> Dict[str, Any]:
    kept: Dict[str, Any] = {}
    for column, name in UNIT_FIELDS.items():
        value = row.get(column)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        kept[name] = value.strip() if isinstance(value, str) else value
    # The origin travels WITH the node, so a graph holding units from two
    # databases can say which came from where without an external register.
    kept["origin"] = ORIGIN
    return kept


def ops_for_units(units: Iterable[Dict[str, Any]],
                  delivery: Optional[Delivery] = None) -> Delivery:
    """`add_node` for each unit, and a line for each one refused.

    THE PAYLOAD GOES IN `node`, and that is not a stylistic choice:
    `apply_op_to_section` reads `dict(op.get("node") or op.get("data") or {})`
    (crdt.py:727). An operation carrying `node_type` and `name` at the top level
    is ACCEPTED and lands a node with neither — measured, silently. And
    `update_field` cannot repair it afterwards: only `name`, `description` and
    `data.*` are addressable (crdt.py:749), so `node_type` travels here or not
    at all.
    """
    made = delivery if delivery is not None else Delivery()
    for row in units:
        sito, us = row.get("sito"), row.get("us")
        if not str(sito or "").strip() or not str(us or "").strip():
            made.skipped.append(
                f"a row with sito={sito!r} and us={us!r}: a unit with no site "
                f"or no number cannot be identified, so it cannot be a node")
            made.bump("units_unidentifiable")
            continue

        declared = str(row.get("unita_tipo") or "").strip()
        if not declared:
            node_type = DEFAULT_UNIT_TYPE
            made.bump("units_typed_by_default")
        elif declared in UNIT_TYPES:
            node_type = UNIT_TYPES[declared]
            if UNIT_TYPES[declared] != declared:
                made.bump(f"units_remapped_{declared}_to_{UNIT_TYPES[declared]}")
        else:
            made.skipped.append(
                f"{sito}/{normalize_area(row.get('area'))}/{us}: "
                f"unita_tipo={declared!r} has no counterpart among s3Dgraphy's "
                f"stratigraphic node types — left out rather than approximated")
            made.bump(f"units_unmappable_type_{declared}")
            continue

        node = unit_id(sito, row.get("area"), us)
        made.ops.append({
            "op": "add_node",
            "id": node,
            "node": {
                "node_type": node_type,
                # The unit's own number is its name. Not "US 12": the number is
                # what an archaeologist wrote on the form and what they will
                # look for in the graph.
                "name": str(us).strip(),
                "description": (row.get("d_stratigrafica") or "").strip() or None,
                "data": _node_data(row),
            },
        })
        made.bump("units")
    return made


def ops_for_relationships(relationships: Iterable[Dict[str, Any]],
                          *, known: Optional[Dict[str, str]] = None,
                          delivery: Optional[Delivery] = None) -> Delivery:
    """`add_edge` for each relationship whose verb has a counterpart.

    `known` maps `(sito, us)` — as `"sito\\x00us"` — to a node id, so an edge is
    only produced between two units that were actually delivered. Without it a
    relationship pointing at a unit from another site, or at one that was
    skipped, would produce an edge to a node that is not there.

    THE JOIN IS BETWEEN TYPES THAT DO NOT MATCH, and it is worth knowing:
    `us_relationships_table.us_from/us_to` are `Integer`
    (`models/harris_matrix.py:36-37`) while `us_table.us` is
    `Text` — «TEXT for unlimited alphanumeric US codes», says the model's own
    comment. So a unit numbered `12a` **cannot be referenced by a
    relationship at all**. Measured on the tutorial database: all 187
    relationships resolve, because that site's units are numbered `1`…`51`.

    AND THERE IS NO `area`. A relationship is `(sito, us_from, us_to)`, while a
    unit is `(sito, area, us)`. On a site with two areas that both have a unit
    `1`, a relationship is ambiguous — and this function resolves it against
    whatever unit was delivered for that number, reporting when a number matched
    more than one.
    """
    made = delivery if delivery is not None else Delivery()
    index = known or {}
    for row in relationships:
        sito = str(row.get("sito") or "").strip()
        verb = str(row.get("relationship_type") or "").strip()
        left, right = row.get("us_from"), row.get("us_to")

        if verb not in RELATIONSHIPS:
            made.skipped.append(
                f"{sito}: {left} —{verb!r}→ {right}: this verb is not in the "
                f"repository's own RELATIONSHIP_TYPES either "
                f"(relationship_sync_service.py:26), so there is nothing to map "
                f"it to")
            made.bump(f"relationships_unknown_verb_{verb or 'empty'}")
            continue

        mapping = RELATIONSHIPS[verb]
        if mapping is None:
            # The inverse of a pair already covered. NOT an error, and counted
            # apart from the unknown verbs: it is how a full arrow gets recorded
            # once from a table that stores it twice.
            made.bump("relationships_inverse_skipped")
            continue

        edge_type, how = mapping
        source = index.get(f"{sito}\x00{str(left).strip()}")
        target = index.get(f"{sito}\x00{str(right).strip()}")
        if source is None or target is None:
            missing = left if source is None else right
            made.skipped.append(
                f"{sito}: {left} —{verb}→ {right}: unit {missing} was not "
                f"delivered (another site, another area, or a skipped type), so "
                f"the edge would point at a node that is not there")
            made.bump("relationships_dangling")
            continue
        if source == target:
            made.skipped.append(
                f"{sito}: {left} —{verb}→ {right}: both ends resolve to the "
                f"same node")
            made.bump("relationships_self")
            continue

        source, target = _oriented(source, target, how)
        made.ops.append({
            "op": "add_edge",
            "id": edge_id(source, edge_type, target),
            "source": source,
            "target": target,
            "edge_type": edge_type,
            # The excavation's own word for the relation, kept beside the
            # graph's: `is_after` is what the ecosystem reasons in, `Copre` is
            # what the archaeologist wrote, and losing it would make the graph
            # unable to explain itself back to the person who filled the form.
            "attributes": {"pyarchinit_relationship": verb,
                           **({"certainty": row["certainty"]}
                              if row.get("certainty") else {})},
        })
        made.bump("relationships")
    return made


def deliver(units: Iterable[Dict[str, Any]],
            relationships: Iterable[Dict[str, Any]] = ()) -> Delivery:
    """Units first, then the relationships between the ones that landed.

    The order is the reason this is one function: an edge whose endpoints were
    not delivered is refused by the room (`update_field`/`remove_node` say
    «node is not here»), and `add_edge` would land an arrow between two ids
    nobody can resolve. So the index of what was delivered is built here and
    handed to the second half.
    """
    made = ops_for_units(units)
    index: Dict[str, str] = {}
    collisions: Dict[str, int] = {}
    for op in made.ops:
        data = op["node"]["data"]
        key = f"{data.get('site')}\x00{data.get('unit')}"
        if key in index and index[key] != op["id"]:
            collisions[key] = collisions.get(key, 1) + 1
        index[key] = op["id"]
    for key, count in collisions.items():
        site, unit = key.split("\x00")
        made.skipped.append(
            f"{site}: unit {unit} exists in {count} areas, and "
            f"us_relationships_table has no `area` column — its relationships "
            f"resolve to whichever area came last")
        made.bump("units_ambiguous_across_areas")

    return ops_for_relationships(relationships, known=index, delivery=made)

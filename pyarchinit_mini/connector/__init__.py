"""The connector's side of the house: from this database to a graph's operations.

## WHY A NEW PACKAGE, and why not one of the three that already exist

* `pyarchinit_mini/stratigraph/` — the map of the useless says not to reuse it,
  and the reason is measured: `sync_orchestrator.py:45` posts to
  `http://localhost:8080/api/v1/bundles`, an endpoint that exists in no
  repository. Its bundle/manifest/validator/state-machine is a parallel
  invention of what a room and a CRDT already do.
* `pyarchinit_mini/sync/` — 547 lines of generic table diffing with no external
  caller, superseded by `s3dgraphy/crdt.py`, which does last-writer-wins per
  field with clocks and tombstones.
* `pyarchinit_mini/s3d_integration/` — builds a whole `s3dgraphy.Graph` and
  exports a DOCUMENT. That is a different job from producing a DELTA, and the
  difference is not cosmetic: a document says «this is the graph», a delta says
  «this is what I changed in the graph you are working on». Only the second can
  be handed to a room somebody else is editing.

So: a package of its own, named after the contract it serves
(`s3dgraphy.contract.connector`), holding pure functions.

**Purity is the whole design.** Nothing here opens a session, a socket or a
file. It takes rows — plain dictionaries — and returns CRDT operations. That is
what lets it be tested without a database, a server or a token, and what keeps
the question «what does an excavation look like as a graph» separate from the
question «how do I deliver it».
"""

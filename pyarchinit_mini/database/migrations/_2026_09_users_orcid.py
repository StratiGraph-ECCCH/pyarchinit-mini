"""Schema migration (2026-09-12):
Add `orcid TEXT` column + UNIQUE INDEX on the `users` table.

The ORCID iD is the identity the StratiGraph ecosystem indexes people by — a
room's ACL is keyed on it (`PUT /rooms/{room_id}/members/{orcid}`). A local
account may now carry one; almost none will.

Idempotent: re-running on a DB that already has the column is a no-op.
Supports SQLite and PostgreSQL backends.

WHY A UNIQUE INDEX AND NOT A UNIQUE CONSTRAINT: an index is what the two
migrations before this one create (`_2026_05_node_uuid_schema`), and on SQLite
`ALTER TABLE … ADD CONSTRAINT` does not exist. A partial index would be tidier
still — NULLs are already exempt from uniqueness on both backends, so a plain
unique index lets any number of accounts have no iD and no two share one, which
is exactly the rule.

NOT ALEMBIC, on purpose: alembic is among the dependencies but it is not the
mechanism this project uses for these columns. `DatabaseManager.run_migrations()`
imports scripts like this one by name and calls `run(url)`, and every one of them
is written to be safe on every startup.
"""
import sqlite3
from dataclasses import dataclass, field


@dataclass
class MigrationReport:
    script: str
    db: str
    tables_changed: list = field(default_factory=list)
    tables_skipped: list = field(default_factory=list)
    dry_run: bool = False
    status: str = "ok"


TABLE = "users"
COLUMN = "orcid"


def _table_exists_sqlite(conn, table):
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return r is not None


def _has_column_sqlite(conn, table, col):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def _run_sqlite(path: str, dry_run: bool, report: MigrationReport) -> None:
    conn = sqlite3.connect(path)
    try:
        if not _table_exists_sqlite(conn, TABLE):
            # A database with no `users` table at all is a database `create_all()`
            # has not reached yet; it will be created WITH the column, so there is
            # nothing to alter and nothing to complain about.
            report.tables_skipped.append(f"{TABLE} (missing)")
            return
        if _has_column_sqlite(conn, TABLE, COLUMN):
            report.tables_skipped.append(f"{TABLE} (already has {COLUMN})")
            return
        if not dry_run:
            conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} TEXT")
            conn.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{TABLE}_{COLUMN} "
                f"ON {TABLE}({COLUMN})"
            )
            conn.commit()
        report.tables_changed.append(TABLE)
    finally:
        conn.close()


def _run_postgresql(url: str, dry_run: bool, report: MigrationReport) -> None:
    from sqlalchemy import create_engine, text
    eng = create_engine(url)
    with eng.begin() as c:
        exists = c.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
            {"t": TABLE}
        ).first()
        if not exists:
            report.tables_skipped.append(f"{TABLE} (missing)")
            return
        col = c.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c"
            ),
            {"t": TABLE, "c": COLUMN}
        ).first()
        if col:
            report.tables_skipped.append(f"{TABLE} (already has {COLUMN})")
            return
        if not dry_run:
            c.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} TEXT"))
            c.execute(
                text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{TABLE}_{COLUMN} "
                     f"ON {TABLE}({COLUMN})")
            )
        report.tables_changed.append(TABLE)


def run(connection_url: str, *, dry_run: bool = False) -> MigrationReport:
    report = MigrationReport(
        script="2026_09_users_orcid",
        db=connection_url,
        dry_run=dry_run,
    )
    if connection_url.startswith("sqlite"):
        path = connection_url.replace("sqlite:///", "", 1)
        _run_sqlite(path, dry_run, report)
    elif connection_url.startswith("postgresql") or connection_url.startswith("postgres"):
        _run_postgresql(connection_url, dry_run, report)
    else:
        report.status = "unsupported_backend"
    return report

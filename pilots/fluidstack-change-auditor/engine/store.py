"""Content-addressed, append-only SQLite snapshots and audit reports."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from engine.audit import canonical_json


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS revisions (
                    id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, original BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS procurement (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audits (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def add_revision(self, snapshot, original):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO revisions VALUES (?, ?, ?)",
                (snapshot["id"], canonical_json(snapshot), original),
            )
        return self.revision(snapshot["id"])

    def revision(self, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT snapshot FROM revisions WHERE id = ?", (identifier,)
            ).fetchone()
        if row is None:
            raise KeyError("Revision not found")
        return json.loads(row[0])

    def original(self, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT original FROM revisions WHERE id = ?", (identifier,)
            ).fetchone()
        if row is None:
            raise KeyError("Revision not found")
        return row[0]

    def revisions(self):
        with self.connect() as db:
            snapshots = [
                json.loads(r[0])
                for r in db.execute("SELECT snapshot FROM revisions ORDER BY rowid")
            ]
        return [
            {
                **{k: v for k, v in s.items() if k != "components"},
                "component_count": len(s["components"]),
            }
            for s in snapshots
        ]

    def add_procurement(self, payload):
        serialized = canonical_json(payload)
        identifier = hashlib.sha256(serialized.encode()).hexdigest()
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO procurement VALUES (?, ?)",
                (identifier, serialized),
            )
        return identifier

    def procurement(self, identifier):
        return self._payload("procurement", identifier)

    def add_audit(self, report):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO audits VALUES (?, ?)",
                (report["id"], canonical_json(report)),
            )
        return report

    def audit(self, identifier):
        return self._payload("audits", identifier)

    def _payload(self, table, identifier):
        # table is always an internal constant, never user input.
        with self.connect() as db:
            row = db.execute(
                f"SELECT payload FROM {table} WHERE id = ?", (identifier,)
            ).fetchone()
        if row is None:
            raise KeyError("Record not found")
        return json.loads(row[0])

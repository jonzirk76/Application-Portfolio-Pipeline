"""Reuse revision/audit storage; add immutable drawing manifests and artifact bytes."""

import json

from engine.audit import canonical_json
from engine.store import Store


class EnclosureStore(Store):
    def __init__(self, path):
        super().__init__(path)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS packages (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS artifacts (
                    package_id TEXT NOT NULL, name TEXT NOT NULL, data BLOB NOT NULL,
                    PRIMARY KEY (package_id, name)
                );
            """)

    def add_package(self, package, files):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO packages VALUES (?, ?)",
                (package["id"], canonical_json(package)),
            )
            db.executemany(
                "INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?)",
                [(package["id"], name, data) for name, data in files.items()],
            )
        return self.package(package["id"])

    def package(self, identifier):
        return self._payload("packages", identifier)

    def packages(self):
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute("SELECT payload FROM packages ORDER BY rowid")
            ]

    def artifact(self, identifier, name):
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM artifacts WHERE package_id = ? AND name = ?", (identifier, name)
            ).fetchone()
        if row is None:
            raise KeyError("Drawing artifact not found")
        return bytes(row[0])

"""Disposable file/owner position index over verified native fact shards."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from library_guides.collection import CollectionError, confined
from library_guides.facts.contracts import FactArtifact

_VERSION = "locations.v1"
_MAX_ROWS = 2_000


def index(root: Path, artifact: FactArtifact) -> Path:
    """Index file coordinates without retaining a monolithic compiler document in Python.

    Returns:
        Disposable receipt-bound position index; caller verifies artifact bytes first.

    """
    path = confined(root, artifact.receipt_path).parent / "locations.sqlite"
    if path.is_file():
        try:
            with sqlite3.connect(path) as db:
                if db.execute("SELECT version,receipt FROM metadata").fetchone() == (
                    _VERSION,
                    artifact.receipt_digest,
                ):
                    return path
        except sqlite3.DatabaseError:
            pass
    with sqlite3.connect(path) as db:
        db.executescript(
            "DROP TABLE IF EXISTS locations; CREATE TABLE locations(id TEXT PRIMARY KEY, file TEXT, start INTEGER, end INTEGER, owner TEXT, family TEXT, kind TEXT); CREATE INDEX location_file ON locations(file,start,end); CREATE INDEX location_owner ON locations(owner); DROP TABLE IF EXISTS metadata; CREATE TABLE metadata(version TEXT, receipt TEXT);"
        )
        for shard in artifact.shards:
            with confined(root, shard.path).open("rb") as stream:
                for line in stream:
                    record = json.loads(line)
                    payload = record.get("payload", {})
                    anchor = payload.get("anchor", payload.get("source", payload))
                    start = anchor.get("start", anchor.get("byte_start"))
                    end = anchor.get("end", anchor.get("byte_end"))
                    if type(start) is int and type(end) is int:
                        db.execute(
                            "INSERT INTO locations VALUES (?,?,?,?,?,?,?)",
                            (
                                record["id"],
                                record.get("file", anchor.get("file", "")),
                                start,
                                end,
                                payload.get("owner"),
                                payload.get("family", ""),
                                payload.get("kind", payload.get("node_kind", "")),
                            ),
                        )
        db.execute("INSERT INTO metadata VALUES (?,?)", (_VERSION, artifact.receipt_digest))
    return path


def in_file(path: Path, file: str, start: int, end: int) -> list[str]:
    """Retrieve the finite source interval with no basename or approximate matching.

    Returns:
        Exact record IDs in deterministic source order.

    Raises:
        CollectionError: If an owner exceeds the finite position query budget.

    """
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        rows = db.execute(
            "SELECT id FROM locations WHERE file=? AND start>=? AND end<=? ORDER BY start,end,id LIMIT ?",
            (file, start, end, _MAX_ROWS + 1),
        ).fetchall()
    if len(rows) > _MAX_ROWS:
        message = "source owner exceeds 2000 position facts; select a smaller owner"
        raise CollectionError(message)
    return [r[0] for r in rows]

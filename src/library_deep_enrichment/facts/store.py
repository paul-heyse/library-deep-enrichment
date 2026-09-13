"""Content-addressed fact shards and a disposable, bounded query index."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from attrs import asdict

from library_deep_enrichment.collection import CollectionError, confined, select
from library_deep_enrichment.facts.contracts import FactArtifact, FactSelection
from library_deep_enrichment.facts.witness_origins import read as read_witness_origins
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file

_MAX_PAGE_ROWS = 200


def ensure_index(root: Path, artifact: FactArtifact, path: Path) -> None:
    """Rebuild a missing or obsolete disposable index from verified shard bytes."""
    compatible = False
    if path.is_file():
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(types)")}
                receipt = db.execute("SELECT digest FROM metadata").fetchone()
                routes = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='routes'"
                ).fetchone()
                compatible = (
                    "canonical" in columns
                    and routes is not None
                    and receipt == (artifact.receipt_digest,)
                )
        except sqlite3.DatabaseError:
            compatible = False
    if not compatible:
        build_index(root, artifact, path)


def verify(root: Path, artifact: FactArtifact) -> None:
    """Verify the raw input, receipt and all fact bytes.

    Raises:
        CollectionError: If content-addressed dependencies changed.

    """
    files = [
        (artifact.input_path, artifact.input_digest),
        (artifact.receipt_path, artifact.receipt_digest),
    ]
    files.extend((shard.path, shard.digest) for shard in artifact.shards)
    files.extend((item.path, item.digest) for item in artifact.witnesses)
    if artifact.acquisition_path:
        files.append((artifact.acquisition_path, artifact.acquisition_digest))
    for relative, expected in files:
        if digest_file(confined(root, relative)) != expected:
            message = f"fact artifact changed: {artifact.id}: {relative}"
            raise CollectionError(message)
    receipt = json.loads(confined(root, artifact.receipt_path).read_bytes())
    read_witness_origins(receipt)
    if receipt.get("dependencies", []) != [asdict(item) for item in artifact.dependencies]:
        message = f"fact derivation input manifest changed: {artifact.id}"
        raise CollectionError(message)
    if artifact.artifact_kind == "derived" and not artifact.dependencies:
        message = "derived evidence requires primitive support closure"
        raise CollectionError(message)
    if receipt.get("witnesses", []) != [asdict(item) for item in artifact.witnesses] or any(
        confined(root, item.path).stat().st_size != item.size for item in artifact.witnesses
    ):
        message = f"provenance witness manifest changed: {artifact.id}"
        raise CollectionError(message)
    header = json.loads(confined(root, artifact.header_path).read_bytes())
    if header != receipt["header"] or header["input_digest"] != artifact.input_digest:
        message = f"fact context changed: {artifact.id}"
        raise CollectionError(message)
    terminal = receipt["terminal"]
    if artifact.outcome != "complete" or terminal["coverage"]["state"] != "complete":
        message = f"incomplete fact artifact: {artifact.id}"
        raise CollectionError(message)
    if (
        sum(shard.records for shard in artifact.shards) != terminal["records"]
        or header["expected_records"] != terminal["records"]
    ):
        message = f"fact denominator changed: {artifact.id}"
        raise CollectionError(message)


def build_index(root: Path, artifact: FactArtifact, path: Path) -> None:
    """Build a disposable offset index over verified shards."""
    verify(root, artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript("""
            DROP TABLE IF EXISTS records;
            CREATE TABLE records(id TEXT PRIMARY KEY, symbol TEXT, kind TEXT, shard TEXT, start INTEGER, size INTEGER);
            CREATE INDEX record_symbol ON records(symbol);
            DROP TABLE IF EXISTS types;
            CREATE TABLE types(owner TEXT, role TEXT, nominal TEXT, direct INTEGER, selector TEXT, canonical TEXT);
            CREATE INDEX type_nominal ON types(nominal, role);
            DROP TABLE IF EXISTS routes;
            CREATE TABLE routes(owner TEXT, path TEXT, canonical TEXT);
            CREATE INDEX route_path ON routes(path);
            DROP TABLE IF EXISTS metadata;
            CREATE TABLE metadata(digest TEXT);
        """)
        db.execute("INSERT INTO metadata VALUES (?)", (artifact.receipt_digest,))
        for shard in artifact.shards:
            with confined(root, shard.path).open("rb") as stream:
                offset = 0
                for line in stream:
                    record = json.loads(line)
                    db.execute(
                        "INSERT INTO records VALUES (?,?,?,?,?,?)",
                        (
                            record["id"],
                            record.get("symbol", ""),
                            record.get("kind", ""),
                            shard.path,
                            offset,
                            len(line),
                        ),
                    )
                    for occurrence in record.get("type_occurrences", []):
                        db.execute(
                            "INSERT INTO types VALUES (?,?,?,?,?,?)",
                            (
                                record["id"],
                                occurrence["role"],
                                occurrence["path"],
                                occurrence["direct"],
                                occurrence["selector"],
                                occurrence.get("resolved_symbol"),
                            ),
                        )
                    db.executemany(
                        "INSERT INTO routes VALUES (?,?,?)",
                        (
                            (record["id"], route, record.get("symbol", ""))
                            for route in record.get("public_routes", [])
                        ),
                    )
                    offset += len(line)


def query(
    path: Path, text: str, *, role: str = "", limit: int = 30, offset: int = 0
) -> dict[str, object]:
    """Read bounded declaration/nominal-type candidates with explicit pagination.

    Returns:
        A finite page, total count and deterministic continuation position.

    Raises:
        CollectionError: If the query budget is invalid.

    """
    if not 1 <= limit <= _MAX_PAGE_ROWS or offset < 0:
        message = "query requires 1..200 rows and a nonnegative offset"
        raise CollectionError(message)
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        if role:
            sql = "SELECT DISTINCT r.* FROM records r JOIN types t ON r.id=t.owner WHERE (t.nominal=? OR t.canonical=? OR t.canonical IN (SELECT canonical FROM routes WHERE path=?)) AND (?='any' OR t.role=?)"
            args = (text, text, text, role, role)
        else:
            sql = "SELECT * FROM records WHERE instr(symbol,?)>0"
            args = (text,)
        total = db.execute(f"SELECT COUNT(*) FROM ({sql})", args).fetchone()[0]
        rows = [
            dict(row)
            for row in db.execute(
                sql + " ORDER BY symbol,id LIMIT ? OFFSET ?", (*args, limit, offset)
            )
        ]
    return {
        "state": "unreviewed",
        "total": total,
        "rows": rows,
        "next_offset": offset + len(rows) if offset + len(rows) < total else None,
    }


def record(root: Path, index: Path, identifier: str, *, artifact: FactArtifact) -> bytes:
    """Read an indexed record by exact identity.

    Returns:
        Canonical record bytes.

    Raises:
        CollectionError: If the record is missing or the disposable index is stale.

    """
    with sqlite3.connect(f"file:{index}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT shard,start,size FROM records WHERE id=?", (identifier,)
        ).fetchone()
    if row is None:
        message = f"unknown fact record: {identifier}"
        raise CollectionError(message)
    if row[0] not in {shard.path for shard in artifact.shards} or row[1] < 0 or row[2] <= 0:
        message = "fact index escapes its declared artifact"
        raise CollectionError(message)
    with confined(root, row[0]).open("rb") as stream:
        stream.seek(row[1])
        value = json.loads(stream.read(row[2]))
    if value["id"] != identifier:
        message = "stale fact offset index"
        raise CollectionError(message)
    return canonical_bytes(value)


def selected(root: Path, index: Path, selection: FactSelection, *, artifact: FactArtifact) -> bytes:
    """Resolve one exact fact field and verify its selected-content digest.

    Returns:
        Selected canonical bytes.

    Raises:
        CollectionError: If an entire record/corpus is offered or selected bytes changed.

    """
    if selection.selector in {"json:", "json:/", "json:/item"}:
        message = "a specific contract field is required"
        raise CollectionError(message)
    if selection.artifact != artifact.id:
        message = "selection names a different fact artifact"
        raise CollectionError(message)
    payload = select(record(root, index, selection.record, artifact=artifact), selection.selector)
    if digest_bytes(payload) != selection.digest:
        message = f"fact selection changed: {selection.record}"
        raise CollectionError(message)
    return payload

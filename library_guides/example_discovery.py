"""Source-backed example discovery; locating and parsing never imply execution."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from attrs import asdict, evolve
from filelock import FileLock

from library_guides import source_maps as maps
from library_guides.collection import CollectionError, confined, load, save, select
from library_guides.facts.contracts import (
    ExampleDiscovery,
    FactArtifact,
    FactSelection,
    FileEntry,
    SourceAnchor,
    SourceSnapshot,
)
from library_guides.facts.support import SupportGraph
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic

_MAX_PAGE = 100
_MAX_BYTES = 1_000_000


def discover(root: Path, identifier: str) -> dict[str, object]:
    """Discover examples from verified L1 documentation roles and exact source maps.

    Returns:
        Located/parsed examples and explicit per-file limitations, with no reviews added.

    Raises:
        CollectionError: If the artifact is not current structural evidence or authoring changes.

    """
    knowledge = load(root)
    if not isinstance(knowledge, KnowledgeV3):
        message = "source example discovery requires V3"
        raise CollectionError(message)
    before = digest_file(root / "knowledge.yaml")
    artifact = SupportGraph(root, knowledge).artifact(identifier)
    if artifact.artifact_kind != "syntax":
        message = "example discovery requires a source-facts artifact"
        raise CollectionError(message)
    snapshots = tuple(s for s in knowledge.source_snapshots if s.id in artifact.snapshots)
    examples, dispositions = _files(root, artifact, snapshots)
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        if digest_file(root / "knowledge.yaml") != before:
            message = "authoring changed during source example discovery"
            raise CollectionError(message)
        retained = {e.id: e for e in (*knowledge.example_discoveries, *examples)}
        save(root, evolve(knowledge, example_discoveries=tuple(retained.values())))
    report: dict[str, object] = {
        "artifact": artifact.id,
        "examples": [asdict(e) for e in examples],
        "files": dispositions,
        "execution": "not_requested",
    }
    write_atomic(
        root / "discovery" / f"{identifier.removeprefix('facts:')}.json", canonical_bytes(report)
    )
    return report


def _files(
    root: Path, artifact: FactArtifact, snapshots: tuple[SourceSnapshot, ...]
) -> tuple[list[ExampleDiscovery], list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for shard in artifact.shards:
        with confined(root, shard.path).open("rb") as stream:
            for line in stream:
                row = json.loads(line)
                grouped.setdefault(row["file"], []).append(row)
    examples = []
    dispositions: list[dict] = []
    for file, records in sorted(grouped.items()):
        matches = [
            (s, e)
            for s in snapshots
            for e in s.files
            if file in {e.path, e.path.removeprefix(f"snapshots/{s.source_digest}/source/")}
        ]
        if len(matches) != 1:
            dispositions.append(
                {"file": file, "state": "unresolved_source", "candidates": len(matches)}
            )
            continue
        snapshot, entry = matches[0]
        if entry.kind not in {"markdown", "rust", "python"}:
            dispositions.append(
                {
                    "file": file,
                    "state": "unsupported",
                    "reason": "source language not modeled for examples",
                }
            )
            continue
        try:
            found = _file_examples(
                confined(root, entry.path).read_bytes(), (snapshot, entry), records, artifact
            )
        except (CollectionError, UnicodeDecodeError, SyntaxError, ValueError) as error:
            dispositions.append({"file": file, "state": "unavailable", "reason": str(error)})
        else:
            examples.extend(found)
            dispositions.append(
                {
                    "file": file,
                    "state": "complete",
                    "examples": len(found),
                    "empty_reason": None
                    if found
                    else "No supported example in the enumerated documentation roles",
                }
            )
    return examples, dispositions


def _documentation(
    data: bytes, entry: FileEntry, records: list[dict]
) -> list[tuple[maps.Mapped, tuple[dict, ...]]]:
    if entry.kind == "markdown":
        return [(maps.identity(data), ())]
    rows = sorted(
        (
            r
            for r in records
            if r["payload"].get("documentation") and r["payload"].get("syntax_valid")
        ),
        key=lambda r: r["payload"]["start"],
    )
    result: list[tuple[maps.Mapped, tuple[dict, ...]]] = []
    groups: list[list[dict]] = []
    for row in rows:
        payload = row["payload"]
        if payload["documentation"] == "python_docstring":
            result.append(
                (
                    maps.python_literal(
                        maps.identity(data[payload["start"] : payload["end"]], payload["start"])
                    ),
                    (row,),
                )
            )
        elif groups and not data[groups[-1][-1]["payload"]["end"] : payload["start"]].strip():
            groups[-1].append(row)
        else:
            groups.append([row])
    for group in groups:
        start, end = group[0]["payload"]["start"], group[-1]["payload"]["end"]
        result.append((maps.rust_line_docs(maps.identity(data[start:end], start)), tuple(group)))
    return result


def _file_examples(
    data: bytes,
    source: tuple[SourceSnapshot, FileEntry],
    records: list[dict],
    artifact: FactArtifact,
) -> list[ExampleDiscovery]:
    snapshot, entry = source
    result = []
    for document, supporting in _documentation(data, entry, records):
        views = list(
            maps.fences(document, default_language="rust" if entry.kind == "rust" else "unknown")
        )
        if entry.kind == "python":
            views.extend(("python", item, ("doctest_input",)) for item in maps.doctests(document))
        for language, code, directives in views:
            result.append(
                _example((snapshot, entry), code, (language, directives), (artifact, supporting))
            )
    return list({item.id: item for item in result}.values())


def _example(
    source: tuple[SourceSnapshot, FileEntry],
    code: maps.Mapped,
    syntax: tuple[str, tuple[str, ...]],
    support: tuple[FactArtifact, tuple[dict, ...]],
) -> ExampleDiscovery:
    snapshot, entry = source
    language, directives = syntax
    artifact, records = support
    view = maps.example_view(code, language, executable=True)
    display = maps.example_view(code, language, executable=False)
    limitations = [
        "Not executed, name-resolved or type-checked; imports and environment requirements need separate review."
    ]
    status = "located"
    if language in {"python", "py"}:
        try:
            ast.parse(view.data.decode())
        except SyntaxError as error:
            limitations.append(f"Host Python syntax parser: {error.msg}")
        else:
            status = "parsed"
    anchor = SourceAnchor(
        snapshot=snapshot.id,
        file=entry.path,
        digest=entry.digest,
        role="example_executable_view",
        segments=view.segments,
    )
    selections = tuple(
        FactSelection(
            artifact=artifact.id,
            record=row["id"],
            selector="json:/payload/documentation",
            digest=digest_bytes(select(canonical_bytes(row), "json:/payload/documentation")),
            role="context",
        )
        for row in records
    )
    key = digest_bytes(canonical_bytes([asdict(anchor), language, directives, view.data.decode()]))
    return ExampleDiscovery(
        id="discovered:" + key,
        anchor=anchor,
        language=language,
        code=view.data.decode(),
        directives=directives,
        status=status,
        limitations=tuple(limitations),
        facts=selections,
        display_code=display.data.decode(),
        display_segments=display.segments,
    )


def page(root: Path, *, text: str = "", limit: int = 20, offset: int = 0) -> dict[str, object]:
    """Read a bounded example page with exact maps and explicit verification status.

    Returns:
        Matching examples without assuming that parsing grants runtime evidence.

    Raises:
        CollectionError: If the requested page is invalid or exceeds its byte budget.

    """
    knowledge = load(root)
    if not isinstance(knowledge, KnowledgeV3) or not 1 <= limit <= _MAX_PAGE or offset < 0:
        message = "example query requires V3 and a bounded page"
        raise CollectionError(message)
    values = [e for e in knowledge.example_discoveries if text in e.code or text in e.anchor.file]
    graph = SupportGraph(root, knowledge)
    rows = []
    for example in values[offset : offset + limit]:
        try:
            verify_example(root, knowledge, example, graph)
        except (CollectionError, OSError, ValueError) as error:
            rows.append({"id": example.id, "state": "unavailable", "reason": str(error)})
        else:
            rows.append({"state": "current", **asdict(example)})
    result: dict[str, object] = {"total": len(values), "offset": offset, "examples": rows}
    if len(canonical_bytes(result)) > _MAX_BYTES:
        message = "source example page exceeds 1 MB; request fewer rows"
        raise CollectionError(message)
    return result


def verify_example(
    root: Path, knowledge: KnowledgeV3, example: ExampleDiscovery, graph: SupportGraph
) -> None:
    """Reconstruct the located view from exact host bytes and producer documentation roles.

    Raises:
        CollectionError: If maps, status, current facts or source closure no longer agree.

    """
    from library_guides.facts import store
    from library_guides.source_pipeline import artifact_index
    from library_guides.source_snapshots import verify

    snapshots = [s for s in knowledge.source_snapshots if s.id == example.anchor.snapshot]
    if len(snapshots) != 1:
        message = "example source snapshot is absent or ambiguous"
        raise CollectionError(message)
    snapshot = snapshots[0]
    verify(root, snapshot)
    entries = [
        e
        for e in snapshot.files
        if e.path == example.anchor.file and e.digest == example.anchor.digest
    ]
    if len(entries) != 1:
        message = "example source entry changed"
        raise CollectionError(message)
    artifacts = {f.artifact for f in example.facts}
    if not artifacts:
        artifacts = {
            a.id
            for a in knowledge.fact_artifacts
            if a.artifact_kind == "syntax"
            and snapshot.id in a.snapshots
            and graph.heads.get((a.job, a.profile)) is not None
            and graph.heads[a.job, a.profile].artifact == a.id
        }
    if len(artifacts) != 1:
        message = "example requires one exact structural producer"
        raise CollectionError(message)
    artifact = graph.artifact(artifacts.pop())
    records = []
    for selection in example.facts:
        store.selected(root, artifact_index(root, artifact), selection, artifact=artifact)
        records.append(
            json.loads(
                store.record(
                    root, artifact_index(root, artifact), selection.record, artifact=artifact
                )
            )
        )
    candidates = _file_examples(
        confined(root, entries[0].path).read_bytes(), (snapshot, entries[0]), records, artifact
    )
    if example not in candidates:
        message = (
            "example text, map, directives or status differs from its reconstructed source view"
        )
        raise CollectionError(message)

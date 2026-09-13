"""Exact source-position reconciliation of Python syntax, lexical and typed call evidence."""

from __future__ import annotations

import json
from pathlib import Path

from library_guides.collection import CollectionError, confined, load, select
from library_guides.facts import locations, store
from library_guides.facts.contracts import FactArtifact
from library_guides.facts.support import SupportGraph
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.source_pipeline import artifact_index
from library_guides.store.digests import canonical_bytes, digest_bytes

_MAX_BYTES = 1_000_000


def boundary(root: Path, syntax: str, owner: str, types: str) -> dict[str, object]:
    """Join calls to a source owner by exact file bytes and callee expression intervals.

    Returns:
        Every syntactic call with lexical/type evidence or an explicit unresolved target.

    Raises:
        CollectionError: If profiles, snapshots or query budgets do not match.

    """
    knowledge = load(root)
    if not isinstance(knowledge, KnowledgeV3):
        message = "Python boundary query requires V3 source evidence"
        raise CollectionError(message)
    graph = SupportGraph(root, knowledge)
    structural, semantic = graph.artifact(syntax), graph.artifact(types)
    if (
        structural.artifact_kind != "syntax"
        or semantic.artifact_kind != "types"
        or structural.profile != semantic.profile
    ):
        message = (
            "Python boundary requires structural and typed evidence under the same declared profile"
        )
        raise CollectionError(message)
    row = _read(root, structural, owner)
    payload = row["payload"]
    sources = [
        (s, e)
        for s in knowledge.source_snapshots
        if s.id in structural.snapshots and s.id in semantic.snapshots
        for e in s.files
        if row["file"] in {e.path, e.path.removeprefix(f"snapshots/{s.source_digest}/source/")}
        and e.digest == payload.get("source_digest")
    ]
    if len(sources) != 1 or payload.get("node_kind") != "function_definition":
        message = "Python owner does not join one identical source file in both evidence lanes"
        raise CollectionError(message)
    entry = sources[0][1]
    syntax_rows = _interval(root, structural, row["file"], payload)
    type_rows = _interval(root, semantic, entry.path, payload)
    report = _report(
        (structural, semantic), row, syntax_rows, type_rows, confined(root, entry.path).read_bytes()
    )
    if len(canonical_bytes(report)) > _MAX_BYTES:
        message = "Python boundary packet exceeds 1 MB"
        raise CollectionError(message)
    return report


def _read(root: Path, artifact: FactArtifact, identifier: str) -> dict:
    return json.loads(
        store.record(root, artifact_index(root, artifact), identifier, artifact=artifact)
    )


def _interval(root: Path, artifact: FactArtifact, file: str, payload: dict) -> list[dict]:
    return [
        _read(root, artifact, i)
        for i in locations.in_file(
            locations.index(root, artifact), file, payload["start"], payload["end"]
        )
    ]


def _selection(artifact: FactArtifact, row: dict, field: str, *, role: str = "mechanism") -> dict:
    return {
        "artifact": artifact.id,
        "record": row["id"],
        "selector": "json:/payload/" + field,
        "digest": digest_bytes(select(canonical_bytes(row), "json:/payload/" + field)),
        "role": role,
    }


def _report(
    artifacts: tuple[FactArtifact, FactArtifact],
    owner: dict,
    syntax: list[dict],
    typed: list[dict],
    source: bytes,
) -> dict[str, object]:
    structural, semantic = artifacts
    calls = []
    for row in syntax:
        payload = row["payload"]
        if payload.get("node_kind") != "call" or payload.get("owner") != owner["id"]:
            continue
        callee = next((f for f in payload["fields"] if f["name"] == "function"), None)
        if callee is None:
            continue
        lexical = [
            r
            for r in syntax
            if r["payload"].get("event") == "callee_expression"
            and (r["payload"]["start"], r["payload"]["end"]) == (callee["start"], callee["end"])
        ]
        targets = [
            r
            for r in typed
            if r.get("source_digest") == owner["payload"]["source_digest"]
            and r["payload"]["kind"] == "call"
            and callee["start"]
            <= r["payload"]["anchor"]["start"]
            <= r["payload"]["anchor"]["end"]
            <= callee["end"]
        ]
        calls.append(
            {
                "site": row["id"],
                "source": source[payload["start"] : payload["end"]].decode(),
                "anchor": {
                    "file": owner["file"],
                    "digest": payload["source_digest"],
                    "start": payload["start"],
                    "end": payload["end"],
                },
                "syntax": _selection(structural, row, "fields", role="context"),
                "lexical": [
                    {
                        "facts": r["payload"],
                        "evidence": _selection(structural, r, "target", role="context"),
                    }
                    for r in lexical
                ],
                "typed_candidates": [
                    {
                        "facts": r["payload"],
                        "evidence": [
                            _selection(semantic, r, f)
                            for f in ("target", "identity", "dispatch", "target_origin")
                        ],
                    }
                    for r in targets
                ],
                "state": "candidate" if targets else "unresolved",
                "frontier": [
                    "Call result and callee effects are not established by target identity.",
                    "Native or missing-type calls remain unresolved; lexical qualification is not runtime dispatch.",
                ],
            }
        )
    return {
        "owner": owner["id"],
        "profile": structural.profile,
        "artifacts": [structural.id, semantic.id],
        "contexts": [structural.context, semantic.context],
        "matching": "identical source file bytes and callee-expression containment; nested owners excluded",
        "signature": owner["payload"]["signature"],
        "calls": calls,
        "call_denominator": len(calls),
        "typed_calls": sum(bool(c["typed_candidates"]) for c in calls),
        "unknown_calls": sum(not c["typed_candidates"] for c in calls),
        "certainty": "combined evidence never upgrades heuristic or absent dispatch",
        "native_boundary": "Cython/shared-object bodies are not Python source bodies; no cross-language owner join by spelling.",
    }

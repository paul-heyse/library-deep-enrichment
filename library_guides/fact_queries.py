"""Bounded fact retrieval for agents without exposing whole compiler artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict

from library_guides.collection import CollectionError, load, select
from library_guides.facts import store
from library_guides.facts.contracts import FactArtifact, FactSelection
from library_guides.facts.support import SupportGraph
from library_guides.source_pipeline import artifact_index
from library_guides.store.digests import canonical_bytes, digest_bytes

_MAX_BYTES = 1_000_000
_MAX_SITES = 30


def mechanisms(
    root: Path, artifact_id: str, text: str, *, limit: int = 10, offset: int = 0
) -> dict[str, object]:
    """Read exact owner/call candidates with citations and their required limitations.

    Returns:
        A bounded page of mechanisms, retaining declared matching mode and continuation.

    Raises:
        CollectionError: If the requested page exceeds its byte budget.

    """
    graph = SupportGraph(root, load(root))
    artifact = graph.artifact(artifact_id)
    index = artifact_index(root, artifact)
    page = store.query(index, text, limit=limit, offset=offset)
    rows = page["rows"]
    if not isinstance(rows, list):
        message = "fact query returned an invalid page"
        raise CollectionError(message)
    result = []
    for item in rows:
        row = json.loads(store.record(root, index, item["id"], artifact=artifact))
        result.append(_mechanism(artifact, row))
    report = {
        "artifact": artifact.id,
        "profile": artifact.profile,
        "context": artifact.context,
        "matching": "literal symbol substring; candidate discovery, not entity or dispatch resolution",
        "total": page["total"],
        "next_offset": page["next_offset"],
        "records": result,
    }
    if len(canonical_bytes(report)) > _MAX_BYTES:
        message = "mechanism page exceeds 1 MB; request fewer owners"
        raise CollectionError(message)
    return report


def _mechanism(artifact: FactArtifact, row: dict) -> dict:
    selections = []
    summary: dict[str, object] = {}
    if artifact.artifact_kind == "mir":
        payload = row["payload"]
        for number, terminal in enumerate(payload["exits"]):
            if terminal["kind"] in {"call", "drop", "assert", "switch"}:
                selections.append(_selection(artifact, row, f"json:/payload/exits/{number}"))
        summary = {
            "source": payload["source"],
            "frontier": payload["frontier"],
            "locals": len(payload["locals"]),
            "events": len(payload["events"]),
            "limitation": "Body events and compiler call identity do not establish unobserved callee effects or application-level guarantees.",
        }
    elif artifact.artifact_kind == "derived":
        selections = [
            _selection(artifact, row, f"json:/analysis/{name}")
            for name in ("flow", "control", "effects", "absence")
        ]
        summary = {
            "frontier": row["analysis"]["frontier"],
            "causal_inputs": [asdict(i) for i in artifact.dependencies],
            "limitation": "May-dependencies and may-effects are bounded by the retained owner universe and declared place model.",
        }
    elif artifact.artifact_kind == "types":
        payload = row["payload"]
        pointers = (
            ("target", "dispatch", "target_origin", "identity") if payload["kind"] == "call" else ()
        )
        selections = [_selection(artifact, row, f"json:/payload/{name}") for name in pointers]
        summary = {
            "kind": payload["kind"],
            "limitation": "Type shape, exact identity and heuristic dispatch remain separate; native and untyped bodies are opaque.",
        }
        if not pointers:
            summary["record"] = payload
    else:
        summary = {
            "record": row,
            "limitation": "Structural/declaration evidence; no runtime behavior or consumer availability inferred.",
        }
    return {
        "id": row["id"],
        "symbol": row.get("symbol", ""),
        "summary": summary,
        "selections": selections[:_MAX_SITES],
        "omitted_sites": max(0, len(selections) - _MAX_SITES),
        "site_query": {"record": row["id"], "offset": _MAX_SITES}
        if len(selections) > _MAX_SITES
        else None,
    }


def _selection(artifact: FactArtifact, row: dict, pointer: str) -> dict:
    content = select(canonical_bytes(row), pointer)
    return {
        "selection": asdict(
            FactSelection(
                artifact=artifact.id,
                record=row["id"],
                selector=pointer,
                digest=digest_bytes(content),
                role="mechanism",
            )
        ),
        "content": json.loads(content),
    }


def why_unknown(root: Path, artifact_id: str) -> dict[str, object]:
    """Expose receipt/context boundaries independently of positive fact counts.

    Returns:
        Exact coverage and effective settings, including absent context knowledge.

    """
    graph = SupportGraph(root, load(root))
    artifact = graph.artifact(artifact_id)
    receipt = json.loads((root / artifact.receipt_path).read_bytes())
    return {
        "artifact": artifact.id,
        "profile": artifact.profile,
        "coverage": receipt["terminal"]["coverage"],
        "context": receipt.get("semantic_profile"),
        "dependencies": [asdict(d) for d in artifact.dependencies],
        "authority": "A complete extraction enumerates its declared surface; it does not imply a closed semantic frontier or reviewed claim.",
    }

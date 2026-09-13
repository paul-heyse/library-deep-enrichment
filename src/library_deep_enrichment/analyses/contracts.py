"""Generic trait checklists, composition candidates and declaration/profile deltas."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict

from library_deep_enrichment.analyses.declarations import selection
from library_deep_enrichment.collection import CollectionError, load
from library_deep_enrichment.facts import store
from library_deep_enrichment.facts.contracts import FactArtifact
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.source_pipeline import artifact_index
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes

_MAX_MEMBERS = 200
_MAX_BYTES = 1_000_000


def _read(root: Path, artifact: FactArtifact, identifier: str) -> dict:
    return json.loads(
        store.record(root, artifact_index(root, artifact), identifier, artifact=artifact)
    )


def _bounded(report: dict[str, object]) -> dict[str, object]:
    if len(canonical_bytes(report)) > _MAX_BYTES:
        message = "contract query exceeds 1 MB; select a smaller page"
        raise CollectionError(message)
    return report


def extension_contract(
    root: Path, artifact_id: str, identifier: str, *, offset: int = 0, limit: int = 50
) -> dict[str, object]:
    """Build a declaration-supported trait checklist with explicit required/default methods.

    Returns:
        Bounded members, associated requirements, implementation candidates and exact citations.

    Raises:
        CollectionError: If the input is not a trait or query bounds are invalid.

    """
    artifact = SupportGraph(root, load(root)).artifact(artifact_id)
    row = _read(root, artifact, identifier)
    trait = row.get("item", {}).get("inner", {}).get("trait")
    if (
        artifact.artifact_kind != "declarations"
        or trait is None
        or not 1 <= limit <= _MAX_MEMBERS
        or offset < 0
    ):
        message = "extension contract requires a trait declaration and 1..200 members per page"
        raise CollectionError(message)
    items = [("requirement", number) for number in trait["items"]] + [
        ("implementation_candidate", number) for number in trait["implementations"]
    ]
    members = []
    for role, local_id in items[offset : offset + limit]:
        try:
            member = _read(root, artifact, row["id"].rsplit(":", 1)[0] + ":" + str(local_id))
        except CollectionError as error:
            members.append(
                {"local_id": local_id, "role": role, "state": "unresolved", "reason": str(error)}
            )
        else:
            members.append(_member(artifact, member, role))
    return _bounded(
        {
            "artifact": artifact.id,
            "profile": artifact.profile,
            "trait": row["symbol"],
            "contract": {k: v for k, v in trait.items() if k not in {"items", "implementations"}},
            "evidence": asdict(selection(artifact, row, "json:/item/inner/trait")),
            "members": members,
            "total": len(items),
            "next_offset": offset + len(members) if offset + len(members) < len(items) else None,
            "limitations": [
                "Declaration requirements do not certify implementation correctness, active cfg or applicable blanket bounds.",
                "Built-in registry membership and runtime activation require their own evidence.",
            ],
        }
    )


def _member(artifact: FactArtifact, row: dict, role: str) -> dict:
    kind, contract = next(iter(row["item"]["inner"].items()))
    requirement = "unknown"
    if kind == "function":
        requirement = (
            "provided_body"
            if contract.get("has_body")
            else "required"
            if contract.get("has_body") is False
            else "unknown"
        )
    elif kind in {"assoc_type", "assoc_const"}:
        default = "type" if kind == "assoc_type" else "value"
        requirement = (
            "default"
            if contract.get(default) is not None
            else "required"
            if default in contract
            else "unknown"
        )
    elif kind == "impl":
        requirement = (
            "negative_exclusion"
            if contract["is_negative"]
            else "candidate_requires_bounds_and_context"
        )
    return {
        "id": row["id"],
        "symbol": row["symbol"],
        "role": role,
        "requirement": requirement,
        "signature": row["signature"],
        "contract": contract,
        "evidence": asdict(selection(artifact, row, f"json:/item/inner/{kind}")),
    }


def composition(root: Path, artifact_id: str, producer: str, consumer: str) -> dict[str, object]:
    """Compare actual output/input occurrences without impersonating Rust inference.

    Returns:
        Nominal connection candidates, wrapper/bound contracts and unresolved applicability.

    Raises:
        CollectionError: If either endpoint lacks a callable declaration contract.

    """
    artifact = SupportGraph(root, load(root)).artifact(artifact_id)
    first, second = _read(root, artifact, producer), _read(root, artifact, consumer)
    if any("function" not in r.get("item", {}).get("inner", {}) for r in (first, second)):
        message = "composition query requires two callable declarations"
        raise CollectionError(message)
    connections = []
    for output in first["type_occurrences"]:
        if output["role"] != "output":
            continue
        for input_ in second["type_occurrences"]:
            target = output.get("resolved_symbol")
            if input_["role"] == "input" and target and target == input_.get("resolved_symbol"):
                connections.append(
                    {
                        "nominal": target,
                        "producer_role": output,
                        "consumer_role": input_,
                        "matching": "resolved nominal occurrence; candidate only",
                    }
                )
    return _bounded(
        {
            "profile": artifact.profile,
            "artifact": artifact.id,
            "connections": connections,
            "contracts": [
                {
                    "symbol": r["symbol"],
                    "signature": r["signature"],
                    "evidence": asdict(selection(artifact, r, "json:/item/inner/function")),
                }
                for r in (first, second)
            ],
            "state": "candidate" if connections else "no_nominal_connection_observed",
            "frontier": [
                "Inference, coercion, trait bounds, lifetimes, generic instantiation and effects have not been solved.",
                "Nested occurrence does not establish that a container can be passed directly; a targeted compile witness is needed.",
            ],
        }
    )


def declaration_diff(
    root: Path, previous: str, current: str, *, limit: int = 50, offset: int = 0
) -> dict[str, object]:
    """Classify declaration, route and documentation changes independently of raw bytes.

    Returns:
        Inspectable affected records; no semantic-version or runtime availability verdict.

    Raises:
        CollectionError: If artifacts or page bounds are incompatible.

    """
    graph = SupportGraph(root, load(root))
    old, new = graph.artifact(previous, current=False), graph.artifact(current)
    if (
        any(a.artifact_kind != "declarations" for a in (old, new))
        or not 1 <= limit <= _MAX_MEMBERS
        or offset < 0
    ):
        message = "declaration diff requires two typed artifacts and a bounded page"
        raise CollectionError(message)
    before, after = _catalog(root, old), _catalog(root, new)
    changes: list[dict] = []
    for key in sorted(before.keys() | after.keys()):
        first, second = before.get(key, []), after.get(key, [])
        if len(first) > 1 or len(second) > 1:
            changes.append(
                {"symbol": key, "kind": "ambiguous_identity", "old": first, "new": second}
            )
        elif not first or not second:
            changes.append(
                {
                    "symbol": key,
                    "kind": "added" if second else "removed",
                    "old": first,
                    "new": second,
                }
            )
        else:
            reasons = [
                name
                for name in ("declaration", "routes", "documentation")
                if first[0][name] != second[0][name]
            ]
            if reasons:
                changes.append(
                    {
                        "symbol": key,
                        "kind": "changed",
                        "reasons": reasons,
                        "old": first,
                        "new": second,
                    }
                )
    return _bounded(
        {
            "previous": old.id,
            "current": new.id,
            "contexts": [old.context, new.context],
            "profiles": [old.profile, new.profile],
            "context_changed": old.context != new.context,
            "raw_changed": old.input_digest != new.input_digest,
            "total": len(changes),
            "changes": changes[offset : offset + limit],
            "next_offset": offset + limit if offset + limit < len(changes) else None,
            "availability": "Documentation surface only; compare actual consumer invocation evidence separately.",
            "causality": "A profile difference is not attributed to one feature unless all other effective inputs are controlled.",
        }
    )


def _catalog(root: Path, artifact: FactArtifact) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for shard in artifact.shards:
        with (root / shard.path).open("rb") as stream:
            for line in stream:
                row = json.loads(line)
                key = row["symbol"] + "|" + row["kind"]
                result.setdefault(key, []).append(
                    {
                        "id": row["id"],
                        "declaration": row["semantic_digest"],
                        "routes": digest_bytes(canonical_bytes(row["public_routes"])),
                        "documentation": digest_bytes(canonical_bytes(row["item"]["docs"])),
                    }
                )
    return result

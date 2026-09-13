"""Immutable derived evidence from verified owner facts; publication retains causal inputs."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from attrs import asdict, evolve
from filelock import FileLock

from library_deep_enrichment.analyses import effects, flow
from library_deep_enrichment.collection import CollectionError, confined, load, save, select
from library_deep_enrichment.facts import store
from library_deep_enrichment.facts.contracts import FactArtifact, FactHead, FactSelection, FactShard
from library_deep_enrichment.facts.support import SupportGraph
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.source_pipeline import artifact_index
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file
from library_deep_enrichment.store.staging import sync_directory, write_atomic

_MODEL = "library-guides.mir-analysis.v1"
_MAX_BYTES = 64_000_000
_MAX_OWNERS = 200


def derive(
    root: Path, artifact_id: str, identifiers: tuple[str, ...], *, job: str
) -> dict[str, object]:
    """Analyze a finite owner universe without running any extraction worker.

    Returns:
        Derived fact identities and exact input dependencies; no reviews are created.

    Raises:
        CollectionError: If input scope is invalid or authoring changes during derivation.

    """
    knowledge = load(root)
    if (
        not isinstance(knowledge, KnowledgeV3)
        or not job
        or not 1 <= len(identifiers) <= _MAX_OWNERS
        or len(set(identifiers)) != len(identifiers)
    ):
        message = "analysis requires V3, a job identity and 1..200 unique owner IDs"
        raise CollectionError(message)
    before = digest_file(root / "knowledge.yaml")
    source = SupportGraph(root, knowledge).artifact(artifact_id)
    if source.artifact_kind != "mir":
        message = "MIR analysis requires actual body facts"
        raise CollectionError(message)
    records = _read(root, source, identifiers)
    inputs = tuple(
        FactSelection(
            artifact=source.id,
            record=r["id"],
            selector="json:/payload",
            digest=digest_bytes(select(canonical_bytes(r), "json:/payload")),
            role="mechanism",
        )
        for r in records
    )
    producer = digest_bytes(
        canonical_bytes(
            {
                name: digest_file(Path(__file__).parent / name)
                for name in ("flow.py", "effects.py", "pipeline.py")
            }
        )
    )
    request = {
        "model": _MODEL,
        "inputs": [asdict(i) for i in inputs],
        "producer": producer,
        "profile": source.profile,
        "context": source.context,
        "job": job,
    }
    key = digest_bytes(canonical_bytes(request))
    reused, result = _compute(root, key, records)
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        if digest_file(root / "knowledge.yaml") != before:
            message = "authoring changed during analysis; attachment refused"
            raise CollectionError(message)
        artifact = _commit(root, root / "facts" / key, source, request, result)
        head = FactHead(
            job=job, profile=source.profile, request=key, artifact=artifact.id, outcome="complete"
        )
        save(
            root,
            evolve(
                knowledge,
                fact_artifacts=(
                    *[a for a in knowledge.fact_artifacts if a.id != artifact.id],
                    artifact,
                ),
                fact_heads=(
                    *[
                        h
                        for h in knowledge.fact_heads
                        if (h.job, h.profile) != (job, source.profile)
                    ],
                    head,
                ),
            ),
        )
    return {
        "state": "complete",
        "artifact": artifact.id,
        "owners": len(result),
        "model": _MODEL,
        "workers_invoked": 0,
        "analysis_reused": reused,
        "automatic_reviews": 0,
        "records": [
            {"id": r["id"], "symbol": r["symbol"], "frontier": r["analysis"]["frontier"]}
            for r in result
        ],
    }


def _results(records: tuple[dict, ...]) -> list[dict]:
    summaries = effects.summarize(records)
    result = []
    for record in records:
        analyzed = flow.analyze(record["payload"])
        control = flow.control_dependence(record["payload"], analyzed.reachable)
        effect = summaries[record["id"]]
        control_frontier = control["frontier"]
        if not isinstance(control_frontier, list):
            message = "control analysis returned an invalid frontier"
            raise CollectionError(message)
        frontier = sorted(
            set(analyzed.frontier) | set(effect["frontier"]) | {str(x) for x in control_frontier}
        )
        absence = {
            "predicate": "no-modeled-memory-writes",
            "holds": effect["closed"] and "projected_memory_write" not in effect["may_effects"],
            "closed": effect["closed"],
            "model": effect["model"],
            "scope": effect["scope"],
            "frontier": effect["frontier"],
            "limitation": "Only writes represented by the named full-CFG place model; no allocation, race, termination, I/O or arbitrary effect-free guarantee.",
        }
        result.append(
            {
                "id": "analysis:" + digest_bytes(canonical_bytes([_MODEL, record["id"]])),
                "symbol": record["symbol"],
                "kind": "mir_analysis",
                "analysis": {
                    "model": _MODEL,
                    "owner": record["id"],
                    "flow": asdict(analyzed),
                    "control": control,
                    "effects": effect,
                    "absence": absence,
                    "frontier": frontier,
                },
            }
        )
    return result


def _commit(
    root: Path, destination: Path, source: FactArtifact, request: dict, records: list[dict]
) -> FactArtifact:
    from cattrs import Converter

    inputs = Converter(forbid_extra_keys=True).structure(
        request["inputs"], tuple[FactSelection, ...]
    )
    key = destination.name
    if (destination / "artifact.json").is_file():
        existing = Converter(forbid_extra_keys=True).structure(
            json.loads((destination / "artifact.json").read_bytes()), FactArtifact
        )
        try:
            store.verify(root, existing)
        except CollectionError, OSError, ValueError:
            destination.rename(destination.with_name(key + ".invalid-" + uuid4().hex))
        else:
            return existing
    staging = Path(tempfile.mkdtemp(prefix="derive-", dir=root / "facts"))
    try:
        body = canonical_bytes(request)
        header = {
            "schema": _MODEL,
            "input_digest": digest_bytes(body),
            "expected_records": len(records),
            "profile": source.profile,
            "model": _MODEL,
        }
        coverage = {
            "state": "complete",
            "owners": len(records),
            "semantic_closed": all(r["analysis"]["absence"]["closed"] for r in records),
            "scope": [r["analysis"]["owner"] for r in records],
            "model": _MODEL,
        }
        context = json.loads(confined(root, source.receipt_path).read_bytes())["semantic_profile"]
        receipt = {
            "header": header,
            "terminal": {"records": len(records), "coverage": coverage},
            "producer_digest": request["producer"],
            "semantic_profile": context,
            "dependencies": [asdict(i) for i in inputs],
            "witnesses": [],
        }
        for name, value in (
            ("input.json", body),
            ("header.json", canonical_bytes(header)),
            ("receipt.json", canonical_bytes(receipt)),
            ("records.jsonl", b"".join(canonical_bytes(r) + b"\n" for r in records)),
        ):
            write_atomic(staging / name, value)
        relative = f"facts/{key}"
        artifact = FactArtifact(
            id="facts:" + key,
            schema=_MODEL,
            profile=source.profile,
            producer=request["producer"],
            input_path=relative + "/input.json",
            input_digest=digest_bytes(body),
            header_path=relative + "/header.json",
            receipt_path=relative + "/receipt.json",
            receipt_digest=digest_file(staging / "receipt.json"),
            shards=(
                FactShard(
                    path=relative + "/records.jsonl",
                    digest=digest_file(staging / "records.jsonl"),
                    records=len(records),
                ),
            ),
            outcome="complete",
            artifact_kind="derived",
            job=request["job"],
            context=source.context,
            snapshots=source.snapshots,
            dependencies=inputs,
        )
        write_atomic(staging / "artifact.json", canonical_bytes(asdict(artifact)))
        staging.rename(destination)
        sync_directory(destination.parent)
        store.build_index(root, artifact, artifact_index(root, artifact))
        return artifact
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _read(root: Path, source: FactArtifact, identifiers: tuple[str, ...]) -> tuple[dict, ...]:
    records = []
    total = 0
    for identifier in sorted(identifiers):
        raw = store.record(root, artifact_index(root, source), identifier, artifact=source)
        total += len(raw)
        if total > _MAX_BYTES:
            message = "analysis owner input exceeds 64 MB; select a smaller universe"
            raise CollectionError(message)
        records.append(json.loads(raw))
    return tuple(records)


def _compute(root: Path, key: str, records: tuple[dict, ...]) -> tuple[bool, list[dict]]:
    from library_deep_enrichment.source_pipeline import cached

    previous = cached(root, key)
    if (
        previous is not None
        and previous.id == "facts:" + key
        and previous.schema == _MODEL
        and previous.input_digest == key
    ):
        return True, [
            json.loads(line)
            for shard in previous.shards
            for line in confined(root, shard.path).read_bytes().splitlines()
        ]
    return False, _results(records)

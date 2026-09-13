"""Migrate into a new collection, preserving original sources and reviews."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from attrs import asdict, evolve
from cattrs import Converter
from filelock import FileLock

from library_guides.collection import CollectionError, confined, load, save
from library_guides.evidence_graph import EvidenceGraph
from library_guides.facts.contracts import ReviewRevalidation
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.store.digests import canonical_bytes, digest_file
from library_guides.store.staging import write_atomic


def migrate(source: Path, destination: Path, *, apply: bool = False) -> dict[str, object]:
    """Plan or write a separate V3 authority without upgrading evidence claims.

    Returns:
        Per-review equivalence/reopen report and the intended write set.

    Raises:
        CollectionError: If source/destination or existing authority is unsuitable.

    """
    before = digest_file(source / "knowledge.yaml")
    old = load(source)
    if (
        isinstance(old, KnowledgeV3)
        or destination.exists()
        or destination.resolve().is_relative_to(source.resolve())
    ):
        message = "migration requires a V2 source and a new separate destination"
        raise CollectionError(message)
    raw = asdict(old)
    raw["schema_version"] = "library-guides.knowledge.v3"
    migrated = Converter(forbid_extra_keys=True).structure(raw, KnowledgeV3)
    paths = {"obligations.yaml", *(item.path for item in old.sources)}
    paths.update(path for example in old.examples for path in example.inputs)
    old_graph = EvidenceGraph(source, old)
    revalidations = []
    reviews = []
    source_reviewed = {item.id for item in old.claims if item.verification == "source_reviewed"}
    for review in old.reviews:
        digest = old_graph.fingerprint(review.subject)
        valid = review.digest == digest and review.subject not in source_reviewed
        reviews.append(review if valid else evolve(review, disposition="needs_review"))
        revalidations.append(
            ReviewRevalidation(
                subject=review.subject,
                previous_digest=review.digest,
                current_digest=digest,
                policy="library-guides.migration.v1",
                checks=(
                    "same subject and selected source bytes",
                    "same existing profile and obligations",
                    "no new fact support or scope",
                ),
                outcome="equivalent" if valid else "needs_review",
            )
        )
    report: dict[str, object] = {
        "source": str(source),
        "destination": str(destination),
        "files": sorted(paths),
        "reviews": [asdict(item) for item in revalidations],
        "state": "planned",
    }
    if not apply:
        return report
    _commit(source, destination, (old, migrated), (paths, reviews, revalidations, before), report)
    report["state"] = "migrated"
    return report


def _commit(
    source: Path, destination: Path, authorities: tuple, state: tuple, report: dict
) -> None:
    old, migrated = authorities
    paths, reviews, revalidations, before = state
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="migrate-", dir=destination.parent))
    try:
        for relative in sorted(paths):
            write_atomic(confined(staging, relative), confined(source, relative).read_bytes())
        migrated = evolve(migrated, reviews=tuple(reviews), revalidations=tuple(revalidations))
        save(staging, migrated)
        write_atomic(staging / "migration/v2-knowledge.json", canonical_bytes(asdict(old)))
        write_atomic(staging / "migration/report.json", canonical_bytes(report))
        with FileLock(str(destination) + ".lock", timeout=60):
            if destination.exists() or digest_file(source / "knowledge.yaml") != before:
                message = "migration source or destination changed; commit refused"
                raise CollectionError(message)
            staging.rename(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

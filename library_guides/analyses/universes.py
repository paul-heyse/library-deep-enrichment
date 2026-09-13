"""Independent candidate denominators derived from declared queries over current facts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from attrs import asdict

from library_guides.collection import CollectionError
from library_guides.facts import store
from library_guides.facts.contracts import CandidateUniverse
from library_guides.facts.support import SupportGraph
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.source_pipeline import artifact_index
from library_guides.store.digests import canonical_bytes, digest_bytes

_MAX_MEMBERS = 100_000


def policy_errors(root: Path, knowledge: KnowledgeV3) -> list[str]:
    """Compare candidate queries against separately authored policy.

    Returns:
        Missing, altered or inconsistent denominator failures.

    """
    if not knowledge.candidate_universes and not knowledge.universe_dependencies:
        return []
    path = root / "candidate-universes.yaml"
    expected = {
        "universes": [asdict(u) for u in knowledge.candidate_universes],
        "dependencies": [asdict(d) for d in knowledge.universe_dependencies],
    }
    if not path.is_file() or canonical_bytes(yaml.safe_load(path.read_bytes())) != canonical_bytes(
        expected
    ):
        return ["candidate universes differ from independent candidate-universes.yaml policy"]
    ids = {u.id for u in knowledge.candidate_universes}
    errors = []
    if len(ids) != len(knowledge.candidate_universes) or any(
        not u.id or not u.jobs or len(u.jobs) != len(set(u.jobs)) or not u.nominal
        for u in knowledge.candidate_universes
    ):
        errors.append(
            "candidate universes require unique IDs, finite jobs and a nominal contract query"
        )
    if any(d.universe not in ids for d in knowledge.universe_dependencies):
        errors.append("choice depends on an absent candidate universe")
    return errors


def enumerate_candidates(
    root: Path, knowledge: KnowledgeV3, universe: CandidateUniverse
) -> dict[str, object]:
    """Enumerate every matching declaration from current requested artifact heads.

    Returns:
        Candidate witnesses, semantic membership digest and open applicability frontiers.

    Raises:
        CollectionError: If a requested head is missing/failed or the universe exceeds budget.

    """
    graph = SupportGraph(root, knowledge)
    members = []
    artifacts = []
    for job in universe.jobs:
        head = graph.heads.get((job, universe.profile))
        if head is None or head.outcome != "complete" or head.artifact is None:
            message = f"candidate denominator includes missing/failed job: {job}"
            raise CollectionError(message)
        artifact = graph.artifact(head.artifact)
        if artifact.artifact_kind != "declarations":
            message = "nominal candidate policy requires typed declaration artifacts"
            raise CollectionError(message)
        artifacts.append(artifact.id)
        offset = 0
        while True:
            page = store.query(
                artifact_index(root, artifact),
                universe.nominal,
                role=universe.role,
                offset=offset,
                limit=200,
            )
            rows = page["rows"]
            if not isinstance(rows, list):
                message = "invalid candidate query result"
                raise CollectionError(message)
            for member in rows:
                row = json.loads(
                    store.record(
                        root, artifact_index(root, artifact), member["id"], artifact=artifact
                    )
                )
                members.append(
                    {
                        "artifact": artifact.id,
                        "record": row["id"],
                        "symbol": row["symbol"],
                        "contract": row["semantic_digest"],
                        "routes": row["public_routes"],
                    }
                )
            if len(members) > _MAX_MEMBERS:
                message = "candidate denominator exceeds finite analysis budget"
                raise CollectionError(message)
            if page["next_offset"] is None:
                break
            if not isinstance(page["next_offset"], int):
                message = "invalid candidate continuation"
                raise CollectionError(message)
            offset = page["next_offset"]
    semantic = sorted(
        (
            {k: v for k, v in member.items() if k not in {"artifact", "record"}}
            for member in members
        ),
        key=canonical_bytes,
    )
    return {
        "universe": asdict(universe),
        "artifacts": artifacts,
        "members": members,
        "total": len(members),
        "semantic_digest": digest_bytes(canonical_bytes(semantic)),
        "frontier": [
            "Nominal occurrences nominate candidates; trait applicability, consumer availability and behavioral suitability require separate evidence."
        ],
        "semantic_closed": False,
    }

"""Auditable review equivalence with independently verified historical and current bytes."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict, evolve
from cattrs import Converter
from filelock import FileLock

from library_guides.collection import CollectionError, confined, dependencies, load, save
from library_guides.evidence_graph import EvidenceGraph
from library_guides.facts import store
from library_guides.facts.contracts import FileEntry, ReviewRevalidation
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.source_pipeline import artifact_index
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic

_POLICY = "library-guides.review-equivalence.v1"


class Semantics:
    """A conservative projection; unsupported equivalence requires a fresh review."""

    def __init__(self, root: Path, knowledge: KnowledgeV3) -> None:
        """Use the ordinary verified authority graph before any semantic projection."""
        self.graph = EvidenceGraph(root, knowledge)
        self.knowledge = knowledge
        self.memo: dict[str, object] = {}

    def subject(self, key: str) -> object:
        """Resolve verified contract-sensitive material without weakening byte checks.

        Returns:
            Canonical semantic dependencies or exact evidence for unsupported projections.

        """
        self.graph.fingerprint(key)
        if key in self.memo:
            return self.memo[key]
        if key in self.graph.universes:
            from library_guides.analyses.universes import enumerate_candidates

            report = enumerate_candidates(
                self.graph.root, self.knowledge, self.graph.universes[key]
            )
            value = [report["universe"], report["semantic_digest"], report["frontier"]]
        elif key in self.graph.support.supports:
            value = self._support(key)
        elif key in self.graph.evidence:
            value = self._evidence(key)
        elif key in self.graph.owners:
            record = self.graph.owners[key]
            value = [
                asdict(record),
                [
                    self.subject(dep)
                    for dep in sorted(set(dependencies(self.graph.knowledge, record)))
                ],
            ]
        else:
            value = self.graph.fingerprint(key)
        self.memo[key] = value
        return value

    def _context(self, identifier: str) -> object:
        knowledge = self.graph.knowledge
        if not isinstance(knowledge, KnowledgeV3):
            return identifier
        profile = next((p for p in knowledge.semantic_profiles if p.id == identifier), None)
        if profile is None:
            return identifier
        # Only the normalized input-byte witness is presentation-sensitive here.
        # Dependency snapshots and observed compiler arguments remain exact inputs.
        return asdict(evolve(profile, id="", source_digest=""))

    def _declaration(self, identifier: str, row: dict, selector: str) -> object:
        artifact = self.graph.support.artifact(identifier)
        if artifact.artifact_kind != "declarations":
            return [artifact.id, row, selector]
        value = row["semantic_digest"] if selector != "json:/item/docs" else row["item"]["docs"]
        if selector == "json:/public_routes":
            value = [value, row["public_routes"]]
        receipt = json.loads(confined(self.graph.root, artifact.receipt_path).read_bytes())
        return [
            row["symbol"],
            selector,
            value,
            artifact.profile,
            artifact.producer,
            artifact.schema,
            self._context(artifact.context),
            receipt["terminal"]["coverage"],
            [(w.kind, w.digest) for w in artifact.witnesses],
        ]

    def _support(self, key: str) -> object:
        support = self.graph.support.supports[key]
        material = asdict(evolve(support, facts=()))
        facts = []
        for selection in support.facts:
            artifact = self.graph.support.artifact(selection.artifact)
            store.selected(
                self.graph.root,
                artifact_index(self.graph.root, artifact),
                selection,
                artifact=artifact,
            )
            row = json.loads(
                store.record(
                    self.graph.root,
                    artifact_index(self.graph.root, artifact),
                    selection.record,
                    artifact=artifact,
                )
            )
            facts.append([selection.role, self._declaration(artifact.id, row, selection.selector)])
        return [material, facts]

    def _evidence(self, key: str) -> object:
        evidence = self.graph.evidence[key]
        source = self.graph.sources[evidence.source]
        if source.acquisition not in self.graph.support.artifacts:
            return self.graph.fingerprint(key)
        artifact = self.graph.support.artifact(source.acquisition)
        if artifact.artifact_kind != "declarations":
            return self.graph.fingerprint(key)
        body = self.graph.payload(source.id)
        if digest_bytes(body) != source.digest:
            message = "historical or current projection bytes changed"
            raise CollectionError(message)
        row = json.loads(body)
        actual = store.record(
            self.graph.root, artifact_index(self.graph.root, artifact), row["id"], artifact=artifact
        )
        if canonical_bytes(row) != actual:
            message = "declaration projection is not the cited producer record"
            raise CollectionError(message)
        return [
            asdict(evolve(evidence, digest="")),
            source.profile,
            source.origin,
            source.attribution,
            self._declaration(artifact.id, row, evidence.selector),
        ]


def equivalent(root: Path, knowledge: KnowledgeV3, proof: ReviewRevalidation) -> bool:
    """Recompute a historical equivalence proof; stored check labels grant no authority.

    Returns:
        Whether exact valid evidence supports the same reviewed declaration contract.

    """
    if proof.policy != _POLICY or proof.outcome != "equivalent" or proof.prior_knowledge is None:
        return False
    witness = proof.prior_knowledge
    path = confined(root, witness.path)
    if path.stat().st_size != witness.size or digest_file(path) != witness.digest:
        return False
    if any(
        confined(root, item.path).stat().st_size != item.size
        or digest_file(confined(root, item.path)) != item.digest
        for item in proof.prior_inputs
    ):
        return False
    previous = Converter(forbid_extra_keys=True).structure(
        json.loads(path.read_bytes()), KnowledgeV3
    )
    prior = next((r for r in previous.reviews if r.subject == proof.subject), None)
    if prior is None or prior.disposition != "accepted" or prior.digest != proof.previous_digest:
        return False
    old, new = Semantics(root, previous), Semantics(root, knowledge)
    if (
        old.graph.fingerprint(proof.subject) != proof.previous_digest
        or new.graph.fingerprint(proof.subject) != proof.current_digest
    ):
        return False
    return canonical_bytes(old.subject(proof.subject)) == canonical_bytes(
        new.subject(proof.subject)
    )


def record(root: Path, previous_root: Path) -> dict[str, object]:
    """Retain old authority and recompute every changed review without altering it.

    Returns:
        Equivalence or needs-review dispositions with their inspectable prior authority.

    Raises:
        CollectionError: If authorities differ or historical paths conflict with current bytes.

    """
    from library_guides.generations import _portable_paths

    previous = load(previous_root)
    with FileLock(str(root / "knowledge.lock"), timeout=60):
        current = load(root)
        if (
            not isinstance(previous, KnowledgeV3)
            or not isinstance(current, KnowledgeV3)
            or current.collection_id != previous.collection_id
        ):
            message = "review revalidation requires two V3 views of the same collection"
            raise CollectionError(message)
        inputs = []
        for relative in sorted(_portable_paths(previous) - {"knowledge.yaml", "obligations.yaml"}):
            source, target = confined(previous_root, relative), confined(root, relative)
            if target.exists() and digest_file(target) != digest_file(source):
                message = f"historical evidence path conflicts with current bytes: {relative}"
                raise CollectionError(message)
            if not target.exists():
                write_atomic(target, source.read_bytes())
            inputs.append(
                FileEntry(
                    path=relative,
                    digest=digest_file(source),
                    size=source.stat().st_size,
                    kind="historical_input",
                )
            )
        payload = canonical_bytes(asdict(previous))
        digest = digest_bytes(payload)
        path = f"review-history/{digest}.json"
        write_atomic(confined(root, path), payload)
        witness = FileEntry(path=path, digest=digest, size=len(payload), kind="prior_knowledge")
        graph = EvidenceGraph(root, current)
        proofs = []
        for review in previous.reviews:
            if review.subject not in graph.owners:
                continue
            proof = ReviewRevalidation(
                subject=review.subject,
                previous_digest=review.digest,
                current_digest=graph.fingerprint(review.subject),
                policy=_POLICY,
                checks=(
                    "old review matches exact historical support",
                    "current bytes and selectors verified independently",
                    "same assertion, qualifiers, selected declaration semantics, coverage, context and producer",
                ),
                outcome="equivalent",
                prior_knowledge=witness,
                prior_inputs=tuple(inputs),
            )
            try:
                valid = equivalent(root, current, proof)
            except CollectionError, KeyError, ValueError, OSError:
                valid = False
            proofs.append(proof if valid else evolve(proof, outcome="needs_review"))
        keys = {(p.subject, p.current_digest) for p in proofs}
        save(
            root,
            evolve(
                current,
                revalidations=tuple(
                    p for p in current.revalidations if (p.subject, p.current_digest) not in keys
                )
                + tuple(proofs),
            ),
        )
    return {
        "policy": _POLICY,
        "reviews": [asdict(p) for p in proofs],
        "original_reviews_changed": False,
    }

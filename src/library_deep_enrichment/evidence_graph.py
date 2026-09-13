"""Bounded, memoized evidence resolution for large collections."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict

from library_deep_enrichment.collection import (
    CollectionError,
    confined,
    dependencies,
    select,
    subjects,
)
from library_deep_enrichment.knowledge import Evidence, Knowledge
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes


class EvidenceGraph:
    """Pin source bytes for an operation and memoize exact semantic digests."""

    def __init__(self, root: Path, knowledge: Knowledge) -> None:
        """Build indexes once, without reading source bodies yet."""
        from library_deep_enrichment.facts.support import SupportGraph

        self.support = SupportGraph(root, knowledge)
        self.root = root
        self.knowledge = knowledge
        self.owners = subjects(knowledge)
        self.evidence = {item.id: item for item in knowledge.evidence}
        self.sources = {item.id: item for item in knowledge.sources}
        self.principles = {item.id: item for item in knowledge.principles}
        self.examples = {item.id: item for item in knowledge.examples}
        self.profiles = {item.id: item for item in knowledge.profiles}
        from library_deep_enrichment.knowledge_v3 import KnowledgeV3

        self.universes = (
            {u.id: u for u in knowledge.candidate_universes}
            if isinstance(knowledge, KnowledgeV3)
            else {}
        )
        self.payloads: dict[str, bytes] = {}
        self.documents: dict[str, object] = {}
        self.digests: dict[str, str] = {}

    def payload(self, source: str) -> bytes:
        """Read an artifact once, pinning a coherent view for this operation.

        Returns:
            Source bytes pinned for this operation.

        """
        if source not in self.payloads:
            self.payloads[source] = confined(self.root, self.sources[source].path).read_bytes()
        return self.payloads[source]

    def selected(self, evidence: Evidence) -> bytes:
        """Resolve a concrete selection, parsing a JSON source only once.

        Returns:
            Canonical bytes selected by the exact evidence pointer.

        Raises:
            CollectionError: If the evidence selector cannot address a concrete value.

        """
        if not evidence.selector.startswith("json:"):
            return select(self.payload(evidence.source), evidence.selector)
        if evidence.source not in self.documents:
            self.documents[evidence.source] = json.loads(self.payload(evidence.source))
        value = self.documents[evidence.source]
        pointer = evidence.selector.removeprefix("json:")
        if not pointer.startswith("/"):
            message = f"item-level JSON pointer required: {evidence.id}"
            raise CollectionError(message)
        for encoded in pointer.split("/")[1:]:
            token = encoded.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                value = value[int(token)]
            elif isinstance(value, dict):
                value = value[token]
            else:
                message = f"selector crosses a scalar: {evidence.id}"
                raise CollectionError(message)
        return canonical_bytes(value)

    def fingerprint(self, key: str, ancestors: frozenset[str] = frozenset()) -> str:
        """Hash an exact record and its positive and candidate-set dependencies.

        Returns:
            A digest covering the subject and its semantic dependency closure.

        Raises:
            CollectionError: If a dependency is missing or cyclic.

        """
        if key in ancestors:
            message = f"dependency cycle: {key}"
            raise CollectionError(message)
        if key in self.digests:
            return self.digests[key]
        if key in self.universes:
            material = [self._universe(key)]
        elif key in self.support.supports:
            material = [self.support.fingerprint(key)]
        elif key in self.principles:
            material = [asdict(self.principles[key])]
        elif key in self.examples:
            example = self.examples[key]
            material = [
                asdict(example),
                {
                    path: digest_bytes(confined(self.root, path).read_bytes())
                    for path in example.inputs
                },
                [self.fingerprint(claim, ancestors | {key}) for claim in example.claims],
            ]
        elif key in self.evidence:
            item = self.evidence[key]
            source = self.sources[item.source]
            material = [
                asdict(item),
                source.profile,
                asdict(self.profiles[source.profile]) if source.profile in self.profiles else None,
                source.locator,
                source.origin,
                source.attribution,
                digest_bytes(self.selected(item)),
            ]
            if source.origin == "behavior":
                material.append(source.digest)
        elif key in self.owners:
            record = self.owners[key]
            material = [
                asdict(record),
                asdict(self.profiles[record.profile]) if record.profile in self.profiles else None,
                [
                    self.fingerprint(dep, ancestors | {key})
                    for dep in sorted(set(dependencies(self.knowledge, record)))
                ],
            ]
        else:
            message = f"unknown dependency: {key}"
            raise CollectionError(message)
        self.digests[key] = digest_bytes(canonical_bytes(material))
        return self.digests[key]

    def _universe(self, key: str) -> dict[str, object]:
        from library_deep_enrichment.analyses.universes import enumerate_candidates
        from library_deep_enrichment.knowledge_v3 import KnowledgeV3

        if not isinstance(self.knowledge, KnowledgeV3):
            message = "candidate universe requires V3"
            raise CollectionError(message)
        return enumerate_candidates(self.root, self.knowledge, self.universes[key])

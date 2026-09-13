"""Claim-specific fact validation and semantic dependencies for the active authority."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import asdict

from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.facts import store
from library_deep_enrichment.facts.contracts import ClaimSupport, FactArtifact, FactSelection
from library_deep_enrichment.knowledge import Claim, Knowledge
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.source_pipeline import artifact_index
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes

_DECLARATION_KINDS = frozenset({"signature", "shape", "trait_obligation", "public_route"})


class SupportGraph:
    """Verify source dependencies once per read/review operation."""

    def __init__(self, root: Path, knowledge: Knowledge) -> None:
        """Index V3 extensions without introducing another knowledge authority."""
        self.root = root
        self.knowledge = knowledge
        self.artifacts = (
            {item.id: item for item in knowledge.fact_artifacts}
            if isinstance(knowledge, KnowledgeV3)
            else {}
        )
        self.supports = (
            {item.id: item for item in knowledge.claim_support}
            if isinstance(knowledge, KnowledgeV3)
            else {}
        )
        self.verified: set[str] = set()
        self.verified_snapshots: set[str] = set()
        self.visiting: set[str] = set()
        self.closures: set[tuple[str, bool]] = set()
        self.heads = (
            {(item.job, item.profile): item for item in knowledge.fact_heads}
            if isinstance(knowledge, KnowledgeV3)
            else {}
        )

    def artifact(self, identifier: str, *, current: bool = True) -> FactArtifact:
        """Resolve a verified artifact and ensure its disposable index exists.

        Returns:
            The exact artifact declared by the active authority.

        Raises:
            CollectionError: If a cited artifact is absent or stale.

        """
        item = self.artifacts.get(identifier)
        if item is None:
            message = f"unknown or superseded fact artifact: {identifier}"
            raise CollectionError(message)
        head = self.heads.get((item.job, item.profile))
        if (
            current
            and head is not None
            and (head.artifact != item.id or head.outcome != "complete")
        ):
            message = f"fact artifact is not the current requested head: {identifier}"
            raise CollectionError(message)
        if identifier not in self.verified:
            store.verify(self.root, item)
            self._context(item)
            self._snapshots(item)
            index = artifact_index(self.root, item)
            store.ensure_index(self.root, item, index)
            self.verified.add(identifier)
        if (identifier, current) not in self.closures:
            if identifier in self.visiting:
                message = "cyclic artifact dependencies are not admissible support"
                raise CollectionError(message)
            self.visiting.add(identifier)
            try:
                for selection in item.dependencies:
                    dependency = self.artifact(selection.artifact, current=current)
                    if dependency.profile != item.profile:
                        message = "derived input crosses profiles without explicit reconciliation"
                        raise CollectionError(message)
                    store.selected(
                        self.root,
                        artifact_index(self.root, dependency),
                        selection,
                        artifact=dependency,
                    )
            finally:
                self.visiting.remove(identifier)
            self.closures.add((identifier, current))
        return item

    def _context(self, artifact: FactArtifact) -> None:
        from library_deep_enrichment.facts.context import verify

        profiles = (
            {item.id: item for item in self.knowledge.semantic_profiles}
            if isinstance(self.knowledge, KnowledgeV3)
            else {}
        )
        if not artifact.context:
            # Historical pre-context artifacts remain inspectable, never availability evidence.
            return
        profile = profiles.get(artifact.context)
        if profile is None:
            message = f"effective context is absent: {artifact.context}"
            raise CollectionError(message)
        verify(profile)
        receipt = json.loads((self.root / artifact.receipt_path).read_bytes())
        if receipt.get("semantic_profile") != json.loads(canonical_bytes(asdict(profile))):
            message = "effective profile differs from its extraction receipt"
            raise CollectionError(message)

    def _snapshots(self, artifact: FactArtifact) -> None:
        from library_deep_enrichment.source_snapshots import verify

        snapshots = (
            {item.id: item for item in self.knowledge.source_snapshots}
            if isinstance(self.knowledge, KnowledgeV3)
            else {}
        )
        for identifier in artifact.snapshots:
            if identifier not in snapshots:
                message = f"fact source snapshot is absent: {identifier}"
                raise CollectionError(message)
            if identifier not in self.verified_snapshots:
                verify(self.root, snapshots[identifier])
                self.verified_snapshots.add(identifier)

    def fingerprint(self, identifier: str) -> str:
        """Hash exact assertions, actual selected facts and applicable context.

        Returns:
            A support fingerprint independent of unrelated rendering changes.

        """
        support = self.supports[identifier]
        material: list[object] = [asdict(support)]
        for selection in support.facts:
            artifact = self.artifact(selection.artifact)
            payload = store.selected(
                self.root, artifact_index(self.root, artifact), selection, artifact=artifact
            )
            material.append(
                [
                    artifact.input_digest,
                    artifact.profile,
                    artifact.context,
                    artifact.producer,
                    artifact.receipt_digest,
                    digest_bytes(payload),
                ]
            )
        return digest_bytes(canonical_bytes(material))

    def selections(self, support: ClaimSupport) -> list[dict[str, object]]:
        """Read exact support fields for a bounded authoring packet.

        Returns:
            Selected values with their full provenance and applicability.

        """
        result: list[dict[str, object]] = []
        for selection in support.facts:
            artifact = self.artifact(selection.artifact)
            payload = store.selected(
                self.root, artifact_index(self.root, artifact), selection, artifact=artifact
            )
            result.append(
                {
                    "selection": asdict(selection),
                    "profile": artifact.profile,
                    "kind": artifact.artifact_kind,
                    "content": payload.decode(),
                }
            )
        return result

    def errors(self, claim: Claim) -> list[str]:
        """Validate the evidence class without pretending to review entailment.

        Returns:
            Missing, stale or inappropriate support failures.

        """
        supports = [item for item in self.supports.values() if item.claim == claim.id]
        errors = []
        fact_sources = {
            source.id
            for source in self.knowledge.sources
            if source.origin in {"source_code", "fact", "derived"}
        }
        uses_facts = any(
            e.id in claim.evidence and e.source in fact_sources for e in self.knowledge.evidence
        )
        if (claim.verification == "source_reviewed" or uses_facts) and not supports:
            errors.append(f"source-reviewed claim requires fact support: {claim.id}")
        for support in supports:
            errors.extend(self._support_errors(claim, support))
        return errors

    def _support_errors(self, claim: Claim, support: ClaimSupport) -> list[str]:
        errors = []
        if not support.assertion.strip() or not support.facts:
            errors.append(f"empty assertion/support: {support.id}")
        if support.assertion != claim.statement:
            errors.append(f"support assertion differs from the claimed statement: {support.id}")
        try:
            self.fingerprint(support.id)
            errors.extend(self._selection_errors(claim, support))
            if support.kind == "bounded_absence":
                errors.extend(self._absence_errors(support))
        except (KeyError, ValueError, OSError, TypeError) as error:
            errors.append(f"invalid fact support: {support.id}: {error}")
        return errors

    def _selection_errors(self, claim: Claim, support: ClaimSupport) -> list[str]:
        errors = []
        typed_calls: dict[tuple[str, str], set[str]] = {}
        for selection in support.facts:
            artifact = self.artifact(selection.artifact)
            if artifact.profile != claim.profile:
                errors.append(f"fact profile mismatch: {support.id}")
            if artifact.artifact_kind == "declarations":
                errors.extend(self._declaration_errors(support, selection))
            else:
                errors.extend(self._lane_errors(support, selection, artifact))
            if artifact.artifact_kind == "types" and support.kind == "mechanism":
                typed_calls.setdefault((artifact.id, selection.record), set()).add(
                    selection.selector
                )
            if selection.selector in {"json:/id", "json:/symbol", "json:/kind", "json:/local_id"}:
                errors.append(f"API identity cannot establish a contract: {support.id}")
        required = {
            "json:/payload/target",
            "json:/payload/dispatch",
            "json:/payload/target_origin",
            "json:/payload/identity",
        }
        if any(not required <= selectors for selectors in typed_calls.values()):
            errors.append(
                f"typed call support must retain target, origin, identity and dispatch together: {support.id}"
            )
        return errors

    def _lane_errors(
        self, support: ClaimSupport, selection: FactSelection, artifact: FactArtifact
    ) -> list[str]:
        if artifact.artifact_kind == "syntax" and support.kind == "upstream_statement":
            record = json.loads(
                store.record(
                    self.root,
                    artifact_index(self.root, artifact),
                    selection.record,
                    artifact=artifact,
                )
            )
            payload = record.get("payload", {})
            return (
                []
                if selection.selector == "json:/payload/documentation_text"
                and selection.role == "statement"
                and payload.get("documentation") in {"python_docstring", "rust_line"}
                and payload.get("documentation_text")
                and payload.get("syntax_valid")
                else [
                    f"source statement requires a verified documentation role and its exact text: {support.id}"
                ]
            )
        if artifact.artifact_kind == "types" and support.kind == "mechanism":
            record = json.loads(
                store.record(
                    self.root,
                    artifact_index(self.root, artifact),
                    selection.record,
                    artifact=artifact,
                )
            )
            return (
                []
                if record.get("payload", {}).get("kind") == "call"
                and selection.role == "mechanism"
                and selection.selector
                in {
                    "json:/payload/target",
                    "json:/payload/dispatch",
                    "json:/payload/target_origin",
                    "json:/payload/identity",
                }
                else [f"typed call support requires target and uncertainty fields: {support.id}"]
            )
        allowed = {
            "syntax": ({"shape"}, "json:/payload/", "declaration"),
            "lexical": ({"shape"}, "json:/payload/", "declaration"),
            "types": ({"shape", "signature", "trait_obligation"}, "json:/payload/", "declaration"),
            "mir": ({"mechanism"}, "json:/", "mechanism"),
            "derived": (
                {"mechanism", "bounded_absence", "comparison"},
                "json:/analysis/",
                "mechanism",
            ),
        }
        policy = allowed.get(artifact.artifact_kind)
        if (
            policy is None
            or support.kind not in policy[0]
            or selection.role != policy[2]
            or not selection.selector.startswith(policy[1])
        ):
            return [f"lane/field cannot establish {support.kind}: {support.id}"]
        if artifact.artifact_kind == "mir" and not selection.selector.startswith(
            ("json:/payload/events/", "json:/payload/exits/", "json:/payload/locals/")
        ):
            return [
                f"MIR support requires a selected transfer, call, branch or local contract: {support.id}"
            ]
        if artifact.artifact_kind == "syntax" and selection.selector != "json:/payload/signature":
            return [f"source shape support requires a definition signature: {support.id}"]
        return []

    def _declaration_errors(self, support: ClaimSupport, selection: FactSelection) -> list[str]:
        if support.kind == "upstream_statement":
            return (
                []
                if selection.selector == "json:/item/docs" and selection.role == "statement"
                else [f"upstream statement requires the item documentation field: {support.id}"]
            )
        permitted = {
            "signature": ("json:/item/inner/function", "json:/owner_contract"),
            "shape": ("json:/item/inner/",),
            "trait_obligation": (
                "json:/item/inner/trait",
                "json:/item/inner/impl",
                "json:/item/inner/function",
            ),
            "public_route": ("json:/public_routes",),
        }
        if support.kind not in _DECLARATION_KINDS or not selection.selector.startswith(
            permitted.get(support.kind, ())
        ):
            return [f"declaration field cannot establish {support.kind}: {support.id}"]
        if selection.role != "declaration":
            return [f"declaration support has incompatible evidence role: {support.id}"]
        if support.kind == "public_route":
            artifact = self.artifact(selection.artifact)
            receipt = json.loads((self.root / artifact.receipt_path).read_bytes())
            if receipt["terminal"]["coverage"].get("route_state") != "complete":
                return [f"public route universe is incomplete: {support.id}"]
        return []

    def _absence_errors(self, support: ClaimSupport) -> list[str]:
        scope = support.scope
        if scope is None or not scope.closed or scope.frontier or scope.mode != "conservative":
            return [f"absence requires a closed conservative analysis: {support.id}"]
        errors = []
        for selection in support.facts:
            artifact = self.artifact(selection.artifact)
            if (
                artifact.artifact_kind != "derived"
                or artifact.schema != "library-guides.mir-analysis.v1"
                or selection.selector != "json:/analysis/absence"
            ):
                errors.append(f"absence requires an owned predicate certificate: {support.id}")
                continue
            certificate = json.loads(
                store.selected(
                    self.root, artifact_index(self.root, artifact), selection, artifact=artifact
                )
            )
            expected = {
                "predicate": scope.predicate,
                "model": scope.model,
                "scope": list(scope.owners),
                "closed": True,
                "holds": True,
                "frontier": [],
            }
            if (
                any(certificate.get(k) != v for k, v in expected.items())
                or scope.predicate != "no-modeled-memory-writes"
                or scope.profile != artifact.profile
            ):
                errors.append(
                    f"absence predicate, model or universe disagrees with its certificate: {support.id}"
                )
            receipt = json.loads((self.root / artifact.receipt_path).read_bytes())
            if not receipt["terminal"]["coverage"].get("semantic_closed", False):
                errors.append(
                    f"extraction completeness does not prove semantic closure: {support.id}"
                )
        return errors

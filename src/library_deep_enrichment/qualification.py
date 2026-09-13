"""Structural qualification and honest four-axis coverage reporting."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml
from attrs import asdict
from cattrs import Converter

from library_deep_enrichment.collection import (
    Subject,
    dependencies,
    subjects,
)
from library_deep_enrichment.evidence_graph import EvidenceGraph
from library_deep_enrichment.knowledge import (
    Binding,
    Capability,
    Claim,
    Decision,
    Integration,
    Knowledge,
    Obligation,
)
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes

_READ_ERRORS = (KeyError, ValueError, OSError, IndexError, TypeError)
_AXIS_TYPES = {
    "surface": Binding,
    "use_case": Capability,
    "decision": Decision,
    "composition": Integration,
}


class Qualification:
    """Validate one immutable input view, retaining failures by subject."""

    def __init__(self, root: Path, knowledge: Knowledge) -> None:
        """Index the authority without inferring coverage from generated prose."""
        self.graph = EvidenceGraph(root, knowledge)
        self.root = root
        self.knowledge = knowledge
        self.owners = subjects(knowledge)
        self.sources = {item.id: item for item in knowledge.sources}
        self.evidence = {item.id: item for item in knowledge.evidence}
        self.profiles = {
            profile.id: {profile.id, *profile.components} for profile in knowledge.profiles
        }
        self.reviews = {item.subject: item for item in knowledge.reviews}
        policy = root / "obligations.yaml"
        self.policy_present = policy.is_file()
        raw = yaml.safe_load(policy.read_text(encoding="utf-8")) if self.policy_present else {}
        self.obligations = tuple(
            Converter(forbid_extra_keys=True).structure(item, Obligation)
            for item in raw.get("obligations", [])
        )

    def integrity_errors(self) -> list[str]:
        """Return concrete input integrity failures.

        Returns:
            Source, selector and identifier integrity failures.

        """
        errors: list[str] = []
        groups = (
            self.knowledge.sources,
            self.knowledge.evidence,
            self.knowledge.obligations,
            self.knowledge.examples,
            self.knowledge.profiles,
            self.knowledge.principles,
        )
        errors.extend(
            "duplicate source, evidence, obligation or example id"
            for group in groups
            if len({item.id for item in group}) != len(group)
        )
        if len(self.reviews) != len(self.knowledge.reviews):
            errors.append("duplicate current reviews")
        if self.owners.keys() & self.evidence.keys():
            errors.append("evidence and subject identifiers collide")
        identities = [*self.owners, *self.evidence, *self.graph.principles, *self.graph.examples]
        if any(not key.strip() for key in identities) or len(identities) != len(set(identities)):
            errors.append("semantic identifiers must be nonempty and unique across record kinds")
        errors.extend(self._source_errors())
        errors.extend(self._profile_errors())
        errors.extend(self._example_errors())
        errors.extend(
            f"review names no semantic subject: {key}"
            for key in self.reviews
            if key not in self.owners
        )
        for item in self.evidence.values():
            try:
                if not item.subject or item.selector == "json:":
                    errors.append(f"evidence requires an item-level selector: {item.id}")
                if digest_bytes(self.graph.selected(item)) != item.digest:
                    errors.append(f"evidence changed: {item.id}")
            except _READ_ERRORS as error:
                errors.append(f"invalid evidence {item.id}: {error}")
        if isinstance(self.knowledge, KnowledgeV3):
            from library_deep_enrichment.analyses.universes import policy_errors

            errors.extend(policy_errors(self.root, self.knowledge))
            errors.extend(self._fact_errors())
        return errors

    def _fact_errors(self) -> list[str]:
        errors = []
        for artifact in self.graph.support.artifacts.values():
            try:
                self.graph.support.artifact(artifact.id, current=False)
            except _READ_ERRORS as error:
                errors.append(f"invalid fact artifact: {artifact.id}: {error}")
        errors.extend(
            f"fact support has no claim: {support.id}"
            for support in self.graph.support.supports.values()
            if not isinstance(self.owners.get(support.claim), Claim)
        )
        if isinstance(self.knowledge, KnowledgeV3):
            groups = (
                self.knowledge.fact_artifacts,
                self.knowledge.semantic_profiles,
                self.knowledge.source_snapshots,
                self.knowledge.claim_support,
                self.knowledge.candidate_universes,
            )
            if any(len({item.id for item in group}) != len(group) for group in groups):
                errors.append("duplicate V3 evidence identity")
            errors.extend(
                f"unknown fact profile: {artifact.id}"
                for artifact in self.knowledge.fact_artifacts
                if artifact.profile not in self.profiles
            )
        return errors

    def _profile_errors(self) -> list[str]:
        errors = [
            f"unknown profile: {record.id} -> {record.profile}"
            for record in (*self.knowledge.sources, *self.owners.values(), *self.knowledge.examples)
            if record.profile not in self.profiles
        ]
        errors.extend(
            f"invalid profile declaration: {profile.id}"
            for profile in self.knowledge.profiles
            if not profile.description.strip()
            or any(key == profile.id or key not in self.profiles for key in profile.components)
        )
        return errors

    def _example_errors(self) -> list[str]:
        errors = []
        for example in self.knowledge.examples:
            if not example.argv or not example.inputs or example.timeout_seconds <= 0:
                errors.append(f"incomplete example: {example.id}")
            for key in example.claims:
                claim = self.owners.get(key)
                if not isinstance(claim, Claim) or claim.profile not in self.profiles.get(
                    example.profile, {example.profile}
                ):
                    errors.append(f"invalid example claim: {example.id} -> {key}")
            try:
                self.graph.fingerprint(example.id)
            except _READ_ERRORS as error:
                errors.append(f"invalid example input: {example.id}: {error}")
        return errors

    def _source_errors(self) -> list[str]:
        errors: list[str] = []
        for source in self.sources.values():
            try:
                if digest_bytes(self.graph.payload(source.id)) != source.digest:
                    errors.append(f"source changed: {source.id}")
                if not source.profile or not source.locator or not source.attribution:
                    errors.append(f"source lacks provenance: {source.id}")
            except _READ_ERRORS as error:
                errors.append(f"source unavailable {source.id}: {error}")
        return errors

    def evidence_errors(self, record: Binding | Claim) -> list[str]:
        """Return evidence origin, applicability and specificity failures.

        Returns:
            Missing evidence, applicability and evidence-origin failures.

        """
        errors = []
        if not record.evidence:
            errors.append(f"unsupported subject: {record.id}")
        for ref in record.evidence:
            item = self.evidence.get(ref)
            source = self.sources.get(item.source) if item else None
            if source is None or item is None:
                errors.append(f"unknown evidence: {record.id} -> {ref}")
                continue
            if source.profile not in self.profiles.get(record.profile, {record.profile}):
                errors.append(f"wrong evidence profile: {record.id} -> {ref}")
            if isinstance(record, Claim) and item.kind == "api" and record.category != "structural":
                errors.append(f"API existence cannot support behavior: {record.id}")
            if (
                isinstance(record, Claim)
                and record.verification == "behavior_tested"
                and (item.kind != "behavior" or source.origin != "behavior")
            ):
                errors.append(f"behavior-tested claim needs an execution receipt: {record.id}")
        return errors

    def contract_errors(self, record: Subject) -> list[str]:
        """Return failures specific to the semantic kind.

        Returns:
            Structural defects for the subject kind.

        """
        if isinstance(record, (Binding, Claim)):
            errors = self.evidence_errors(record)
            if isinstance(record, Claim) and isinstance(self.knowledge, KnowledgeV3):
                errors.extend(self.graph.support.errors(record))
            if isinstance(record, Claim) and (not record.statement or not record.mechanism):
                errors.append(f"claim has no statement or mechanism: {record.id}")
            return errors
        if isinstance(record, Capability):
            return self._capability_errors(record)
        if isinstance(record, Decision):
            return self._decision_errors(record)
        required = (
            record.representation,
            record.ownership,
            record.lifecycle,
            record.failures,
            record.claims,
            record.examples,
        )
        errors = [] if all(required) else [f"incomplete integration: {record.id}"]
        if not all(
            isinstance(self.owners.get(key), Capability)
            for key in (record.producer, record.consumer)
        ):
            errors.append(f"integration endpoints must be capabilities: {record.id}")
        return errors

    def _capability_errors(self, record: Capability) -> list[str]:
        errors: list[str] = []
        if not record.claims or not record.bindings or not record.intent or not record.family:
            errors.append(f"capability has no contract or binding: {record.id}")
        if not all(isinstance(self.owners.get(key), Binding) for key in record.bindings):
            errors.append(f"capability binding has wrong type: {record.id}")
        if len({facet.name for facet in record.facets}) != len(record.facets):
            errors.append(f"duplicate capability facet: {record.id}")
        errors.extend(
            f"unsupported facet: {record.id}/{facet.name}"
            for facet in record.facets
            if not facet.value or not facet.claims
        )
        errors.extend(
            f"incomplete principle realization: {record.id}"
            for realization in record.realizations
            if not all(
                (
                    realization.principle,
                    realization.mechanism,
                    realization.conditions,
                    realization.claims,
                )
            )
        )
        fact_refs = [key for facet in record.facets for key in facet.claims]
        fact_refs.extend(key for realization in record.realizations for key in realization.claims)
        errors.extend(
            f"facet or principle link is not a claim: {record.id} -> {key}"
            for key in fact_refs
            if not isinstance(self.owners.get(key), Claim)
        )
        return errors

    def _decision_errors(self, record: Decision) -> list[str]:
        errors: list[str] = []
        minimum_candidates = 2
        if len(record.candidates) < minimum_candidates or not all(
            (record.reversing_conditions, record.claims, record.comparison, record.requirements)
        ):
            errors.append(f"incomplete comparison: {record.id}")
        selected = {item.capability for item in record.candidates}
        if len(selected) != len(record.candidates):
            errors.append(f"duplicate candidates: {record.id}")
        for candidate in record.candidates:
            capability = self.owners.get(candidate.capability)
            if not isinstance(capability, Capability) or capability.family != record.family:
                errors.append(f"candidate outside declared family: {record.id}")
            if not candidate.when or not candidate.claims:
                errors.append(f"unsupported candidate applicability: {record.id}")
            errors.extend(
                f"candidate applicability link is not a claim: {record.id} -> {key}"
                for key in candidate.claims
                if not isinstance(self.owners.get(key), Claim)
            )
        return errors

    def subject_errors(self, record: Subject, *, require_review: bool) -> list[str]:
        """Return all structural and review failures for one subject.

        Returns:
            All contract, dependency and acceptance defects for the subject.

        """
        errors = self.contract_errors(record)
        for key in dependencies(self.knowledge, record):
            linked = self.owners.get(key)
            if linked is not None and linked.profile not in self.profiles.get(
                record.profile, {record.profile}
            ):
                errors.append(f"wrong profile: {record.id} -> {key}")
        try:
            self.graph.fingerprint(record.id)
            if require_review and not isinstance(record, Binding):
                review = self.reviews.get(record.id)
                if review is None or not (
                    review.disposition == "accepted"
                    and review.reviewer.strip()
                    and review.rationale.strip()
                    and self._review_current(record.id, review.digest)
                ):
                    errors.append(f"review required: {record.id}")
        except _READ_ERRORS as error:
            errors.append(f"invalid dependency for {record.id}: {error}")
        if not isinstance(record, Binding):
            claims = record.claims if not isinstance(record, Claim) else ()
            errors.extend(
                f"claim link has wrong type: {record.id} -> {key}"
                for key in claims
                if not isinstance(self.owners.get(key), Claim)
            )
        examples = {example.id: example for example in self.knowledge.examples}
        if isinstance(record, (Decision, Integration)):
            errors.extend(
                f"missing example: {record.id} -> {key}"
                for key in record.examples
                if key not in examples
            )
        return errors

    def obligation_errors(self) -> list[str]:
        """Return unsatisfied declared obligations, including missing targets.

        Returns:
            Missing, unresolved or incorrectly scoped denominator members.

        """
        errors: list[str] = []
        if not self.policy_present or not self.obligations:
            errors.append("independent obligations.yaml policy is missing or empty")
        elif canonical_bytes([asdict(item) for item in self.obligations]) != canonical_bytes(
            [asdict(item) for item in self.knowledge.obligations]
        ):
            errors.append("knowledge obligations differ from the independent scope policy")
        if not self.knowledge.sources or not self.knowledge.obligations:
            errors.append("collection requires sources and independently declared obligations")
        axes = {item.axis for item in self.knowledge.obligations}
        errors.extend(
            f"coverage axis not declared: {axis}" for axis in _AXIS_TYPES if axis not in axes
        )
        errors.extend(self._targets_errors())
        return errors

    def _targets_errors(self) -> list[str]:
        errors: list[str] = []
        for obligation in self.obligations:
            if obligation.disposition != "required":
                if not obligation.reason.strip():
                    errors.append(f"unexplained scope disposition: {obligation.id}")
                continue
            target = self.owners.get(obligation.target)
            if not isinstance(target, _AXIS_TYPES[obligation.axis]):
                errors.append(f"unfulfilled obligation: {obligation.id}")
            elif target.profile != obligation.profile:
                errors.append(f"wrong obligation profile: {obligation.id}")
            elif isinstance(target, Capability):
                facets = {facet.name for facet in target.facets}
                if set(obligation.required_facets) - facets:
                    errors.append(f"missing required facets: {obligation.id}")
            elif isinstance(target, Binding) and target.resolution != "resolved":
                errors.append(f"unresolved required binding: {obligation.id}")
        return errors

    def _review_current(self, key: str, previous_digest: str) -> bool:
        from library_deep_enrichment.revalidation import equivalent

        current = self.graph.fingerprint(key)
        if current == previous_digest:
            return True
        if not isinstance(self.knowledge, KnowledgeV3):
            return False
        return any(
            proof.subject == key
            and proof.previous_digest == previous_digest
            and proof.current_digest == current
            and equivalent(self.root, self.knowledge, proof)
            for proof in self.knowledge.revalidations
        )

    def closure_accepted(self, key: str, visiting: frozenset[str] = frozenset()) -> bool:
        """Require accepted dependency reviews before counting an obligation.

        Returns:
            Whether every semantic subject in the dependency closure is accepted.

        """
        if key in visiting:
            return False
        if key not in self.owners:
            if key in self.graph.support.supports or key in self.graph.universes:
                try:
                    self.graph.fingerprint(key)
                except _READ_ERRORS:
                    return False
                return True
            return (
                key in self.evidence or key in self.graph.principles or key in self.graph.examples
            )
        record = self.owners[key]
        return not self.subject_errors(record, require_review=True) and all(
            self.closure_accepted(dependency, visiting | {key})
            for dependency in dependencies(self.knowledge, record)
        )


def validate(root: Path, knowledge: Knowledge, *, require_reviews: bool = True) -> tuple[str, ...]:
    """Return qualification failures; structural checks do not prove entailment.

    Returns:
        Every qualification defect; an empty tuple indicates structural acceptance.

    """
    check = Qualification(root, knowledge)
    errors = check.integrity_errors() + check.obligation_errors()
    for record in check.owners.values():
        errors.extend(check.subject_errors(record, require_review=require_reviews))
    return tuple(errors)


def coverage(root: Path, knowledge: Knowledge) -> dict[str, object]:
    """Report each independent denominator, preserving unavailable and excluded work.

    Returns:
        Separate surface, use-case, decision and composition coverage counts and gaps.

    """
    check = Qualification(root, knowledge)
    integrity = check.integrity_errors()
    policy_errors = [
        error
        for error in check.obligation_errors()
        if not error.startswith(
            (
                "unfulfilled obligation:",
                "missing required facets:",
                "unresolved required binding:",
                "wrong obligation profile:",
            )
        )
    ]
    result: dict[str, object] = {}
    for axis, required_type in _AXIS_TYPES.items():
        obligations = [item for item in check.obligations if item.axis == axis]
        counts = Counter(item.disposition for item in obligations)
        fulfilled = []
        gaps = []
        for item in obligations:
            if item.disposition != "required":
                continue
            target = check.owners.get(item.target)
            valid = (
                not integrity
                and not policy_errors
                and isinstance(target, required_type)
                and target.profile == item.profile
                and check.closure_accepted(target.id)
            )
            if isinstance(target, Binding):
                valid = valid and target.resolution == "resolved"
            if isinstance(target, Capability):
                valid = valid and set(item.required_facets) <= {f.name for f in target.facets}
            (fulfilled if valid else gaps).append(item.id)
        result[axis] = {
            "enumerated": len(obligations),
            "required": counts["required"],
            "fulfilled": len(fulfilled),
            "gaps": gaps,
            "reference_only": counts["reference_only"],
            "excluded": counts["excluded"],
            "state": "unavailable" if not obligations else "partial" if gaps else "complete",
            "policy_errors": policy_errors,
        }
    return result

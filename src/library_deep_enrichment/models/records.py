"""The eight evidence and knowledge records.

A common envelope with language-specific payloads. A Python callable and a Rust
trait method can both expose a capability, but their signatures, dispatch rules,
ownership, and import paths are not forced into one textual signature field.
"""

from __future__ import annotations

from attrs import field, frozen

from library_deep_enrichment.models.enums import (
    Ecosystem,
    EvidenceOrigin,
    ResolutionState,
    ReviewState,
    StageCompletion,
    SurfaceKind,
    VerificationLevel,
)
from library_deep_enrichment.models.ids import ApiIdentity, SurfaceId
from library_deep_enrichment.models.spans import EvidenceSpan

__all__ = [
    "ApiBinding",
    "DependencyEdge",
    "ExtractionReceipt",
    "Observation",
    "SemanticClaim",
    "SourceArtifact",
    "SurfaceEntry",
    "UnprocessedInput",
]


@frozen(kw_only=True)
class SourceArtifact:
    """One acquired input, with the scope its content is evidence for."""

    artifact_id: str = field()
    library_id: str = field()
    package: str = field()
    ecosystem: Ecosystem = field()
    upstream_locator: str = field()
    content_digest: str = field()
    artifact_kind: str = field()
    acquisition_result: str = field()
    build_scope: tuple[str, ...] = field(default=())
    attribution: str | None = field(default=None)
    license_expression: str | None = field(default=None)


@frozen(kw_only=True)
class ApiBinding:
    """One public API item, as reported by one extractor under one profile."""

    library_id: str = field()
    profile_id: str = field()
    identity: ApiIdentity = field()
    signature: str | None = field(default=None)
    structured_signature: tuple[tuple[str, str], ...] = field(default=())
    defining_path: str | None = field(default=None)
    availability_conditions: tuple[str, ...] = field(default=())
    documentation_refs: tuple[str, ...] = field(default=())
    deprecation: str | None = field(default=None)
    evidence_origin: EvidenceOrigin = field()
    resolution_state: ResolutionState = field(default=ResolutionState.RESOLVED)
    span: EvidenceSpan | None = field(default=None)


@frozen(kw_only=True)
class SurfaceEntry:
    """One non-symbol surface with its own coverage denominator."""

    library_id: str = field()
    profile_id: str = field()
    identity: SurfaceId = field()
    surface_kind: SurfaceKind = field()
    description: str | None = field(default=None)
    aliases: tuple[str, ...] = field(default=())
    attributes: tuple[tuple[str, str], ...] = field(default=())
    availability_conditions: tuple[str, ...] = field(default=())
    evidence_origin: EvidenceOrigin = field()
    resolution_state: ResolutionState = field(default=ResolutionState.RESOLVED)
    span: EvidenceSpan | None = field(default=None)


@frozen(kw_only=True)
class Observation:
    """One subject-predicate-object fact attributed to one extractor.

    ``resolution_state`` records how well ``subject`` binds to a library
    identity, independently of how the observation was produced.
    """

    observation_id: str = field()
    library_id: str = field()
    subject: str = field()
    predicate: str = field()
    object_value: str = field()
    evidence_origin: EvidenceOrigin = field()
    resolution_state: ResolutionState = field()
    extractor_id: str = field()
    scope: tuple[str, ...] = field(default=())
    competing_subjects: tuple[str, ...] = field(default=())
    span: EvidenceSpan | None = field(default=None)


@frozen(kw_only=True)
class SemanticClaim:
    """One reviewed statement connecting a requirement to a mechanism.

    A claim carrying no supporting evidence may never reach
    :data:`~library_deep_enrichment.models.enums.ReviewState.ACCEPTED`; publication
    validation rejects it.
    """

    claim_id: str = field()
    library_id: str = field()
    use_case: str = field()
    requirement: str = field()
    candidate: str = field()
    principle: str | None = field(default=None)
    mechanism: str = field()
    conditions: tuple[str, ...] = field(default=())
    exceptions: tuple[str, ...] = field(default=())
    alternatives: tuple[str, ...] = field(default=())
    counterfactuals: tuple[str, ...] = field(default=())
    evidence_refs: tuple[str, ...] = field(default=())
    verification_level: VerificationLevel = field(default=VerificationLevel.DOCUMENTED)
    review_state: ReviewState = field(default=ReviewState.NEEDS_REVIEW)
    reviewed_by: str | None = field(default=None)
    reviewed_evidence_digest: str | None = field(default=None)

    def is_publishable(self) -> bool:
        """Return whether this claim may be rendered as accepted guidance.

        Returns:
            ``True`` only when the claim is accepted and cites evidence.

        """
        return self.review_state is ReviewState.ACCEPTED and bool(self.evidence_refs)


@frozen(kw_only=True)
class DependencyEdge:
    """What a downstream artifact or claim depends on, and at what granularity.

    ``dependency_kind`` distinguishes an ordinary input from a *candidate set* or
    a *bounded absence query*. A decision that preferred a custom extension
    because no built-in was found depends on the searched inventory, so a newly
    added built-in must reopen it even though the extension's own source is
    unchanged.
    """

    consumer_id: str = field()
    upstream_id: str = field()
    dependency_kind: str = field()
    invalidation_granularity: str = field(default="artifact")
    search_scope: tuple[str, ...] = field(default=())


@frozen(kw_only=True)
class UnprocessedInput:
    """One declared input a stage did not turn into output, and why."""

    input_id: str = field()
    disposition: str = field()
    reason: str = field()


@frozen(kw_only=True)
class ExtractionReceipt:
    """Complete account of one stage execution.

    A stage that enumerated inputs it could not process reports
    :data:`~library_deep_enrichment.models.enums.StageCompletion.PARTIAL`. Downstream
    absence claims are invalid against a partial receipt.
    """

    stage_id: str = field()
    library_id: str | None = field(default=None)
    profile_id: str | None = field(default=None)
    tool_identity: tuple[tuple[str, str], ...] = field(default=())
    configuration_digest: str = field()
    enumerated_inputs: int = field()
    processed_inputs: int = field()
    unprocessed: tuple[UnprocessedInput, ...] = field(default=())
    output_digests: tuple[tuple[str, str], ...] = field(default=())
    completion: StageCompletion = field()

    @completion.validator
    def _check_completion(self, _attribute: object, value: StageCompletion) -> None:
        complete = value is StageCompletion.COMPLETE
        if complete and self.processed_inputs != self.enumerated_inputs:
            message = (
                f"stage {self.stage_id} reported complete with "
                f"{self.processed_inputs}/{self.enumerated_inputs} inputs processed"
            )
            raise ValueError(message)
        if complete and self.unprocessed:
            message = f"stage {self.stage_id} reported complete with unprocessed inputs"
            raise ValueError(message)

    def authorizes_absence_claim(self) -> bool:
        """Return whether a negative claim may cite this receipt.

        Returns:
            ``True`` only for a complete receipt with no unprocessed inputs.

        """
        return self.completion is StageCompletion.COMPLETE and not self.unprocessed

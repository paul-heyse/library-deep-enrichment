"""The record model keeps evidence origin, resolution, and review independent."""

from __future__ import annotations

import pytest

from library_deep_enrichment.models import (
    ApiBinding,
    ApiIdentity,
    Ecosystem,
    EvidenceOrigin,
    EvidenceSpan,
    ExtractionReceipt,
    LineRange,
    ResolutionState,
    ReviewState,
    SemanticClaim,
    StageCompletion,
    UnprocessedInput,
    VerificationLevel,
    structure_record,
    unstructure_record,
)


def _binding() -> ApiBinding:
    return ApiBinding(
        library_id="example-rust",
        profile_id="example-rust-1.0.0",
        identity=ApiIdentity(
            ecosystem=Ecosystem.RUST,
            package="example",
            public_path="example::prelude::Thing",
            item_kind="struct",
            aliases=("example::Thing",),
        ),
        signature="pub struct Thing",
        evidence_origin=EvidenceOrigin.COMPILER_API,
    )


def test_records_round_trip_through_the_converter() -> None:
    """Unstructuring and restructuring a record preserves it exactly."""
    binding = _binding()
    assert structure_record(unstructure_record(binding), ApiBinding) == binding


def test_unstructured_records_are_json_encodable_primitives() -> None:
    """Enums reach JSONL as their stable string values, not as repr output."""
    payload = unstructure_record(_binding())
    assert payload["evidence_origin"] == "compiler_api"
    assert payload["resolution_state"] == "resolved"


def test_a_syntax_match_can_be_fully_extracted_yet_unresolved() -> None:
    """Extraction quality and identity resolution are separate axes."""
    binding = ApiBinding(
        library_id="example-rust",
        profile_id="example-rust-1.0.0",
        identity=ApiIdentity(
            ecosystem=Ecosystem.RUST,
            package="example",
            public_path="unknown_receiver::register_udf",
            item_kind="method",
        ),
        evidence_origin=EvidenceOrigin.SYNTAX_MATCH,
        resolution_state=ResolutionState.AMBIGUOUS,
    )
    assert binding.evidence_origin is EvidenceOrigin.SYNTAX_MATCH
    assert binding.resolution_state is ResolutionState.AMBIGUOUS


def test_a_claim_without_evidence_is_never_publishable() -> None:
    """Acceptance alone does not license a claim; it must cite evidence."""
    claim = SemanticClaim(
        claim_id="example.prefer_builtin",
        library_id="example-rust",
        use_case="transform_values",
        requirement="preserve_row_semantics",
        candidate="example.expression_composition",
        mechanism="Keep the operation in the query expression tree.",
        review_state=ReviewState.ACCEPTED,
        evidence_refs=(),
    )
    assert not claim.is_publishable()


def test_an_accepted_claim_with_evidence_is_publishable() -> None:
    """An accepted claim citing evidence may be rendered as guidance."""
    claim = SemanticClaim(
        claim_id="example.prefer_builtin",
        library_id="example-rust",
        use_case="transform_values",
        requirement="preserve_row_semantics",
        candidate="example.expression_composition",
        mechanism="Keep the operation in the query expression tree.",
        review_state=ReviewState.ACCEPTED,
        evidence_refs=("src://example/lib.rs#L10-L20",),
        verification_level=VerificationLevel.SOURCE_REVIEWED,
    )
    assert claim.is_publishable()


def test_a_receipt_cannot_claim_completeness_with_unprocessed_inputs() -> None:
    """A receipt that skipped declared inputs cannot call itself complete."""
    with pytest.raises(ValueError, match="reported complete"):
        ExtractionReceipt(
            stage_id="extract-api",
            configuration_digest="0" * 64,
            enumerated_inputs=4,
            processed_inputs=2,
            completion=StageCompletion.COMPLETE,
        )


def test_only_a_complete_receipt_authorizes_an_absence_claim() -> None:
    """A partial scan cannot establish that something is absent."""
    partial = ExtractionReceipt(
        stage_id="mine-source",
        configuration_digest="0" * 64,
        enumerated_inputs=3,
        processed_inputs=2,
        unprocessed=(
            UnprocessedInput(input_id="a.rs", disposition="skipped", reason="unreadable"),
        ),
        completion=StageCompletion.PARTIAL,
    )
    complete = ExtractionReceipt(
        stage_id="mine-source",
        configuration_digest="0" * 64,
        enumerated_inputs=3,
        processed_inputs=3,
        completion=StageCompletion.COMPLETE,
    )
    assert not partial.authorizes_absence_claim()
    assert complete.authorizes_absence_claim()


def test_byte_offsets_are_kept_separate_from_display_lines() -> None:
    """Byte offsets and rendered line numbers are distinct coordinates."""
    span = EvidenceSpan(
        artifact_id="doc-1",
        byte_start=120,
        byte_end=180,
        line_range=LineRange(start_line=4, end_line=6),
    )
    assert span.has_exact_location()
    assert span.byte_start != span.line_range.start_line if span.line_range else False


def test_an_inverted_byte_range_is_rejected() -> None:
    """A span whose end precedes its start is a defect, not a location."""
    with pytest.raises(ValueError, match="invalid byte range"):
        EvidenceSpan(artifact_id="doc-1", byte_start=200, byte_end=100)

"""The store never lets a failed stage overwrite a good inventory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from library_deep_enrichment.models import ApiBinding, ApiIdentity, Ecosystem, EvidenceOrigin
from library_deep_enrichment.models.enums import StageCompletion
from library_deep_enrichment.models.records import ExtractionReceipt, UnprocessedInput
from library_deep_enrichment.store import (
    PublicationRefusedError,
    ReceiptRequest,
    StagedBundle,
    build_receipt,
    digest_mapping,
    encode_line,
    publish_bundle,
    read_records,
    write_atomic,
    write_records,
)
from library_deep_enrichment.store.digests import digest_file

if TYPE_CHECKING:
    from pathlib import Path


def _binding(name: str) -> ApiBinding:
    return ApiBinding(
        library_id="example",
        profile_id="example-1",
        identity=ApiIdentity(
            ecosystem=Ecosystem.PYTHON,
            package="example",
            public_path=f"example.{name}",
            item_kind="function",
        ),
        evidence_origin=EvidenceOrigin.STATIC_API,
    )


def test_jsonl_round_trips_and_is_byte_stable(tmp_path: Path) -> None:
    """Rewriting the same records produces identical bytes."""
    path = tmp_path / "api.jsonl"
    records = [_binding("alpha"), _binding("beta")]
    expected_count = len(records)
    assert write_records(path, records) == expected_count
    first = path.read_bytes()
    write_records(path, records)
    assert path.read_bytes() == first
    assert list(read_records(path, ApiBinding)) == records


def test_the_encoder_refuses_unknown_objects() -> None:
    """A silent string coercion would disguise an extraction defect."""
    with pytest.raises(TypeError, match="not JSON-encodable"):
        encode_line({"value": object()})


def test_operational_keys_do_not_change_a_semantic_digest() -> None:
    """Refreshing an unchanged source must not invalidate downstream work."""
    first = digest_mapping({"body": "unchanged", "acquired_at": "2026-09-11T00:00:00Z"})
    second = digest_mapping({"body": "unchanged", "acquired_at": "2026-09-12T09:30:00Z"})
    assert first == second


def test_a_content_change_does_change_the_digest() -> None:
    """Semantic content still drives the digest."""
    assert digest_mapping({"body": "a"}) != digest_mapping({"body": "b"})


def test_atomic_write_leaves_no_partial_file(tmp_path: Path) -> None:
    """A write either lands whole or leaves nothing behind."""
    path = tmp_path / "nested" / "artifact.json"
    write_atomic(path, b'{"ok":true}')
    assert path.read_bytes() == b'{"ok":true}'
    assert not list(path.parent.glob("tmp*"))


def _receipt(*, failed: bool = False) -> ExtractionReceipt:
    return build_receipt(
        ReceiptRequest(
            stage_id="extract-api",
            configuration={"profile": "example-1"},
            enumerated_inputs=1,
            processed_inputs=0 if failed else 1,
            failed=failed,
        )
    )


def test_publication_refuses_a_failed_stage(tmp_path: Path) -> None:
    """A failed stage must not replace a previously good inventory."""
    staging = tmp_path / "staging"
    published = tmp_path / "published"
    payload = tmp_path / "staging" / "api.jsonl"
    write_atomic(payload, b"{}\n")
    bundle = StagedBundle(
        staging_root=staging,
        expected_digests={"api.jsonl": digest_file(payload)},
    )
    receipt = build_receipt(
        ReceiptRequest(
            stage_id="extract-api",
            configuration={},
            enumerated_inputs=1,
            processed_inputs=0,
            failed=True,
        )
    )
    with pytest.raises(PublicationRefusedError, match="failed"):
        publish_bundle(bundle, receipt, published)
    assert not published.exists()


def test_publication_refuses_bytes_the_build_did_not_declare(tmp_path: Path) -> None:
    """Publication writes only what the build accounted for."""
    staging = tmp_path / "staging"
    published = tmp_path / "published"
    write_atomic(staging / "api.jsonl", b"{}\n")
    bundle = StagedBundle(staging_root=staging, expected_digests={"api.jsonl": "0" * 64})
    receipt = build_receipt(
        ReceiptRequest(
            stage_id="extract-api",
            configuration={},
            enumerated_inputs=1,
            processed_inputs=1,
        )
    )
    with pytest.raises(PublicationRefusedError, match="changed"):
        publish_bundle(bundle, receipt, published)


def test_publication_writes_exactly_the_declared_artifacts(tmp_path: Path) -> None:
    """The published set equals the declared set."""
    staging = tmp_path / "staging"
    published = tmp_path / "published"
    payload = staging / "libraries" / "api.jsonl"
    write_atomic(payload, b'{"a":1}\n')
    bundle = StagedBundle(
        staging_root=staging,
        expected_digests={"libraries/api.jsonl": digest_file(payload)},
    )
    written = publish_bundle(bundle, _receipt(), published)
    assert written == ("libraries/api.jsonl",)
    assert (published / "libraries" / "api.jsonl").read_bytes() == b'{"a":1}\n'


def test_completion_is_derived_from_counts_not_asserted() -> None:
    """A stage cannot assert success over inputs it did not process."""
    partial = build_receipt(
        ReceiptRequest(
            stage_id="mine-source",
            configuration={},
            enumerated_inputs=5,
            processed_inputs=4,
            unprocessed=(
                UnprocessedInput(input_id="x.rs", disposition="failed", reason="unreadable"),
            ),
        )
    )
    assert partial.completion is StageCompletion.PARTIAL
    assert not partial.authorizes_absence_claim()

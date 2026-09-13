"""Adversarial controls for transport completeness and bounded process execution."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from attrs import evolve
from library_guides.collection import CollectionError
from library_guides.facts.contracts import Budget
from library_guides.facts.protocol import Frames
from library_guides.store.digests import canonical_bytes
from library_guides.worker_runtime import WorkerLimitError, WorkerRequest, run


def _frame(value: object) -> bytes:
    payload = canonical_bytes(value)
    return len(payload).to_bytes(4, "big") + payload


def _stream() -> tuple[bytes, bytes, bytes]:
    header = _frame(
        {
            "kind": "header",
            "protocol": "library-guides.facts.v1",
            "header": {"request_id": "request", "input_digest": "input", "expected_records": 1},
        }
    )
    record = {"kind": "record", "sequence": 0, "record": {"id": "example", "value": "é"}}
    body = canonical_bytes(record)
    digest = hashlib.sha256(len(body).to_bytes(8, "big") + body).hexdigest()
    terminal = _frame(
        {"kind": "terminal", "records": 1, "digest": digest, "coverage": {"state": "complete"}}
    )
    return header, _frame(record), terminal


def test_fragmented_unicode_frames_commit_exact_records() -> None:
    """Byte splits through UTF-8 and prefixes never alter the declared evidence."""
    frames = Frames(Budget(), "request", "input")
    records = []
    for byte in b"".join(_stream()):
        records.extend(frames.feed(bytes([byte])))
    frames.finish()
    assert records == [{"id": "example", "value": "é"}]


@pytest.mark.parametrize(
    "mutation",
    [
        "truncated",
        "duplicate_header",
        "after_terminal",
        "wrong_input",
        "wrong_sequence",
        "empty_success",
        "wrong_digest",
    ],
)
def test_incomplete_or_mismatched_evidence_never_commits(mutation: str) -> None:
    """Success-looking streams cannot hide missing, stale or reordered evidence."""
    header, record, terminal = _stream()
    mutations = {
        "truncated": header + record + terminal[:-1],
        "duplicate_header": header + header + record + terminal,
        "after_terminal": header + record + terminal + record,
        "wrong_input": header.replace(b'"input"', b'"other"') + record + terminal,
        "wrong_sequence": header + record.replace(b'"sequence":0', b'"sequence":9') + terminal,
        "empty_success": header + terminal,
        "wrong_digest": header + record.replace(b'"example"', b'"changed"') + terminal,
    }
    frames = Frames(Budget(), "request", "input")
    with pytest.raises((CollectionError, ValueError)):
        _consume_complete(frames, mutations[mutation])


def test_oversized_frame_rejected_before_body_arrives() -> None:
    """An attacker cannot request an allocation by sending only a large prefix."""
    frames = Frames(evolve(Budget(), frame_bytes=64), "request", "input")
    with pytest.raises(CollectionError, match="oversized"):
        list(frames.feed((65).to_bytes(4, "big")))


def test_worker_zero_exit_without_receipt_is_failure(tmp_path: Path) -> None:
    """An inert executable is not a successful extractor."""
    request = WorkerRequest(
        argv=("/usr/bin/true",),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=Budget(),
    )
    with pytest.raises(CollectionError, match="incomplete"):
        run(request, lambda _: None)


def test_worker_deadline_stops_a_hanging_child(tmp_path: Path) -> None:
    """A stalled worker cannot keep the extraction operation pending indefinitely."""
    request = WorkerRequest(
        argv=("/usr/bin/sleep", "30"),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=evolve(Budget(), wall_seconds=1),
    )
    with pytest.raises(CollectionError, match="wall-time"):
        run(request, lambda _: None)


def _consume_complete(frames: Frames, data: bytes) -> None:
    list(frames.feed(data))
    frames.finish()


def test_closed_stdout_does_not_escape_the_deadline(tmp_path: Path) -> None:
    """The supervisor keeps monitoring a worker after it closes the output channel."""
    request = WorkerRequest(
        argv=(sys.executable, "-c", "import os,time; os.close(1); time.sleep(30)"),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=evolve(Budget(), wall_seconds=1),
    )
    with pytest.raises(WorkerLimitError, match="wall-time"):
        run(request, lambda _: None)


def test_resident_memory_budget_is_independent_of_virtual_mapping_ceiling(tmp_path: Path) -> None:
    """A worker may map libraries but cannot retain more resident memory than declared."""
    request = WorkerRequest(
        argv=(sys.executable, "-c", "import time; value=bytearray(96*1024*1024); time.sleep(30)"),
        cwd=tmp_path,
        request_id="request",
        input_digest="input",
        budget=evolve(Budget(), wall_seconds=5, memory_bytes=48 * 1024**2),
        address_space_bytes=512 * 1024**2,
    )
    with pytest.raises(WorkerLimitError, match="resident-memory"):
        run(request, lambda _: None)

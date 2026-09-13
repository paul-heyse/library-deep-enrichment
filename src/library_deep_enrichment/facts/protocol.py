"""Incremental, bounded validation of native fact frames."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from library_deep_enrichment.collection import CollectionError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.facts.contracts import Budget


_PREFIX_BYTES = 4


class Frames:
    """Validate ordering and exact transport digests without retaining the stream."""

    def __init__(self, budget: Budget, request: str, input_digest: str) -> None:
        """Bind one stream to the request and its immutable input."""
        self.budget = budget
        self.request = request
        self.input_digest = input_digest
        self.buffer = bytearray()
        self.total = 0
        self.count = 0
        self.digest = hashlib.sha256()
        self.header: dict[str, object] | None = None
        self.terminal: dict[str, object] | None = None

    def feed(self, data: bytes) -> Iterator[dict[str, object]]:
        """Consume bounded chunks and yield validated record frames.

        Yields:
            Owned record objects in producer order.

        Raises:
            CollectionError: If transport, identity or budget validation fails.

        """
        self.total += len(data)
        if self.total > self.budget.output_bytes:
            message = "worker output budget exceeded"
            raise CollectionError(message)
        self.buffer.extend(data)
        while len(self.buffer) >= _PREFIX_BYTES:
            size = int.from_bytes(self.buffer[:4], "big")
            if not 0 < size <= self.budget.frame_bytes:
                message = "invalid or oversized worker frame"
                raise CollectionError(message)
            if len(self.buffer) < size + 4:
                break
            payload = bytes(self.buffer[4 : size + 4])
            del self.buffer[: size + 4]
            frame = json.loads(
                payload, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
            )
            if not isinstance(frame, dict) or self.terminal is not None:
                message = "invalid frame or data after terminal"
                raise CollectionError(message)
            result = self._accept(frame, payload)
            if result is not None:
                yield result

    def _accept(self, frame: dict[str, object], payload: bytes) -> dict[str, object] | None:
        kind = frame.get("kind")
        fields = {
            "header": {"kind", "protocol", "header"},
            "record": {"kind", "sequence", "record"},
            "terminal": {"kind", "records", "digest", "coverage"},
        }
        if not isinstance(kind, str) or set(frame) != fields.get(kind):
            message = "unknown transport fields or frame kind"
            raise CollectionError(message)
        if self.header is None:
            self._handshake(frame)
        elif kind == "record":
            return self._record(frame, payload)
        elif kind == "terminal":
            self._commit(frame)
        else:
            message = "duplicate header or unsupported frame kind"
            raise CollectionError(message)
        return None

    def _handshake(self, frame: dict[str, object]) -> None:
        header = frame.get("header")
        if (
            frame.get("kind") != "header"
            or frame.get("protocol") != "library-guides.facts.v1"
            or not isinstance(header, dict)
        ):
            message = "missing or unsupported worker handshake"
            raise CollectionError(message)
        if (
            header.get("request_id") != self.request
            or header.get("input_digest") != self.input_digest
        ):
            message = "worker request/input identity mismatch"
            raise CollectionError(message)
        expected = header.get("expected_records")
        if type(expected) is not int or expected < 0:
            message = "worker denominator must be a nonnegative integer"
            raise CollectionError(message)
        self.header = header

    def _record(self, frame: dict[str, object], payload: bytes) -> dict[str, object]:
        record = frame.get("record")
        if (
            type(frame.get("sequence")) is not int
            or frame.get("sequence") != self.count
            or not isinstance(record, dict)
        ):
            message = "invalid record or sequence"
            raise CollectionError(message)
        self.count += 1
        if self.count > self.budget.max_records:
            message = "worker record budget exceeded"
            raise CollectionError(message)
        self.digest.update(len(payload).to_bytes(8, "big"))
        self.digest.update(payload)
        return record

    def _commit(self, frame: dict[str, object]) -> None:
        if (
            type(frame.get("records")) is not int
            or frame.get("records") != self.count
            or frame.get("digest") != self.digest.hexdigest()
        ):
            message = "terminal digest/count mismatch"
            raise CollectionError(message)
        if self.header is None or self.header.get("expected_records") != self.count:
            message = "enumerated/processed record mismatch"
            raise CollectionError(message)
        coverage = frame.get("coverage")
        if not isinstance(coverage, dict) or coverage.get("state") not in {
            "complete",
            "partial",
            "failed",
            "unsupported",
            "not_requested",
        }:
            message = "worker receipt requires an explicit scope outcome"
            raise CollectionError(message)
        if self.count == 0 and not coverage.get("empty_reason"):
            message = "empty extraction requires a retained explanation of its scope"
            raise CollectionError(message)
        self.terminal = frame

    def finish(self) -> None:
        """Reject truncation and successful exits without committed evidence.

        Raises:
            CollectionError: If the stream did not terminate cleanly.

        """
        if self.buffer or self.header is None or self.terminal is None:
            message = "incomplete worker stream"
            raise CollectionError(message)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        message = "duplicate JSON keys in worker protocol"
        raise CollectionError(message)
    return result


def _invalid_constant(value: str) -> object:
    message = f"non-finite JSON constant in worker protocol: {value}"
    raise CollectionError(message)

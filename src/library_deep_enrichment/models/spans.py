"""Evidence locations.

A source interval is an evidence location, not a concept identity. UTF-8 byte
offsets are preserved separately from rendered line numbers so that a correct
extraction over a file containing non-ASCII text cannot link an agent to the
wrong expression.
"""

from __future__ import annotations

from attrs import field, frozen

__all__ = ["CoordinateConvention", "EvidenceSpan", "LineRange", "byte_range_is_sane"]

CoordinateConvention = str
"""Name of the coordinate system an upstream tool reported, kept verbatim."""


def byte_range_is_sane(start: int, end: int) -> bool:
    """Return whether a byte range is non-negative and non-inverted.

    Returns:
        ``True`` when ``0 <= start <= end``.

    """
    return 0 <= start <= end


@frozen(kw_only=True)
class LineRange:
    """One-based inclusive display line range."""

    start_line: int = field()
    end_line: int = field()

    @start_line.validator
    def _check_start(self, _attribute: object, value: int) -> None:
        if value < 1:
            message = f"start_line must be one-based, got {value}"
            raise ValueError(message)

    @end_line.validator
    def _check_end(self, _attribute: object, value: int) -> None:
        if value < self.start_line:
            message = f"end_line {value} precedes start_line {self.start_line}"
            raise ValueError(message)


@frozen(kw_only=True)
class EvidenceSpan:
    """Where an observation was found inside one acquired artifact.

    ``byte_start``/``byte_end`` are UTF-8 offsets into the artifact whose digest
    is recorded on the owning record. ``line_range`` is a rendering convenience
    and is never the authority.
    """

    artifact_id: str = field()
    byte_start: int | None = field(default=None)
    byte_end: int | None = field(default=None)
    line_range: LineRange | None = field(default=None)
    enclosing_symbol: str | None = field(default=None)
    enclosing_heading_path: tuple[str, ...] = field(default=())
    extraction_method: str = field(default="unspecified")
    original_convention: CoordinateConvention = field(default="utf8_bytes")

    @byte_end.validator
    def _check_byte_range(self, _attribute: object, value: int | None) -> None:
        start = self.byte_start
        if value is None or start is None:
            return
        if not byte_range_is_sane(start, value):
            message = f"invalid byte range [{start}, {value}) in {self.artifact_id}"
            raise ValueError(message)

    def has_exact_location(self) -> bool:
        """Return whether this span carries an exact byte interval.

        Returns:
            ``True`` when both byte offsets are present.

        """
        return self.byte_start is not None and self.byte_end is not None

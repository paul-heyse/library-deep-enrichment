"""Receipt construction and the guarantees receipts carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.models.enums import StageCompletion
from library_guides.models.records import ExtractionReceipt, UnprocessedInput
from library_guides.store.digests import digest_mapping

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ["ReceiptRequest", "build_receipt", "configuration_digest", "merge_completion"]


def configuration_digest(configuration: Mapping[str, object]) -> str:
    """Return the semantic digest of a stage configuration.

    Returns:
        Lowercase hexadecimal digest.

    """
    return digest_mapping(configuration)


def merge_completion(parts: Sequence[StageCompletion]) -> StageCompletion:
    """Return the weakest completion state among ``parts``.

    A single failed or partial part makes the whole result non-authoritative for
    absence claims, so completion never improves by aggregation.

    Returns:
        ``FAILED`` if any part failed, ``PARTIAL`` if any part is partial, else
        ``COMPLETE``.

    """
    if any(part is StageCompletion.FAILED for part in parts):
        return StageCompletion.FAILED
    if any(part is StageCompletion.PARTIAL for part in parts):
        return StageCompletion.PARTIAL
    return StageCompletion.COMPLETE


@frozen(kw_only=True)
class ReceiptRequest:
    """Everything one stage observed about its own execution."""

    stage_id: str = field()
    configuration: Mapping[str, object] = field()
    enumerated_inputs: int = field()
    processed_inputs: int = field()
    unprocessed: tuple[UnprocessedInput, ...] = field(default=())
    output_digests: Mapping[str, str] = field(factory=dict)
    tool_identity: Mapping[str, str] = field(factory=dict)
    library_id: str | None = field(default=None)
    profile_id: str | None = field(default=None)
    failed: bool = field(default=False)

    def completion(self) -> StageCompletion:
        """Return the completion state implied by these counts.

        Returns:
            The derived completion state.

        """
        if self.failed:
            return StageCompletion.FAILED
        if self.unprocessed or self.processed_inputs != self.enumerated_inputs:
            return StageCompletion.PARTIAL
        return StageCompletion.COMPLETE


def build_receipt(request: ReceiptRequest) -> ExtractionReceipt:
    """Return a receipt whose completion state follows from its own counts.

    Completion is derived rather than supplied, so a stage cannot report success
    while leaving declared inputs unprocessed.

    Returns:
        The constructed receipt.

    """
    return ExtractionReceipt(
        stage_id=request.stage_id,
        library_id=request.library_id,
        profile_id=request.profile_id,
        tool_identity=tuple(sorted(request.tool_identity.items())),
        configuration_digest=configuration_digest(request.configuration),
        enumerated_inputs=request.enumerated_inputs,
        processed_inputs=request.processed_inputs,
        unprocessed=tuple(request.unprocessed),
        output_digests=tuple(sorted(request.output_digests.items())),
        completion=request.completion(),
    )

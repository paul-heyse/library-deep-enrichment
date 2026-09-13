"""Observed transport progress; unfinished worker computation remains unobserved."""

from __future__ import annotations

from attrs import define, frozen

from library_guides.collection import CollectionError


@frozen(kw_only=True)
class WorkerObservation:
    """A bounded supervisor snapshot, never a receipt admitting a partial product."""

    request: str
    input_digest: str
    elapsed_seconds: float
    peak_sampled_tree_rss_bytes: int
    rss_samples: int
    output_bytes: int
    delivered_records: int
    consumed_records: int
    expected_records: tuple[int, ...]
    terminal_seen: bool
    returncode: int
    rss_limit_bytes: int
    address_space_limit_bytes: int
    internal_progress: str = "unobserved"


@define(kw_only=True)
class WorkerProgress:
    """Mutable supervisor counters retained even when draining raises an exception."""

    started: float
    peak_rss: int = 0
    rss_samples: int = 0
    delivered_records: int = 0
    consumed_records: int = 0


class ObservedWorkerFailureError(CollectionError):
    """A typed cause preserving observations without replacing the original exception."""

    def __init__(self, observation: WorkerObservation) -> None:
        """Retain the observed prefix and cleanup outcome as diagnostic evidence."""
        self.observation = observation
        super().__init__("supervisor retained worker failure observations")


def failure_observations(error: BaseException) -> tuple[WorkerObservation, ...]:
    """Read bounded typed causes through exception translation.

    Returns:
        At most one supervisor snapshot; no snapshot means unobserved execution.

    """
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ObservedWorkerFailureError):
            return (current.observation,)
        current = current.__cause__
    return ()

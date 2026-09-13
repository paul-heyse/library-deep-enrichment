"""Typed, allocation-time projection limits, separate from malformed source evidence."""

from library_deep_enrichment.corpus.backend import BudgetExceededError


class ProjectionBudgetError(BudgetExceededError):
    """A selected owner's projection exceeded one independent finite output bound."""

    def __init__(self, dimension: str, attempted: int, limit: int) -> None:
        """Retain actual attempted projection size for an attributed owner outcome."""
        self.dimension = dimension
        self.attempted = attempted
        self.limit = limit
        super().__init__(f"behavior projection {dimension} budget exhausted: {attempted} > {limit}")


def bound(dimension: str, attempted: int, limit: int) -> None:
    """Check before growing an owned graph collection.

    Raises:
        ProjectionBudgetError: The requested next size exceeds the declared owner bound.

    """
    if attempted > limit:
        raise ProjectionBudgetError(dimension, attempted, limit)

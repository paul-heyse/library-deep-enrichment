"""Semantic invalidation and review queues including new competing candidates."""

from __future__ import annotations

from pathlib import Path

from library_guides.evidence_graph import EvidenceGraph
from library_guides.knowledge import Knowledge


def compare(
    before_root: Path, before: Knowledge, after_root: Path, after: Knowledge
) -> dict[str, object]:
    """Return changed subjects and stale reviews from exact dependency fingerprints.

    Returns:
        Added, removed and changed subjects plus stale review identifiers.

    """
    left, right = EvidenceGraph(before_root, before), EvidenceGraph(after_root, after)
    shared = left.owners.keys() & right.owners.keys()
    changed = [key for key in sorted(shared) if left.fingerprint(key) != right.fingerprint(key)]
    return {
        "added": sorted(right.owners.keys() - left.owners.keys()),
        "removed": sorted(left.owners.keys() - right.owners.keys()),
        "changed": changed,
        "review_queue": [
            review.subject
            for review in after.reviews
            if review.subject not in right.owners
            or review.digest != right.fingerprint(review.subject)
        ],
    }

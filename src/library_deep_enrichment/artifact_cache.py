"""Verified content-addressed reuse for independent compiler products."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from filelock import FileLock

from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file
from library_deep_enrichment.store.staging import write_atomic


def implementation_digest() -> str:
    """Identify compiler code and shipped policy assets independently of collection inputs.

    Returns:
        A digest of all implementation and policy bytes.

    """
    package = Path(__file__).parent
    return digest_bytes(
        canonical_bytes(
            {
                path.relative_to(package).as_posix(): digest_file(path)
                for path in sorted(package.rglob("*"))
                if path.is_file() and "__pycache__" not in path.parts
            }
        )
    )


class ArtifactCache:
    """Reuse only bytes whose stage, input key and output digest all agree."""

    def __init__(self, root: Path) -> None:
        """Bind a local cache and per-build disposition counters."""
        self.root = root
        self.compiler = implementation_digest()
        self.counts: Counter[str] = Counter()

    def key(self, material: object) -> str:
        """Bind a stage's semantic inputs to this exact implementation.

        Returns:
            The content-derived stage input key.

        """
        return digest_bytes(canonical_bytes({"compiler": self.compiler, "inputs": material}))

    def restore(self, stage: str, key: str, destination: Path) -> bool:
        """Restore a verified product, treating damaged cache entries as misses.

        Returns:
            Whether the exact verified artifact was reused.

        """
        entry = self.root / stage / key
        try:
            receipt = json.loads((entry / "receipt.json").read_bytes())
            body = (entry / "artifact").read_bytes()
            valid = receipt == {"stage": stage, "key": key, "digest": digest_bytes(body)}
        except OSError, ValueError:
            valid = False
            body = b""
        if valid:
            write_atomic(destination, body)
            self.counts[stage + ":reused"] += 1
        return valid

    def retain(self, stage: str, key: str, product: Path) -> None:
        """Store a completed product under an exclusive entry lock."""
        entry = self.root / stage / key
        entry.mkdir(parents=True, exist_ok=True)
        with FileLock(str(entry / "write.lock"), timeout=60):
            body = product.read_bytes()
            write_atomic(entry / "artifact", body)
            write_atomic(
                entry / "receipt.json",
                canonical_bytes({"stage": stage, "key": key, "digest": digest_bytes(body)}),
            )
        self.counts[stage + ":executed"] += 1

"""Atomic staging and publication of build outputs.

A failed or partial stage must never replace a previous complete inventory with
an apparently successful empty one. Outputs are therefore written into a staging
directory and promoted only when the owning receipt authorises it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.models.enums import StageCompletion
from library_guides.store.digests import digest_file

if TYPE_CHECKING:
    from collections.abc import Mapping

    from library_guides.models.records import ExtractionReceipt

__all__ = ["PublicationRefusedError", "StagedBundle", "publish_bundle", "write_atomic"]


class PublicationRefusedError(RuntimeError):
    """Raised when a bundle may not overwrite the published tree."""


@frozen(kw_only=True)
class StagedBundle:
    """One staging directory and the digests it is expected to publish."""

    staging_root: Path = field()
    expected_digests: Mapping[str, str] = field()

    def observed_digests(self) -> dict[str, str]:
        """Return the digest of every file currently staged.

        Returns:
            Mapping of repository-relative POSIX path to hexadecimal digest.

        """
        observed: dict[str, str] = {}
        for path in sorted(self.staging_root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(self.staging_root).as_posix()
                observed[relative] = digest_file(path)
        return observed


def write_atomic(path: Path, payload: bytes) -> None:
    """Write ``payload`` to ``path`` through a same-directory temporary file.

    Args:
        path: Destination file; parent directories are created.
        payload: Bytes to write.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_name = tempfile.mkstemp(dir=path.parent)
    temporary = Path(raw_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    sync_directory(path.parent)


def sync_directory(path: Path) -> None:
    """Persist an atomic directory entry update on the local filesystem."""
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bundle(
    bundle: StagedBundle,
    receipt: ExtractionReceipt,
    destination: Path,
) -> tuple[str, ...]:
    """Promote a staged bundle into the published tree.

    Args:
        bundle: Staged outputs and the digests the build declared.
        receipt: Receipt for the stage that produced the bundle.
        destination: Published root.

    Returns:
        Repository-relative POSIX paths that were written.

    Raises:
        PublicationRefusedError: When the stage failed, or when the staged bytes do
            not match the digests the build declared.

    """
    if receipt.completion is not StageCompletion.COMPLETE:
        message = f"stage {receipt.stage_id} is {receipt.completion}; refusing to publish"
        raise PublicationRefusedError(message)
    observed = bundle.observed_digests()
    if len(observed) != 1:
        message = "legacy publication supports one artifact only; use immutable v2 generations for bundles"
        raise PublicationRefusedError(message)
    if observed != dict(bundle.expected_digests):
        missing = sorted(set(bundle.expected_digests) - set(observed))
        unexpected = sorted(set(observed) - set(bundle.expected_digests))
        changed = sorted(
            name
            for name, digest in observed.items()
            if name in bundle.expected_digests and bundle.expected_digests[name] != digest
        )
        message = (
            f"staged bundle does not match the declared outputs: "
            f"missing={missing} unexpected={unexpected} changed={changed}"
        )
        raise PublicationRefusedError(message)
    written: list[str] = []
    for relative in sorted(observed):
        source = bundle.staging_root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, source.read_bytes())
        written.append(relative)
    return tuple(written)

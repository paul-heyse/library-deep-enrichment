"""Run a library's declared registry probes and record what they reported."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_deep_enrichment import registry_adapters
from library_deep_enrichment.models.records import SurfaceEntry, UnprocessedInput
from library_deep_enrichment.stages.paths import surfaces_path
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.store.jsonl import write_records
from library_deep_enrichment.store.receipts import ReceiptRequest, build_receipt

if TYPE_CHECKING:
    from pathlib import Path

    from library_deep_enrichment.manifest import LibraryManifest, Profile
    from library_deep_enrichment.models.records import ExtractionReceipt

__all__ = ["RegistryProbeRun", "run_registry_probes"]

_STAGE_ID = "probe-registry"


@frozen(kw_only=True)
class RegistryProbeRun:
    """What one library's registry probes reported."""

    library_id: str = field()
    profile_id: str = field()
    entries: tuple[SurfaceEntry, ...] = field()
    details: tuple[str, ...] = field()
    receipt: ExtractionReceipt = field()

    def summary(self) -> str:
        """Describe the probe run in one line.

        Returns:
            A short human-readable summary.

        """
        return (
            f"{self.library_id}/{self.profile_id}: {len(self.entries):,} registered surfaces "
            f"from {len(self.details)} probe(s), completion={self.receipt.completion}"
        )


def _surface_sort_key(entry: SurfaceEntry) -> tuple[str, str, str, str]:
    return entry.identity.sort_key()


def run_registry_probes(
    manifest: LibraryManifest,
    profile: Profile,
    *,
    repository_root: Path,
) -> RegistryProbeRun:
    """Run every probe the library declares and write the surface inventory.

    Args:
        manifest: Library manifest.
        profile: Profile the observations are evidence for.
        repository_root: Repository root.

    Returns:
        The probe run, including its receipt.

    """
    entries: list[SurfaceEntry] = []
    details: list[str] = []
    failed: list[str] = []
    for probe_id in manifest.registry_probes:
        try:
            probe = registry_adapters.probe_by_id(probe_id)
            result = probe(library_id=manifest.library_id, profile_id=profile.profile_id)
        except (LookupError, ImportError, RuntimeError, ValueError) as error:
            failed.append(f"{probe_id}: {type(error).__name__}: {error}")
            continue
        entries.extend(result.entries)
        details.append(result.detail)

    destination = surfaces_path(
        manifest.library_id, profile.profile_id, repository_root=repository_root
    )
    ordered = tuple(sorted(entries, key=_surface_sort_key))
    if not failed:
        write_records(destination, ordered)

    receipt = build_receipt(
        ReceiptRequest(
            stage_id=_STAGE_ID,
            library_id=manifest.library_id,
            profile_id=profile.profile_id,
            configuration={"probes": list(manifest.registry_probes)},
            enumerated_inputs=len(manifest.registry_probes),
            processed_inputs=len(manifest.registry_probes) - len(failed),
            unprocessed=tuple(
                UnprocessedInput(input_id=item.split(":")[0], disposition="failed", reason=item)
                for item in failed
            ),
            output_digests={destination.name: digest_file(destination)} if not failed else {},
            tool_identity={"probe_count": str(len(manifest.registry_probes))},
        )
    )
    return RegistryProbeRun(
        library_id=manifest.library_id,
        profile_id=profile.profile_id,
        entries=ordered,
        details=tuple(details),
        receipt=receipt,
    )

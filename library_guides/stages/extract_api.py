"""Build one library profile's public API inventory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.adapters.acquire import fetch_cached
from library_guides.adapters.python.dist_metadata import read_locked_distributions
from library_guides.adapters.python.griffe_api import load_python_api
from library_guides.adapters.rust.cargo_metadata import (
    read_locked_packages,
    read_workspace_dependencies,
)
from library_guides.adapters.rust.rustdoc_json import (
    UnsupportedRustdocFormatError,
    decompress_docs_rs_payload,
    docs_rs_json_url,
    parse_rustdoc_json,
)
from library_guides.models.enums import Ecosystem, ResolutionState
from library_guides.models.records import SourceArtifact, UnprocessedInput
from library_guides.stages.paths import api_path
from library_guides.store.digests import digest_file
from library_guides.store.jsonl import write_records
from library_guides.store.receipts import ReceiptRequest, build_receipt
from library_guides.validate.authored import AuthoredRecordError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from library_guides.adapters.rust.cargo_metadata import CargoDependency
    from library_guides.manifest import LibraryManifest, Profile
    from library_guides.models.records import ApiBinding, ExtractionReceipt

__all__ = ["ApiExtraction", "extract_api"]

_STAGE_ID = "extract-api"


@frozen(kw_only=True)
class ApiExtraction:
    """One profile's inventory, its excluded items, and its receipt."""

    library_id: str = field()
    profile_id: str = field()
    resolved_version: str | None = field()
    included: tuple[ApiBinding, ...] = field()
    excluded_packages: tuple[tuple[str, int], ...] = field()
    receipt: ExtractionReceipt = field()
    source: SourceArtifact | None = field(default=None)

    def summary(self) -> str:
        """Describe the extraction in one line.

        Returns:
            A short human-readable summary.

        """
        excluded = sum(count for _, count in self.excluded_packages)
        return (
            f"{self.library_id}/{self.profile_id}: {len(self.included):,} in-surface bindings, "
            f"{excluded:,} excluded as out-of-surface, completion={self.receipt.completion}"
        )


def _binding_sort_key(binding: ApiBinding) -> tuple[str, str, str, str, str]:
    return binding.identity.sort_key()


def _by_descending_count(item: tuple[str, int]) -> int:
    return -item[1]


def _resolved_version(
    profile: Profile,
    *,
    repository_root: Path,
) -> str | None:
    """Return the version this profile describes.

    Lock resolution is preferred. A dependency that is *declared* but that no
    member actually uses never reaches the lock, so an exact declaration is the
    fallback - it is a weaker fact than a lock entry, but a real one.

    Returns:
        The version, or ``None`` when neither source establishes one.

    """
    if profile.version_source == "cargo_workspace_dependency":
        locked = read_locked_packages(repository_root / "Cargo.lock").get(profile.version_key)
        if locked is not None:
            return locked
        declared = read_workspace_dependencies(repository_root / "Cargo.toml").get(
            profile.version_key
        )
        return declared.exact_version() if declared else None
    distribution = read_locked_distributions(repository_root / "uv.lock").get(profile.version_key)
    return distribution.version if distribution else None


def extract_api(
    manifest: LibraryManifest,
    profile: Profile,
    *,
    repository_root: Path,
    cache_root: Path,
) -> ApiExtraction:
    """Extract one profile's public API inventory and write it to the content tree.

    Args:
        manifest: Library manifest.
        profile: Profile to extract.
        repository_root: Repository root.
        cache_root: Directory for acquired payloads.

    Returns:
        The extraction, including its receipt.

    Raises:
        AuthoredRecordError: When the profile's version cannot be resolved.

    """
    version = _resolved_version(profile, repository_root=repository_root)
    if version is None:
        message = (
            f"library {manifest.library_id}: cannot resolve a version for "
            f"{profile.version_key!r} via {profile.version_source}"
        )
        raise AuthoredRecordError(message)

    if manifest.ecosystem == Ecosystem.RUST:
        bindings, source, unprocessed, tool = _extract_rust(
            manifest, profile, version=version, cache_root=cache_root
        )
    else:
        bindings, source, unprocessed, tool = _extract_python(manifest, profile, version=version)

    included = tuple(
        binding for binding in bindings if manifest.owns_package(binding.identity.package)
    )
    excluded: dict[str, int] = {}
    for binding in bindings:
        if not manifest.owns_package(binding.identity.package):
            excluded[binding.identity.package] = excluded.get(binding.identity.package, 0) + 1

    destination = api_path(manifest.library_id, profile.profile_id, repository_root=repository_root)
    if not unprocessed:
        write_records(destination, included)

    receipt = build_receipt(
        ReceiptRequest(
            stage_id=_STAGE_ID,
            library_id=manifest.library_id,
            profile_id=profile.profile_id,
            configuration={
                "api_source": profile.api_source.kind,
                "target": profile.api_source.target,
                "version": version,
                "surface_packages": list(manifest.surface_packages),
            },
            enumerated_inputs=len(bindings),
            processed_inputs=len(bindings) - len(unprocessed),
            unprocessed=unprocessed,
            output_digests={destination.name: digest_file(destination)} if not unprocessed else {},
            tool_identity=tool,
        )
    )
    return ApiExtraction(
        library_id=manifest.library_id,
        profile_id=profile.profile_id,
        resolved_version=version,
        included=included,
        excluded_packages=tuple(sorted(excluded.items(), key=_by_descending_count)),
        receipt=receipt,
        source=source,
    )


def _extract_rust(
    manifest: LibraryManifest,
    profile: Profile,
    *,
    version: str,
    cache_root: Path,
) -> tuple[
    tuple[ApiBinding, ...], SourceArtifact | None, tuple[UnprocessedInput, ...], dict[str, str]
]:
    """Acquire and normalize every crate this profile covers.

    A crate family is only fully inventoried by acquiring each member: the
    umbrella crate's documentation names its dependencies' items without
    describing their surface.

    Returns:
        Bindings, the primary source artifact, unprocessed inputs, and tool identity.

    """
    locked = read_locked_packages(Path.cwd() / "Cargo.lock")
    declared = read_workspace_dependencies(Path.cwd() / "Cargo.toml")
    bindings: list[ApiBinding] = []
    unprocessed: list[UnprocessedInput] = []
    formats: set[str] = set()
    primary: SourceArtifact | None = None
    acquired = 0

    for crate in profile.api_source.all_targets():
        crate_version = locked.get(crate) or _declared_exact(declared, crate) or version
        url = docs_rs_json_url(crate, crate_version)
        result = fetch_cached(
            url, cache_root=cache_root, cache_name=f"{crate}-{crate_version}.json.zst"
        )
        if result.payload is None:
            unprocessed.append(
                UnprocessedInput(
                    input_id=url,
                    disposition=result.outcome,
                    reason=result.detail or "no payload",
                )
            )
            continue
        try:
            model = parse_rustdoc_json(
                decompress_docs_rs_payload(result.payload),
                library_id=manifest.library_id,
                profile_id=profile.profile_id,
                package=crate,
            )
        except UnsupportedRustdocFormatError as error:
            unprocessed.append(
                UnprocessedInput(input_id=url, disposition="failed", reason=str(error))
            )
            continue
        acquired += 1
        formats.add(str(model.format_version))
        bindings.extend(model.bindings)
        unprocessed.extend(
            UnprocessedInput(
                input_id=f"{crate}:{item_id}",
                disposition="unresolved",
                reason="no path recorded",
            )
            for item_id in model.unresolved_item_ids
        )
        if primary is None:
            primary = SourceArtifact(
                artifact_id=f"docsrs:{crate}:{crate_version}",
                library_id=manifest.library_id,
                package=crate,
                ecosystem=Ecosystem.RUST,
                upstream_locator=url,
                content_digest=result.content_digest or "",
                artifact_kind="rustdoc_json",
                acquisition_result=result.outcome,
                build_scope=(profile.scope,),
            )

    tool = {
        "source": "docs.rs",
        "crates_declared": str(len(profile.api_source.all_targets())),
        "crates_acquired": str(acquired),
        "rustdoc_format_versions": ",".join(sorted(formats)),
    }
    return _deduplicate(bindings), primary, tuple(unprocessed), tool


def _declared_exact(declared: Mapping[str, CargoDependency], crate: str) -> str | None:
    dependency = declared.get(crate)
    return dependency.exact_version() if dependency else None


def _deduplicate(bindings: Sequence[ApiBinding]) -> tuple[ApiBinding, ...]:
    """Keep the strongest record per identity across overlapping crate documents.

    The same item appears in several crates' documents - once as a local
    definition and repeatedly as a referenced dependency. The local definition is
    the authoritative one, so a resolved record always displaces a candidate.

    Returns:
        One binding per public path, in sorted order.

    """
    best: dict[str, ApiBinding] = {}
    for binding in bindings:
        key = binding.identity.public_path
        current = best.get(key)
        if current is None or (
            current.resolution_state is not ResolutionState.RESOLVED
            and binding.resolution_state is ResolutionState.RESOLVED
        ):
            best[key] = binding
    return tuple(sorted(best.values(), key=_binding_sort_key))


def _extract_python(
    manifest: LibraryManifest,
    profile: Profile,
    *,
    version: str,
) -> tuple[
    tuple[ApiBinding, ...], SourceArtifact | None, tuple[UnprocessedInput, ...], dict[str, str]
]:
    module = profile.api_source.target
    model = load_python_api(
        module,
        library_id=manifest.library_id,
        profile_id=profile.profile_id,
        package=manifest.packages[0].name,
    )
    source = SourceArtifact(
        artifact_id=f"installed:{module}:{version}",
        library_id=manifest.library_id,
        package=manifest.packages[0].name,
        ecosystem=Ecosystem.PYTHON,
        upstream_locator=f"python://{module}",
        content_digest="",
        artifact_kind="installed_distribution",
        acquisition_result="reused_environment",
        build_scope=(profile.scope,),
    )
    unprocessed = tuple(
        UnprocessedInput(input_id=path, disposition="failed", reason="member could not be read")
        for path in model.failed_members
    )
    tool = {"extractor": "griffe", "static_only": "true"}
    return model.bindings, source, unprocessed, tool

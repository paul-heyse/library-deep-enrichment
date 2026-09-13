"""Normalize rustdoc JSON into public API bindings.

``format_version`` is validated before anything is read. Rustdoc JSON is an
unstable interface, so an unrecognized version is a hard stop rather than a
best-effort parse that would silently mis-describe an API.

Rustdoc item identifiers are opaque and build-specific; they are used only to
join within one document and never recorded as durable identities.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_guides.models.enums import Ecosystem, EvidenceOrigin, ResolutionState
from library_guides.models.ids import ApiIdentity
from library_guides.models.records import ApiBinding

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "SUPPORTED_FORMAT_VERSIONS",
    "RustdocModel",
    "UnsupportedRustdocFormatError",
    "decompress_docs_rs_payload",
    "docs_rs_json_url",
    "parse_rustdoc_json",
]

SUPPORTED_FORMAT_VERSIONS: Final = frozenset({59, 60, 61})
"""Rustdoc JSON schema versions this adapter has been checked against."""

_PUBLIC_VISIBILITY: Final = frozenset({"public", "default"})


class UnsupportedRustdocFormatError(ValueError):
    """Raised when rustdoc JSON declares a schema version we have not verified."""


def docs_rs_json_url(crate: str, version: str) -> str:
    """Return the hosted rustdoc JSON URL for one crate release.

    Returns:
        The docs.rs JSON endpoint.

    """
    return f"https://docs.rs/crate/{crate}/{version}/json"


def decompress_docs_rs_payload(payload: bytes) -> bytes:
    """Return the decompressed rustdoc JSON document.

    Args:
        payload: Raw bytes as served by docs.rs, which are zstd-compressed.

    Returns:
        The decompressed JSON bytes.

    """
    from compression import zstd

    return zstd.decompress(payload)


@frozen(kw_only=True)
class RustdocModel:
    """One parsed rustdoc document and the gaps encountered reading it."""

    crate_name: str = field()
    crate_version: str | None = field()
    format_version: int = field()
    bindings: tuple[ApiBinding, ...] = field()
    foreign_path_count: int = field(default=0)
    unresolved_item_ids: tuple[str, ...] = field(default=())

    def gap_summary(self) -> str:
        """Describe what this model could not resolve.

        Returns:
            A short human-readable summary.

        """
        return (
            f"{self.foreign_path_count} items defined in dependency crates "
            f"(recorded at their defining path as candidates), "
            f"{len(self.unresolved_item_ids)} unresolved item ids"
        )


def _visibility_is_public(item: Mapping[str, object]) -> bool:
    visibility = item.get("visibility")
    if isinstance(visibility, str):
        return visibility in _PUBLIC_VISIBILITY
    # A restricted visibility is expressed as a mapping and is not public API.
    return False


def _item_kind(item: Mapping[str, object]) -> str:
    inner = item.get("inner")
    if isinstance(inner, dict) and inner:
        return next(iter(inner))
    return "unknown"


def parse_rustdoc_json(
    payload: bytes,
    *,
    library_id: str,
    profile_id: str,
    package: str,
) -> RustdocModel:
    """Return the public API bindings a rustdoc document describes.

    ``package`` is normalized to the Rust crate-path spelling, so a Cargo name
    such as ``arrow-schema`` and the path prefix ``arrow_schema`` are one
    identity rather than two that silently fail to match each other.

    Args:
        payload: Decompressed rustdoc JSON bytes.
        library_id: Owning library identifier.
        profile_id: Profile the model is evidence for.
        package: Cargo package name.

    Returns:
        The parsed model, including its own extraction gaps.

    Raises:
        UnsupportedRustdocFormatError: When the document declares a schema
            version this adapter has not been verified against.

    """
    document = json.loads(payload)
    format_version = document.get("format_version")
    if not isinstance(format_version, int) or format_version not in SUPPORTED_FORMAT_VERSIONS:
        supported = ", ".join(str(value) for value in sorted(SUPPORTED_FORMAT_VERSIONS))
        message = (
            f"rustdoc format_version {format_version!r} is not supported "
            f"(verified: {supported}); refusing to parse"
        )
        raise UnsupportedRustdocFormatError(message)

    package = package.replace("-", "_")
    index = document.get("index") or {}
    paths = document.get("paths") or {}
    root_id = document.get("root")
    crate_name = _crate_name(paths, root_id, package)

    bindings, unresolved, foreign = _collect_bindings(
        _CollectRequest(
            index=index,
            paths=paths,
            external_crates=_external_crate_names(document.get("external_crates")),
            library_id=library_id,
            profile_id=profile_id,
            package=package,
        )
    )

    return RustdocModel(
        crate_name=crate_name,
        crate_version=_optional_str(document.get("crate_version")),
        format_version=format_version,
        bindings=bindings,
        foreign_path_count=foreign,
        unresolved_item_ids=tuple(sorted(unresolved)),
    )


@frozen(kw_only=True)
class _CollectRequest:
    """Inputs for one rustdoc collection pass."""

    index: Mapping[str, object] = field()
    paths: Mapping[str, object] = field()
    external_crates: Mapping[str, str] = field()
    library_id: str = field()
    profile_id: str = field()
    package: str = field()


def _binding_for(
    request: _CollectRequest,
    item_id: str,
    entry: Mapping[str, object],
) -> ApiBinding | None:
    """Return the binding for one rustdoc path entry.

    An item defined in this crate resolves to the path an author writes. An item
    defined in a dependency is recorded at its *defining* path and left as a
    candidate: this document establishes that the item exists and is referenced,
    not that it is re-exported under this crate's namespace.

    Returns:
        The binding, or ``None`` when the entry carries no usable path.

    """
    path_parts = entry.get("path")
    if not isinstance(path_parts, list) or not path_parts:
        return None
    crate_ordinal = entry.get("crate_id")
    is_local = crate_ordinal == 0
    item = request.index.get(item_id) if is_local else None
    signature: str | None = None
    docs: tuple[str, ...] = ()
    if isinstance(item, dict):
        if not _visibility_is_public(item):
            return None
        docstring = item.get("docs")
        if isinstance(docstring, str) and docstring:
            docs = (docstring.strip().splitlines()[0],)
        signature = _item_kind(item)
    package = (
        request.package
        if is_local
        else request.external_crates.get(str(crate_ordinal), str(path_parts[0]))
    )
    return ApiBinding(
        library_id=request.library_id,
        profile_id=request.profile_id,
        identity=ApiIdentity(
            ecosystem=Ecosystem.RUST,
            package=package,
            public_path="::".join(str(part) for part in path_parts),
            item_kind=str(entry.get("kind", "unknown")),
        ),
        signature=signature,
        documentation_refs=docs,
        availability_conditions=() if is_local else (f"defined in `{package}`",),
        evidence_origin=EvidenceOrigin.COMPILER_API,
        resolution_state=ResolutionState.RESOLVED if is_local else ResolutionState.CANDIDATE,
    )


def _collect_bindings(
    request: _CollectRequest,
) -> tuple[tuple[ApiBinding, ...], tuple[str, ...], int]:
    paths = request.paths
    bindings: list[ApiBinding] = []
    unresolved: list[str] = []
    foreign = 0
    for item_id, entry in paths.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("crate_id") != 0:
            foreign += 1
        binding = _binding_for(request, item_id, entry)
        if binding is None:
            if not isinstance(entry.get("path"), list) or not entry.get("path"):
                unresolved.append(item_id)
            continue
        bindings.append(binding)
    ordered = tuple(sorted(bindings, key=_binding_sort_key))
    return ordered, tuple(sorted(unresolved)), foreign


def _binding_sort_key(binding: ApiBinding) -> tuple[str, str, str, str, str]:
    return binding.identity.sort_key()


def _external_crate_names(value: object) -> Mapping[str, str]:
    if not isinstance(value, dict):
        return {}
    names: dict[str, str] = {}
    for ordinal, entry in value.items():
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            names[str(ordinal)] = entry["name"]
    return names


def _crate_name(paths: Mapping[str, object], root_id: object, fallback: str) -> str:
    root = paths.get(str(root_id)) if root_id is not None else None
    if isinstance(root, dict):
        parts = root.get("path")
        if isinstance(parts, list) and parts:
            return str(parts[0])
    return fallback


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None

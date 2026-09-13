"""Stack build manifests.

A stack manifest declares which documents a guide is built from, which version
anchors it reports, which consumer files carry generated blocks, and which files
must remain byte-identical mirrors. Adding a library or stack is a manifest
change; no module in this package names one.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Final

import yaml
from attrs import field, frozen

from library_deep_enrichment.validate.authored import (
    AuthoredRecordError,
    require_mapping,
    require_sequence,
    require_str,
    require_str_sequence,
    require_value_in,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "BLOCK_NAMES",
    "ApiSource",
    "ConsumerTarget",
    "DocumentEntry",
    "LibraryManifest",
    "MirrorGroup",
    "PackageEntry",
    "Profile",
    "StackManifest",
    "VersionAnchor",
    "known_stack_ids",
    "load_library_manifest",
    "load_stack_manifest",
    "manifest_root",
    "stack_manifest_path",
]

SCHEMA_VERSION: Final = "library-guides.stack_manifest.v1"

BLOCK_NAMES: Final = frozenset(
    {
        "api-families",
        "decision-briefs",
        "decision-index",
        "document-inventory",
        "section-index",
        "version-anchors",
    }
)

_ECOSYSTEMS: Final = frozenset({"rust", "python"})
_DOCUMENT_ROLES: Final = frozenset({"secondary_research", "upstream_reference", "generated"})
_ANCHOR_SOURCES: Final = frozenset(
    {
        "cargo_workspace_dependency",
        "python_locked_distribution",
    }
)


@frozen(kw_only=True)
class DocumentEntry:
    """One long-form document a stack routes into.

    ``chapter_pattern`` says which headings are chapters worth indexing, so the
    renderer never needs to know how a particular corpus numbers its sections.
    Its first capture group is the chapter key; front matter that does not match
    is left out of the generated index.
    """

    doc_id: str = field()
    path: str = field()
    role: str = field()
    scope: str = field()
    chapter_levels: tuple[int, ...] = field(default=(1,))
    chapter_pattern: str | None = field(default=None)
    deep_dive_prefix: str = field(default="")

    def chapter_key(self, heading_text: str) -> str | None:
        """Return the chapter key ``heading_text`` declares, when it is a chapter.

        Returns:
            The first capture group, or ``None`` when the heading is not a
            chapter under this document's declared pattern.

        """
        if self.chapter_pattern is None:
            return heading_text
        match = re.match(self.chapter_pattern, heading_text)
        if match is None:
            return None
        return match.group(1) if match.groups() else heading_text


@frozen(kw_only=True)
class VersionAnchor:
    """One version fact the guide reports, and where it is read from."""

    anchor_id: str = field()
    source: str = field()
    key: str = field()


@frozen(kw_only=True)
class ConsumerTarget:
    """One file that carries generated blocks."""

    path: str = field()
    blocks: tuple[str, ...] = field()


@frozen(kw_only=True)
class MirrorGroup:
    """One authoritative file and the copies that must match it byte for byte."""

    authoritative: str = field()
    mirrors: tuple[str, ...] = field()


@frozen(kw_only=True)
class StackManifest:
    """Everything the build needs to render one stack's consumer files."""

    stack_id: str = field()
    title: str = field()
    ecosystem: str = field()
    documents: tuple[DocumentEntry, ...] = field()
    version_anchors: tuple[VersionAnchor, ...] = field()
    consumers: tuple[ConsumerTarget, ...] = field()
    libraries: tuple[str, ...] = field(default=())
    mirror_groups: tuple[MirrorGroup, ...] = field(default=())

    def document(self, doc_id: str) -> DocumentEntry:
        """Return the document entry with ``doc_id``.

        Returns:
            The matching entry.

        Raises:
            AuthoredRecordError: When no document carries that identifier.

        """
        for entry in self.documents:
            if entry.doc_id == doc_id:
                return entry
        message = f"stack {self.stack_id}: no document {doc_id!r}"
        raise AuthoredRecordError(message)

    def consumers_for(self, block_name: str) -> tuple[ConsumerTarget, ...]:
        """Return every consumer that carries ``block_name``.

        Returns:
            Consumer targets in declaration order.

        """
        return tuple(target for target in self.consumers if block_name in target.blocks)


def manifest_root() -> Path:
    """Return the directory holding the checked-in build manifests.

    Returns:
        Path to ``tooling/library_deep_enrichment/manifests``.

    """
    return Path(__file__).resolve().parent / "assets" / "manifests"


def known_stack_ids(*, root: Path | None = None) -> tuple[str, ...]:
    """Return every stack that has a checked-in build manifest.

    Discovering stacks from the manifest directory is what keeps a library name
    out of the command line and the retrieval layer.

    Returns:
        Stack identifiers in sorted order.

    """
    base = (root if root is not None else manifest_root()) / "stacks"
    if not base.is_dir():
        return ()
    return tuple(sorted(path.stem for path in base.glob("*.yaml")))


def stack_manifest_path(stack_id: str) -> Path:
    """Return the manifest path for ``stack_id``.

    Returns:
        Path to the stack manifest file.

    """
    return manifest_root() / "stacks" / f"{stack_id}.yaml"


def _optional_levels(mapping: Mapping[str, object], key: str, *, context: str) -> tuple[int, ...]:
    if key not in mapping:
        return (1,)
    value = mapping[key]
    if not isinstance(value, list) or not value:
        message = f"{context}: field {key!r} must be a non-empty list of heading levels"
        raise AuthoredRecordError(message)
    levels: list[int] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, int) or isinstance(entry, bool):
            message = f"{context}: {key}[{index}] must be an integer heading level"
            raise AuthoredRecordError(message)
        levels.append(entry)
    return tuple(levels)


def _optional_str(mapping: Mapping[str, object], key: str, *, context: str) -> str:
    if key not in mapping:
        return ""
    value = mapping[key]
    if not isinstance(value, str):
        message = f"{context}: field {key!r} must be a string"
        raise AuthoredRecordError(message)
    return value


def _optional_pattern(mapping: Mapping[str, object], key: str, *, context: str) -> str | None:
    if key not in mapping:
        return None
    value = mapping[key]
    if not isinstance(value, str):
        message = f"{context}: field {key!r} must be a string"
        raise AuthoredRecordError(message)
    try:
        re.compile(value)
    except re.error as error:
        message = f"{context}: field {key!r} is not a valid regular expression: {error}"
        raise AuthoredRecordError(message) from error
    return value


def _parse_documents(raw: Sequence[object], *, context: str) -> tuple[DocumentEntry, ...]:
    entries: list[DocumentEntry] = []
    for index, item in enumerate(raw):
        where = f"{context}.documents[{index}]"
        mapping = require_mapping(item, context=where)
        entries.append(
            DocumentEntry(
                doc_id=require_str(mapping, "doc_id", context=where),
                path=require_str(mapping, "path", context=where),
                role=require_value_in(
                    require_str(mapping, "role", context=where),
                    _DOCUMENT_ROLES,
                    context=f"{where}.role",
                ),
                scope=require_str(mapping, "scope", context=where),
                deep_dive_prefix=_optional_str(mapping, "deep_dive_prefix", context=where),
                chapter_levels=_optional_levels(mapping, "chapter_levels", context=where),
                chapter_pattern=_optional_pattern(mapping, "chapter_pattern", context=where),
            )
        )
    return tuple(entries)


def _parse_anchors(raw: Sequence[object], *, context: str) -> tuple[VersionAnchor, ...]:
    anchors: list[VersionAnchor] = []
    for index, item in enumerate(raw):
        where = f"{context}.version_anchors[{index}]"
        mapping = require_mapping(item, context=where)
        anchors.append(
            VersionAnchor(
                anchor_id=require_str(mapping, "anchor_id", context=where),
                source=require_value_in(
                    require_str(mapping, "source", context=where),
                    _ANCHOR_SOURCES,
                    context=f"{where}.source",
                ),
                key=require_str(mapping, "key", context=where),
            )
        )
    return tuple(anchors)


def _parse_consumers(raw: Sequence[object], *, context: str) -> tuple[ConsumerTarget, ...]:
    targets: list[ConsumerTarget] = []
    for index, item in enumerate(raw):
        where = f"{context}.consumers[{index}]"
        mapping = require_mapping(item, context=where)
        blocks = require_str_sequence(mapping, "blocks", context=where)
        for block in blocks:
            require_value_in(block, BLOCK_NAMES, context=f"{where}.blocks")
        targets.append(
            ConsumerTarget(
                path=require_str(mapping, "path", context=where),
                blocks=blocks,
            )
        )
    return tuple(targets)


def _parse_mirrors(raw: Sequence[object], *, context: str) -> tuple[MirrorGroup, ...]:
    groups: list[MirrorGroup] = []
    for index, item in enumerate(raw):
        where = f"{context}.mirror_groups[{index}]"
        mapping = require_mapping(item, context=where)
        groups.append(
            MirrorGroup(
                authoritative=require_str(mapping, "authoritative", context=where),
                mirrors=require_str_sequence(mapping, "mirrors", context=where),
            )
        )
    return tuple(groups)


def load_stack_manifest(stack_id: str, *, root: Path | None = None) -> StackManifest:
    """Return the parsed build manifest for ``stack_id``.

    Args:
        stack_id: Stack identifier, matching the manifest file stem.
        root: Optional manifest directory override, for tests.

    Returns:
        The validated manifest.

    Raises:
        AuthoredRecordError: When the manifest is absent or malformed.

    """
    base = root if root is not None else manifest_root()
    path = base / "stacks" / f"{stack_id}.yaml"
    if not path.is_file():
        message = f"no build manifest for stack {stack_id!r} at {path}"
        raise AuthoredRecordError(message)
    context = f"stack manifest {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    declared_stack = require_str(document, "stack_id", context=context)
    if declared_stack != stack_id:
        message = f"{context}: declares stack_id {declared_stack!r} but is filed as {stack_id!r}"
        raise AuthoredRecordError(message)
    libraries_raw = document.get("libraries")
    libraries = (
        require_str_sequence(document, "libraries", context=context)
        if libraries_raw is not None
        else ()
    )
    mirrors_raw = document.get("mirror_groups")
    mirrors = (
        _parse_mirrors(
            require_sequence(document, "mirror_groups", context=context), context=context
        )
        if mirrors_raw is not None
        else ()
    )
    return StackManifest(
        stack_id=declared_stack,
        title=require_str(document, "title", context=context),
        ecosystem=require_value_in(
            require_str(document, "ecosystem", context=context),
            _ECOSYSTEMS,
            context=f"{context}.ecosystem",
        ),
        documents=_parse_documents(
            require_sequence(document, "documents", context=context), context=context
        ),
        version_anchors=_parse_anchors(
            require_sequence(document, "version_anchors", context=context), context=context
        ),
        consumers=_parse_consumers(
            require_sequence(document, "consumers", context=context), context=context
        ),
        libraries=libraries,
        mirror_groups=mirrors,
    )


LIBRARY_SCHEMA_VERSION: Final = "library-guides.library_manifest.v1"

_API_SOURCE_KINDS: Final = frozenset(
    {"docs_rs_rustdoc_json", "local_rustdoc_json", "griffe_static"}
)


@frozen(kw_only=True)
class ApiSource:
    """Where one profile's public API model comes from.

    ``additional_targets`` lets one profile span a crate family. An umbrella
    crate's own documentation names its dependencies' items but does not
    describe their surface, so a family is only fully inventoried by acquiring
    each member.
    """

    kind: str = field()
    target: str = field()
    additional_targets: tuple[str, ...] = field(default=())

    def all_targets(self) -> tuple[str, ...]:
        """Return every crate or module this profile covers.

        Returns:
            The primary target followed by any additional ones.

        """
        return (self.target, *self.additional_targets)


@frozen(kw_only=True)
class Profile:
    """One coherent resolved environment for a library.

    ``scope`` records what the API model is evidence *for*. A hosted
    documentation build is evidence for that build's feature set, not
    automatically for every consumer configuration.
    """

    profile_id: str = field()
    version_source: str = field()
    version_key: str = field()
    scope: str = field()
    api_source: ApiSource = field()


@frozen(kw_only=True)
class PackageEntry:
    """One distribution or Cargo package inside a library."""

    name: str = field()
    public_root: str = field()


@frozen(kw_only=True)
class LibraryManifest:
    """Identity, packages, profiles, and registry probes for one library."""

    library_id: str = field()
    ecosystem: str = field()
    packages: tuple[PackageEntry, ...] = field()
    profiles: tuple[Profile, ...] = field()
    surface_packages: tuple[str, ...] = field(default=())
    registry_probes: tuple[str, ...] = field(default=())

    def owns_package(self, package: str) -> bool:
        """Return whether ``package`` belongs to this library's declared surface.

        A rustdoc document references every transitive dependency it touches.
        Counting ``libc`` or ``core`` toward a library's functionality would
        inflate the denominator, so membership is declared, not inferred.

        Returns:
            ``True`` when the package matches a declared surface pattern.

        """
        return any(fnmatch(package, pattern) for pattern in self.surface_packages)

    def profile(self, profile_id: str) -> Profile:
        """Return the profile with ``profile_id``.

        Returns:
            The matching profile.

        Raises:
            AuthoredRecordError: When no profile carries that identifier.

        """
        for candidate in self.profiles:
            if candidate.profile_id == profile_id:
                return candidate
        message = f"library {self.library_id}: no profile {profile_id!r}"
        raise AuthoredRecordError(message)


def _parse_profiles(raw: Sequence[object], *, context: str) -> tuple[Profile, ...]:
    profiles: list[Profile] = []
    for index, item in enumerate(raw):
        where = f"{context}.profiles[{index}]"
        mapping = require_mapping(item, context=where)
        source = require_mapping(mapping.get("api_source"), context=f"{where}.api_source")
        kind = require_value_in(
            require_str(source, "kind", context=f"{where}.api_source"),
            _API_SOURCE_KINDS,
            context=f"{where}.api_source.kind",
        )
        target_key = "module" if kind == "griffe_static" else "crate"
        profiles.append(
            Profile(
                profile_id=require_str(mapping, "profile_id", context=where),
                version_source=require_value_in(
                    require_str(mapping, "version_source", context=where),
                    _ANCHOR_SOURCES,
                    context=f"{where}.version_source",
                ),
                version_key=require_str(mapping, "version_key", context=where),
                scope=require_str(mapping, "scope", context=where),
                api_source=ApiSource(
                    kind=kind,
                    target=require_str(source, target_key, context=f"{where}.api_source"),
                    additional_targets=(
                        require_str_sequence(
                            source, "additional_crates", context=f"{where}.api_source"
                        )
                        if "additional_crates" in source
                        else ()
                    ),
                ),
            )
        )
    return tuple(profiles)


def library_manifest_path(library_id: str, *, root: Path | None = None) -> Path:
    """Return the manifest path for ``library_id``.

    Returns:
        Path to the library manifest file.

    """
    base = root if root is not None else manifest_root()
    return base / "libraries" / f"{library_id}.yaml"


def load_library_manifest(library_id: str, *, root: Path | None = None) -> LibraryManifest:
    """Return the parsed build manifest for one library.

    Returns:
        The validated manifest.

    Raises:
        AuthoredRecordError: When the manifest is absent or malformed.

    """
    path = library_manifest_path(library_id, root=root)
    if not path.is_file():
        message = f"no build manifest for library {library_id!r} at {path}"
        raise AuthoredRecordError(message)
    context = f"library manifest {path}"
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), context=context)
    declared = require_str(document, "schema_version", context=context)
    if declared != LIBRARY_SCHEMA_VERSION:
        message = f"{context}: schema_version {declared!r} is not {LIBRARY_SCHEMA_VERSION!r}"
        raise AuthoredRecordError(message)
    packages = tuple(
        PackageEntry(
            name=require_str(
                require_mapping(item, context=f"{context}.packages"), "name", context=context
            ),
            public_root=require_str(
                require_mapping(item, context=f"{context}.packages"), "public_root", context=context
            ),
        )
        for item in require_sequence(document, "packages", context=context)
    )
    profiles = _parse_profiles(
        require_sequence(document, "profiles", context=context), context=context
    )
    surface_raw = document.get("surface_packages")
    surface = (
        require_str_sequence(document, "surface_packages", context=context)
        if surface_raw is not None
        else ()
    )
    probes_raw = document.get("registry_probes")
    probes = (
        require_str_sequence(document, "registry_probes", context=context)
        if probes_raw is not None
        else ()
    )
    return LibraryManifest(
        library_id=require_str(document, "library_id", context=context),
        ecosystem=require_value_in(
            require_str(document, "ecosystem", context=context),
            _ECOSYSTEMS,
            context=f"{context}.ecosystem",
        ),
        packages=packages,
        profiles=profiles,
        surface_packages=surface,
        registry_probes=probes,
    )

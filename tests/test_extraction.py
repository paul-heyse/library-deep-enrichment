"""Extraction records what it found, and is explicit about what it did not."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from library_guides.adapters.rust.rustdoc_json import (
    SUPPORTED_FORMAT_VERSIONS,
    UnsupportedRustdocFormatError,
    parse_rustdoc_json,
)
from library_guides.manifest import known_stack_ids, load_library_manifest, load_stack_manifest
from library_guides.models.enums import ResolutionState
from library_guides.models.records import ApiBinding, SurfaceEntry
from library_guides.stages.paths import api_path, surfaces_path
from library_guides.store.jsonl import read_records

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _minimal_rustdoc(format_version: int) -> bytes:
    document = {
        "root": "0",
        "crate_version": "1.2.3",
        "format_version": format_version,
        "index": {},
        "paths": {
            "0": {"crate_id": 0, "path": ["demo"], "kind": "module"},
            "1": {"crate_id": 0, "path": ["demo", "Thing"], "kind": "struct"},
            "2": {"crate_id": 1, "path": ["other", "Borrowed"], "kind": "struct"},
        },
        "external_crates": {"1": {"name": "other"}},
    }
    return json.dumps(document).encode("utf-8")


def test_an_unverified_rustdoc_format_is_refused() -> None:
    """Rustdoc JSON is unstable; a best-effort parse would mis-describe an API."""
    unsupported = max(SUPPORTED_FORMAT_VERSIONS) + 100
    with pytest.raises(UnsupportedRustdocFormatError, match="not supported"):
        parse_rustdoc_json(
            _minimal_rustdoc(unsupported),
            library_id="demo",
            profile_id="demo-profile",
            package="demo",
        )


def test_a_dependency_item_is_recorded_as_a_candidate_not_a_local_api() -> None:
    """Referencing an item is not evidence that this crate re-exports it."""
    model = parse_rustdoc_json(
        _minimal_rustdoc(min(SUPPORTED_FORMAT_VERSIONS)),
        library_id="demo",
        profile_id="demo-profile",
        package="demo",
    )
    by_path = {binding.identity.public_path: binding for binding in model.bindings}
    assert by_path["demo::Thing"].resolution_state is ResolutionState.RESOLVED
    borrowed = by_path["other::Borrowed"]
    assert borrowed.resolution_state is ResolutionState.CANDIDATE
    assert borrowed.identity.package == "other"
    assert model.foreign_path_count == 1


def _profiles() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for stack_id in known_stack_ids():
        for library_id in load_stack_manifest(stack_id).libraries:
            library = load_library_manifest(library_id)
            pairs.extend((library_id, profile.profile_id) for profile in library.profiles)
    return pairs


@pytest.mark.parametrize(("library_id", "profile_id"), _profiles())
def test_every_declared_profile_has_an_inventory(library_id: str, profile_id: str) -> None:
    """A stack cannot claim breadth it never extracted."""
    path = api_path(library_id, profile_id, repository_root=REPOSITORY_ROOT)
    assert path.is_file(), f"no inventory at {path}"
    records = list(read_records(path, ApiBinding))
    assert records, f"{path} is empty"
    assert all(record.profile_id == profile_id for record in records)


@pytest.mark.parametrize(("library_id", "profile_id"), _profiles())
def test_inventories_only_contain_declared_surface_packages(
    library_id: str,
    profile_id: str,
) -> None:
    """Counting a transitive dependency would inflate the denominator."""
    manifest = load_library_manifest(library_id)
    path = api_path(library_id, profile_id, repository_root=REPOSITORY_ROOT)
    offenders = {
        record.identity.package
        for record in read_records(path, ApiBinding)
        if not manifest.owns_package(record.identity.package)
    }
    assert not offenders, (
        f"{library_id} inventory includes undeclared packages: {sorted(offenders)}"
    )


def test_registry_probes_record_what_they_are_evidence_for() -> None:
    """A runtime observation is scoped to the profile that produced it."""
    checked = 0
    for stack_id in known_stack_ids():
        for library_id in load_stack_manifest(stack_id).libraries:
            library = load_library_manifest(library_id)
            if not library.registry_probes:
                continue
            for profile in library.profiles:
                path = surfaces_path(
                    library_id, profile.profile_id, repository_root=REPOSITORY_ROOT
                )
                assert path.is_file(), f"declared a probe but produced no surfaces: {path}"
                for record in read_records(path, SurfaceEntry):
                    assert record.profile_id == profile.profile_id
                    assert record.availability_conditions
                    checked += 1
    assert checked > 0, "no registry surfaces were checked"

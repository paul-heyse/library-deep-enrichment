"""Produce the coverage report for every declared stack."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_guides.decisions import load_decisions
from library_guides.manifest import known_stack_ids, load_library_manifest, load_stack_manifest
from library_guides.models.enums import StageCompletion
from library_guides.models.records import ApiBinding, ExtractionReceipt, SurfaceEntry
from library_guides.obligations import load_obligations
from library_guides.stages.coverage import AxisCoverage, CoverageReport, surface_axis
from library_guides.stages.paths import api_path, coverage_path, surfaces_path
from library_guides.store.jsonl import read_records
from library_guides.store.staging import write_atomic

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["build_coverage_reports", "write_coverage_report"]


def _routed_identifiers(stack_id: str, *, repository_root: Path) -> frozenset[str]:
    """Return every identifier the stack's authored guidance points at.

    Returns:
        Candidate API identifiers named by decision briefs.

    """
    routed: set[str] = set()
    for brief in load_decisions(stack_id, repository_root=repository_root).values():
        routed.update(candidate.api for candidate in brief.candidates)
    return frozenset(routed)


def _decision_axis(stack_id: str, *, repository_root: Path) -> AxisCoverage:
    obligations = load_obligations()
    briefs = tuple(load_decisions(stack_id, repository_root=repository_root).values())
    satisfied = 0
    for brief in briefs:
        obligation = obligations.get(brief.family_kind)
        if obligation is None:
            continue
        minimum_candidates = 2
        if (
            brief.is_publishable()
            and len(brief.candidates) >= minimum_candidates
            and brief.reversing_conditions
        ):
            satisfied += 1
    return AxisCoverage(
        axis="decision",
        numerator=satisfied,
        denominator=len(briefs),
        denominator_is_complete=False,
        note=(
            "The denominator is the set of briefs authored so far, not every "
            "choice an agent could face. This measures brief quality, not breadth."
        ),
    )


def build_coverage_reports(*, repository_root: Path) -> tuple[CoverageReport, ...]:
    """Return coverage for every library profile in every declared stack.

    Returns:
        One report per library profile.

    """
    reports: list[CoverageReport] = []
    for stack_id in known_stack_ids():
        stack = load_stack_manifest(stack_id)
        routed = _routed_identifiers(stack_id, repository_root=repository_root)
        decision = _decision_axis(stack_id, repository_root=repository_root)
        for library_id in stack.libraries:
            library = load_library_manifest(library_id)
            for profile in library.profiles:
                api_file = api_path(library_id, profile.profile_id, repository_root=repository_root)
                surface_file = surfaces_path(
                    library_id, profile.profile_id, repository_root=repository_root
                )
                bindings = list(read_records(api_file, ApiBinding)) if api_file.is_file() else []
                surfaces = (
                    list(read_records(surface_file, SurfaceEntry)) if surface_file.is_file() else []
                )
                receipt = ExtractionReceipt(
                    stage_id="extract-api",
                    configuration_digest="",
                    enumerated_inputs=len(bindings),
                    processed_inputs=len(bindings),
                    completion=StageCompletion.PARTIAL,
                )
                reports.append(
                    CoverageReport(
                        library_id=library_id,
                        profile_id=profile.profile_id,
                        axes=(
                            surface_axis(
                                bindings,
                                surfaces,
                                routed_paths=routed,
                                excluded=(),
                                receipt=receipt,
                            ),
                            decision,
                        ),
                    )
                )
    return tuple(reports)


def write_coverage_report(*, repository_root: Path) -> Path:
    """Write the coverage report and return where it landed.

    Returns:
        Path to ``evidence/coverage.json``.

    """
    reports = build_coverage_reports(repository_root=repository_root)
    payload = {
        "schema_version": "library-guides.coverage.v1",
        "profiles": [
            {
                "library_id": report.library_id,
                "profile_id": report.profile_id,
                "axes": [
                    {
                        "axis": axis.axis,
                        "numerator": axis.numerator,
                        "denominator": axis.denominator,
                        "unresolved": axis.unresolved,
                        "denominator_is_complete": axis.denominator_is_complete,
                        "note": axis.note,
                    }
                    for axis in report.axes
                ],
            }
            for report in reports
        ],
    }
    destination = coverage_path(repository_root=repository_root)
    write_atomic(destination, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    return destination

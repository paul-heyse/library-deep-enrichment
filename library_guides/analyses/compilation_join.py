"""Contextual Cargo joins using opaque IDs, exact target inputs and observed output recipes."""

from __future__ import annotations

import json
import posixpath
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.compilation_contracts import CargoCandidate, ContextSetting
from library_guides.analyses.compilation_inputs import absolute
from library_guides.corpus.encoding import digest
from library_guides.corpus.schemas import revision_of
from library_guides.facts.compiler_invocation import Arguments

if TYPE_CHECKING:
    from library_guides.analyses.compilation_contracts import CompilationRequest, ContextInput
    from library_guides.analyses.compilation_inputs import CompilationCatalog
    from library_guides.facts.compiler_invocation import CompilerInvocation


@frozen(kw_only=True)
class JoinInput:
    """Checked compiler observation, token interpretation and exact input witness states."""

    observed: CompilerInvocation
    parsed: Arguments
    inputs: tuple[ContextInput, ...]


def features(parsed: Arguments) -> ContextSetting:
    """Read only enabled feature cfgs; check-cfg's declared values never enable a feature.

    Returns:
        Observed enabled names with opaque argument and cfg syntax limits retained.

    """
    names = []
    complete = not parsed.frontier
    for cfg in parsed.values("--cfg"):
        key, separator, value = cfg.partition("=")
        if key.strip() != "feature":
            continue
        try:
            item = json.loads(value) if separator else None
        except json.JSONDecodeError:
            item = None
        if isinstance(item, str):
            names.append(item)
        else:
            complete = False
    return ContextSetting(
        name="enabled_feature_cfgs",
        values=tuple(sorted(set(names))),
        state="observed_explicit_options" if complete else "partial_option_observation",
    )


def settings(parsed: Arguments, observed: CompilerInvocation) -> tuple[ContextSetting, ...]:
    """Preserve explicit option categories without inferring target or compiler defaults.

    Returns:
        Separate cfg, validation-cfg, codegen, target and environment observations.

    """
    result = [features(parsed)]
    for name in (
        "--crate-name",
        "--crate-type",
        "--edition",
        "--target",
        "--cfg",
        "--check-cfg",
        "--out-dir",
        "--emit",
        "--extern",
        "-C",
        "--codegen",
        "--test",
    ):
        values = parsed.values(name)
        result.append(
            ContextSetting(
                name=name,
                values=values,
                state="observed_explicit_options" if values else "default_or_unobserved",
            )
        )
    result.extend(
        ContextSetting(name="env:" + name, values=(value,), state="observed_environment")
        for name, value in observed.environment
    )
    return tuple(result)


def _output_matches(parsed: Arguments, message: dict, cwd: str) -> bool:
    explicit = parsed.values("-o")
    if len(explicit) == 1:
        return absolute(explicit[0], cwd) in message["filenames"]
    outputs, names = parsed.values("--out-dir"), parsed.values("--crate-name")
    extra = [
        value.partition("=")[2]
        for value in (*parsed.values("-C"), *parsed.values("--codegen"))
        if value.startswith("extra-filename=")
    ]
    if len(outputs) != 1 or len(names) != 1 or len(extra) != 1:
        return False
    # This bounded recipe covers Linux library artifacts. Other target artifact
    # conventions remain candidates and require their own observed mapping.
    if parsed.values("--target") or set(message["target"]["crate_types"]) - {"lib", "rlib"}:
        return False
    directory = absolute(outputs[0], cwd)
    if not directory:
        return False
    expected = {
        posixpath.join(directory, "lib" + names[0] + extra[0] + suffix)
        for suffix in (".rlib", ".rmeta")
    }
    return bool(expected.intersection(message["filenames"]))


def _targets(
    package: dict, observed: CompilerInvocation, parsed: Arguments, inputs: tuple[ContextInput, ...]
) -> tuple[dict, ...]:
    environment = dict(observed.environment)
    manifest = environment.get("CARGO_MANIFEST_DIR")
    if not manifest or posixpath.dirname(package["manifest"]) != manifest:
        return ()
    if (
        environment.get("CARGO_PKG_NAME") != package["symbol"]
        or environment.get("CARGO_PKG_VERSION") != package["version"]
    ):
        return ()
    cwd = observed.execution.working_directory if observed.execution else ""
    input_paths = {item.path for item in inputs}
    positional = {absolute(path, cwd) for path in parsed.positionals}
    return tuple(
        target
        for target in package["targets"]
        if (
            target["source"] in input_paths.intersection(positional)
            and parsed.values("--crate-name") == (target["name"].replace("-", "_"),)
            and parsed.values("--edition") == (target["edition"],)
            and {value for option in parsed.values("--crate-type") for value in option.split(",")}
            == set(target["crate_types"])
        )
    )


def _candidate(
    package_row: tuple,
    message_row: tuple | None,
    target: dict,
    unit: JoinInput,
) -> CargoCandidate:
    observed, parsed, inputs = unit.observed, unit.parsed, unit.inputs
    fact, package = package_row
    message = message_row[1]["observation"] if message_row else None
    enabled = features(parsed)
    compiled = tuple(sorted(message["features"])) if message else ()
    cwd = observed.execution.working_directory if observed.execution else ""
    retained = any(item.path == target["source"] and item.source for item in inputs)
    state = "metadata_target_candidate"
    frontier = [
        "metadata_resolution_and_compilation_are_distinct_observations",
        "binary_outputs_and_dependency_byte_closure_unwitnessed",
        "matching_output_recipe_is_correspondence_not_same_process_attestation",
    ]
    if package.get("resolved_features") is None:
        frontier.append("metadata_resolved_features_unobserved")
    if message:
        state = (
            "target_and_output_recipe_correspondence"
            if _output_matches(parsed, message, cwd)
            else "output_recipe_unresolved"
        )
        if enabled.state != "observed_explicit_options":
            state = "compiler_options_incomplete"
        elif enabled.values != compiled:
            state = "compiled_feature_conflict"
        if message.get("fresh"):
            frontier.append("cargo_reused_artifact_does_not_attest_current_invocation")
    else:
        frontier.append("no_matching_artifact_in_finite_message_catalog")
    if not retained:
        state = "target_input_bytes_unobserved"
    if not observed.success or observed.extraction != "complete":
        state = "compiler_capture_incomplete"
    return CargoCandidate(
        metadata=revision_of(fact),
        message=revision_of(message_row[0]) if message_row else "",
        package_id=package["package_id"],
        target_source=target["source"],
        declared_features=tuple(
            ContextSetting(name=name, values=tuple(values), state="declared_feature_definition")
            for name, values in sorted(package["feature_definitions"].items())
        ),
        resolved_features=tuple(sorted(package.get("resolved_features") or ())),
        compiled_features=compiled,
        state=state,
        frontier=tuple(frontier),
    )


def candidates(
    selected: dict[str, CompilationCatalog],
    request: CompilationRequest,
    unit: JoinInput,
) -> tuple[CargoCandidate, ...]:
    """Retain all matching contextual candidates, including conflicts and incomplete units.

    Returns:
        Exact finite correspondences without name-only or parsed-PackageId joins.

    """
    message_rows: dict[tuple[str, str], list[tuple]] = {}
    for key in request.messages:
        for row in selected[key].rows:
            message = row[1].get("observation", {})
            if message.get("kind") == "artifact":
                message_rows.setdefault(
                    (message["package_id"], digest(message["target"])), []
                ).append(row)
    result = []
    for key in request.metadata:
        for row in selected[key].rows:
            package = row[1]
            for target in _targets(package, unit.observed, unit.parsed, unit.inputs):
                matches = message_rows.get((package["package_id"], digest(target)), [])
                for message in matches or [None]:
                    require(
                        "compilation candidate product exceeds fact budget",
                        condition=len(result) < request.max_facts,
                    )
                    result.append(_candidate(row, message, target, unit))
    return tuple(
        sorted(result, key=lambda value: (value.metadata, value.message, value.target_source))
    )

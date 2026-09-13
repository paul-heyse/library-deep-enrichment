"""Bounded original-byte compilation observations; no access to acquisition-time paths."""

from __future__ import annotations

import json
import posixpath
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.callable_sources import MAX_BYTES, RetainedSource, paths, sources
from library_deep_enrichment.analyses.compilation_contracts import (
    CargoCommand,
    CompilationRequest,
    ContextInput,
    ContextSetting,
)
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.facts.compiler_invocation import CompilerInvocation, read
from library_deep_enrichment.facts.witness_origins import read as read_origins

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader

MAX_FACTS = 100_000
MAX_ARTIFACTS = 128
MAX_OPTIONS = 10_000


@frozen(kw_only=True)
class CompilationCatalog:
    """One exact native artifact with an ordered catalog and byte-attributed witnesses."""

    artifact: NativeArtifact
    header: dict
    receipt: dict
    rows: tuple[tuple[NativeFact, dict], ...]
    sources: dict[str, RetainedSource]
    paths: dict[str, RetainedSource]

    def witnesses(self, kind: str) -> tuple[RetainedSource, ...]:
        """Select witnesses by acquisition role.

        Returns:
            Only origin-attributed retained bytes of the requested role.

        """
        return tuple(
            self.paths[path] for path, entry in read_origins(self.receipt) if entry["kind"] == kind
        )


def catalogs(reader: CorpusReader, request: CompilationRequest) -> dict[str, CompilationCatalog]:
    """Acquire finite unit and complete Cargo catalogs under exact schemas and budgets.

    Returns:
        Deterministically ordered native evidence with no inferred missing members.

    """
    groups = (request.executables, request.metadata, request.messages)
    require(
        "invalid compilation catalog selection or budget",
        condition=(
            bool(request.executables)
            and all(len(set(group)) == len(group) for group in groups)
            and 0 < request.max_facts <= MAX_FACTS
            and 0 < request.max_bytes <= 128 * 1024 * 1024
        ),
    )
    keys = sorted(set(request.executables + request.metadata + request.messages))
    require("compilation artifact budget exceeded", condition=len(keys) <= MAX_ARTIFACTS)
    result = {}
    total = count = 0
    for key in keys:
        artifact = reader.get("native_artifacts", key)
        require(
            "compilation artifact escaped profile",
            condition=isinstance(artifact, NativeArtifact) and artifact.profile == request.profile,
        )
        assert isinstance(artifact, NativeArtifact)
        require(
            "unsupported compilation catalog schema",
            condition=(
                (
                    key not in request.executables
                    or artifact.schema
                    in {
                        "library-guides.mir.v1",
                        "library-guides.mir-execution.v1",
                        "library-guides.mir-instances.v1",
                        "library-guides.mir-callables.v1",
                        "library-guides.mir-lifecycle.v1",
                        "library-guides.mir-memory.v1",
                    }
                )
                and (key not in request.metadata or artifact.schema == "library-guides.cargo.v1")
                and (
                    key not in request.messages
                    or artifact.schema == "library-guides.cargo-messages.v1"
                )
            ),
        )
        rows = []
        if key in request.metadata + request.messages:
            for fact in reader.filtered_records("native_facts", (("artifact", key),)):
                assert isinstance(fact, NativeFact)
                total += fact.original.end - fact.original.start
                count += 1
                require(
                    "compilation native fact budget exceeded",
                    condition=count <= request.max_facts and total <= request.max_bytes,
                )
                rows.append(
                    (
                        fact,
                        json.loads(
                            resolve_bytes(reader, fact.original, max_bytes=request.max_bytes)
                        ),
                    )
                )
            require(
                "incomplete compilation Cargo denominator",
                condition=len(rows) == artifact.record_count,
            )
        retained = sources(reader, artifact)
        total += sum(len(source.data) for source in retained.values())
        require("compilation retained byte budget exceeded", condition=total <= request.max_bytes)
        result[key] = CompilationCatalog(
            artifact=artifact,
            header=json.loads(resolve_bytes(reader, artifact.header, max_bytes=MAX_BYTES)),
            receipt=json.loads(resolve_bytes(reader, artifact.receipt, max_bytes=MAX_BYTES)),
            rows=tuple(sorted(rows, key=lambda pair: revision_of(pair[0]))),
            sources=retained,
            paths=paths(reader, artifact, retained),
        )
    return result


def invocation(catalog: CompilationCatalog) -> tuple[CompilerInvocation, RetainedSource] | None:
    """Validate exact original invocation/header correspondence when a witness was retained.

    Returns:
        The checked original observation or an explicit absence for historical captures.

    """
    witnesses = catalog.witnesses("compiler_invocation")
    require("ambiguous original compiler invocation witnesses", condition=len(witnesses) <= 1)
    if not witnesses:
        return None
    source = witnesses[0]
    observed = read(json.loads(source.data))
    require(
        "original compiler invocation differs from normalized header",
        condition=(
            observed.identity == catalog.header.get("original_request")
            and observed.context == catalog.header.get("context")
            and observed.argv == tuple(catalog.header.get("argv", ()))
            and observed.purpose == "mir"
        ),
    )
    if observed.execution:
        require(
            "compiler execution schema differs from capture",
            condition=observed.execution.schema == catalog.artifact.schema,
        )
    return observed, source


def absolute(path: str, cwd: str) -> str:
    """Normalize an observed Linux path lexically; never resolve or open it.

    Returns:
        An absolute lexical path, or an empty string when its base is unobserved.

    """
    return (
        posixpath.normpath(path if path.startswith("/") else posixpath.join(cwd, path))
        if path.startswith("/") or cwd.startswith("/")
        else ""
    )


def inputs(catalog: CompilationCatalog, observed: CompilerInvocation) -> tuple[ContextInput, ...]:
    """Match invocation input digests against retained original-path associations.

    Returns:
        Every observed input, retaining missing bytes or unresolved relative paths.

    """
    result = []
    cwd = observed.execution.working_directory if observed.execution else ""
    for path, identity in observed.inputs:
        selected = absolute(path, cwd)
        source = catalog.paths.get(selected)
        require(
            "compiler input source bytes differ from original invocation",
            condition=source is None or source.digest == identity,
        )
        result.append(
            ContextInput(
                path=selected or path,
                digest=identity,
                source=source.revision if source else "",
                state="retained_original_bytes" if source else "input_bytes_unobserved",
            )
        )
    return tuple(result)


def commands(catalog: CompilationCatalog) -> tuple[CargoCommand, ...]:
    """Retain externally attributed Cargo requests separately from native unit settings.

    Returns:
        Exact observed command records; absence cannot imply default feature selection.

    """
    result = []
    for source in catalog.witnesses("cargo_command"):
        raw = json.loads(source.data)
        require(
            "unsupported or unrelated Cargo command observation",
            condition=(
                raw.get("kind") == "library-guides.cargo-command-observation.v1"
                and raw.get("output_digest") == catalog.artifact.input.digest
                and isinstance(raw.get("observer"), str)
                and bool(raw["observer"])
            ),
        )
        settings = []
        for name in ("requested_features", "argv"):
            value = raw.get(name)
            require(
                "invalid Cargo command vector",
                condition=isinstance(value, list)
                and len(value) <= MAX_OPTIONS
                and all(isinstance(item, str) for item in value),
            )
            settings.append(
                ContextSetting(
                    name=name, values=tuple(value), state="attributed_command_observation"
                )
            )
        for name in ("all_features", "no_default_features", "locked", "offline"):
            value = raw.get(name)
            require("invalid Cargo command flag", condition=type(value) is bool)
            settings.append(
                ContextSetting(
                    name=name, values=(str(value).lower(),), state="attributed_command_observation"
                )
            )
        settings.extend(
            ContextSetting(
                name=name, values=(str(raw.get(name)),), state="attributed_command_observation"
            )
            for name in ("cwd", "toolchain", "exit_code")
        )
        result.append(
            CargoCommand(
                artifact=revision_of(catalog.artifact),
                source=source.revision,
                observer=raw["observer"],
                settings=tuple(settings),
                frontier=(
                    "externally_attributed_observation_not_native_process_attestation",
                    "requested_features_do_not_determine_each_compilation_unit",
                ),
            )
        )
    return tuple(result)

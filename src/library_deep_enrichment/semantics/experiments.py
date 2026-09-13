"""Explicit build-time execution of approved finite witnesses in isolated scratch space."""

from __future__ import annotations

import json
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import evolve

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Context, Disposition, Policy, Scope
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.evidence import field_value, resolve_bytes, select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.processes import ProcessResult, execute
from library_deep_enrichment.semantics.documents import scalar
from library_deep_enrichment.semantics.enrichment_contracts import (
    WitnessObservation,
    WitnessRecipe,
    WitnessRun,
)
from library_deep_enrichment.worker_runtime import WorkerRequest, command
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader

MAX_WITNESS_BYTES = 4 * 1024 * 1024
MAX_COMPILER_FILE_BYTES = 256 * 1024 * 1024


def _request(recipe: WitnessRecipe, root: Path) -> WorkerRequest:
    cargo_home = root / "cargo-home"
    cargo_home.mkdir()
    (cargo_home / "registry").symlink_to(Path.home() / ".cargo/registry")
    if recipe.language == "python":
        argv = (sys.executable, "-I", str(root / "program.py"))
    elif recipe.language == "rust":
        binaries = Path.home() / ".rustup/toolchains" / recipe.toolchain / "bin"
        argv = (
            "/usr/bin/env",
            f"CARGO_HOME={cargo_home}",
            f"CARGO_TARGET_DIR={root / 'target'}",
            f"RUSTC={binaries / 'rustc'}",
            f"RUSTDOC={binaries / 'rustdoc'}",
            str(binaries / "cargo"),
            "run",
            "--offline",
            "--quiet",
            "--manifest-path",
            str(root / "Cargo.toml"),
        )
    else:
        message = "witness language requires an explicitly supported executor"
        raise CorpusError(message)
    return WorkerRequest(
        argv=argv,
        cwd=root,
        request_id=revision_of(recipe),
        input_digest=recipe.program.digest,
        budget=Budget(
            wall_seconds=180,
            cpu_seconds=150,
            memory_bytes=8 * 1024**3,
            output_bytes=MAX_COMPILER_FILE_BYTES,
        ),
        read_roots=(
            Path.home() / ".cargo/registry",
            Path.home() / ".rustup",
            Path("/etc/ld.so.cache"),
        ),
        write_roots=(root,),
        isolate=True,
    )


def _execute(
    reader: CorpusReader, recipe: WitnessRecipe, root: Path
) -> tuple[WorkerRequest, ProcessResult]:
    source = root / ("program.py" if recipe.language == "python" else "src/main.rs")
    source.parent.mkdir(exist_ok=True)
    source.write_bytes(resolve_bytes(reader, recipe.program, max_bytes=MAX_WITNESS_BYTES))
    (root / "Cargo.toml").write_bytes(
        resolve_bytes(reader, recipe.manifest, max_bytes=MAX_WITNESS_BYTES)
    )
    request = _request(recipe, root)
    return request, execute(
        command(request), cwd=root, timeout=request.budget.wall_seconds, max_bytes=MAX_WITNESS_BYTES
    )


def _context(
    builder: ObservationBuilder, recipe: WitnessRecipe, result: ProcessResult, lockfile: bytes
) -> Context:
    data = json.loads(result.stdout) if result.returncode == 0 else {}
    if not isinstance(data, dict) or not isinstance(data.get("environment", {}), dict):
        message = "witness did not emit a structured environment and observation object"
        raise CorpusError(message)
    environment = data.get("environment", {})
    observed = tuple(sorted(f"{key}=={value}" for key, value in environment.items()))
    if recipe.language == "rust" and result.returncode == 0:
        packages = tomllib.loads(lockfile.decode()).get("package", [])
        resolved = {f"{package['name']}=={package['version']}" for package in packages}
        if not set(recipe.packages) <= resolved:
            message = "Cargo's actual resolution differs from the approved witness package versions"
            raise CorpusError(message)
    if result.returncode == 0 and not set(recipe.packages) <= set(observed):
        message = "witness environment differs from the approved package versions"
        raise CorpusError(message)
    raw = builder.observe(
        f"witness-environment:{revision_of(recipe)}",
        environment,
        profile=recipe.profile,
        kind="witness-environment",
    )
    context = Context(
        logical_id=f"witness-context:{digest([revision_of(recipe), observed])}",
        profile=recipe.profile,
        language=recipe.language,
        package=recipe.name,
        version="finite-experiment",
        toolchain=recipe.toolchain,
        target="isolated-local-host",
        features=(),
        components=observed,
        evidence=tuple(
            builder.select(raw, f"/{key}", "observed-package-version")
            for key in sorted(environment)
        ),
    )
    builder.add(context)
    return context


def _observations(
    builder: ObservationBuilder,
    run: WitnessRun,
    recipe: WitnessRecipe,
    data: Mapping[str, object],
    bindings: Mapping[str, str],
) -> None:
    raw = builder.observe(
        f"witness-output:{revision_of(run)}",
        data,
        profile=recipe.profile,
        kind="finite-witness-output",
        context=run.context,
    )
    scope = Scope(
        logical_id=f"witness-scope:{revision_of(run)}",
        profile=recipe.profile,
        owner=revision_of(run),
        query="Exactly the retained program inputs and environment of this execution",
        members=(revision_of(run),),
        sources=(select(run, "/stdout", "executed-output"),),
        disposition=Disposition.COMPLETE,
        frontier=(),
    )
    builder.add(scope)
    for field, operation in sorted(bindings.items()):
        if field not in recipe.fields:
            message = "observation binding requests a field outside the approved witness protocol"
            raise CorpusError(message)
        value = scalar(field_value(data, field))
        if value is None:
            message = "witness observation field is not a canonical scalar"
            raise CorpusError(message)
        builder.add(
            WitnessObservation(
                logical_id=f"witness-observation:{revision_of(run)}:{operation}:{field}",
                profile=recipe.profile,
                operation=operation,
                run=revision_of(run),
                field=field,
                value=value,
                scope=revision_of(scope),
                support=(
                    builder.select(raw, field, "observed-result"),
                    select(run, "/stdout", "execution-output"),
                ),
            )
        )


def _produce_witness(
    reader: CorpusReader, recipe: WitnessRecipe, bindings: Mapping[str, str]
) -> Iterable[Record]:
    reader.get("witness_recipes", revision_of(recipe))
    if not any(
        isinstance(policy, Policy)
        and policy.kind == "witness-recipe-approval"
        and policy.subject == revision_of(recipe)
        for policy in reader.records("policies")
    ):
        message = "witness execution requires approval of the exact finite program recipe"
        raise CorpusError(message)
    for operation in bindings.values():
        record = reader.get("operations", operation)
        if record.profile != recipe.profile:
            message = "witness binding crosses the approved execution profile"
            raise CorpusError(message)
    builder = ObservationBuilder("isolated-witness-executor.v1")
    with tempfile.TemporaryDirectory(prefix="library-guides-witness-") as temporary:
        root = Path(temporary)
        request, result = _execute(reader, recipe, root)
        lockfile = root / "Cargo.lock"
        lock_bytes = lockfile.read_bytes() if lockfile.exists() else b""
        context = _context(builder, recipe, result, lock_bytes)
        run = WitnessRun(
            logical_id=f"witness-run:{revision_of(recipe)}",
            profile=recipe.profile,
            recipe=revision_of(recipe),
            context=revision_of(context),
            command=request.argv,
            stdout=builder.own_bytes(result.stdout, media_type="application/json"),
            stderr=builder.own_bytes(result.stderr, media_type="text/plain"),
            lockfile=builder.own_bytes(lock_bytes, media_type="text/plain"),
            returncode=result.returncode,
            isolation="filesystem-network-process-resource-limits",
            disposition="complete" if result.returncode == 0 else "failed",
        )
        builder.add(run)
        if result.returncode == 0:
            _observations(builder, run, recipe, json.loads(result.stdout), bindings)
    if result.returncode:
        message = f"isolated witness failed ({result.returncode}): {result.stderr.decode(errors='replace')[:3000]}"
        raise CorpusError(message)
    return builder.records.values()


def run_witness(corpus: Corpus, recipe: WitnessRecipe, bindings: Mapping[str, str]) -> str:
    """Run an explicitly approved build experiment with warm reuse and failure currentness.

    Returns:
        A coherent manifest retaining execution inputs, outputs, and finite observations.

    """
    stage = definition(
        f"witness:{recipe.logical_id}",
        {
            "witness_recipes": ("/program", "/manifest", "/packages", "/toolchain", "/fields"),
            "policies": ("/kind", "/subject"),
            "operations": ("/signature", "/parameters", "/profile"),
        },
        (
            "blobs",
            "blob_chunks",
            "contexts",
            "raw_observations",
            "witness_runs",
            "witness_observations",
            "scopes",
        ),
        ("semantics/experiments.py", "worker_runtime.py", "_worker_entry.py", "processes.py"),
    )
    stage = evolve(
        stage, implementation=digest([stage.implementation, revision_of(recipe), dict(bindings)])
    )
    return run_stage(
        corpus, stage, lambda reader: _produce_witness(reader, recipe, bindings)
    ).manifest

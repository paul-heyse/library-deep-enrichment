"""Reconcile generated Cargo workspaces, actual invocations and owned fact artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from attrs import asdict, evolve, frozen

from library_deep_enrichment.collection import CollectionError, load, save
from library_deep_enrichment.facts.context import identify
from library_deep_enrichment.facts.contracts import (
    FactArtifact,
    FactHead,
    FileEntry,
    SemanticProfile,
    Setting,
    SourceSnapshot,
)
from library_deep_enrichment.knowledge import Profile
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.rust_workspace import InvocationOptions, Workspace, invoke, prepare
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.source_snapshots import Acquisition, freeze, inventory
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file
from library_deep_enrichment.store.staging import write_atomic

_SCHEMAS = Path(__file__).parent / "assets/schemas"


@frozen(kw_only=True)
class Producers:
    """Explicit built worker locations; no application-runtime dependency."""

    declarations: Path
    mir: Path


@frozen(kw_only=True)
class Execution:
    """One immutable extraction context shared across selected Cargo targets."""

    root: Path
    spec: Workspace
    workspace: Path
    directory: Path
    producers: Producers
    lane: Literal["documentation", "mir"]
    context: SemanticProfile
    snapshots: tuple[str, ...]
    source_roots: tuple[tuple[str, str], ...]


def _rows(root: Path, artifact: FactArtifact) -> list[dict]:
    return [
        json.loads(line)
        for shard in artifact.shards
        for line in (root / shard.path).read_bytes().splitlines()
    ]


def _profile(
    spec: Workspace,
    receipt: dict,
    purpose: Literal["metadata", "documentation", "mir"],
    source: str,
    inputs: tuple[str, ...],
) -> SemanticProfile:
    return identify(
        SemanticProfile(
            id="",
            purpose=purpose,
            package="generated-family:" + spec.id,
            version="exact-package-catalog",
            source_digest=source,
            toolchain=spec.toolchain,
            target=spec.target,
            dependency_digests=inputs,
            settings=(
                Setting(
                    name="requested_packages",
                    value=canonical_bytes([asdict(p) for p in spec.packages]).decode(),
                    origin="requested",
                ),
                Setting(
                    name="rustflags",
                    value=canonical_bytes(spec.rustflags).decode(),
                    origin="requested",
                ),
                Setting(name="cargo_lock", value=str(receipt["lock"]), origin="observed"),
                Setting(name="unit_settings", value=None, origin="unknown"),
            ),
            limitations=(
                "Invocation receipts separately retain actual unit arguments, environment and output identity.",
                "Build-script/proc-macro external inputs are not proven hermetic; this context is not unconditional effect or availability evidence.",
            ),
        )
    )


@frozen(kw_only=True)
class Prepared:
    """Verified acquisition inputs, before any body/doc invocation is admitted."""

    workspace: Path
    resolution: dict[str, object]
    project: FactArtifact
    context: SemanticProfile
    selected: list
    snapshots: tuple[SourceSnapshot, ...]
    originals: tuple[tuple[Path, tuple[FileEntry, ...]], ...]


def _prepare(root: Path, spec: Workspace, store: Path, producers: Producers) -> Prepared:
    workspace, resolution = prepare(spec, store)
    workspace = workspace.resolve()
    metadata = invoke(
        spec,
        workspace,
        (
            "metadata",
            "--offline",
            "--locked",
            "--format-version",
            "1",
            "--filter-platform",
            spec.target,
        ),
        "metadata",
    )
    if metadata["returncode"]:
        message = f"Cargo metadata failed: {metadata['stderr']}"
        raise CollectionError(message)
    context = _profile(
        spec, resolution, "metadata", str(resolution["manifest"]), (str(resolution["lock"]),)
    )
    project = extract(
        root,
        SourceJob(
            id=spec.id + ":metadata",
            kind="cargo",
            input=str(metadata["stdout"]),
            helper=str(producers.declarations.resolve()),
            profile=spec.profile,
            schema=str(_SCHEMAS / "cargo.v1.schema.json"),
            semantic_profile=context,
        ),
        spec.budget,
    )
    packages = _rows(root, project)
    selected = [
        (
            requested,
            [
                package
                for package in packages
                if package["symbol"] == requested.name and package["version"] == requested.version
            ],
        )
        for requested in spec.packages
    ]
    if any(len(matches) != 1 for _, matches in selected):
        message = "requested package/version does not resolve to one exact Cargo package identity"
        raise CollectionError(message)
    snapshots, originals = _freeze_packages(root, workspace, packages)
    return Prepared(
        workspace=workspace,
        resolution=resolution,
        project=project,
        context=context,
        selected=selected,
        snapshots=snapshots,
        originals=originals,
    )


def _freeze_packages(
    root: Path, workspace: Path, packages: list[dict]
) -> tuple[tuple[SourceSnapshot, ...], tuple[tuple[Path, tuple[FileEntry, ...]], ...]]:
    snapshots = []
    originals = []
    for package in packages:
        source = Path(package["manifest"]).parent
        if source == workspace:
            continue
        snapshots.append(
            freeze(
                root,
                source,
                Acquisition(
                    package=package["symbol"],
                    version=package["version"],
                    origin=package["source"] or str(source),
                    attribution=package.get("license") or "License retained in acquired source",
                ),
            )
        )
        originals.append((source, inventory(source)))
    return tuple(snapshots), tuple(originals)


def _execution(
    root: Path,
    spec: Workspace,
    prepared: Prepared,
    producers: Producers,
    lane: Literal["documentation", "mir"],
) -> Execution:
    source_key = digest_bytes(
        canonical_bytes([snapshot.source_digest for snapshot in prepared.snapshots])
    )
    context = _profile(
        spec,
        prepared.resolution,
        lane,
        source_key,
        (
            prepared.project.input_digest,
            str(prepared.resolution["lock"]),
            *(s.source_digest for s in prepared.snapshots),
        ),
    )
    key = digest_bytes(
        canonical_bytes(
            [
                asdict(spec),
                lane,
                source_key,
                context.id,
                digest_file(producers.mir),
                digest_file(producers.declarations),
                {
                    name: digest_file(Path(__file__).parent / name)
                    for name in ("rust_pipeline.py", "rust_workspace.py", "cargo_context.py")
                },
            ]
        )
    )
    directory = prepared.workspace / "runs" / key
    directory.mkdir(parents=True, exist_ok=True)
    return Execution(
        root=root,
        spec=spec,
        workspace=prepared.workspace,
        directory=directory,
        producers=producers,
        lane=lane,
        context=context,
        snapshots=tuple(s.id for s in prepared.snapshots),
        source_roots=tuple(
            (str(path), snapshot.id)
            for (path, _), snapshot in zip(prepared.originals, prepared.snapshots, strict=True)
        ),
    )


def run(
    root: Path,
    spec: Workspace,
    workspace_store: Path,
    producers: Producers,
    *,
    lane: Literal["documentation", "mir"],
) -> dict[str, object]:
    """Acquire and reconcile a finite Cargo context and every requested target.

    Returns:
        Per-target outcomes with exact source, context, process and fact receipts.

    Raises:
        CollectionError: If authority, source consistency or authoring concurrency checks fail.

    """
    from filelock import FileLock

    original = load(root)
    if not isinstance(original, KnowledgeV3):
        message = "Rust source extraction requires a V3 authority"
        raise CollectionError(message)
    before = digest_file(root / "knowledge.yaml")
    prepared = _prepare(root, spec, workspace_store, producers)
    execution = _execution(root, spec, prepared, producers, lane)
    products, dispositions = _compile(execution, prepared.selected)
    for source, entries in prepared.originals:
        if inventory(source) != entries:
            message = f"Cargo source changed during compilation: {source}"
            raise CollectionError(message)
    with FileLock(str(root / "knowledge.lock"), timeout=spec.budget.wall_seconds):
        if digest_file(root / "knowledge.yaml") != before:
            message = "authoring changed during extraction; verified products retained, attachment refused"
            raise CollectionError(message)
        save(root, _updated(execution, prepared, original, products, dispositions))
    report: dict[str, object] = {
        "state": "complete" if all(d["state"] == "complete" for d in dispositions) else "partial",
        "context": execution.context.id,
        "workspace": str(prepared.workspace),
        "project": prepared.project.id,
        "artifacts": [a.id for a in products],
        "units": dispositions,
        "source_packages": len(prepared.snapshots),
        "reuse": "unit receipt validation required; build scripts not certified hermetic",
    }
    write_atomic(execution.directory / "report.json", canonical_bytes(report))
    write_atomic(root / f"rust-{lane}-report.json", canonical_bytes(report))
    return report


def _updated(
    execution: Execution,
    prepared: Prepared,
    original: KnowledgeV3,
    products: list[FactArtifact],
    dispositions: list[dict],
) -> KnowledgeV3:
    artifacts = (prepared.project, *products)
    profiles = (
        original.profiles
        if any(p.id == execution.spec.profile for p in original.profiles)
        else (
            *original.profiles,
            Profile(
                id=execution.spec.profile,
                description=f"{execution.lane} of exact {execution.spec.id} generated Cargo context; inspect unit receipts",
            ),
        )
    )
    contexts = {p.id: p for p in (*original.semantic_profiles, prepared.context, execution.context)}
    from cattrs import Converter

    for artifact in artifacts:
        receipt = json.loads((execution.root / artifact.receipt_path).read_bytes())
        context = Converter(forbid_extra_keys=True).structure(
            receipt["semantic_profile"], SemanticProfile
        )
        contexts[context.id] = context
    heads = [
        FactHead(job=a.job, profile=a.profile, request=a.id, artifact=a.id, outcome="complete")
        for a in artifacts
    ]
    heads.extend(
        FactHead(
            job=f"{execution.spec.id}:{execution.lane}:{d['package']}",
            profile=execution.spec.profile,
            request=execution.directory.name,
            artifact=None,
            outcome="failed",
            reason=str(d.get("reason", "missing requested unit")),
        )
        for d in dispositions
        if d["state"] != "complete"
    )
    replaced = {(h.job, h.profile) for h in heads}
    return evolve(
        original,
        profiles=profiles,
        fact_artifacts=tuple(
            a for a in original.fact_artifacts if a.id not in {p.id for p in artifacts}
        )
        + artifacts,
        fact_heads=tuple(h for h in original.fact_heads if (h.job, h.profile) not in replaced)
        + tuple(heads),
        semantic_profiles=tuple(contexts.values()),
        source_snapshots=tuple(
            {s.id: s for s in (*original.source_snapshots, *prepared.snapshots)}.values()
        ),
    )


def _compile(execution: Execution, selected: list) -> tuple[list[FactArtifact], list[dict]]:
    artifacts = []
    dispositions = []
    observation = _family_check(execution) if execution.lane == "mir" else None
    for _requested, matches in selected:
        package = matches[0]
        libraries = [
            t for t in package["targets"] if set(t["kinds"]) & {"lib", "rlib", "proc-macro"}
        ]
        if len(libraries) != 1:
            dispositions.append(
                {
                    "package": package["package_id"],
                    "state": "unsupported",
                    "reason": "No unique selected library target; explicit multi-target selector required",
                }
            )
            continue
        unit_dir = execution.directory / digest_bytes(package["package_id"].encode())
        unit_dir.mkdir(parents=True, exist_ok=True)
        try:
            values, observations = _unit(execution, unit_dir, package, observation)
            artifacts.extend(values)
            dispositions.append(
                {
                    "package": package["package_id"],
                    "target": libraries[0],
                    "state": "complete",
                    "facts": [a.id for a in values],
                    "observations": observations,
                }
            )
        except (CollectionError, OSError, ValueError) as error:
            dispositions.append(
                {
                    "package": package["package_id"],
                    "target": libraries[0],
                    "state": "failed",
                    "reason": str(error),
                    "artifacts": str(unit_dir),
                }
            )
    return (artifacts, dispositions)


def _unit(
    execution: Execution, directory: Path, package: dict, observation: dict[str, object] | None
) -> tuple[list[FactArtifact], dict]:
    units = (execution.directory if execution.lane == "mir" else directory) / "units"
    units.mkdir(exist_ok=True)
    if observation is None:
        environment = (
            ("LDE_MIR_OUTPUT", str(units)),
            ("LDE_MIR_CONTEXT", execution.context.id),
        )
        arguments, environment = _arguments(execution, directory, package, environment)
        observation = invoke(
            execution.spec,
            execution.workspace,
            arguments,
            directory.name + "-" + execution.lane,
            options=InvocationOptions(environment=environment),
        )
    if observation["returncode"]:
        message = (
            f"Cargo {execution.lane} failed ({observation['returncode']}): {observation['stderr']}"
        )
        raise CollectionError(message)
    invocations = [json.loads(path.read_bytes()) for path in units.glob("*.invocation.json")]
    selected = [
        row
        for row in invocations
        if row["invocation"]["environment"].get("CARGO_PKG_NAME") == package["symbol"]
        and row["invocation"]["purpose"] == execution.lane
    ]
    if len(selected) != 1 or not selected[0]["success"]:
        message = "successful Cargo exit has no unique matching extractor invocation receipt"
        raise CollectionError(message)
    invocation = selected[0]["invocation"]
    _check_unit_features(package, invocation)
    raw, helper, schema, kind = _raw(execution, units, invocation)
    witnesses = _witnesses(execution, directory, observation, invocation)
    artifact = extract(
        execution.root,
        SourceJob(
            id=f"{execution.spec.id}:{execution.lane}:{package['package_id']}",
            kind=kind,
            input=str(raw),
            helper=str(helper.resolve()),
            profile=execution.spec.profile,
            schema=str(_SCHEMAS / schema),
            semantic_profile=_unit_context(execution.context, invocation, package),
            snapshots=execution.snapshots,
            witnesses=witnesses,
        ),
        execution.spec.budget,
    )
    messages = extract(
        execution.root,
        SourceJob(
            id=f"{execution.spec.id}:{execution.lane}:messages:{package['package_id']}",
            kind="cargo_messages",
            input=str(observation["stdout"]),
            helper=str(execution.producers.declarations.resolve()),
            profile=execution.spec.profile,
            schema=str(_SCHEMAS / "cargo-messages.v1.schema.json"),
            semantic_profile=execution.context,
        ),
        execution.spec.budget,
    )
    return (
        [artifact, messages],
        {
            "process": observation,
            "invocation": selected[0],
            "artifact": str(raw),
            "artifact_digest": digest_file(raw),
        },
    )


def _unit_context(family: SemanticProfile, invocation: dict, package: dict) -> SemanticProfile:
    settings = tuple(s for s in family.settings if s.name != "unit_settings")
    settings += (
        Setting(
            name="unit_settings", value=canonical_bytes(invocation).decode(), origin="observed"
        ),
    )
    return identify(
        evolve(
            family,
            id="",
            settings=settings,
            package=package["package_id"],
            version=package["version"],
        )
    )


def _witnesses(
    execution: Execution, directory: Path, observation: dict, invocation: dict
) -> tuple[FileEntry, ...]:
    material = {
        "invocation": invocation,
        "process": observation,
        "source_roots": execution.source_roots,
        "snapshot_join": "Exact original source root plus relative path and matching file digest; no basename or fuzzy matches",
    }
    path = directory / ("provenance-" + digest_bytes(canonical_bytes(material)) + ".json")
    write_atomic(path, canonical_bytes(material))
    files = (
        (path, "unit_provenance"),
        (execution.workspace / "Cargo.lock", "cargo_lock"),
        (execution.workspace / "Cargo.toml", "extraction_manifest"),
        (Path(observation["stdout"]), "cargo_messages"),
        (Path(observation["stderr"]), "cargo_diagnostics"),
    )
    return tuple(
        FileEntry(path=str(path), digest=digest_file(path), size=path.stat().st_size, kind=role)
        for path, role in files
    )


def _arguments(
    execution: Execution, directory: Path, package: dict, environment: tuple[tuple[str, str], ...]
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    if execution.lane == "documentation":
        from library_deep_enrichment.processes import execute

        info = execute(
            (str(execution.producers.mir.resolve()), "toolchain"), cwd=execution.workspace
        )
        if info.returncode:
            message = "pinned compiler adapter could not identify its sysroot"
            raise CollectionError(message)
        rustdoc = Path(json.loads(info.stdout)["sysroot"]) / "bin/rustdoc"
        environment += (
            ("RUSTDOC", str(execution.producers.mir.resolve())),
            ("LDE_RUSTDOC_REAL", str(rustdoc)),
        )
        flags = ("--document-private-items",) if execution.spec.doc_policy != "public_docs" else ()
        if execution.spec.doc_policy == "private_hidden_docs":
            flags += ("--document-hidden-items",)
        environment += (
            ("RUSTDOCFLAGS", " ".join(("-Zunstable-options", "--output-format=json", *flags))),
        )
        arguments = (
            "doc",
            "--offline",
            "--locked",
            "--no-deps",
            "--package",
            "library-guides-extraction-root",
            "--package",
            package["package_id"],
            *_feature_arguments(execution.spec, package),
            "--lib",
            "--target",
            execution.spec.target,
            "--target-dir",
            str(directory / "target"),
            "--message-format=json",
        )
    else:
        environment += (
            ("RUSTC_WRAPPER", str(execution.producers.mir.resolve())),
            ("LDE_MIR_PACKAGES", f"{package['symbol']}@{package['version']}"),
        )
        arguments = (
            "check",
            "--offline",
            "--locked",
            "--package",
            package["package_id"],
            "--lib",
            "--target",
            execution.spec.target,
            "--target-dir",
            str(directory / "target"),
            "--message-format=json",
        )
    return arguments, environment


def _family_check(execution: Execution) -> dict[str, object]:
    units = execution.directory / "units"
    units.mkdir(exist_ok=True)
    env = (
        ("LDE_MIR_OUTPUT", str(units)),
        ("LDE_MIR_CONTEXT", execution.context.id),
        ("RUSTC_WRAPPER", str(execution.producers.mir.resolve())),
        (
            "LDE_MIR_PACKAGES",
            ",".join(f"{p.name}@{p.version}" for p in execution.spec.packages),
        ),
    )
    arguments = (
        "check",
        "--offline",
        "--locked",
        "--lib",
        "--target",
        execution.spec.target,
        "--target-dir",
        str(execution.directory / "target"),
        "--message-format=json",
    )
    return invoke(
        execution.spec,
        execution.workspace,
        arguments,
        execution.directory.name + "-mir",
        InvocationOptions(environment=env),
    )


def _raw(
    execution: Execution, units: Path, invocation: dict
) -> tuple[Path, Path, str, Literal["declarations", "mir"]]:
    if execution.lane == "documentation":
        argv = invocation["argv"]
        output = Path(argv[argv.index("-o") + 1])
        name = argv[argv.index("--crate-name") + 1]
        raw = output / (name + ".json")
        helper = execution.producers.declarations
        schema = "declaration.v1.schema.json"
        kind = "declarations"
    else:
        raw = units / (invocation["id"] + ".frames")
        helper = execution.producers.mir
        schema = "mir.v1.schema.json"
        kind = "mir"
    return raw, helper, schema, kind


def _feature_arguments(spec: Workspace, package: dict) -> tuple[str, ...]:
    features = package.get("resolved_features")
    if features is None:
        message = "local selected-package compilation requires resolved family features"
        raise CollectionError(message)
    alias = next(
        f"dependency_{i}"
        for i, p in enumerate(spec.packages)
        if (p.name, p.version) == (package["symbol"], package["version"])
    )
    return (
        (
            "--no-default-features",
            "--features",
            ",".join(alias + "/" + feature for feature in features),
        )
        if features
        else ("--no-default-features",)
    )


def _check_unit_features(package: dict, invocation: dict) -> None:
    argv = invocation["argv"]
    cfgs = [argv[i + 1] for i, value in enumerate(argv[:-1]) if value == "--cfg"]
    cfgs.extend(value.removeprefix("--cfg=") for value in argv if value.startswith("--cfg="))
    observed = sorted(
        value.removeprefix('feature="').removesuffix('"')
        for value in cfgs
        if value.startswith('feature="')
    )
    expected = package.get("resolved_features")
    if expected is None or observed != sorted(expected):
        message = f"actual unit features differ from the requested family resolution: {package['package_id']}: expected {expected}, observed {observed}"
        raise CollectionError(message)

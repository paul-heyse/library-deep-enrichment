"""Isolated, manifest-driven Cargo workspaces shared by local Rustdoc and MIR."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from attrs import asdict, field, frozen
from cattrs import Converter
from filelock import FileLock
from jsonschema import Draft202012Validator

from library_deep_enrichment import cargo_context
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.schemas import schema_for
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes, digest_file
from library_deep_enrichment.store.staging import write_atomic
from library_deep_enrichment.worker_runtime import WorkerRequest


@frozen(kw_only=True)
class Package:
    """An exact dependency request; aliases prevent identity collapse."""

    name: str
    version: str
    features: tuple[str, ...] = ()
    default_features: bool = True


@frozen(kw_only=True)
class Workspace:
    """Finite requested context, distinct from observed Cargo units."""

    schema_version: Literal["library-guides.rust-workspace.v1"]
    id: str
    toolchain: str
    target: str
    packages: tuple[Package, ...]
    profile: str
    rustflags: tuple[str, ...] = ()
    doc_policy: Literal["public_docs", "private_docs", "private_hidden_docs"] = (
        "private_hidden_docs"
    )
    jobs: int = 4
    budget: Budget = field(
        factory=lambda: Budget(
            wall_seconds=1800, cpu_seconds=600, memory_bytes=8_000_000_000, stderr_bytes=5_000_000
        )
    )


@frozen(kw_only=True)
class InvocationOptions:
    """Declared process policy and producer environment for one Cargo operation."""

    isolate: bool = True
    environment: tuple[tuple[str, str], ...] = ()
    write_roots: tuple[Path, ...] = ()


def read(path: Path) -> Workspace:
    """Validate a finite Rust extraction workspace request.

    Returns:
        Typed package, toolchain, feature and target choices.

    Raises:
        CollectionError: If selections are empty, duplicate or unpinned.

    """
    raw = yaml.safe_load(path.read_bytes())
    Draft202012Validator(schema_for(Workspace)).validate(raw)
    value = Converter(forbid_extra_keys=True).structure(raw, Workspace)
    keys = [(package.name, package.version) for package in value.packages]
    if (
        not keys
        or len(set(keys)) != len(keys)
        or not value.toolchain.startswith("nightly-20")
        or not value.target
        or value.jobs <= 0
    ):
        message = "workspace requires finite unique packages, dated nightly, explicit target and positive jobs"
        raise CollectionError(message)
    if any(
        not p.name or not p.version or any(token in p.version for token in "*^~><= ")
        for p in value.packages
    ):
        message = "workspace package versions must be exact"
        raise CollectionError(message)
    return value


def _manifest(spec: Workspace) -> bytes:
    lines = [
        "[package]",
        'name = "library-guides-extraction-root"',
        'version = "0.0.0"',
        'edition = "2024"',
        "publish = false",
        "",
        "[workspace]",
        'resolver = "3"',
        "",
        "[dependencies]",
    ]
    for index, package in enumerate(spec.packages):
        values = {
            "package": package.name,
            "version": "=" + package.version,
            "default-features": package.default_features,
            "features": list(package.features),
        }
        fields = ", ".join(f"{key} = {json.dumps(value)}" for key, value in values.items())
        lines.append(f"dependency_{index} = {{ {fields} }}")
    return ("\n".join(lines) + "\n").encode()


def prepare(spec: Workspace, store: Path) -> tuple[Path, dict[str, object]]:
    """Acquire exact resolution once into a private generated workspace.

    Returns:
        Workspace and verified resolution receipt; acquisition is the network-enabled stage.

    Raises:
        CollectionError: If resolution fails or an existing immutable workspace changed.

    """
    key = digest_bytes(canonical_bytes(asdict(spec)))
    destination = store / key
    store.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination) + ".lock", timeout=spec.budget.wall_seconds):
        if (destination / "resolution.json").is_file():
            receipt = json.loads((destination / "resolution.json").read_bytes())
            _verify_workspace(destination, receipt)
            return destination, receipt
        staging = Path(tempfile.mkdtemp(prefix="resolve-", dir=store)).resolve()
        (staging / "src").mkdir()
        write_atomic(staging / "Cargo.toml", _manifest(spec))
        write_atomic(staging / "src/lib.rs", b"//! Isolated dependency extraction root.\n")
        receipt = invoke(
            spec,
            staging,
            ("generate-lockfile",),
            "resolve",
            options=InvocationOptions(isolate=False),
        )
        if receipt["returncode"]:
            message = f"Cargo resolution failed; diagnostics retained at {staging}"
            raise CollectionError(message)
        fetched = invoke(
            spec,
            staging,
            ("fetch", "--locked", "--target", spec.target),
            "fetch",
            options=InvocationOptions(isolate=False),
        )
        if fetched["returncode"]:
            message = f"Cargo acquisition failed; diagnostics retained at {staging}"
            raise CollectionError(message)
        receipt: dict[str, object] = {
            "key": key,
            "requested": asdict(spec),
            "manifest": digest_file(staging / "Cargo.toml"),
            "lock": digest_file(staging / "Cargo.lock"),
            "harness": digest_file(staging / "src/lib.rs"),
            "acquisition": [receipt, fetched],
            "state": "resolved",
            "effective_units": "not_observed",
            "hermeticity": "uncontrolled-build-inputs-not-yet-qualified",
        }
        write_atomic(staging / "resolution.json", canonical_bytes(receipt))
        if destination.exists():
            message = "incomplete workspace occupies immutable destination"
            raise CollectionError(message)
        staging.rename(destination)
    return destination, receipt


def _verify_workspace(root: Path, receipt: dict[str, object]) -> None:
    expected = {
        "Cargo.toml": receipt["manifest"],
        "Cargo.lock": receipt["lock"],
        "src/lib.rs": receipt["harness"],
    }
    if any(digest_file(root / path) != digest for path, digest in expected.items()):
        message = "generated workspace or resolved lock changed"
        raise CollectionError(message)


def invoke(
    spec: Workspace,
    root: Path,
    arguments: tuple[str, ...],
    label: str,
    options: InvocationOptions = InvocationOptions(),
) -> dict[str, object]:
    """Run Cargo with explicit environment, literal arguments and retained raw streams.

    Returns:
        Actual process observation, never an inferred semantic extraction outcome.

    Raises:
        CollectionError: If Cargo or an explicitly named toolchain is unavailable.

    """
    cargo = shutil.which("cargo")
    if cargo is None:
        message = "Cargo is required for the selected source lane"
        raise CollectionError(message)
    root = root.resolve()
    env = cargo_context.environment()
    env.update(options.environment)
    env["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(spec.rustflags)
    env["CARGO_BUILD_JOBS"] = str(spec.jobs)
    toolchain = Path(env["RUSTUP_HOME"]) / "toolchains"
    cache = Path(env["CARGO_HOME"])
    read_roots = (
        cache,
        toolchain.parent,
        Path(cargo).parent,
        *(
            Path(value).parent
            for key, value in options.environment
            if key in {"RUSTC_WRAPPER", "RUSTDOC"}
        ),
    )
    if options.isolate:
        private_cache = root / "cargo-home"
        private_cache.mkdir(exist_ok=True)
        for name in ("registry", "git"):
            link = private_cache / name
            if (cache / name).exists() and not link.exists():
                link.symlink_to(cache / name, target_is_directory=True)
        env["CARGO_HOME"] = str(private_cache)
    boundary = arguments.index("--") if "--" in arguments else len(arguments)
    argv = (
        cargo,
        "+" + spec.toolchain,
        *arguments[:boundary],
        "--manifest-path",
        str(root / "Cargo.toml"),
        *arguments[boundary:],
    )
    request = WorkerRequest(
        argv=argv,
        cwd=root,
        request_id=label,
        input_digest=digest_file(root / "Cargo.toml"),
        budget=spec.budget,
        isolate=options.isolate,
        read_roots=read_roots,
        write_roots=(root, *options.write_roots),
    )
    observations = root / "observations"
    observations.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=label + "-", dir=observations))
    result = cargo_context.capture(request, directory, env)
    write_atomic(directory / "receipt.json", canonical_bytes(result))
    return result

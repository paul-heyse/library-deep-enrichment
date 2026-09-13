"""Real pinned Cargo/compiler contexts, feature conflicts and retained-byte replay controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Literal

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.compilation import analyze, validate
from library_deep_enrichment.analyses.compilation_contracts import (
    CompilationPopulation,
    CompilationRequest,
)
from library_deep_enrichment.analyses.compilation_inputs import (
    absolute,
    catalogs,
    inputs,
    invocation,
)
from library_deep_enrichment.analyses.compilation_join import JoinInput, candidates, features
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeArtifact
from library_deep_enrichment.corpus.schemas import REGISTRY, revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.corpus.validation import AdmissionReader
from library_deep_enrichment.facts.compiler_invocation import arguments, read
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.compilation import build
from tests.test_native_lanes import SCHEMAS, _binary


def _witness(path: Path, kind: str) -> FileEntry:
    return FileEntry(path=str(path), digest=digest_file(path), size=path.stat().st_size, kind=kind)


def _extract(
    root: Path,
    kind: Literal["mir_execution", "cargo", "cargo_messages"],
    path: Path,
    witnesses: tuple[FileEntry, ...],
) -> FactArtifact:
    modes = {
        "mir_execution": ("mir-facts", "mir-execution.v1.schema.json"),
        "cargo": ("rustdoc", "cargo.v1.schema.json"),
        "cargo_messages": ("rustdoc", "cargo-messages.v1.schema.json"),
    }
    helper, schema = modes[kind]
    return extract(
        root,
        SourceJob(
            id=path.stem + ":" + kind,
            kind=kind,
            input=str(path),
            helper=str(_binary(helper)),
            profile="compilation-controls",
            schema=str(SCHEMAS / schema),
            witnesses=witnesses,
        ),
        Budget(),
    )


@pytest.fixture(scope="module")
def compilation_case(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, tuple[FactArtifact, ...]]:
    """Compile real feature variants with two dependency versions in one Cargo resolution.

    Returns:
        Exact native transport artifacts including original invocation and source witnesses.

    """
    root = tmp_path_factory.mktemp("compilation-context")
    (root / "src").mkdir()
    (root / "src/lib.rs").write_text(
        '#[cfg(feature="base")] pub fn mode() -> u8 { 1 }\n#[cfg(not(feature="base"))] pub fn mode() -> u8 { 2 }\n'
    )
    (root / "Cargo.toml").write_text(
        '[package]\nname="compilation_fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\nexclude=["old", "new"]\n[features]\ndefault=["base"]\nbase=[]\nalternate=[]\n[dependencies]\nlegacy={package="same_name",path="old"}\nlatest={package="same_name",path="new"}\n'
    )
    for directory, version in (("old", "1.0.0"), ("new", "2.0.0")):
        package = root / directory
        (package / "src").mkdir(parents=True)
        (package / "src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n")
        (package / "Cargo.toml").write_text(
            f'[package]\nname="same_name"\nversion="{version}"\nedition="2024"\n'
        )
    artifacts = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RUSTC_WRAPPER", str(_binary("mir-facts")))
        patch.setenv("LDE_MIR_BEHAVIOR", "1")
        patch.setenv("LDE_MIR_PACKAGES", "compilation_fixture@0.1.0")
        patch.setenv("CARGO_BUILD_JOBS", "1")
        for label, flags in (
            ("default", ()),
            ("alternate", ("--no-default-features", "--features", "alternate")),
        ):
            frames = root / (label + "-frames")
            patch.setenv("LDE_MIR_CONTEXT", "context:" + label)
            patch.setenv("LDE_MIR_OUTPUT", str(frames))
            result = execute(
                (
                    "cargo",
                    "+nightly-2026-08-18",
                    "build",
                    "--offline",
                    "--lib",
                    "--message-format=json",
                    *flags,
                ),
                cwd=root,
                timeout=120,
            )
            assert result.returncode == 0, result.stderr.decode()
            messages = root / (label + "-messages.jsonl")
            messages.write_bytes(result.stdout)
            metadata = execute(
                (
                    "cargo",
                    "+nightly-2026-08-18",
                    "metadata",
                    "--offline",
                    "--locked",
                    "--format-version=1",
                    *flags,
                ),
                cwd=root,
                timeout=120,
            )
            assert metadata.returncode == 0, metadata.stderr.decode()
            metadata_path = root / (label + "-metadata.json")
            metadata_path.write_bytes(metadata.stdout)
            frame = tuple(frames.glob("*.frames"))
            assert len(frame) == 1
            witnesses = (
                _witness(root / "src/lib.rs", "rust"),
                _witness(frame[0].with_suffix(".invocation.json"), "compiler_invocation"),
                _witness(root / "Cargo.toml", "build_context"),
                _witness(root / "Cargo.lock", "build_context"),
            )
            artifacts.extend(
                (
                    _extract(root, "mir_execution", frame[0], witnesses),
                    _extract(root, "cargo", metadata_path, witnesses[-2:]),
                    _extract(root, "cargo_messages", messages, witnesses[-2:]),
                )
            )
    return root, tuple(artifacts)


def _corpus(
    tmp_path: Path, case: tuple[Path, tuple[FactArtifact, ...]]
) -> tuple[Corpus, CompilationRequest]:
    root, artifacts = case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts))
    native = tuple(
        item
        for item in corpus.reader().records("native_artifacts")
        if isinstance(item, NativeArtifact)
    )
    return corpus, CompilationRequest(
        logical_id="compilation-controls",
        profile="compilation-controls",
        executables=tuple(
            revision_of(item) for item in native if item.schema == "library-guides.mir-execution.v1"
        ),
        metadata=tuple(
            revision_of(item) for item in native if item.schema == "library-guides.cargo.v1"
        ),
        messages=tuple(
            revision_of(item)
            for item in native
            if item.schema == "library-guides.cargo-messages.v1"
        ),
    )


def test_real_compilation_feature_context_and_portable_replay(
    compilation_case: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """Distinct features retain distinct units and conflicts; export needs no acquisition paths."""
    corpus, request = _corpus(tmp_path, compilation_case)
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    result = next(corpus.reader().records("compilation_populations"))
    assert isinstance(result, CompilationPopulation)
    assert len(result.units) == len(request.executables)
    assert len({unit.invocation for unit in result.units}) == len(result.units)
    assert len({unit.context for unit in result.units}) == len(result.units)
    for unit in result.units:
        assert all(item.source for item in unit.inputs)
        assert {item.state for item in unit.candidates} == {
            "target_and_output_recipe_correspondence",
            "compiled_feature_conflict",
        }
        assert all(
            item.package_id.endswith("compilation_fixture@0.1.0") for item in unit.candidates
        )
        assert all(
            {setting.name for setting in item.declared_features} == {"default", "base", "alternate"}
            for item in unit.candidates
        )
        enabled = next(item for item in unit.settings if item.name == "enabled_feature_cfgs")
        assert enabled.values in {("base", "default"), ("alternate",)}
    assert not result.commands  # Missing command witnesses never imply default requests.
    with pytest.raises(CorpusError, match="original-observation replay"):
        validate(corpus.reader(), (evolve(result, units=()),))
    reverse = AdmissionReader(
        corpus.reader(),
        {
            "native_facts": [
                REGISTRY["native_facts"].encode(item)
                for item in reversed(tuple(corpus.reader().records("native_facts")))
            ]
        },
        replace=False,
    )
    assert analyze(reverse, request) == result
    archive = tmp_path / "portable"
    receipt = export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive) == receipt.manifest
    # Replaying after moving the source tree proves that no original path is opened.
    root, _ = compilation_case
    moved = root.with_name(root.name + "-moved")
    root.rename(moved)
    try:
        assert analyze(restored.reader("release"), request) == result
    finally:
        moved.rename(root)


def test_compiler_identity_and_opaque_argument_controls(
    compilation_case: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """Original compiler IDs detect context mutations; option values cannot inject flags."""
    root, _ = compilation_case
    raw = json.loads(next((root / "default-frames").glob("*.invocation.json")).read_bytes())
    observed = read(raw)
    mutated = copy.deepcopy(raw)
    mutated["invocation"]["execution_context"]["working_directory"] += "/changed"
    with pytest.raises(CollectionError, match="original identity"):
        read(mutated)
    mutated = copy.deepcopy(raw)
    mutated["invocation"]["execution_context"]["schema"] = "future-unsupported"
    with pytest.raises(CollectionError, match="unsupported compiler execution"):
        read(mutated)
    parsed = arguments(
        evolve(
            observed,
            argv=(
                "rustc",
                "--extern",
                "--cfg",
                "--check-cfg",
                'cfg(feature, values("fake"))',
                "--cfg",
                'feature="real"',
            ),
        )
    )
    assert parsed.values("--extern") == ("--cfg",)
    assert features(parsed).values == ("real",)
    assert (
        features(
            arguments(evolve(observed, argv=("rustc", "@args", "--cfg", 'feature="real"')))
        ).state
        == "partial_option_observation"
    )
    assert (
        arguments(evolve(observed, argv=("rustc", "--future", "--cfg", 'feature="fake"'))).values(
            "--cfg"
        )
        == ()
    )
    with pytest.raises(CollectionError, match="lacks its value"):
        arguments(evolve(observed, argv=("rustc", "--cfg")))


def test_real_legacy_invocation_keeps_context_unobserved(
    compilation_case: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """A native legacy capture verifies its own identity without inventing the new context."""
    root, _ = compilation_case
    current = read(
        json.loads(next((root / "default-frames").glob("*.invocation.json")).read_bytes())
    )
    output = root / "legacy-frames"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LDE_MIR_OUTPUT", str(output))
        patch.setenv("LDE_MIR_CONTEXT", "legacy-control")
        patch.delenv("LDE_MIR_BEHAVIOR", raising=False)
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        result = execute(
            (
                str(_binary("mir-facts")),
                current.argv[0],
                "--crate-name",
                "legacy_control",
                "--crate-type",
                "lib",
                str(root / "src/lib.rs"),
                "-o",
                str(root / "legacy.rlib"),
            ),
            cwd=root,
            timeout=120,
        )
    assert result.returncode == 0, result.stderr.decode()
    legacy = read(json.loads(next(output.glob("*.invocation.json")).read_bytes()))
    assert legacy.execution is None
    assert "working_directory_and_original_provider_unobserved" in legacy.frontier


def test_compilation_missing_and_wrong_source_witnesses(
    compilation_case: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """Missing original observations stay unresolved; wrong bytes cannot satisfy a unit join."""
    corpus, request = _corpus(tmp_path, compilation_case)
    selected = catalogs(corpus.reader(), request)
    catalog = selected[request.executables[0]]
    retained = invocation(catalog)
    assert retained is not None
    observed, _ = retained
    assert all(item.source for item in inputs(catalog, observed))
    assert all(not item.source for item in inputs(evolve(catalog, paths={}), observed))
    assert observed.execution is not None
    source_path = absolute(next(iter(dict(observed.inputs))), observed.execution.working_directory)
    source = catalog.paths[source_path]
    with pytest.raises(CorpusError, match="source bytes differ"):
        inputs(evolve(catalog, paths={source_path: evolve(source, digest="0" * 64)}), observed)
    receipt = {key: value for key, value in catalog.receipt.items() if key != "witness_origins"}
    assert invocation(evolve(catalog, receipt=receipt)) is None
    no_cargo = analyze(corpus.reader(), evolve(request, metadata=(), messages=()))
    assert all(
        not unit.candidates and unit.state == "observed_invocation_cargo_unresolved"
        for unit in no_cargo.units
    )


def test_compilation_output_and_opaque_package_controls(
    compilation_case: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """Similar package names and targets cannot replace an exact opaque ID and output recipe."""
    corpus, request = _corpus(tmp_path, compilation_case)
    selected = catalogs(corpus.reader(), request)
    packages = [raw for key in request.metadata for _, raw in selected[key].rows]
    assert {raw["version"] for raw in packages if raw["symbol"] == "same_name"} == {
        "1.0.0",
        "2.0.0",
    }
    catalog = selected[request.executables[0]]
    retained = invocation(catalog)
    assert retained is not None
    observed, _ = retained
    unit = JoinInput(
        observed=observed, parsed=arguments(observed), inputs=inputs(catalog, observed)
    )
    for key in request.messages:
        item = selected[key]
        rows = copy.deepcopy(item.rows)
        for _, raw in rows:
            message = raw.get("observation", {})
            if message.get("kind") == "artifact":
                message["filenames"] = ["/different-build/same-looking.rlib"]
        selected[key] = evolve(item, rows=rows)
    assert {item.state for item in candidates(selected, request, unit)} == {
        "output_recipe_unresolved",
        "compiled_feature_conflict",
    }
    for key in request.messages:
        for _, raw in selected[key].rows:
            if raw.get("observation", {}).get("kind") == "artifact":
                raw["observation"]["package_id"] = "opaque-unrelated-package-id"
    assert all(
        item.state == "metadata_target_candidate" and not item.message
        for item in candidates(selected, request, unit)
    )

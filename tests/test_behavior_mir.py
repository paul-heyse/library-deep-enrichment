"""Pinned Rust compiler identities and cross-unit guarded transfer controls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorRequest,
    BehaviorSummary,
    Outcome,
)
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.behavior import build
from tests.test_native_lanes import SCHEMAS, _binary, _records

DEPENDENCY = """
pub struct Packet { pub enabled: bool, pub value: u32 }
pub fn choose(packet: Packet) -> u32 { if packet.enabled { packet.value } else { 0 } }
pub fn greater(value: u32) -> bool { value > 4 }
pub fn checked(value: u8) -> u8 { value + 1 }
pub fn width<const N: usize>(_: [u8; N]) -> usize { N }
pub fn width_three() -> usize { width([0; 3]) }
#[repr(i8)]
pub enum Tag { Low = -3, High = 5 }
pub fn classify(tag: Tag) -> u8 { match tag { Tag::Low => 0, Tag::High => 1 } }
"""
CONSUMER = """
extern crate behavior_dependency;
pub fn wrapper(packet: behavior_dependency::Packet) -> u32 { behavior_dependency::choose(packet) }
"""


@pytest.fixture(scope="module")
def native_cases(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, tuple[FactArtifact, ...]]:
    """Compile independently owned units through the real compiler wrapper.

    Returns:
        Retained source-attached artifacts under one explicit invocation context.

    """
    root = tmp_path_factory.mktemp("behavior-native")
    sysroot = Path(
        json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=root).stdout)["sysroot"]
    )
    artifacts = []
    sources = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LDE_MIR_CONTEXT", "behavior-cross-unit-controls")
        patch.setenv("LDE_MIR_BEHAVIOR", "1")
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        cases = (
            ("behavior_dependency", DEPENDENCY),
            ("behavior_consumer", CONSUMER),
            ("behavior_dependency", DEPENDENCY.replace("if packet.enabled", "if !packet.enabled")),
        )
        for index, (name, text) in enumerate(cases):
            source = root / f"{name}.rs"
            source.write_text(text)
            if source not in sources:
                sources.append(source)
            output = root / f"{name}-{index}"
            patch.setenv("LDE_MIR_OUTPUT", str(output))
            argv = [
                str(_binary("mir-facts")),
                str(sysroot / "bin/rustc"),
                "--crate-name",
                name,
                "--crate-type",
                "lib",
                "--edition=2024",
                "-o",
                str(root / f"lib{name}.rlib"),
                str(source),
            ]
            if name == "behavior_consumer":
                argv.extend(("--extern", f"behavior_dependency={root}/libbehavior_dependency.rlib"))
            result = execute(tuple(argv), cwd=root, timeout=120)
            assert result.returncode == 0, result.stderr.decode()
            frames = tuple(output.glob("*.frames"))
            assert len(frames) == 1
            witnesses = tuple(
                FileEntry(
                    path=str(path), digest=digest_file(path), size=path.stat().st_size, kind="rust"
                )
                for path in sources
            )
            artifacts.append(
                extract(
                    root,
                    SourceJob(
                        id=f"{name}-{index}",
                        kind="mir_execution",
                        input=str(frames[0]),
                        helper=str(_binary("mir-facts")),
                        profile="behavior-native",
                        schema=str(SCHEMAS / "mir-execution.v1.schema.json"),
                        witnesses=witnesses,
                    ),
                    Budget(),
                )
            )
    return root, tuple(artifacts)


def test_native_typed_operators_and_const_arguments(
    native_cases: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """Check actual compiler scalar operations and a concrete const-generic invocation."""
    root, artifacts = native_cases
    rows = {row["symbol"]: row for artifact in artifacts for row in _records(root, artifact)}
    greater = next(value for key, value in rows.items() if key.endswith("::greater"))
    assert any(
        op["operator"] == "greater" and op["mode"] == "ordinary"
        for op in greater["behavior"]["operators"]
    )
    checked = next(value for key, value in rows.items() if key.endswith("::checked"))
    assert any(
        op["operator"] == "add" and op["mode"] == "checked_pair"
        for op in checked["behavior"]["operators"]
    )
    caller = next(value for key, value in rows.items() if key.endswith("::width_three"))
    assert any(
        arg["kind"] == "constant" and arg["value"] == "3" and arg["frontier"] is None
        for call in caller["behavior"]["calls"]
        for arg in call["substitutions"]
    )


def test_native_logical_members_and_signed_discriminants(
    native_cases: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """The compiler supplies member names and enum tags independently of display-name heuristics."""
    from library_deep_enrichment.analyses.behavior.mir_types import nominals, target_types

    root, artifacts = native_cases
    rows = _records(root, artifacts[0])
    owner = next(row for row in rows if row["symbol"].endswith("::choose"))
    packet = next(
        item for item in owner["behavior"]["nominals"] if item["name"].endswith("::Packet")
    )
    assert [item["name"] for item in packet["variants"][0]["fields"]] == ["enabled", "value"]
    assert all(
        item["definition"].startswith("definition:") for item in packet["variants"][0]["fields"]
    )
    classified = next(row for row in rows if row["symbol"].endswith("::classify"))
    metadata = target_types(
        classified["behavior"], classified["behavior"]["target"]["pointer_bits"]
    )
    assert isinstance(metadata, dict)
    tag = next(item for item in nominals(metadata) if item.name.endswith("::Tag"))
    assert {item.name: item.discriminant for item in tag.variants} == {"Low": "-3", "High": "5"}
    assert {item.discriminant_type for item in tag.variants} == {"rust:i8"}


def test_cross_unit_guards_and_fields_are_composed(
    native_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """Propagate a receiver field relationship using matching compiler identities across crates."""
    root, artifacts = native_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts[:2]))
    reader = corpus.reader()
    owners = tuple(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact) and item.symbol.endswith(("::choose", "::wrapper"))
    )
    expected_owners = 2
    assert len(owners) == expected_owners
    request = BehaviorRequest(
        logical_id="cross-unit",
        profile="behavior-native",
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=tuple(sorted({item.artifact for item in owners})),
    )
    result = build(corpus, request)
    assert not result.reused
    summaries = tuple(
        item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary)
    )
    assert len(summaries) == expected_owners
    assert any(len(item.dependencies) == expected_owners for item in summaries)
    for summary in summaries:
        assert all(clause.outcome == Outcome.RETURN for clause in summary.clauses)
        assert all(clause.guards for clause in summary.clauses)
        assert {summary.terms[clause.result].op for clause in summary.clauses} == {
            "field",
            "literal",
        }
    raw = [json.loads(resolve_bytes(reader, item.original, max_bytes=1_000_000)) for item in owners]
    callee = next(item for item in raw if item["symbol"].endswith("::choose"))
    caller = next(item for item in raw if item["symbol"].endswith("::wrapper"))
    assert caller["behavior"]["calls"][0]["target"] == callee["behavior"]["definition"]


def test_same_definition_from_wrong_compiled_source_does_not_close_call(
    native_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """A same-name callee from changed source cannot satisfy the old caller's target build."""
    from library_deep_enrichment.analyses.behavior.contracts import Precision

    root, artifacts = native_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts[1:]))
    reader = corpus.reader()
    owners = tuple(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact) and item.symbol.endswith(("::choose", "::wrapper"))
    )
    request = BehaviorRequest(
        logical_id="wrong-build",
        profile="behavior-native",
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=tuple(sorted({item.artifact for item in owners})),
    )
    build(corpus, request)
    summaries = tuple(
        item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary)
    )
    unresolved = tuple(item for item in summaries if item.precision == Precision.CONSERVATIVE)
    assert unresolved
    assert any(
        effect.kind == "unknown_call"
        for item in unresolved
        for clause in item.clauses
        for effect in clause.effects
    )

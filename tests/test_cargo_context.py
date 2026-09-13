"""Real Cargo identity controls for virtual workspaces, targets, aliases and graph omission."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.processes import execute
from library_deep_enrichment.source_pipeline import SourceJob, extract

TOOLING = Path(__file__).parents[1]
pytestmark = pytest.mark.native_lanes


def _workspace(root: Path) -> Path:
    files = {
        "Cargo.toml": '[workspace]\nmembers=["app","macros"]\nexclude=["v1","v2"]\nresolver="3"\n',
        "app/Cargo.toml": '[package]\nname="identity-app"\nversion="1.0.0"\nedition="2024"\n[dependencies]\nleft={package="shared",path="../v1",features=["fast"]}\nright={package="shared",path="../v2"}\n[dev-dependencies]\nleft={package="shared",path="../v1"}\n[build-dependencies]\nowned-macros={path="../macros"}\n[[example]]\nname="feature-example"\nrequired-features=["example-feature"]\n[features]\nexample-feature=[]\n',
        "app/src/lib.rs": "pub fn value() -> u8 { left::value() + right::value() }\n",
        "app/src/main.rs": "fn main() {}\n",
        "app/examples/feature-example.rs": "fn main() {}\n",
        "app/build.rs": "fn main() {}\n",
        "macros/Cargo.toml": '[package]\nname="owned-macros"\nversion="1.0.0"\nedition="2024"\n[lib]\nproc-macro=true\n',
        "macros/src/lib.rs": "",
        "v1/Cargo.toml": '[package]\nname="shared"\nversion="1.0.0"\nedition="2024"\n[features]\nfast=[]\n',
        "v1/src/lib.rs": "pub fn value() -> u8 { 1 }\n",
        "v2/Cargo.toml": '[package]\nname="shared"\nversion="2.0.0"\nedition="2024"\n',
        "v2/src/lib.rs": "pub fn value() -> u8 { 2 }\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root / "Cargo.toml"


def _metadata(root: Path, manifest: Path, *, no_deps: bool) -> tuple[list[dict], dict]:
    result = execute(
        (
            "cargo",
            "+stable",
            "metadata",
            "--offline",
            "--format-version",
            "1",
            "--manifest-path",
            str(manifest),
            "--filter-platform",
            "x86_64-unknown-linux-gnu",
            *(("--no-deps",) if no_deps else ()),
        ),
        cwd=manifest.parent,
    )
    assert result.returncode == 0, result.stderr.decode()
    path = root / ("no-deps.json" if no_deps else "metadata.json")
    path.write_bytes(result.stdout)
    artifact = extract(
        root,
        SourceJob(
            id="metadata-no-deps" if no_deps else "metadata",
            kind="cargo",
            input=str(path),
            helper=str(TOOLING / "rustdoc-helper/target/debug/lde-rustdoc-facts"),
            profile="cargo-fixture",
            schema=str(TOOLING / "library_deep_enrichment/assets/schemas/cargo.v1.schema.json"),
        ),
        Budget(),
    )
    rows = [
        json.loads(line)
        for shard in artifact.shards
        for line in (root / shard.path).read_bytes().splitlines()
    ]
    receipt = json.loads((root / artifact.receipt_path).read_bytes())
    return rows, receipt


def test_cargo_virtual_workspace_duplicate_names_targets_and_dependency_kinds(
    tmp_path: Path,
) -> None:
    """Cargo package IDs and target/dependency roles survive normalization without name collapse."""
    manifest = _workspace(tmp_path / "workspace")
    rows, receipt = _metadata(tmp_path, manifest, no_deps=False)
    shared = [r for r in rows if r["symbol"] == "shared"]
    assert {r["version"] for r in shared} == {"1.0.0", "2.0.0"}
    assert len({r["package_id"] for r in shared}) == len(shared)
    app = next(r for r in rows if r["symbol"] == "identity-app")
    assert {kind for t in app["targets"] for kind in t["kinds"]} == {
        "lib",
        "bin",
        "example",
        "custom-build",
    }
    assert next(t for t in app["targets"] if t["name"] == "feature-example")[
        "required_features"
    ] == ["example-feature"]
    edges = {d["alias"]: d for d in app["resolved_dependencies"]}
    assert edges["left"]["package_id"] != edges["right"]["package_id"]
    assert {k["kind"] for k in edges["left"]["kinds"]} == {"normal", "development"}
    assert edges["owned_macros"]["kinds"][0]["kind"] == "build"
    assert next(r for r in shared if r["version"] == "1.0.0")["resolved_features"] == ["fast"]
    assert next(r for r in rows if r["symbol"] == "owned-macros")["targets"][0]["kinds"] == [
        "proc-macro"
    ]
    assert receipt["terminal"]["coverage"]["compilation_units"] == "not_observed"
    without_graph, omitted = _metadata(tmp_path, manifest, no_deps=True)
    assert all(
        r["resolved_features"] is None and r["resolved_dependencies"] is None for r in without_graph
    )
    assert omitted["terminal"]["coverage"]["resolve_state"] == "not_requested"

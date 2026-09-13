"""Run inside the isolated installed-reader namespace with only listed archives mounted."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import library_deep_enrichment
from library_deep_enrichment.corpus.contracts import Release
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.publication.releases import read_guide
from library_deep_enrichment.semantics.contracts import Comparison
from library_deep_enrichment.workflows.shapes import build
from library_deep_enrichment.paths import runtime_root

PAGE_SIZE = 5


def candidate_pages(corpus: Corpus) -> dict[str, object]:
    """Exercise the installed CLI against a complete nested candidate population.

    Returns:
        Pinned first/next page evidence, or an explicit absence of comparisons.

    """
    comparison = next(
        (
            item
            for item in corpus.reader("release").records("comparisons")
            if isinstance(item, Comparison)
        ),
        None,
    )
    if comparison is None:
        return {"comparisons": "absent"}
    command = [
        sys.executable,
        "-I",
        "-m",
        "library_deep_enrichment",
        "--corpus",
        str(corpus.root),
        "candidate-results",
        revision_of(comparison),
        "--head",
        "release",
        "--limit",
        str(PAGE_SIZE),
    ]
    first = json.loads(subprocess.run(command, check=True, capture_output=True).stdout)
    assert first["manifest"] == corpus.reader("release").manifest_id
    assert first["eligible"] == len(comparison.candidates)
    assert len(first["values"]) == min(PAGE_SIZE, len(comparison.candidates))
    next_count = 0
    if first["continuation"]:
        second = json.loads(
            subprocess.run(
                [*command, "--continuation", first["continuation"]], check=True, capture_output=True
            ).stdout
        )
        assert second["manifest"] == first["manifest"]
        assert second["eligible"] == first["eligible"]
        assert not {item["operation"] for item in first["values"]} & {
            item["operation"] for item in second["values"]
        }
        next_count = len(second["values"])
    return {
        "comparison": revision_of(comparison),
        "eligible": first["eligible"],
        "first_page": len(first["values"]),
        "next_page": next_count,
        "installed_cli": True,
    }


class GateResult(TypedDict, total=False):
    """Incrementally retained installed acceptance evidence."""

    results: list[dict[str, object]]
    installed_worker: dict[str, object]
    package: str
    freeze: str
    network: str
    gpu_service: str
    original_sources: str
    native_workers: str
    passed: bool


def verify(item: dict[str, str], root: Path) -> dict[str, object]:
    """Validate both archive imports and exact guide bytes in the installed package.

    Returns:
        The checked manifest, guide hashes and actual bounded-page evidence.

    """
    corpus = Corpus(root / item["name"], max_rows=2_500_000)
    if not corpus.reader("release").manifest_id:
        import_view(corpus, Path(item["path"]))
    reader = corpus.reader("release")
    assert reader.manifest_id == item["manifest"]
    guides = [
        read_guide(reader, record)
        for record in reader.records("releases")
        if isinstance(record, Release)
    ]
    page = reader.page("operations", max_rows=PAGE_SIZE)
    assert len(page.records) <= PAGE_SIZE
    destination = root / (item["name"] + "-export")
    if not destination.exists():
        export_view(reader, destination)
    restored = Corpus(root / (item["name"] + "-second"), max_rows=2_500_000)
    if not restored.reader("release").manifest_id:
        import_view(restored, destination)
    assert restored.reader("release").manifest_id == item["manifest"]
    again = [
        read_guide(restored.reader("release"), record)
        for record in restored.reader("release").records("releases")
        if isinstance(record, Release)
    ]
    assert again == guides
    return {
        "name": item["name"],
        "manifest": item["manifest"],
        "export_reimport": True,
        "guide_sha256": [hashlib.sha256(guide.encode()).hexdigest() for guide in guides],
        "paged_operations": len(page.records),
        "eligible_operations": page.eligible,
        "has_continuation": bool(page.continuation),
        "candidate_pages": candidate_pages(corpus),
    }


def main() -> None:
    """Prove source-independent reading and one installed analytical worker."""
    root = Path.cwd()
    assert not (Path.home() / "library-deep-enrichment/src/library_deep_enrichment").exists()
    assert not runtime_root().exists()
    assert not Path("/dev/nvidia0").exists()
    assert not Path("/home/paul/.cargo/registry").exists()
    with socket.socket() as connection:
        connection.settimeout(0.5)
        assert connection.connect_ex(("127.0.0.1", 18080)) != 0
    package = Path(library_deep_enrichment.__file__).resolve().parent
    assert "installed-all-reader" in str(package)
    assert "site-packages" in str(package)
    freeze = json.loads((root / "freeze.json").read_bytes())
    for name, expected in freeze["files"].items():
        if name.startswith("library_deep_enrichment/") and name.endswith(".py"):
            assert hashlib.sha256((package.parent / name).read_bytes()).hexdigest() == expected
    result_path = root / "result.json"
    result: GateResult = (
        json.loads(result_path.read_bytes()) if result_path.exists() else {"results": []}
    )
    complete = {item["name"] for item in result["results"]}
    archives = json.loads((root / "archives.json").read_bytes())
    for item in archives:
        if item["name"] in complete:
            continue
        sys.stdout.write("VERIFY " + item["name"] + "\n")
        sys.stdout.flush()
        result["results"].append(verify(item, root))
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result.get("installed_worker"):
        source = next(item for item in archives if item["name"] == "successor-python-0")
        corpus = Corpus(root / "installed-worker", max_rows=2_500_000)
        import_view(corpus, Path(source["path"]), head="analysis")
        first, warm = build(corpus), build(corpus)
        assert not first.reused
        assert warm.reused
        result["installed_worker"] = {
            "manifest": first.manifest,
            "request": first.request,
            "outputs": first.outputs,
            "warm_reuse": True,
        }
    result.update(
        {
            "package": str(package),
            "freeze": freeze["digest"],
            "network": "isolated namespace",
            "gpu_service": "unavailable",
            "original_sources": "unmounted",
            "native_workers": "unmounted",
            "passed": True,
        }
    )
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

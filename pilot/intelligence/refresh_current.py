"""Resume the finite current-source projection chain and retain every observed outcome."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import asdict
from library_deep_enrichment.analyses.fabric_contracts import PythonBoundaryRequest
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.workflows import enrichment, semantics, shapes
from library_deep_enrichment.workflows.python_boundaries import build as boundary
from library_deep_enrichment.workflows.python_documents import build as documents
from library_deep_enrichment.workflows.python_interfaces import build as interfaces
from library_deep_enrichment.paths import default_corpus

if TYPE_CHECKING:
    from collections.abc import Callable

    from attrs import AttrsInstance

ARTIFACTS = (
    ("datafusion", "42cbf9ef5a391c139bb7299556f427d12619bb3c3979403ebe94eccd8252fb3f"),
    ("pyarrow", "325485f9450ac605daf009affe9a81d54d951cb0262d58a24db88a942e7e3f37"),
)
LOG = logging.getLogger(__name__)


def run(root: Path, report_path: Path) -> None:
    """Refresh exact retained artifacts, recording first and unchanged receipts."""
    corpus = Corpus(root, max_rows=2_500_000)
    steps: list[tuple[str, Callable[[], AttrsInstance]]] = [
        (label + "-interfaces", lambda artifact=artifact: interfaces(corpus, artifact))
        for label, artifact in ARTIFACTS
    ]
    steps.extend(
        (label + "-documents", lambda artifact=artifact: documents(corpus, artifact))
        for label, artifact in ARTIFACTS
    )
    request = PythonBoundaryRequest(
        logical_id="datafusion-collect-source-boundary",
        profile="python-installed-54-25",
        owner="cf690c88981624c6eb2f60900a4a90b40b262203d898f6567db2f727e62250f9",
        types="c7fc3f4e9d0caf83e4ca2d45932182c206fb045caa9a6a8caad29e03efd520e1",
    )
    steps.extend(
        (
            ("python-boundary", lambda: boundary(corpus, request)),
            ("structure", lambda: enrichment.build(corpus)),
            ("shapes", lambda: shapes.build(corpus)),
            ("semantics", lambda: semantics.build(corpus)),
        )
    )
    report = json.loads(report_path.read_bytes()) if report_path.exists() else []
    for label, execute in steps:
        LOG.info("START %s", label)
        start = time.monotonic()
        try:
            first = asdict(execute())
            LOG.info("%s", json.dumps({"stage": label, "first": first}))
            warm = asdict(execute())
            assert warm["reused"]
            report.append(
                {
                    "stage": label,
                    "first": first,
                    "warm": warm,
                    "wall_seconds": time.monotonic() - start,
                }
            )
        except BaseException as error:
            report.append(
                {
                    "stage": label,
                    "error": f"{type(error).__name__}: {error}",
                    "manifest": corpus.reader().manifest_id,
                }
            )
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            raise
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        LOG.info("VERIFIED %s", label)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(
        default_corpus(),
        Path(__file__).with_name("reports") / "completion-current-projections.json",
    )

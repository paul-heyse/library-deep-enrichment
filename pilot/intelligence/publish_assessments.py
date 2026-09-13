"""Attach exact baseline/generated artifacts to the attributed 24-task review."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

import yaml

from library_deep_enrichment.corpus.encoding import canonical
from pilot.intelligence.qualify_reuse import REPORTS, ROOT, verify_freeze

ORIGINAL_GAP_COUNT = 9


def _generated(task: str, cohort: dict) -> dict:
    if task in {"pydantic-input", "serde-input"}:
        library = task.removesuffix("-input")
        report = json.loads((REPORTS / f"completion-{library}-decision-reuse.json").read_bytes())
        assert report["freeze"] == verify_freeze()
        return {
            "receipt": f"completion-{library}-decision-reuse.json",
            "releases": report["releases"],
            "remaining_interpretation": report["remaining_interpretation"],
        }
    result = next(item for item in cohort["tasks"] if item["task"] == task)
    return {
        "receipt": "completion-main-task-cohort.json",
        "release_manifest": cohort["release_manifest"],
        "release": cohort["release"],
        "guide_sha256": cohort["guide_sha256"],
        "comparison": result["comparison"],
        "universe": result["universe"],
        "universe_count": result["universe_count"],
        "eligible": result["eligible"],
        "counts": result["counts"],
        "unmodeled_requirements": result["unmodeled_requirements"],
        "assurance_limits": result["assurance_limits"],
    }


def run() -> None:
    """Publish an attributed assessment without an automated model judge."""
    cohort = json.loads((REPORTS / "completion-main-task-cohort.json").read_bytes())
    notes = json.loads((ROOT / "pilot/intelligence/task_assessments.json").read_bytes())
    baseline = yaml.safe_load((ROOT / "pilot/observations.yaml").read_bytes())["observations"]
    catalog = yaml.safe_load((ROOT / "pilot/tasks.yaml").read_bytes())["tasks"]
    original = {item["task"]: item for item in baseline}
    required = {item["id"] for item in catalog}
    assert {item["task"] for item in notes["observations"]} == required
    result = []
    for note in notes["observations"]:
        previous = original[note["task"]]
        selected = _generated(note["task"], cohort)
        if note["disposition"] == "supported" and "counts" in selected:
            assert selected["counts"].get("eligible", 0), note["task"]
        result.append(
            {
                **note,
                "baseline": {
                    "kind": "legacy-reviewed-record-selection",
                    "records": previous["records"],
                    "selection_sha256": hashlib.sha256(canonical(previous["records"])).hexdigest(),
                    "disposition": previous["disposition"],
                    "reviewer": previous["reviewer"],
                    "finding": previous["finding"],
                    "note": "The retained baseline is the exact reviewed legacy record selection; most tasks did not have a unified-fabric release. No missing historical release identity is invented.",
                },
                "generated": selected,
                "author": notes["author"],
                "reviewer": notes["reviewer"],
                "independent_review": False,
            }
        )
    original_gap_ids = {item["task"] for item in baseline if item["disposition"] == "gap"}
    gaps = [item for item in result if item["task"] in original_gap_ids]
    assert len(gaps) == ORIGINAL_GAP_COUNT
    report = {
        "freeze": verify_freeze(),
        "author": notes["author"],
        "reviewer": notes["reviewer"],
        "independent_review": False,
        "model_runs": 0,
        "task_count": len(result),
        "dispositions": dict(Counter(item["disposition"] for item in result)),
        "baseline_files": {
            name: hashlib.sha256((ROOT / "pilot" / name).read_bytes()).hexdigest()
            for name in (
                "tasks.yaml",
                "observations.yaml",
                "QUALITATIVE_EVALUATION.md",
                "reports/qualitative-receipt.json",
            )
        },
        "observations": result,
    }
    (REPORTS / "completion-24-task-assessment.json").write_bytes(canonical(report) + b"\n")
    (REPORTS / "completion-nine-gap-dispositions.json").write_bytes(
        canonical(
            {"freeze": verify_freeze(), "original_gap_count": len(gaps), "observations": gaps}
        )
        + b"\n"
    )
    _markdown(report)


def _markdown(report: dict) -> None:
    lines = [
        "# Attributed 24-task assessment",
        "",
        "Author and reviewer: the same implementation agent. No independent review or automated model judge is claimed.",
        "",
        "Generated support is assessed against the retained consumer requirements. Historical manually supported findings do not become automatically qualified generated decisions. A gap records an unmet semantic obligation; it is not a claim that the library lacks the capability.",
        "",
        f"Core freeze: `{report['freeze']}`.",
        "",
        "| Task | Generated assessment | Contribution and limit |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {item['task']} | {item['disposition']} | {item['finding']} |"
        for item in report["observations"]
    )
    lines.extend(
        [
            "",
            "Exact baseline selections, generated comparison/release identities and source receipts are retained in [the machine-readable assessment](reports/completion-24-task-assessment.json). The original nine gaps have [separate dispositions](reports/completion-nine-gap-dispositions.json).",
            "",
        ]
    )
    for item in report["observations"]:
        generated = item["generated"]
        releases = (
            [generated["release_manifest"]]
            if "release_manifest" in generated
            else [entry["manifest"] for entry in generated["releases"]]
        )
        lines.extend(
            [
                f"## {item['task']}",
                "",
                f"Disposition: **{item['disposition']}**. Baseline: `{item['baseline']['selection_sha256']}` ({item['baseline']['disposition']}).",
                "",
                "Generated release(s): " + ", ".join(f"`{value}`" for value in releases) + ".",
                "",
                item["finding"],
                "",
                f"Decision reverses or requires reassessment when: {item['reversing_condition']}",
                "",
                f"Remaining interpretation: {item['remaining_interpretation']}",
                "",
            ]
        )
    (ROOT / "pilot/intelligence/TASK_ASSESSMENT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    run()

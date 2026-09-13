"""Retain qualitative task observations without requiring a model runner or scores."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from attrs import frozen
from cattrs import Converter

from library_guides.collection import CollectionError, confined, load
from library_guides.evidence_graph import EvidenceGraph
from library_guides.facts.contracts import FactSelection, FileEntry
from library_guides.qualification import Qualification
from library_guides.store.digests import digest_file
from library_guides.store.staging import write_atomic


@frozen(kw_only=True)
class Task:
    """An independently declared question and the facts a useful answer must address."""

    id: str
    prompt: str
    profile: str
    requirements: tuple[str, ...]


@frozen(kw_only=True)
class Observation:
    """Attributed qualitative findings pinned to the exact reviewed artifacts."""

    task: str
    disposition: Literal["supported", "partial", "gap"]
    reviewer: str
    finding: str
    comparison: str
    reversing_condition: str
    follow_up: str
    records: tuple[tuple[str, str], ...] = ()
    author: str = ""
    evidence_origin: Literal["documentation", "source_facts", "combined", "execution"] = (
        "documentation"
    )
    baseline: FileEntry | None = None
    enriched: FileEntry | None = None
    inspected_facts: tuple[FactSelection, ...] = ()
    profile_difference: str = ""


def audit(root: Path, tasks_path: Path, observations_path: Path, output: Path) -> dict[str, object]:
    """Verify review references and render candid task-by-task findings.

    Returns:
        Audit identity and the disposition of every independently declared task.

    Raises:
        CollectionError: If tasks are missing, duplicated, unattributed or use stale artifacts.

    """
    converter = Converter(forbid_extra_keys=True)
    tasks = tuple(
        converter.structure(item, Task)
        for item in yaml.safe_load(tasks_path.read_text(encoding="utf-8"))["tasks"]
    )
    observations = tuple(
        converter.structure(item, Observation)
        for item in yaml.safe_load(observations_path.read_text(encoding="utf-8"))["observations"]
    )
    by_task = {item.task: item for item in observations}
    if (
        not tasks
        or len({item.id for item in tasks}) != len(tasks)
        or len(by_task) != len(observations)
        or {item.id for item in tasks} != by_task.keys()
    ):
        message = "qualitative audit requires one observation for every declared task"
        raise CollectionError(message)
    knowledge = load(root)
    check = Qualification(root, knowledge)
    failures = check.integrity_errors()
    if failures:
        message = "qualitative artifacts fail integrity: " + "; ".join(failures[:10])
        raise CollectionError(message)
    graph = EvidenceGraph(root, knowledge)
    lines = [
        "# Qualitative pilot evaluation",
        "",
        (
            "This is an attributed task review, not a "
            "model benchmark. It establishes no statistical improvement or token-saving estimate."
        ),
        "",
        f"Tasks SHA-256: `{digest_file(tasks_path)}`",
        "",
    ]
    for task in tasks:
        observation = by_task[task.id]
        _verify(task, observation, check, graph)
        _inspection(root, task, observation, graph)
        lines.extend(
            [
                f"## {task.id}: {task.prompt}",
                "",
                f"Disposition: **{observation.disposition}**. Profile: `{task.profile}`.",
                "",
                "Required: " + "; ".join(task.requirements),
                "",
                observation.finding,
                "",
                "Comparison with previous approach: " + observation.comparison,
                "",
                "Reversing condition: " + observation.reversing_condition,
                "",
                "Follow-up: " + observation.follow_up,
                "",
                "Authored by: "
                + (observation.author or "Not separately recorded in the legacy observation"),
                "",
                "Evidence origin: " + observation.evidence_origin,
                "",
                "Profile comparison: "
                + (observation.profile_difference or "Same declared applicability"),
                "",
                "Reviewed by: " + observation.reviewer,
                "",
            ]
        )
        lines.extend(f"- `{key}` — SHA-256 `{digest}`" for key, digest in observation.records)
        lines.extend(
            f"- Compared `{item.path}` — SHA-256 `{item.digest}`"
            for item in (observation.baseline, observation.enriched)
            if item is not None
        )
        lines.extend(
            f"- Inspected `{f.artifact}` / `{f.record}` / `{f.selector}` — SHA-256 `{f.digest}`"
            for f in observation.inspected_facts
        )
        lines.append("")
    write_atomic(output, "\n".join(lines).encode())
    return {
        "mode": "qualitative",
        "tasks_digest": digest_file(tasks_path),
        "observations_digest": digest_file(observations_path),
        "report_digest": digest_file(output),
        "full_task_scope_supported": all(item.disposition == "supported" for item in observations),
        "dispositions": {item.task: item.disposition for item in observations},
        "model_runs": 0,
    }


def _verify(
    task: Task, observation: Observation, check: Qualification, graph: EvidenceGraph
) -> None:
    if not all(
        (
            observation.reviewer.strip(),
            observation.finding.strip(),
            observation.comparison.strip(),
            observation.reversing_condition.strip(),
            observation.follow_up.strip(),
        )
    ):
        message = f"incomplete qualitative observation: {task.id}"
        raise CollectionError(message)
    if observation.disposition == "supported" and not observation.records:
        message = f"supported task has no exact artifacts: {task.id}"
        raise CollectionError(message)
    for key, digest in observation.records:
        record = graph.owners.get(key)
        if record is None or record.profile != task.profile or graph.fingerprint(key) != digest:
            message = f"stale or wrongly scoped qualitative observation: {task.id} -> {key}"
            raise CollectionError(message)
        if observation.disposition == "supported" and not check.closure_accepted(key):
            message = f"supported task has unreviewed dependencies: {task.id} -> {key}"
            raise CollectionError(message)


def _inspection(root: Path, task: Task, observation: Observation, graph: EvidenceGraph) -> None:
    from library_guides.facts import store
    from library_guides.source_pipeline import artifact_index

    for entry in (observation.baseline, observation.enriched):
        if entry is not None:
            path = confined(root, entry.path)
            if path.stat().st_size != entry.size or digest_file(path) != entry.digest:
                message = f"compared packet/generation changed: {task.id}: {entry.path}"
                raise CollectionError(message)
    if observation.inspected_facts and not all(
        (observation.author, observation.baseline, observation.enriched)
    ):
        message = (
            f"source comparison needs baseline/enriched artifacts and author attribution: {task.id}"
        )
        raise CollectionError(message)
    for selection in observation.inspected_facts:
        artifact = graph.support.artifact(selection.artifact)
        store.selected(root, artifact_index(root, artifact), selection, artifact=artifact)
        if artifact.profile != task.profile and not observation.profile_difference.strip():
            message = f"source comparison must explain its different profile: {task.id}"
            raise CollectionError(message)

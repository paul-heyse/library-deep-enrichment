"""Reproducible held-out evaluation runs with retained outputs and honest missing cells."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import yaml
from attrs import frozen
from cattrs import Converter

from library_guides.collection import CollectionError
from library_guides.processes import execute
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic


@frozen(kw_only=True)
class Case:
    """A task frozen before evaluation, with independently declared expected facts."""

    id: str
    scope: str
    held_out: bool
    prompt: str
    required_facts: tuple[str, ...]
    forbidden_facts: tuple[str, ...]


def evaluate(
    cases_path: Path,
    configurations: dict[str, Path],
    output: Path,
    *,
    argv: tuple[str, ...],
    repetitions: int = 2,
) -> dict[str, object]:
    """Execute the full case/configuration/repetition matrix and retain every failure.

    Returns:
        The full evaluation matrix, including failed runs and retained receipts.

    Raises:
        CollectionError: If required cases, configurations, repetitions or runner are absent.

    """
    raw = yaml.safe_load(cases_path.read_text(encoding="utf-8"))
    cases = tuple(Converter(forbid_extra_keys=True).structure(item, Case) for item in raw["cases"])
    if not cases or not configurations or repetitions < 1 or not argv:
        message = "evaluation requires cases, configurations, repetitions and a runner"
        raise CollectionError(message)
    rows = []
    for case, (name, context), repetition in product(
        cases, configurations.items(), range(repetitions)
    ):
        request: dict[str, object] = {
            "protocol": "library-guides.evaluation.v2",
            "case": case.id,
            "scope": case.scope,
            "prompt": case.prompt,
            "context": context.read_text(encoding="utf-8"),
            "configuration": name,
            "repetition": repetition,
        }
        key = digest_bytes(
            canonical_bytes(
                {"request": request, "runner": argv, "cases_digest": digest_file(cases_path)}
            )
        )
        destination = output / f"{key}.json"
        row = _evaluate_one(request, case, argv, context.parent)
        write_atomic(destination, canonical_bytes(row))
        rows.append(
            {
                "key": key,
                "case": case.id,
                "configuration": name,
                "repetition": repetition,
                "held_out": case.held_out,
                "state": row["state"],
            }
        )
    summary: dict[str, object] = {
        "cases_digest": digest_file(cases_path),
        "expected": len(cases) * len(configurations) * repetitions,
        "completed": len(rows),
        "rows": rows,
        "runner": argv,
        "scoring": "structured required/forbidden facts; semantic citation review remains separate",
    }
    write_atomic(output / "summary.json", canonical_bytes(summary))
    return summary


def _evaluate_one(
    request: dict[str, object], case: Case, argv: tuple[str, ...], cwd: Path
) -> dict[str, object]:
    try:
        result = execute(argv, cwd=cwd, stdin=canonical_bytes(request), timeout=180)
        if result.returncode:
            return {"state": "failed", "reason": result.stderr.decode(errors="replace")}
        answer = json.loads(result.stdout)
        facts = set(answer["facts"])
        passed = set(case.required_facts) <= facts and not set(case.forbidden_facts) & facts
        return {
            "state": "passed" if passed else "failed",
            "answer": answer,
            "elapsed_seconds": result.elapsed_seconds,
            "stdout_digest": digest_bytes(result.stdout),
        }
    except (CollectionError, OSError, ValueError, KeyError, TypeError) as error:
        return {"state": "failed", "reason": str(error)}

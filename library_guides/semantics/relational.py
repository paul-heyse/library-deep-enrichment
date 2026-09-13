"""Supervised finite Souffle joins and recursion with application-owned input identities."""

from __future__ import annotations

import os
import tempfile
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Operation, Passage, RegistryEntry, TypeUse
from library_guides.corpus.encoding import bytes_digest, digest
from library_guides.corpus.schemas import revision_of
from library_guides.facts.contracts import Budget
from library_guides.processes import execute
from library_guides.semantics.contracts import Rule
from library_guides.semantics.enrichment_contracts import WitnessObservation
from library_guides.worker_runtime import WorkerRequest, command

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MAX_RULE_ROWS = 100_000
MAX_RULE_OUTPUT_BYTES = 16 * 1024 * 1024
SOFTWARE_DIGEST = "e8e4d8bff0b8377d2d42ae30886121a61061ec0c8bb948f1f5129e09aecfa9a1"


def executable() -> Path:
    """Resolve the installed qualified rule runtime with no unverified PATH fallback.

    Returns:
        The exact pinned executable used for finite semantic rules.

    Raises:
        CorpusError: The configured runtime is missing or has a different fingerprint.

    """
    configured = os.environ.get("LIBRARY_GUIDES_SOUFFLE")
    path = (
        Path(configured)
        if configured
        else Path.home()
        / ".cache/library-guides-intelligence/tools/souffle-2.5/runtime/usr/bin/souffle"
    )
    if not path.is_file() or bytes_digest(path.read_bytes()) != SOFTWARE_DIGEST:
        message = "qualified Souffle 2.5 runtime is unavailable; configure LIBRARY_GUIDES_SOUFFLE after verified acquisition"
        raise CorpusError(message)
    return path.resolve()


def evaluate(
    program: str, facts: Mapping[str, Sequence[tuple[int, ...]]], output: str
) -> tuple[tuple[int, ...], ...]:
    """Run an owned finite positive rule program under process and output limits.

    Returns:
        Exact integer-coded consequences; caller dictionaries retain logical identities.

    Raises:
        CorpusError: The program fails or returns malformed/non-domain output.
        BudgetExceededError: Input or output exceeds the explicitly declared boundary.

    """
    if program not in {"owner_rules", "reachability"}:
        message = "semantic workers execute only owned rule programs"
        raise CorpusError(message)
    if sum(len(rows) for rows in facts.values()) > MAX_RULE_ROWS:
        message = "Souffle input exceeds its finite fact boundary"
        raise BudgetExceededError(message)
    source = Path(__file__).parents[1] / "assets/semantic" / f"{program}.dl"
    with tempfile.TemporaryDirectory(prefix="library-guides-rules-") as temporary:
        root = Path(temporary)
        for name, rows in facts.items():
            if not name.isalpha():
                message = "invalid owned rule relation name"
                raise CorpusError(message)
            (root / f"{name}.facts").write_text(
                "".join("\t".join(str(value) for value in row) + "\n" for row in rows)
            )
        worker = WorkerRequest(
            argv=(str(executable()), "-F", str(root), "-D", str(root), str(source)),
            cwd=root,
            request_id=digest([program, facts]),
            input_digest=digest(facts),
            budget=Budget(
                wall_seconds=30,
                cpu_seconds=25,
                memory_bytes=1024 * 1024 * 1024,
                output_bytes=MAX_RULE_OUTPUT_BYTES,
                max_records=MAX_RULE_ROWS,
            ),
        )
        result = execute(command(worker), cwd=root, timeout=30, max_bytes=1_000_000)
        if result.returncode:
            message = f"Souffle failed: {result.stderr.decode(errors='replace')[:2000]}"
            raise CorpusError(message)
        target = root / f"{output}.csv"
        if target.stat().st_size > MAX_RULE_OUTPUT_BYTES:
            message = "Souffle output exceeds its byte boundary"
            raise BudgetExceededError(message)
        rows = tuple(
            tuple(int(value) for value in line.split("\t"))
            for line in target.read_text().splitlines()
        )
        if len(rows) > MAX_RULE_ROWS:
            message = "Souffle result exceeds its row boundary"
            raise BudgetExceededError(message)
        return rows


def _owner(source: Record) -> str:
    if isinstance(source, (Passage, TypeUse)):
        return source.owner
    if isinstance(source, (RegistryEntry, WitnessObservation)):
        return source.operation
    return revision_of(source)


def candidates(reader: CorpusReader) -> Iterator[tuple[Rule, Record, Operation]]:
    """Join rule families, contextual sources, and operations through actual Souffle.

    Yields:
        Exact positive join results, still requiring independent consequence qualification.

    Raises:
        CorpusError: A worker emits an identifier outside its finite input dictionaries.

    """
    operations = {
        revision_of(item): item
        for item in reader.records("operations")
        if isinstance(item, Operation)
    }
    rules = [item for item in reader.records("rules") if isinstance(item, Rule)]
    families = {
        name: index for index, name in enumerate(sorted({rule.source_family for rule in rules}))
    }
    sources = [
        (family, item)
        for family in families
        for item in reader.records(family)
        if _owner(item) in operations
    ]
    owners = {key: index for index, key in enumerate(sorted(operations))}
    profiles = {
        profile: index
        for index, profile in enumerate(
            sorted(
                {item.profile for item in operations.values()}
                | {item.profile for _, item in sources}
            )
        )
    }
    reverse = {value: key for key, value in owners.items()}
    for batch in batched(enumerate(sources), 5000, strict=False):
        included = {_owner(item) for _, (_, item) in batch}
        facts = {
            "Operation": [
                (owners[key], profiles[operations[key].profile]) for key in sorted(included)
            ],
            "Model": [(index, families[rule.source_family]) for index, rule in enumerate(rules)],
            "Source": [
                (index, families[family], owners[_owner(item)], profiles[item.profile])
                for index, (family, item) in batch
            ],
        }
        admitted = {index for index, _ in batch}
        for source, rule, owner in evaluate("owner_rules", facts, "Candidate"):
            if source not in admitted or not 0 <= rule < len(rules) or owner not in reverse:
                message = "rule result contains an identifier outside the supplied finite universe"
                raise CorpusError(message)
            operation = operations[reverse[owner]]
            candidate = sources[source][1]
            if (
                _owner(candidate) != revision_of(operation)
                or candidate.profile != operation.profile
            ):
                message = "rule worker returned an invalid contextual owner join"
                raise CorpusError(message)
            yield rules[rule], candidate, operation

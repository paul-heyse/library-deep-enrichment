"""The shared typed application surface for admitted corpus queries and authoring."""

from __future__ import annotations

from collections import Counter, deque
from itertools import islice
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Job, Record
from library_guides.corpus.encoding import CONVERTER, canonical, payload
from library_guides.corpus.schemas import REGISTRY
from library_guides.corpus.validation import references
from library_guides.discovery.contracts import SearchSelection
from library_guides.discovery.search import search
from library_guides.semantics.contracts import Comparison, Predicate, State, Task
from library_guides.semantics.enrichment_contracts import EvidenceRequest
from library_guides.semantics.planning import PlanBudget, compose
from library_guides.semantics.task_matching import compare

if TYPE_CHECKING:
    from collections.abc import Iterable

    from library_guides.corpus.store import Corpus, CorpusReader
    from library_guides.discovery.contracts import SearchResult
    from library_guides.discovery.embeddings import EmbeddingClient
    from library_guides.semantics.planning import PlanResult

MAX_PACKET_BYTES = 1024 * 1024
MAX_PAGE_ROWS = 200


@frozen(kw_only=True)
class RecordPage:
    """A finite manifest-pinned page with an explicit continuation offset."""

    manifest: str
    family: str
    records: tuple[Record, ...]
    next_offset: int | None


def encode(value: object) -> bytes:
    """Encode a bounded application response without dumping a whole corpus or job read set.

    Returns:
        Canonical JSON suitable for CLI or protocol clients.

    Raises:
        BudgetExceededError: The selected result requires a narrower page.

    """
    data = canonical(CONVERTER.unstructure(value))
    if len(data) > MAX_PACKET_BYTES:
        message = "response exceeds one MiB; narrow the profile, fields, or page size"
        raise BudgetExceededError(message)
    return data


def status(reader: CorpusReader) -> dict[str, object]:
    """Report current evidence and stage outcomes without exposing enormous read-set arrays.

    Returns:
        Logical identity, independent family denominators, and actual currentness receipts.

    """
    return {
        "manifest": reader.manifest_id,
        "semantic_checker": reader.semantic_checker,
        "families": dict(sorted(Counter(item.family for item in reader.members()).items())),
        "jobs": [
            {
                "stage": job.stage,
                "request": job.request,
                "state": job.disposition,
                "reason": job.reason,
                "outputs": len(job.outputs),
            }
            for job in reader.records("jobs")
            if isinstance(job, Job)
        ],
    }


def page(
    reader: CorpusReader, family: str, *, offset: int = 0, limit: int = 20, text: str = ""
) -> RecordPage:
    """Read a finite family page from one sanctioned view, including original source records.

    Returns:
        Rows and a continuation when further matching records exist.

    Raises:
        CorpusError: The family or page bounds are invalid.

    """
    if family not in REGISTRY or offset < 0 or not 0 < limit <= MAX_PAGE_ROWS:
        message = "unknown family or invalid page bounds (maximum 200 rows)"
        raise CorpusError(message)
    matches = (
        record
        for record in reader.records(family)
        if not text or text.casefold() in canonical(payload(record)).decode().casefold()
    )
    selected = tuple(islice(matches, offset, offset + limit + 1))
    return RecordPage(
        manifest=reader.manifest_id,
        family=family,
        records=selected[:limit],
        next_offset=offset + limit if len(selected) > limit else None,
    )


def discover(
    reader: CorpusReader,
    query: str,
    *,
    selection: SearchSelection = SearchSelection(),
    client: EmbeddingClient | None = None,
    limit: int = 20,
) -> SearchResult:
    """Find relevant operations while preserving the separate semantic applicability path.

    Returns:
        Real channel scores, source support, eligible denominator, and outage frontier.

    """
    return search(reader, query, selection=selection, client=client, limit=limit)


def match_task(corpus: Corpus, task: Task, *, save: bool = False) -> Comparison:
    """Evaluate every admitted operation in the task profiles, optionally admitting the result.

    Returns:
        A checked comparison; the corpus changes only when explicitly requested.

    """
    reader = corpus.reader()
    scope, result = compare(reader, task)
    if save:
        Coordinator(corpus, WriterIdentity(principal="task-comparison")).commit(
            (task, scope, result), expected=reader.manifest_id
        )
    return result


def compose_task(reader: CorpusReader, task: Task, budget: PlanBudget = PlanBudget()) -> PlanResult:
    """Plan finite multi-input compositions; no retrieved program executes during a query.

    Returns:
        Bound values, candidate transitions, and required evidence work.

    """
    return compose(reader, task, budget)


def plan_evidence(reader: CorpusReader, comparison: Comparison) -> tuple[EvidenceRequest, ...]:
    """Turn unresolved requirements into the smallest useful source or witness question.

    Returns:
        A finite evidence plan. This never schedules an expensive lane implicitly.

    """
    requests: list[EvidenceRequest] = []
    for candidate in comparison.candidates:
        for requirement in candidate.requirements:
            if requirement.state not in {State.UNKNOWN, State.CONFLICTING}:
                continue
            predicate = reader.get("predicates", requirement.predicate)
            if not isinstance(predicate, Predicate):
                continue
            requests.append(
                EvidenceRequest(
                    logical_id=f"evidence-request:{candidate.operation}:{requirement.predicate}",
                    profile=comparison.profile,
                    subject=candidate.operation,
                    predicate=requirement.predicate,
                    lane="source-or-contrastive-witness",
                    query=f"Establish {predicate.name}={requirement.required.text!r} for this exact operation and task context",
                    expected_information="Exact scoped support or a counterexample, with unresolved native boundaries retained",
                    reason=requirement.reason,
                    dependencies=(),
                )
            )
    return tuple(requests)


def explain(
    reader: CorpusReader, family: str, revision: str, *, limit: int = 20
) -> dict[str, object]:
    """Expand exact typed evidence links with finite continuation and direct source selectors.

    Returns:
        Bounded record bodies and queued continuations, with no filesystem citation shortcut.

    Raises:
        CorpusError: The expansion boundary is invalid.

    """
    if not 0 < limit <= MAX_PAGE_ROWS:
        message = "explanation page limit must be between 1 and 200"
        raise CorpusError(message)
    pending = deque([(family, revision)])
    visited: set[tuple[str, str]] = set()
    records: list[dict[str, object]] = []
    while pending and len(records) < limit:
        key = pending.popleft()
        if key in visited:
            continue
        visited.add(key)
        record = reader.get(*key)
        body = payload(record)
        records.append({"family": key[0], "revision": key[1], "record": body})
        pending.extend(references(record))
        for name in ("support", "evidence", "premises"):
            values = body.get(name, ())
            for selection in values if isinstance(values, (tuple, list)) else ():
                if (
                    isinstance(selection, dict)
                    and "family" in selection
                    and "revision" in selection
                ):
                    pending.append((str(selection["family"]), str(selection["revision"])))
    return {"manifest": reader.manifest_id, "records": records, "continuations": tuple(pending)}


def explore(reader: CorpusReader, query: str, *, limit: int = 20) -> RecordPage:
    """Navigate admitted concepts with their actual structural/support meaning.

    Returns:
        A bounded concept page. Its source and membership fields remain inspectable.

    """
    return page(reader, "concepts", text=query, limit=limit)


def admit(
    corpus: Corpus, records: Iterable[Record], *, authority: str, role: str, expected: str
) -> str:
    """Admit authoring or policy work through the same typed coordinator as extraction.

    Returns:
        A coherent manifest after exact predecessor and consequence checks.

    Raises:
        CorpusError: The authoring request asks for an internal migration authority.

    """
    if role not in {"producer", "policy", "review"} or not authority.strip():
        message = "authoring requires an attributed producer, policy, or review role"
        raise CorpusError(message)
    return Coordinator(corpus, WriterIdentity(principal=authority, role=role)).commit(
        records, expected=expected
    )

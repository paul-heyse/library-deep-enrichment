"""Scoped exact lookup, capability discovery and evidence-bearing rendering."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from attrs import asdict

from library_deep_enrichment.collection import Subject, dependencies, subjects
from library_deep_enrichment.evidence_graph import EvidenceGraph
from library_deep_enrichment.knowledge import Binding, Capability, Claim, Decision, Integration, Knowledge
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.store.digests import canonical_bytes


def render(root: Path, knowledge: Knowledge, identifier: str) -> str:
    """Render a subject with its actual claim, condition and evidence closure.

    Returns:
        Markdown retaining claims, conditions and exact evidence citations.

    """
    graph = EvidenceGraph(root, knowledge)
    record = graph.owners[identifier]
    lines = [f"# {identifier}", "", f"Profile: `{record.profile}`", ""]
    visited: set[str] = set()

    def append(key: str) -> None:
        if key in visited:
            return
        visited.add(key)
        if key in graph.universes:
            lines.extend(_candidate_summary(root, knowledge, key))
            return
        if key in graph.support.supports:
            support = graph.support.supports[key]
            lines.extend([f"### Fact support: {support.kind}", ""])
            for selection in support.facts:
                artifact = graph.support.artifact(selection.artifact)
                lines.extend(
                    [
                        f"- `{selection.record}` · `{selection.selector}` · SHA-256 `{selection.digest}` · profile `{artifact.profile}` · context `{artifact.context or 'not established'}`.",
                        "",
                    ]
                )
            lines.extend(_support_limits((*support.assumptions, *support.exceptions)))
            return
        if key in graph.principles:
            principle = graph.principles[key]
            lines.extend(
                [
                    f"## Principle: {key}",
                    "",
                    principle.statement,
                    "",
                    "Exceptions: " + "; ".join(principle.exceptions),
                    "",
                ]
            )
            return
        if key in graph.examples:
            example = graph.examples[key]
            lines.extend(
                [
                    (
                        f"- Verification `{key}`: `{example.profile}`; "
                        f"inputs {', '.join(example.inputs)}; "
                        f"SHA-256 `{graph.fingerprint(key)}`."
                    ),
                    "",
                ]
            )
            return
        if key in graph.evidence:
            item = graph.evidence[key]
            source = graph.sources[item.source]
            lines.extend(
                [
                    (
                        f"- Evidence `{key}`: **{item.subject}**; `{item.selector}`; "
                        f"SHA-256 `{item.digest}`; [source]({source.locator})."
                    ),
                    "",
                ]
            )
            return
        owner = graph.owners[key]
        lines.extend([f"## {key}", "", _body(owner), ""])
        lines.extend(_uncertainty(knowledge, owner))
        for dependency in dependencies(knowledge, owner):
            append(dependency)

    append(identifier)
    return "\n".join(lines)


def _candidate_summary(root: Path, knowledge: Knowledge, key: str) -> list[str]:
    from library_deep_enrichment.analyses.universes import enumerate_candidates

    if not isinstance(knowledge, KnowledgeV3):
        return []
    universe = next(u for u in knowledge.candidate_universes if u.id == key)
    report = enumerate_candidates(root, knowledge, universe)
    return [
        f"Candidate scope `{key}`: {report['total']} nominal declarations; membership SHA-256 `{report['semantic_digest']}`.",
        "",
        str(report["frontier"]),
        "",
    ]


def _support_limits(limits: tuple[str, ...]) -> list[str]:
    return ["Applicability: " + "; ".join(limits), ""] if limits else []


def _uncertainty(knowledge: Knowledge, owner: Subject) -> list[str]:
    if not isinstance(knowledge, KnowledgeV3) or not isinstance(owner, Capability):
        return []
    missing = [
        seed for seed in knowledge.facet_seeds if seed.capability == owner.id and seed.missing
    ]
    return (
        [
            "Unresolved evidence:",
            "",
            *(f"- {seed.dimension}: {'; '.join(seed.missing)}" for seed in missing),
            "",
        ]
        if missing
        else []
    )


def _body(record: Subject) -> str:
    if isinstance(record, Claim):
        return (
            f"{record.statement}\n\nMechanism: {record.mechanism}\n\n"
            f"Conditions: {'; '.join(record.conditions) or 'not specified'}\n\n"
            f"Exceptions: {'; '.join(record.exceptions) or 'not specified'}\n\n"
            f"Evidence class: {record.verification}."
        )
    if isinstance(record, Binding):
        return (
            f"`{record.symbol}` ({record.language}, {record.package} {record.version}, "
            f"{record.resolution})\n\n```text\n{record.signature}\n```"
        )
    if isinstance(record, Capability):
        facets = "\n".join(
            f"- {facet.name}: {facet.value} ({', '.join(facet.claims)})" for facet in record.facets
        )
        realizations = "\n".join(
            f"- Principle {item.principle}: {item.mechanism}; "
            f"when {'; '.join(item.conditions)} ({', '.join(item.claims)})"
            for item in record.realizations
        )
        return f"{record.title}\n\n{record.intent}\n\n{facets}\n\n{realizations}"
    if isinstance(record, Decision):
        candidates = "\n".join(
            f"- {candidate.capability}: {candidate.when} ({', '.join(candidate.claims)})"
            for candidate in record.candidates
        )
        return (
            f"{record.task}\n\nRequirements: {'; '.join(record.requirements)}\n\n"
            f"{candidates}\n\n{record.comparison}\n\n"
            f"Reversing conditions: {'; '.join(record.reversing_conditions)}"
        )
    return (
        f"{record.producer} → {record.consumer}\n\nRepresentation: {record.representation}"
        f"\n\nOwnership: {record.ownership}\n\nLifecycle: {record.lifecycle}"
        f"\n\nFailures: {'; '.join(record.failures)}"
    )


def index(path: Path, knowledge: Knowledge, *, evidence_root: Path | None = None) -> None:
    """Compile disposable SQLite exact, alias and FTS5 indexes."""
    graph = EvidenceGraph(evidence_root, knowledge) if evidence_root else None
    documentation: dict[tuple[str, str], list[str]] = {}
    if graph:
        for item in knowledge.evidence:
            if item.kind in {"statement", "registry"}:
                key = (graph.sources[item.source].profile, item.subject)
                documentation.setdefault(key, []).append(item.id)
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE records(id TEXT PRIMARY KEY, profile TEXT, kind TEXT, body TEXT);
            CREATE TABLE symbols(symbol TEXT, profile TEXT, id TEXT);
            CREATE INDEX exact_symbol ON symbols(symbol, profile);
            CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, profile UNINDEXED, text);
        """)
        for record in subjects(knowledge).values():
            body = canonical_bytes(asdict(record)).decode()
            db.execute(
                "INSERT INTO records VALUES (?,?,?,?)",
                (record.id, record.profile, type(record).__name__, body),
            )
            if isinstance(record, Binding):
                db.executemany(
                    "INSERT INTO symbols VALUES (?,?,?)",
                    [
                        (name, record.profile, record.id)
                        for name in (record.symbol, *record.aliases)
                    ],
                )
                if graph:
                    docs = documentation.get((record.profile, record.symbol), [])
                    text = (
                        record.signature
                        + "\n"
                        + "\n".join(
                            graph.selected(graph.evidence[key]).decode(errors="replace")
                            for key in docs
                        )
                    )
                    db.execute(
                        "INSERT INTO search VALUES (?,?,?)", (record.id, record.profile, text)
                    )
            if isinstance(record, (Capability, Decision, Integration)):
                db.execute(
                    "INSERT INTO search VALUES (?,?,?)", (record.id, record.profile, _body(record))
                )


def search(path: Path, query: str, *, profile: str, exact: bool = False) -> list[dict[str, str]]:
    """Retrieve only within the explicitly selected applicability profile.

    Returns:
        Scoped exact matches or ranked capability and decision records.

    """
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        if exact:
            rows = db.execute(
                "SELECT DISTINCT records.id,kind,body FROM records JOIN symbols "
                "ON records.id=symbols.id WHERE symbols.symbol=? "
                "AND records.profile=? ORDER BY records.id",
                (query, profile),
            )
        else:
            terms = re.findall(r"\w+", query)
            if not terms:
                return []
            expression = " OR ".join('"' + term + '"' for term in terms)
            rows = db.execute(
                "SELECT records.id,kind,body FROM search JOIN records "
                "ON records.id=search.id WHERE search MATCH ? "
                "AND records.profile=? ORDER BY rank,records.id LIMIT 20",
                (expression, profile),
            )
        return [{"id": row[0], "kind": row[1], "record": row[2]} for row in rows]

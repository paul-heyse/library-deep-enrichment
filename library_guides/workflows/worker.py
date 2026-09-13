"""Supervised analytical entry point: pinned reads, private spool, framed typed output."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader
    from library_guides.workflows.remote import AnalyticalRequest


def _produce(reader: CorpusReader, request: AnalyticalRequest) -> Iterable[Record]:
    if request.route == "shapes":
        from library_guides.semantics.type_shapes import shapes

        return shapes(reader)

    if request.route == "behavior":
        from library_guides.analyses.behavior.contracts import BehaviorRequest
        from library_guides.analyses.behavior.service import analyze as behavior

        subject = reader.get("behavior_requests", request.subject)
        if not isinstance(subject, BehaviorRequest):
            message = "behavior worker requires a typed source request"
            raise ValueError(message)
        return behavior(reader, subject)

    from library_guides.analyses.fabric import analyze as mir_analysis
    from library_guides.analyses.fabric_contracts import AnalysisRequest, PythonBoundaryRequest
    from library_guides.analyses.python_fabric import analyze as python_boundary
    from library_guides.corpus.python_documents import project as python_documents
    from library_guides.corpus.python_interfaces import project as python_interfaces
    from library_guides.discovery.fca import concepts, support_context
    from library_guides.discovery.graphs import project_graphs
    from library_guides.discovery.labels import descriptors
    from library_guides.discovery.scopes import population
    from library_guides.discovery.units import build_units
    from library_guides.semantics.documents import project
    from library_guides.workflows.semantics import _produce as semantic_products

    if request.route == "mir-analysis":
        analysis_request = reader.get("analysis_requests", request.subject)
        if not isinstance(analysis_request, AnalysisRequest):
            message = "MIR analysis worker needs a typed owner request"
            raise ValueError(message)
        return mir_analysis(reader, analysis_request)
    if request.route == "python-boundary":
        boundary_request = reader.get("python_boundary_requests", request.subject)
        if not isinstance(boundary_request, PythonBoundaryRequest):
            message = "Python boundary worker needs a typed source request"
            raise ValueError(message)
        return (python_boundary(reader, boundary_request),)

    routes = {
        "retrieval": lambda: chain(
            build_units(reader, request.scope),
            () if request.scope is None else (population(reader, request.scope),),
        ),
        "graphs": lambda: project_graphs(reader, selection=request.scope),
        "fca": lambda: concepts(support_context(reader, scope=request.scope)),
        "labels": lambda: descriptors(reader, scope=request.scope),
        "structure": lambda: project(reader),
        "semantics": lambda: semantic_products(reader),
        "python-interfaces": lambda: python_interfaces(reader, request.subject),
        "python-documents": lambda: python_documents(reader, request.subject),
    }
    if request.route not in routes:
        message = "unsupported analytical worker route"
        raise ValueError(message)
    return routes[request.route]()


def _produce_checked(reader: CorpusReader, request: AnalyticalRequest) -> Iterable[Record]:
    if request.route in {"native-call-index", "native-call-closure"}:
        from library_guides.analyses.call_graph.worker import produce

        return produce(reader, request)

    if request.route == "behavior-characterization":
        from library_guides.analyses.characterization.contracts import CharacterizationRequest
        from library_guides.analyses.characterization.service import analyze as characterize

        subject = reader.get("characterization_requests", request.subject)
        if not isinstance(subject, CharacterizationRequest):
            message = "characterization worker requires a typed population request"
            raise TypeError(message)
        return characterize(reader, subject)

    if request.route == "compilation-population":
        from library_guides.analyses.compilation import analyze as compilation
        from library_guides.analyses.compilation_contracts import CompilationRequest

        subject = reader.get("compilation_requests", request.subject)
        if not isinstance(subject, CompilationRequest):
            message = "compilation worker requires a typed context request"
            raise TypeError(message)
        return (compilation(reader, subject),)

    if request.route == "callable-population":
        from library_guides.analyses.callable_contracts import CallableRequest
        from library_guides.analyses.callable_population import analyze as callables

        subject = reader.get("callable_requests", request.subject)
        if not isinstance(subject, CallableRequest):
            message = "callable worker requires a typed population request"
            raise TypeError(message)
        return (callables(reader, subject),)

    if request.route != "behavior-witness":
        return _produce(reader, request)
    from library_guides.analyses.behavior.witness_contracts import BehaviorWitnessRequest
    from library_guides.analyses.behavior.witness_service import analyze

    subject = reader.get("behavior_witness_requests", request.subject)
    if not isinstance(subject, BehaviorWitnessRequest):
        message = "behavior witness worker requires a typed comparison request"
        raise TypeError(message)
    return analyze(reader, subject)


def main() -> None:
    """Emit a complete denominator and exact framed records after bounded private staging.

    Raises:
        ValueError: The pinned view changed.
        BudgetExceededError: The output exceeds declared limits.

    """
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "RAYON_NUM_THREADS"):
        os.environ[name] = "1"
    from library_guides.corpus.backend import BudgetExceededError
    from library_guides.corpus.encoding import CONVERTER, canonical, digest
    from library_guides.corpus.schemas import codec_for
    from library_guides.corpus.store import CorpusReader
    from library_guides.corpus.validation import AdmissionReader
    from library_guides.workflows.remote import AnalyticalRequest

    raw = json.loads(Path(sys.argv[1]).read_bytes())
    request = CONVERTER.structure(raw, AnalyticalRequest)
    base = CorpusReader(Path(request.root), max_rows=request.max_rows)
    if base.manifest_id != request.manifest:
        message = "analytical input head changed before the worker pinned its view"
        raise ValueError(message)
    retired = set(request.retired)
    reader = AdmissionReader(
        base,
        {},
        replace=False,
        retire=tuple(
            item
            for item in base.members()
            if (item.family, item.logical_id, item.profile) in retired
        ),
    )
    stream_hash = hashlib.sha256()
    count, total = 0, 0
    with tempfile.TemporaryFile(dir=Path(sys.argv[1]).parent) as spool:
        for record in _produce_checked(reader, request):
            codec = codec_for(record)
            frame = canonical(
                {
                    "kind": "record",
                    "sequence": count,
                    "record": {"family": codec.family, "row": codec.encode(record)},
                }
            )
            count += 1
            total += len(frame) + 4
            if count > request.max_records or total > request.max_bytes:
                message = "analytical worker exceeded its record/output/spool budget"
                raise BudgetExceededError(message)
            stream_hash.update(len(frame).to_bytes(8, "big"))
            stream_hash.update(frame)
            spool.write(len(frame).to_bytes(4, "big") + frame)
        identity = digest(raw)
        header = canonical(
            {
                "kind": "header",
                "protocol": "library-guides.facts.v1",
                "header": {
                    "request_id": identity,
                    "input_digest": identity,
                    "expected_records": count,
                },
            }
        )
        output = sys.stdout.buffer
        output.write(len(header).to_bytes(4, "big") + header)
        spool.seek(0)
        while chunk := spool.read(64 * 1024):
            output.write(chunk)
        terminal = canonical(
            {
                "kind": "terminal",
                "records": count,
                "digest": stream_hash.hexdigest(),
                "coverage": {
                    "state": "complete",
                    "empty_reason": "No products in the exact selected input",
                    "scope": "transport; product semantic frontiers are retained",
                },
            }
        )
        output.write(len(terminal).to_bytes(4, "big") + terminal)
        output.flush()


if __name__ == "__main__":
    from library_guides.corpus.backend import BudgetExceededError
    from library_guides.workflows.remote import BUDGET_EXIT

    try:
        main()
    except BudgetExceededError as error:
        sys.stderr.write(str(error) + "\n")
        raise SystemExit(BUDGET_EXIT) from error

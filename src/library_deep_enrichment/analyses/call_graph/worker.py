"""Typed route dispatch inside the existing supervised analytical worker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.call_graph import closure, index
from library_deep_enrichment.analyses.call_graph.contracts import (
    CallClosureRequest,
    CallIndexRequest,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader
    from library_deep_enrichment.workflows.remote import AnalyticalRequest


def produce(reader: CorpusReader, request: AnalyticalRequest) -> Iterable[Record]:
    """Dispatch a checked native catalog or helper-selection request.

    Returns:
        Typed results produced entirely from the pinned corpus reader.

    Raises:
        TypeError: The route does not have its exact typed subject.

    """
    if request.route == "native-call-index":
        subject = reader.get("call_index_requests", request.subject)
        if not isinstance(subject, CallIndexRequest):
            message = "native call worker requires a typed catalog request"
            raise TypeError(message)
        return (index.analyze(reader, subject),)
    subject = reader.get("call_closure_requests", request.subject)
    if request.route != "native-call-closure" or not isinstance(subject, CallClosureRequest):
        message = "native call worker requires a typed helper request"
        raise TypeError(message)
    return closure.analyze(reader, subject)

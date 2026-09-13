"""Bounded local embedding client with explicit model, tokenizer, and numerical contracts."""

from __future__ import annotations

import json
import math
from itertools import batched
from typing import TYPE_CHECKING, Protocol, cast

import httpx
import numpy as np
from attrs import frozen

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.encoding import digest
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import Embedding, EmbeddingRecipe, RetrievalUnit

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
NORM_TOLERANCE = 0.005


class Tokenizer(Protocol):
    """The local token-count boundary, isolated from the inference service."""

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        """Return token IDs for exact request text.

        Returns:
            Tokenizer output without truncation.

        """
        ...


@frozen(kw_only=True)
class Endpoint:
    """Operational location; this is not a second corpus authority."""

    url: str
    served_model: str
    tokenizer_path: Path
    timeout_seconds: float = 60.0
    batch_size: int = 4


def validate_vector(values: object, recipe: EmbeddingRecipe) -> tuple[float, ...]:
    """Validate model output before quantizing it to the declared float32 representation.

    Returns:
        A finite, correctly sized and normalized vector.

    Raises:
        CorpusError: A model response is malformed or violates its recipe.

    """
    if not isinstance(values, list) or len(values) != recipe.dimension:
        message = "embedding response dimension differs from its recipe"
        raise CorpusError(message)
    if any(type(value) not in {float, int} or not math.isfinite(value) for value in values):
        message = "embedding response contains non-numerical or non-finite components"
        raise CorpusError(message)
    vector = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(vector.astype(np.float64)))
    if (
        recipe.dtype != "float32"
        or recipe.normalization != "l2"
        or abs(norm - 1.0) > NORM_TOLERANCE
    ):
        message = "embedding dtype or normalization differs from its qualified recipe"
        raise CorpusError(message)
    return tuple(float(value) for value in vector)


class EmbeddingClient:
    """Actual inference only; callers explicitly choose lexical fallback after failure."""

    def __init__(self, endpoint: Endpoint, recipe: EmbeddingRecipe) -> None:
        """Bind a recipe; defer local tokenizer loading until inference is requested."""
        self.endpoint = endpoint
        self.recipe = recipe
        self._tokenizer: Tokenizer | None = None

    @property
    def tokenizer(self) -> Tokenizer:
        """Load the pinned tokenizer inside the caller's inference failure boundary."""
        from transformers import AutoTokenizer

        if self._tokenizer is None:
            self._tokenizer = cast(
                "Tokenizer",
                AutoTokenizer.from_pretrained(
                    str(self.endpoint.tokenizer_path),
                    local_files_only=True,
                    trust_remote_code=False,
                ),
            )
        return self._tokenizer

    def _request(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        if not texts or len(texts) > self.endpoint.batch_size:
            message = "embedding request exceeds its finite batch size"
            raise BudgetExceededError(message)
        with (
            httpx.Client(timeout=self.endpoint.timeout_seconds) as client,
            client.stream(
                "POST",
                f"{self.endpoint.url.rstrip('/')}/v1/embeddings",
                json={
                    "model": self.endpoint.served_model,
                    "input": list(texts),
                    "encoding_format": "float",
                },
            ) as response,
        ):
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > MAX_RESPONSE_BYTES:
                    message = "embedding response exceeded its byte budget"
                    raise BudgetExceededError(message)
        result = json.loads(data)
        rows = result.get("data") if isinstance(result, dict) else None
        if not isinstance(rows, list) or len(rows) != len(texts):
            message = "embedding response does not cover the exact requested input batch"
            raise CorpusError(message)
        indexed = {row.get("index"): row for row in rows if isinstance(row, dict)}
        if set(indexed) != set(range(len(texts))):
            message = "embedding response indices are missing, duplicated, or foreign"
            raise CorpusError(message)
        return [
            validate_vector(indexed[index].get("embedding"), self.recipe)
            for index in range(len(texts))
        ]

    def token_count(self, text: str) -> int:
        """Reject oversized inputs before inference instead of silently truncating evidence.

        Returns:
            Actual tokenizer count for the exact service input.

        Raises:
            BudgetExceededError: The input exceeds the recipe's context budget.

        """
        count = len(self.tokenizer.encode(text, add_special_tokens=True))
        if count > self.recipe.max_tokens:
            message = (
                f"embedding input has {count} tokens; recipe limit is {self.recipe.max_tokens}"
            )
            raise BudgetExceededError(message)
        return count

    def embed_units(self, units: Sequence[RetrievalUnit]) -> Iterator[Embedding]:
        """Infer exact document vectors, retaining tokenizer and input fingerprints.

        Yields:
            Validated model responses, never placeholder vectors.

        """
        for batch in batched(units, self.endpoint.batch_size, strict=False):
            texts = [self.recipe.document_prefix + unit.text for unit in batch]
            counts = [self.token_count(text) for text in texts]
            for unit, text, count, vector in zip(
                batch, texts, counts, self._request(texts), strict=True
            ):
                yield Embedding(
                    logical_id=f"embedding:{revision_of(self.recipe)}:{unit.logical_id}",
                    profile=unit.profile,
                    unit=revision_of(unit),
                    recipe=revision_of(self.recipe),
                    input_digest=digest(text),
                    vector=vector,
                    tokens=count,
                )

    def embed_query(self, query: str) -> tuple[float, ...]:
        """Embed a query using the recipe's distinct instruction template.

        Returns:
            The actual query vector in the same embedding space as its documents.

        """
        text = self.recipe.query_template.replace("{query}", query)
        self.token_count(text)
        return self._request([text])[0]

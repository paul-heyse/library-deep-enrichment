"""Explicit Arrow contracts for analytical records in the same corpus."""

import pyarrow as pa

from library_guides.corpus.schemas import NUMBER, SELECTIONS, TEXTS, fields, register
from library_guides.discovery import contracts as c

register(
    "discovery_scopes",
    c.DiscoveryScope,
    [
        ("profiles", TEXTS),
        ("packages", TEXTS),
        ("artifacts", TEXTS),
        ("max_units", NUMBER),
    ],
)

register(
    "retrieval_units",
    c.RetrievalUnit,
    [
        *fields("subject", "family", "title", "text", "text_digest"),
        ("support", SELECTIONS),
        ("frontier", TEXTS),
    ],
)
register(
    "embedding_recipes",
    c.EmbeddingRecipe,
    [
        *fields(
            "model",
            "model_revision",
            "tokenizer",
            "tokenizer_revision",
            "dtype",
            "pooling",
            "normalization",
            "document_prefix",
            "query_template",
            "runtime",
        ),
        ("dimension", NUMBER),
        ("max_tokens", NUMBER),
    ],
)
register(
    "embeddings",
    c.Embedding,
    [
        *fields("unit", "recipe", "input_digest"),
        ("vector", pa.list_(pa.field("item", pa.float32(), nullable=False))),
        ("tokens", NUMBER),
    ],
)
register("graph_nodes", c.GraphNode, fields("projection", "subject", "unit"))
register(
    "graph_edges",
    c.GraphEdge,
    [
        *fields("projection", "source", "target", "kind"),
        ("weight", pa.float64()),
        ("support", SELECTIONS),
    ],
)
register(
    "concepts",
    c.Concept,
    [
        *fields("kind", "scope", "recipe"),
        ("members", TEXTS),
        ("attributes", TEXTS),
        ("support", SELECTIONS),
        ("frontier", TEXTS),
    ],
)
register(
    "descriptors",
    c.Descriptor,
    [
        *fields("concept", "phrase"),
        ("score", pa.float64()),
        ("support", SELECTIONS),
    ],
)
register(
    "attributes",
    c.Attribute,
    fields(
        "predicate",
        "value_digest",
        "condition",
        "interpretation",
        "quantifier",
        "domain",
        "phase",
    ),
)

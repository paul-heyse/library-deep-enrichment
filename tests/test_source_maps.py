"""Exact source mapping controls across encodings, escapes and example transformations."""

from __future__ import annotations

import pytest
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.source_maps import (
    example_view,
    fences,
    identity,
    python_literal,
    rust_line_docs,
    select,
)


def test_unicode_crlf_doc_comments_and_hidden_lines() -> None:
    """Rustdoc prefixes and hidden lines map back to exact UTF-8 host byte slices."""
    raw = "/// Schema π\r\n/// ```rust,no_run\r\n/// # let π = 2;\r\n/// assert_eq!(π, 2);\r\n/// ```\r\n".encode()
    markdown = rust_line_docs(identity(raw))
    language, code, directives = fences(markdown)[0]
    assert language == "rust"
    assert directives == ("rust", "no_run")
    visible = example_view(code, language, executable=False)
    executable = example_view(code, language, executable=True)
    assert visible.data == "assert_eq!(π, 2);\n".encode()
    assert executable.data.startswith("let π = 2;\n".encode())
    position = visible.data.index("π".encode())
    selected = select(visible, position, position + len("π".encode()))
    assert selected.segments
    for segment in selected.segments:
        assert raw[segment.host_start : segment.host_end] == "π".encode()


def test_escaped_python_literal_has_non_linear_support() -> None:
    """A decoded Unicode escape cites its entire encoded source interval."""
    raw = b'"""A \\u03c0 value.\\n>>> identity(1)\r\n"""'
    mapped = python_literal(identity(raw))
    assert mapped.data.startswith("A π value.\n".encode())
    position = mapped.data.index("π".encode())
    selected = select(mapped, position, position + len("π".encode()))
    assert any(raw[s.host_start : s.host_end] == b"\\u03c0" for s in selected.segments)
    partial = select(mapped, position, position + 1)
    assert all(s.host_start is None for s in partial.segments)


def test_blockquote_fence_and_python_prompt_offsets() -> None:
    """Container prefixes and interactive prompts do not shift host coordinates."""
    raw = b"> ```python\n> >>> value = 1\n> ... value + 1\n> ```\n"
    language, mapped, _ = fences(identity(raw))[0]
    code = example_view(mapped, language, executable=True)
    assert code.data == b"value = 1\nvalue + 1\n"
    selected = select(code, 0, len(b"value"))
    assert raw[selected.segments[0].host_start : selected.segments[0].host_end] == b"value"


def test_unknown_language_and_non_documentation_remain_unknown() -> None:
    """A generic fence is not silently declared Rust, and ordinary comments are rejected."""
    assert fences(identity(b"```\nselect * from source\n```\n"))[0][0] == "unknown"
    with pytest.raises(CollectionError, match="ordinary comments"):
        rust_line_docs(identity(b"//// not Rustdoc\n"))
    with pytest.raises(CollectionError, match="single static"):
        python_literal(identity(b'f"computed {value}"'))

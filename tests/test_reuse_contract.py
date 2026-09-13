"""Core decision behavior must remain independent of the documented library.

This is the property that makes the compiler worth building: adding a library is
a manifest, not a code change. Infrastructure dependencies such as the fabric's
Arrow schemas and portable columnar format are distinct from library-specific
decision branches and per-operation content.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "tooling/library_guides/library_guides"

# Directories allowed to name a library, because naming one is their purpose.
_LIBRARY_AWARE = ("registry_adapters",)

_LIBRARY_TOKENS = (
    "datafusion",
    "pyarrow",
    "deltalake",
    "parquet",
    "pydantic",
    "polars",
    "duckdb",
)


def _library_blind_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if not any(part in _LIBRARY_AWARE for part in path.relative_to(PACKAGE_ROOT).parts)
    )


def _domain_mentions(source: str, token: str) -> list[int]:
    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    pattern = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and node.value != ".parquet"
        and pattern.search(node.value)
    ]


def test_there_are_library_blind_modules_to_check() -> None:
    """A vacuous pass would hide the very drift this guards."""
    modules = _library_blind_modules()
    minimum_expected = 20
    assert len(modules) >= minimum_expected, f"only found {len(modules)} modules"


@pytest.mark.parametrize("token", _LIBRARY_TOKENS)
def test_core_modules_do_not_name_a_library(token: str) -> None:
    """Library-specific behaviour belongs in manifests and registry adapters."""
    offenders: list[str] = []
    for path in _library_blind_modules():
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for number in _domain_mentions(source, token):
            relative = path.relative_to(PACKAGE_ROOT).as_posix()
            offenders.append(f"{relative}:{number}: {lines[number - 1].strip()[:90]}")
    assert not offenders, "core modules named a library:\n" + "\n".join(offenders[:8])


def test_storage_dependencies_do_not_license_library_specific_decisions() -> None:
    """Storage imports are allowed while an executable library-name branch still fails."""
    assert not _domain_mentions('import pyarrow as pa\npath = f"{family}.parquet"', "pyarrow")
    assert _domain_mentions('if package == "pyarrow":\n    choose_special_case()', "pyarrow")
    assert _domain_mentions('label = "Use pyarrow for this task"', "pyarrow")


def test_registry_adapters_are_resolved_by_identifier_not_import() -> None:
    """Stages resolve a probe through the registry so they never import one."""
    probe_stage = (PACKAGE_ROOT / "stages" / "probe_registry.py").read_text(encoding="utf-8")
    assert "probe_by_id" in probe_stage
    assert "pyarrow_compute" not in probe_stage
    assert "datafusion_functions" not in probe_stage

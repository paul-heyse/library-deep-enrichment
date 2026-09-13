"""Isolated, explicitly selected native-module introspection worker."""

from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import json
import sys

_PUBLIC_PROTOCOLS = frozenset(
    {
        "__arrow_c_array__",
        "__arrow_c_stream__",
        "__arrow_c_schema__",
        "__dlpack__",
        "__dataframe__",
        "__iter__",
    }
)


def signature_of(value: object) -> tuple[list[dict[str, object]], str, str]:
    """Inspect a real signature; missing metadata stays an explicit gap.

    Returns:
        Parameter metadata, the return annotation, and the resolution state.

    """
    if not callable(value):
        return [], "", "unresolved"
    try:
        signature = inspect.signature(value)
    except ValueError, TypeError:
        return [], "", "unresolved"
    parameters: list[dict[str, object]] = [
        {
            "name": item.name,
            "type": str(item.annotation) if item.annotation is not inspect.Parameter.empty else "",
            "kind": item.kind.name.lower(),
            "default": str(item.default) if item.default is not inspect.Parameter.empty else None,
        }
        for item in signature.parameters.values()
    ]
    returns = signature.return_annotation
    return parameters, "" if returns is inspect.Signature.empty else str(returns), "resolved"


def inspect_module(module: str) -> dict[str, object]:
    """Record public native APIs and docs without calling inspected functions.

    Returns:
        Native declarations and their distribution and interpreter versions.

    """
    loaded = importlib.import_module(module)
    records = {}
    pending: list[tuple[str, object, int]] = [(module, loaded, 0)]
    visited: set[int] = set()
    while pending:
        prefix, parent, depth = pending.pop()
        for name, value in inspect.getmembers_static(parent):
            if name.startswith("_") and name not in _PUBLIC_PROTOCOLS:
                continue
            path = f"{prefix}.{name}"
            if inspect.ismodule(value):
                continue
            if not callable(value) and not inspect.isdatadescriptor(value):
                continue
            parameters, returns, resolution = signature_of(value)
            records[path] = {
                "path": path,
                "canonical": path,
                "kind": "class" if inspect.isclass(value) else "function",
                "parameters": parameters,
                "returns": returns,
                "docs": inspect.getdoc(value) or "",
                "resolution": resolution,
            }
            if inspect.isclass(value) and depth < 1 and id(value) not in visited:
                visited.add(id(value))
                pending.append((path, value, depth + 1))
    return {
        "adapter": "isolated-native-v2",
        "module": module,
        "version": importlib.metadata.version(module.split(".", maxsplit=1)[0]),
        "python": sys.version,
        "records": records,
    }


if __name__ == "__main__":
    json.dump(inspect_module(sys.argv[1]), sys.stdout, sort_keys=True)

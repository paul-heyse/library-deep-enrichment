"""Isolated registry acquisition for the pilot; the core consumes generic records."""

from __future__ import annotations

import importlib.metadata
import json
import sys

from library_guides.registry_adapters.datafusion_functions import probe_datafusion_functions
from library_guides.registry_adapters.datafusion_settings import probe_datafusion_settings
from library_guides.registry_adapters.pyarrow_compute import probe_pyarrow_compute


def export(name: str) -> dict[str, object]:
    """Adapt registered runtime functionality to an evidence-first interchange shape.

    Returns:
        Versioned records preserving descriptions, availability and registry properties.

    Raises:
        ValueError: If any enumerated registry entry could not be read.

    """
    probes = {
        "pyarrow-compute": probe_pyarrow_compute,
        "datafusion-functions": probe_datafusion_functions,
        "datafusion-settings": probe_datafusion_settings,
    }
    package = name.split("-", 1)[0]
    result = probes[name](library_id=package, profile_id="installed-runtime")
    unreadable = getattr(result, "unreadable", ())
    if unreadable:
        message = f"registry entries could not be read: {unreadable}"
        raise ValueError(message)
    return {
        "package": package,
        "version": importlib.metadata.version(package),
        "acquisition": result.detail,
        "records": {
            entry.identity.name: {
                "description": entry.description or "",
                "kind": str(entry.surface_kind),
                "attributes": dict(entry.attributes),
                "conditions": entry.availability_conditions,
            }
            for entry in result.entries
        },
    }


if __name__ == "__main__":
    sys.stdout.write(json.dumps(export(sys.argv[1]), sort_keys=True) + "\n")

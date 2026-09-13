"""Registry probes: ask each library for its own catalog.

Importing this package registers every built-in probe, so the stage layer can
resolve a probe by identifier without naming any library.
"""

from __future__ import annotations

from library_guides.registry_adapters import (
    datafusion_functions,
    datafusion_settings,
    pyarrow_compute,
)
from library_guides.registry_adapters.registry import (
    ProbeResult,
    RegistryProbe,
    available_probes,
    probe_by_id,
    register_probe,
)

__all__ = [
    "ProbeResult",
    "RegistryProbe",
    "available_probes",
    "datafusion_functions",
    "datafusion_settings",
    "probe_by_id",
    "pyarrow_compute",
    "register_probe",
]

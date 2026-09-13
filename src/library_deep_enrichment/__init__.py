"""Library knowledge compiler for agent-facing library guides.

The package compiles acquired evidence and reviewed semantic records into the
guides described in ``docs/library_ref/library_reference_architecture_and_agent_skill_flow_2026-09-11.md``.

No module in this package may name a specific library. Library-specific
behaviour belongs in declarative manifests, optional registry adapters, and
optional rule packs.
"""

from __future__ import annotations

__all__ = ["SCHEMA_REVISION"]

SCHEMA_REVISION = "library-guides.records.v1"

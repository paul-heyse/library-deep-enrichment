"""Read structured RST and Sphinx inventories without crawling rendered HTML."""

from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import urljoin

import sphobjinv
from docutils import nodes
from docutils.core import publish_doctree

from library_guides.store.digests import digest_file


def rst_sections(path: Path) -> dict[str, object]:
    """Parse sections and links, preserving diagnostics and disabling file inclusion.

    Returns:
        Structural sections and unresolved directive/role diagnostics.

    """
    warnings = io.StringIO()
    tree = publish_doctree(
        path.read_text(encoding="utf-8"),
        source_path=str(path),
        settings_overrides={
            "file_insertion_enabled": False,
            "raw_enabled": False,
            "doctitle_xform": False,
            "sectsubtitle_xform": False,
            "warning_stream": warnings,
            "halt_level": 6,
        },
    )
    sections = []
    for section in tree.findall(nodes.section):
        title = next(section.findall(nodes.title), None)
        sections.append(
            {
                "ids": section.get("ids", []),
                "line": section.line,
                "title": title.astext() if title is not None else "",
                "text": section.astext(),
                "links": [
                    reference.get("refuri", reference.get("refid", ""))
                    for reference in section.findall(nodes.reference)
                ],
            }
        )
    return {
        "source_digest": digest_file(path),
        "sections": sections,
        "diagnostics": warnings.getvalue(),
        "authority": "documentation-structure",
    }


def sphinx_inventory(path: Path, *, base_url: str, profile: str) -> dict[str, object]:
    """Resolve domain object locations from a locally acquired inventory.

    Returns:
        Exact scoped object identifiers and documentation URLs, without behavioral claims.

    """
    inventory = sphobjinv.Inventory(fname_zlib=str(path))
    return {
        "profile": profile,
        "source_digest": digest_file(path),
        "project": inventory.project,
        "version": inventory.version,
        "objects": [
            {
                "name": item.name,
                "domain": item.domain,
                "role": item.role,
                "uri": urljoin(
                    base_url, item.uri[:-1] + item.name if item.uri.endswith("$") else item.uri
                ),
            }
            for item in inventory.objects
        ],
        "authority": "documentation-locator",
    }

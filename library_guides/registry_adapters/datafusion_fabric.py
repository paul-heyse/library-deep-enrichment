"""Acquire all SQL signatures, registry semantics, and settings from the exact loaded engine."""

from __future__ import annotations

import platform
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import datafusion
from datafusion import SessionContext

from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.contracts import (
    Context,
    Disposition,
    Job,
    Operation,
    Passage,
    RegistryEntry,
    RegistryKernel,
    RegistryProperty,
)
from library_guides.corpus.encoding import canonical, digest
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.staging import ObservationBuilder
from library_guides.store.digests import digest_file

if TYPE_CHECKING:
    from library_guides.corpus.store import Corpus


def _entry(
    builder: ObservationBuilder,
    context: Context,
    rows: list[dict[str, object]],
    parameters: list[dict[str, object]],
) -> None:
    row = {
        key: rows[0][key] if all(item[key] == rows[0][key] for item in rows) else None
        for key in rows[0]
    }
    name = str(row["specific_name"])
    raw = builder.observe(
        f"observation:sql:{name}",
        {"routines": rows, "parameters": parameters},
        profile=context.profile,
        kind="sql-registry",
        context=revision_of(context),
    )
    operation = Operation(
        logical_id=f"operation:sql-registry:{name}",
        profile=context.profile,
        symbol=f"sql:{name}",
        package="datafusion",
        version=datafusion.__version__,
        language="sql",
        kind="sql-function",
        signature=str(row.get("syntax_example") or ""),
        parameters=(),
        returns=" | ".join(
            sorted({str(item["data_type"]) for item in rows if item.get("data_type")})
        ),
        routes=(f"SQL:{name}",),
        resolution="registered-syntax-example-not-complete-signature",
        evidence=tuple(
            builder.select(raw, f"/routines/{index}", "registry-declaration")
            for index in range(len(rows))
        ),
    )
    owner = builder.add(operation)
    description = str(row.get("description") or "")
    entry = RegistryEntry(
        logical_id=f"registry:sql:{name}",
        profile=context.profile,
        operation=owner,
        namespace=f"{row['specific_catalog']}.{row['specific_schema']}",
        kind=str(row.get("function_type") or "unknown"),
        arity="overload-dependent",
        argument_names=tuple(
            dict.fromkeys(
                str(item["parameter_name"]) for item in parameters if item.get("parameter_name")
            )
        ),
        options_class="",
        options_required=False,
        summary=description,
        description=description,
        input_domain="sql-expressions-in-the-loaded-engine",
        phase="registered",
        evidence=operation.evidence,
    )
    entry_revision = builder.add(entry)
    builder.add(
        RegistryProperty(
            logical_id=f"registry-property:{name}:determinism",
            profile=context.profile,
            owner=entry_revision,
            owner_family="registry_entries",
            name="is_deterministic",
            value_kind="null" if row.get("is_deterministic") is None else "boolean",
            value_text=""
            if row.get("is_deterministic") is None
            else str(row["is_deterministic"]).lower(),
            evidence=tuple(
                builder.select(raw, f"/routines/{index}/is_deterministic", "runtime-declaration")
                for index in range(len(rows))
            ),
        )
    )
    if description:
        builder.add(
            Passage(
                logical_id=f"document:sql:{name}",
                profile=context.profile,
                owner=owner,
                role="upstream-registry-contract",
                text=description,
                language="en",
                source=builder.own_bytes(canonical(description), media_type="application/json"),
                evidence=tuple(
                    builder.select(raw, f"/routines/{index}/description", "upstream-contract")
                    for index in range(len(rows))
                ),
            )
        )
    signatures: dict[int, list[dict[str, object]]] = defaultdict(list)
    for parameter in parameters:
        rid = parameter.get("rid")
        if isinstance(rid, int):
            signatures[rid].append(parameter)
    for rid, members in sorted(signatures.items()):
        ordered = sorted(
            members,
            key=lambda item: (str(item["parameter_mode"]), int(str(item["ordinal_position"]))),
        )
        inputs = tuple(str(item["data_type"]) for item in ordered if item["parameter_mode"] == "IN")
        outputs = tuple(
            str(item["data_type"]) for item in ordered if item["parameter_mode"] == "OUT"
        )
        builder.add(
            RegistryKernel(
                logical_id=f"signature:sql:{name}:{rid}",
                profile=context.profile,
                operation=owner,
                registry_entry=entry_revision,
                kind="sql-overload",
                signature=f"({', '.join(inputs)}) -> {', '.join(outputs)}",
                inputs=inputs,
                output=", ".join(outputs),
                resolution="runtime-signature-variadic"
                if any(item.get("is_variadic") for item in members)
                else "runtime-signature",
                evidence=(builder.select(raw, "/parameters", "overload-domain"),),
            )
        )


def import_registry(corpus: Corpus, *, profile: str) -> dict[str, object]:
    """Capture complete registry tables, preserving overload rows and nullable declarations.

    Returns:
        Exact observed row and function counts for the pinned runtime context.

    """
    reader = corpus.reader()
    session = SessionContext()
    builder = ObservationBuilder(f"sql-registry.v1:{digest_file(Path(__file__))}")
    context = Context(
        logical_id=f"context:sql-registry:{datafusion.__version__}",
        profile=profile,
        language="sql",
        package="datafusion",
        version=datafusion.__version__,
        toolchain=f"python-{platform.python_version()}",
        target=f"{platform.system()}-{platform.machine()}",
        features=(),
        components=("default-SessionContext",),
    )
    builder.add(context)
    tables = {
        name: session.sql(f"SELECT * FROM information_schema.{name}").to_pylist()
        for name in ("routines", "parameters", "df_settings")
    }
    parameters: dict[str, list[dict[str, object]]] = defaultdict(list)
    for parameter in tables["parameters"]:
        parameters[str(parameter["specific_name"])].append(parameter)
    routines: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in tables["routines"]:
        routines[str(row["specific_name"])].append(row)
    builder.observe(
        "observation:sql:complete-tables",
        tables,
        profile=profile,
        kind="complete-registry-tables",
        context=revision_of(context),
    )
    for name, row in sorted(routines.items()):
        _entry(builder, context, row, parameters[name])
    for row in tables["df_settings"]:
        raw = builder.observe(
            f"observation:setting:{row['name']}",
            row,
            profile=profile,
            kind="registry-setting",
            context=revision_of(context),
        )
        builder.add(
            RegistryProperty(
                logical_id=f"setting:{row['name']}",
                profile=profile,
                owner=revision_of(context),
                owner_family="contexts",
                name=str(row["name"]),
                value_kind="null" if row.get("value") is None else "text",
                value_text=str(row["value"]) if row.get("value") is not None else "",
                evidence=tuple(
                    builder.select(raw, f"/{field}", "observed-setting-not-influence")
                    for field in row
                ),
            )
        )
    request = digest([builder.producer, revision_of(context), tables])
    builder.add(
        Job(
            logical_id="registry:sql",
            profile=profile,
            stage="sql-registry.v1",
            request=request,
            inputs=(),
            universes=(),
            outputs=tuple(builder.records),
            disposition=Disposition.COMPLETE,
            reason="All registry tables retained; overload signatures preserve source rid, modes, defaults, and variadic flags",
        )
    )
    manifest = Coordinator(corpus, WriterIdentity(principal="sql-registry-probe")).commit(
        builder.records.values(), expected=reader.manifest_id
    )
    return {
        "manifest": manifest,
        "functions": len(routines),
        "routines": len(tables["routines"]),
        "parameters": len(tables["parameters"]),
        "settings": len(tables["df_settings"]),
        "request": request,
    }

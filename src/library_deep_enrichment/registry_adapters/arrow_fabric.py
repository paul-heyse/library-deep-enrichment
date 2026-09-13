"""Capture the full native compute registry into the unified corpus."""

from __future__ import annotations

import inspect
import platform
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
from pyarrow import compute

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import (
    Argument,
    Context,
    Disposition,
    Job,
    Operation,
    Passage,
    RawObservation,
    RegistryEntry,
    RegistryKernel,
    Relation,
)
from library_deep_enrichment.corpus.encoding import canonical, digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.store.digests import digest_file

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus

_KERNEL = re.compile(r"^(?P<kind>\w+)Kernel<\((?P<inputs>.*?)\) -> (?P<output>.+)>$")


def _signature(name: str) -> tuple[str, tuple[Argument, ...], str]:
    function = getattr(compute, name, None)
    if function is None:
        return "", (), "registry-only"
    try:
        signature = inspect.signature(function)
    except ValueError, TypeError:
        return "", (), "opaque-callable"
    arguments = tuple(
        Argument(
            name=parameter.name,
            kind=parameter.kind.name.lower(),
            type_expression=""
            if parameter.annotation is inspect.Parameter.empty
            else str(parameter.annotation),
            default_expression=""
            if parameter.default is inspect.Parameter.empty
            else repr(parameter.default),
            required=parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD},
        )
        for parameter in signature.parameters.values()
    )
    return str(signature), arguments, "runtime-callable"


def _kernel_inputs(value: str) -> tuple[str, ...]:
    """Split only top-level kernel arguments, preserving nested type expressions.

    Returns:
        Ordered argument expressions, or an empty tuple for malformed delimiters.

    """
    stack: list[str] = []
    parts: list[str] = []
    start = 0
    closing = {">": "<", ")": "(", "]": "[", "}": "{"}
    for offset, character in enumerate(value):
        if character in "<([{":
            stack.append(character)
        elif character in closing:
            if not stack or stack.pop() != closing[character]:
                return ()
        elif character == "," and not stack:
            parts.append(value[start:offset].strip())
            start = offset + 1
    if stack:
        return ()
    return (*parts, value[start:].strip()) if value else ()


def _wrapper(
    builder: ObservationBuilder,
    name: str,
    context: Context,
    observation: RawObservation,
    parameters: tuple[Argument, ...],
) -> None:
    function = getattr(compute, name)
    captured = inspect.getclosurevars(function).nonlocals if inspect.isfunction(function) else {}
    target = captured.get("func")
    target_name = getattr(target, "name", "")
    try:
        source = inspect.getsource(function)
    except TypeError, OSError:
        source = ""
    bridge = builder.observe(
        f"observation:compute-wrapper:{name}",
        {
            "source": source,
            "captured_native_name": target_name,
            "doc": inspect.getdoc(function) or "",
            "signature": str(inspect.signature(function)),
        },
        profile=context.profile,
        kind="runtime-wrapper",
        context=revision_of(context),
    )
    operation = Operation(
        logical_id=f"operation:compute-wrapper:{name}",
        profile=context.profile,
        symbol=f"pyarrow.compute.{name}",
        package="pyarrow",
        version=str(pa.__version__),
        language="python",
        kind="function",
        signature=str(inspect.signature(function)),
        parameters=parameters,
        returns="",
        routes=(f"pyarrow.compute.{name}",),
        resolution="runtime-callable",
        evidence=(
            builder.select(observation, "/parameters", "runtime-parameters"),
            builder.select(bridge, "/signature", "runtime-interface"),
        ),
    )
    owner = builder.add(operation)
    documentation = inspect.getdoc(function) or ""
    if documentation:
        builder.add(
            Passage(
                logical_id=f"document:compute-wrapper:{name}",
                profile=context.profile,
                owner=owner,
                role="upstream-wrapper-contract",
                text=documentation,
                language="en",
                source=builder.own_bytes(canonical(documentation), media_type="application/json"),
                evidence=(builder.select(bridge, "/doc", "upstream-contract"),),
            )
        )
    if target_name == name:
        native = next(
            item
            for item in builder.records.values()
            if isinstance(item, Operation)
            and item.logical_id == f"operation:compute-registry:{name}"
        )
        builder.add(
            Relation(
                logical_id=f"relation:wrapper-capture:{name}",
                profile=context.profile,
                source=owner,
                target=revision_of(native),
                kind="captures-native-function",
                position=0,
                resolution="exact-capture-not-unconditional-dispatch",
                evidence=(
                    builder.select(bridge, "/captured_native_name", "captured-binding"),
                    builder.select(bridge, "/source", "branch-and-option-frontier"),
                ),
            )
        )


def _capture(builder: ObservationBuilder, name: str, context: Context) -> None:
    function = compute.get_function(name)
    documentation = getattr(function, "_doc", None)
    if documentation is None:
        message = f"registry documentation is unavailable for {name}"
        raise ValueError(message)
    signature, parameters, resolution = _signature(name)
    kernels = tuple(str(kernel) for kernel in getattr(function, "kernels", ()))
    data: dict[str, object] = {
        "name": name,
        "kind": function.kind,
        "arity": str(function.arity),
        "summary": documentation.summary,
        "description": documentation.description,
        "argument_names": documentation.arg_names,
        "options_class": documentation.options_class,
        "options_required": documentation.options_required,
        "kernels": list(kernels),
        "signature": signature,
        "resolution": resolution,
        "parameters": [
            {
                "name": p.name,
                "kind": p.kind,
                "type_expression": p.type_expression,
                "default_expression": p.default_expression,
                "required": p.required,
            }
            for p in parameters
        ],
        "input_domain": "grouped-kernel-inputs"
        if function.kind == "hash_aggregate"
        else "native-datum-inputs",
        "phase": "execution",
        "namespace": "grouped-compute-registry"
        if function.kind == "hash_aggregate"
        else "compute-registry",
    }
    observation = builder.observe(
        f"observation:compute:{name}",
        data,
        profile=context.profile,
        kind="native-compute-registry",
        context=revision_of(context),
    )
    operation = Operation(
        logical_id=f"operation:compute-registry:{name}",
        profile=context.profile,
        symbol=f"compute-registry:{name}",
        package="pyarrow",
        version=str(pa.__version__),
        language="python",
        kind="compute-function",
        signature="",
        parameters=(),
        returns="",
        routes=(),
        resolution="native-registry",
        evidence=(builder.select(observation, "/name", "registry-identity"),),
    )
    owner = builder.add(operation)
    if resolution == "runtime-callable":
        _wrapper(builder, name, context, observation, parameters)
    entry = RegistryEntry(
        logical_id=f"registry:compute:{name}",
        profile=context.profile,
        operation=owner,
        namespace=str(data["namespace"]),
        kind=function.kind,
        arity=str(function.arity),
        argument_names=tuple(documentation.arg_names),
        options_class=documentation.options_class,
        options_required=documentation.options_required,
        summary=documentation.summary,
        description=documentation.description,
        input_domain=str(data["input_domain"]),
        phase="execution",
        evidence=tuple(
            builder.select(observation, f"/{field}", "native-registry") for field in data
        ),
    )
    entry_revision = builder.add(entry)
    for field in ("summary", "description"):
        value = str(data[field])
        if value:
            builder.add(
                Passage(
                    logical_id=f"registry-document:compute:{name}:{field}",
                    profile=context.profile,
                    owner=owner,
                    role=f"upstream-{field}",
                    text=value,
                    language="en",
                    source=builder.own_bytes(canonical(value), media_type="application/json"),
                    evidence=(builder.select(observation, f"/{field}", "upstream-contract"),),
                )
            )
    for position, kernel in enumerate(kernels):
        match = _KERNEL.fullmatch(kernel)
        builder.add(
            RegistryKernel(
                logical_id=f"kernel:compute:{name}:{position}",
                profile=context.profile,
                operation=owner,
                registry_entry=entry_revision,
                kind=function.kind,
                signature=kernel,
                inputs=_kernel_inputs(match["inputs"]) if match else (),
                output=match["output"] if match else "",
                resolution=(
                    "computed-output"
                    if match and match["output"] == "computed"
                    else "registry-signature"
                    if match
                    else "unparsed"
                ),
                evidence=(
                    builder.select(observation, f"/kernels/{position}", "native-kernel-signature"),
                ),
            )
        )


def import_registry(corpus: Corpus, *, profile: str) -> dict[str, object]:
    """Admit every registered compute function and its original metadata and kernel signatures.

    Returns:
        Exact function/kernel counts and the coherent admitted manifest.

    """
    reader = corpus.reader()
    producer = f"native-compute-registry.v1:{digest_file(Path(__file__))}"
    builder = ObservationBuilder(producer)
    context = Context(
        logical_id=f"context:compute-registry:{pa.__version__}",
        profile=profile,
        language="python",
        package="pyarrow",
        version=str(pa.__version__),
        toolchain=f"python-{platform.python_version()}",
        target=f"{platform.system()}-{platform.machine()}",
        features=(),
        components=(f"arrow-cpp:{pa.cpp_version}",),
    )
    builder.add(context)
    names = tuple(sorted(compute.list_functions()))
    for name in names:
        _capture(builder, name, context)
    request = digest([producer, revision_of(context), sorted(builder.records)])
    builder.add(
        Job(
            logical_id="registry:compute",
            profile=profile,
            stage="native-compute-registry.v1",
            request=request,
            inputs=(),
            universes=(),
            outputs=tuple(builder.records),
            disposition=Disposition.COMPLETE,
            reason=f"All {len(names)} runtime registry entries captured; registry-only routes and computed kernel results remain explicit",
        )
    )
    manifest = Coordinator(corpus, WriterIdentity(principal="native-registry-probe")).commit(
        builder.records.values(),
        expected=reader.manifest_id,
    )
    return {
        "manifest": manifest,
        "functions": len(names),
        "kernels": sum(isinstance(item, RegistryKernel) for item in builder.records.values()),
        "request": request,
        "profile": profile,
    }

"""Decode exact Rust compiler invocation identities without reopening observed paths."""

from __future__ import annotations

import json
import re

from attrs import frozen

from library_guides.collection import CollectionError
from library_guides.store.digests import digest_bytes

MAX_ARGUMENTS = 10_000
MAX_SETTINGS = 10_000
MAX_TEXT = 1024 * 1024
SHORT_OPTION_LENGTH = 2
EXECUTION_SCHEMA = "library-guides.mir-execution.v1"
INSTANCE_SCHEMA = "library-guides.mir-instances.v1"
CALLABLE_SCHEMA = "library-guides.mir-callables.v1"
LIFECYCLE_SCHEMA = "library-guides.mir-lifecycle.v1"
MEMORY_SCHEMA = "library-guides.mir-memory.v1"
MAX_INSTANCES = 128
MAX_INSTANCE_DEPTH = 8
MAX_INSTANCE_CANDIDATES = 4096
VALUE_OPTIONS = frozenset(
    {
        "--crate-name",
        "--edition",
        "--error-format",
        "--json",
        "--crate-type",
        "--emit",
        "--check-cfg",
        "--out-dir",
        "--cap-lints",
        "--extern",
        "--target",
        "--sysroot",
        "--remap-path-prefix",
        "--diagnostic-width",
        "--color",
        "--print",
        "--cfg",
        "--codegen",
        "--allow",
        "--warn",
        "--deny",
        "--forbid",
        "--force-warn",
        "-C",
        "-L",
        "-A",
        "-W",
        "-D",
        "-F",
        "-Z",
        "-l",
        "-o",
    }
)
FLAG_OPTIONS = frozenset(
    {"--test", "-g", "-O", "--verbose", "-v", "--version", "-V", "--help", "-h"}
)


@frozen(kw_only=True)
class Arguments:
    """Parsed observed tokens; an unknown option leaves the remaining suffix opaque."""

    entries: tuple[tuple[str, str], ...]
    positionals: tuple[str, ...]
    frontier: tuple[str, ...]

    def values(self, name: str) -> tuple[str, ...]:
        """Select an option's observations.

        Returns:
            Repeated values in original invocation order.

        """
        return tuple(value for key, value in self.entries if key == name)


@frozen(kw_only=True)
class InstanceOptions:
    """Exact finite concrete-body acquisition options from the original compiler process."""

    max_instances: int
    max_depth: int
    max_candidates: int
    callable_references: bool = False
    lifecycle_uses: bool = False
    definition_roots: tuple[str, ...] = ()
    constant_memory: bool = False


@frozen(kw_only=True)
class ExecutionContext:
    """Observed process directory and exact original producer, separate from a normalizer."""

    working_directory: str
    schema: str
    provider_digest: str
    selected_packages: str | None
    instance_options: InstanceOptions | None = None


@frozen(kw_only=True)
class CompilerInvocation:
    """An exact process receipt; unobserved settings and dependency bytes stay unproved."""

    identity: str
    context: str
    purpose: str
    argv: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    inputs: tuple[tuple[str, str], ...]
    compiler_digest: str
    execution: ExecutionContext | None
    success: bool
    extraction: str
    frontier: tuple[str, ...]


def _string(value: object) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_TEXT:
        message = "invalid compiler invocation text"
        raise CollectionError(message)
    return value


def _digest(value: object) -> str:
    text = _string(value)
    digest_length = 64
    if len(text) != digest_length or any(character not in "0123456789abcdef" for character in text):
        message = "invalid compiler invocation digest"
        raise CollectionError(message)
    return text


def _mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > MAX_SETTINGS:
        message = "invalid compiler invocation setting map"
        raise CollectionError(message)
    return dict(sorted((_string(key), _string(item)) for key, item in value.items()))


def _wire_digest(value: object) -> str:
    # Invocation::new hashes serde tuples and declaration-ordered structs. Sorting
    # object keys globally would change the ExecutionContext identity preimage.
    return digest_bytes(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


def _execution(raw: object, legacy: str) -> tuple[ExecutionContext | None, str]:
    if raw is None:
        return None, legacy
    required = {
        "working_directory",
        "schema",
        "provider_digest",
        "selected_packages",
    }
    if not isinstance(raw, dict) or set(raw) not in (required, required | {"instance_options"}):
        message = "unsupported compiler execution context"
        raise CollectionError(message)
    schema = _string(raw["schema"])
    if schema not in {
        EXECUTION_SCHEMA,
        INSTANCE_SCHEMA,
        CALLABLE_SCHEMA,
        LIFECYCLE_SCHEMA,
        MEMORY_SCHEMA,
    } or not _string(raw["working_directory"]).startswith("/"):
        message = "unsupported compiler execution context schema or working directory"
        raise CollectionError(message)
    selected = raw["selected_packages"]
    execution = ExecutionContext(
        working_directory=_string(raw["working_directory"]),
        schema=schema,
        provider_digest=_digest(raw["provider_digest"]),
        selected_packages=None if selected is None else _string(selected),
        instance_options=_instance_options(raw, schema),
    )
    ordered: dict[str, object] = {
        "working_directory": execution.working_directory,
        "schema": execution.schema,
        "provider_digest": execution.provider_digest,
        "selected_packages": execution.selected_packages,
    }
    if execution.instance_options is not None:
        options = execution.instance_options
        selection: dict[str, object] = {
            "max_instances": options.max_instances,
            "max_depth": options.max_depth,
            "max_candidates": options.max_candidates,
        }
        if options.callable_references:
            selection["callable_references"] = True
        if options.lifecycle_uses:
            selection["lifecycle_uses"] = True
        if options.definition_roots:
            selection["definition_roots"] = list(options.definition_roots)
        if options.constant_memory:
            selection["constant_memory"] = True
        ordered["instance_options"] = selection
    return execution, _wire_digest([legacy, ordered])


def _instance_options(raw: dict, schema: str) -> InstanceOptions | None:
    if schema == EXECUTION_SCHEMA and "instance_options" not in raw:
        return None
    options = raw.get("instance_options")
    keys = {"max_instances", "max_depth", "max_candidates"}
    expected = (
        keys
        | (
            {"callable_references"}
            if schema in {CALLABLE_SCHEMA, LIFECYCLE_SCHEMA, MEMORY_SCHEMA}
            else set()
        )
        | ({"lifecycle_uses"} if schema in {LIFECYCLE_SCHEMA, MEMORY_SCHEMA} else set())
        | ({"constant_memory"} if schema == MEMORY_SCHEMA else set())
    )
    if (
        schema not in {INSTANCE_SCHEMA, CALLABLE_SCHEMA, LIFECYCLE_SCHEMA, MEMORY_SCHEMA}
        or not isinstance(options, dict)
        or set(options).difference({"definition_roots"}) != expected
    ):
        message = "instance execution context lacks its exact acquisition budget"
        raise CollectionError(message)
    if any(options[key] is not True for key in expected - keys):
        message = "versioned compiler execution features were not explicitly enabled"
        raise CollectionError(message)
    if not all(type(options[key]) is int for key in keys) or not (
        0 < options["max_instances"] <= MAX_INSTANCES
        and 0 <= options["max_depth"] <= MAX_INSTANCE_DEPTH
        and options["max_candidates"] == MAX_INSTANCE_CANDIDATES
    ):
        message = "invalid observed compiler instance budget"
        raise CollectionError(message)
    return InstanceOptions(
        max_instances=options["max_instances"],
        max_depth=options["max_depth"],
        max_candidates=options["max_candidates"],
        callable_references=options.get("callable_references", False),
        lifecycle_uses=options.get("lifecycle_uses", False),
        definition_roots=_definition_roots(options),
        constant_memory=options.get("constant_memory", False),
    )


def _definition_roots(options: dict) -> tuple[str, ...]:
    if "definition_roots" not in options:
        return ()
    roots = options["definition_roots"]
    if (
        not isinstance(roots, list)
        or not 0 < len(roots) <= MAX_INSTANCES
        or not all(
            isinstance(root, str)
            and re.fullmatch(r"definition:[0-9a-f]{16}:[0-9a-f]{32}:[0-9a-f]{32}", root)
            for root in roots
        )
        or roots != sorted(set(roots))
    ):
        message = "invalid exact compiler definition root denominator"
        raise CollectionError(message)
    return tuple(roots)


def read(raw: dict) -> CompilerInvocation:
    """Validate the original wrapper identity, including its versioned execution context.

    Returns:
        A bounded owned invocation. Legacy receipts explicitly lack execution context.

    Raises:
        CollectionError: The receipt is malformed, unsupported or identity-mismatched.

    """
    if set(raw) != {"invocation", "success", "extraction"} or type(raw["success"]) is not bool:
        message = "invalid compiler invocation receipt envelope"
        raise CollectionError(message)
    value = raw["invocation"]
    required = {
        "id",
        "context",
        "purpose",
        "argv",
        "environment",
        "inputs",
        "compiler_digest",
        "source_observation",
    }
    if not isinstance(value, dict) or set(value) not in (
        required,
        required | {"execution_context"},
    ):
        message = "unsupported compiler invocation fields"
        raise CollectionError(message)
    argv = value["argv"]
    if not isinstance(argv, list) or not 1 <= len(argv) <= MAX_ARGUMENTS:
        message = "invalid compiler invocation argument denominator"
        raise CollectionError(message)
    arguments = tuple(_string(item) for item in argv)
    environment = _mapping(value["environment"])
    inputs = {path: _digest(identity) for path, identity in _mapping(value["inputs"]).items()}
    context, purpose = _string(value["context"]), _string(value["purpose"])
    compiler = _digest(value["compiler_digest"])
    legacy = _wire_digest([context, purpose, arguments, environment, inputs, compiler])
    execution, identity = _execution(value.get("execution_context"), legacy)
    if _digest(value["id"]) != identity:
        message = "compiler invocation differs from its original identity"
        raise CollectionError(message)
    return CompilerInvocation(
        identity=identity,
        context=context,
        purpose=purpose,
        argv=arguments,
        environment=tuple(environment.items()),
        inputs=tuple(inputs.items()),
        compiler_digest=compiler,
        execution=execution,
        success=raw["success"],
        extraction=_string(raw["extraction"]),
        frontier=(
            _string(value["source_observation"]),
            *(() if execution else ("working_directory_and_original_provider_unobserved",)),
            "binary_dependency_and_generated_input_closure_requires_separate_witnesses",
        ),
    )


def arguments(invocation: CompilerInvocation) -> Arguments:
    """Read tokenized rustc options without interpreting values as later option names.

    Returns:
        Observed values only; opaque response files and unknown option arity remain open.

    Raises:
        CollectionError: A known option has a missing argument.

    """
    entries = []
    positionals = []
    frontier = []
    tokens = iter(invocation.argv[1:])
    for argument in tokens:
        name, separator, value = argument.partition("=")
        if argument == "--":
            positionals.extend(tokens)
            break
        if name in VALUE_OPTIONS:
            value = value if separator else next(tokens, None)
            if value is None:
                message = "compiler option lacks its value"
                raise CollectionError(message)
            entries.append((name, value))
        elif argument in FLAG_OPTIONS:
            entries.append((argument, "true"))
        elif (
            argument[:SHORT_OPTION_LENGTH] in VALUE_OPTIONS and len(argument) > SHORT_OPTION_LENGTH
        ):
            entries.append((argument[:SHORT_OPTION_LENGTH], argument[SHORT_OPTION_LENGTH:]))
        elif argument.startswith("@"):
            frontier.append("response_file_options_unexpanded:" + argument)
        elif argument.startswith("-"):
            frontier.append("unrecognized_option_arity_and_remaining_suffix:" + argument)
            break
        else:
            positionals.append(argument)
    return Arguments(
        entries=tuple(entries), positionals=tuple(positionals), frontier=tuple(frontier)
    )

"""Reusable predicate and rule data; no library names or per-operation prose cards."""

from __future__ import annotations

from library_deep_enrichment.corpus.contracts import Policy, Record
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import (
    CapabilitySchema,
    Interpretation,
    Predicate,
    Requirement,
    Rule,
    Value,
    ValueKind,
)

REGISTRY_KIND_TEMPLATE = "The loaded registry declares function kind {value}."


def text_value(value: str) -> Value:
    """Construct a semantic text value.

    Returns:
        An explicit tagged value, never an unknown/null sentinel.

    """
    return Value(kind=ValueKind.TEXT, text=value)


def foundation() -> tuple[Record, ...]:
    """Return the versioned initial language-neutral vocabulary and reusable rules.

    Returns:
        Predicate and rule definitions. Approval is a separate policy transaction.

    """
    carrier = Predicate(
        logical_id="predicate:declares-result-carrier",
        name="declares_result_carrier",
        description="Carrier named by the declared return type; excludes body and memory guarantees.",
        value_kind=ValueKind.TEXT,
        allowed_values=("stream", "collection", "table", "expression"),
        exclusive=True,
        interpretations=(Interpretation.DECLARATION,),
        template="The declared result carrier is {value}.",
    )
    delivery = Predicate(
        logical_id="predicate:documented-result-delivery",
        name="documented_result_delivery",
        description="The upstream result-consumption contract, excluding upstream operator memory.",
        value_kind=ValueKind.TEXT,
        allowed_values=("incremental", "collected"),
        exclusive=True,
        interpretations=(Interpretation.UPSTREAM_CONTRACT,),
        template="Upstream documents {value} result delivery; total operator memory remains unproved.",
    )
    operation_class = Predicate(
        logical_id="predicate:documented-operation-class",
        name="documented_operation_class",
        description="The action stated by an unqualified upstream summary; behavioral details remain separate.",
        value_kind=ValueKind.TEXT,
        allowed_values=(
            "construct-object",
            "validate-input",
            "read-data",
            "serialize-data",
            "deserialize-data",
        ),
        exclusive=False,
        interpretations=(Interpretation.UPSTREAM_CONTRACT,),
        template="Upstream describes the operation as {value}.",
    )
    rules: list[Record] = [carrier, delivery, operation_class]
    nominal = Predicate(
        logical_id="predicate:declares-nominal-output",
        name="declares_nominal_output",
        description="Direct output nominal resolved by the declaration producer in its exact artifact context; nested payloads remain separate.",
        value_kind=ValueKind.TEXT,
        allowed_values=(),
        exclusive=True,
        interpretations=(Interpretation.DECLARATION,),
        template="The declared direct output nominal is {value}.",
    )
    rules.extend(
        [
            nominal,
            Rule(
                logical_id="rule:direct-output-nominal",
                algorithm="direct-output-type",
                source_family="type_uses",
                selector="/nominal",
                pattern=".+",
                predicate=revision_of(nominal),
                value=text_value(""),
                condition="",
                quantifier="declared-interface",
                domain="the direct output type in the exact declaration artifact context",
                phase="declared",
                interpretation=Interpretation.DECLARATION,
                description=nominal.description,
                version="1",
            ),
        ]
    )
    patterns = (
        (
            "stream-carrier",
            carrier,
            "stream",
            r"^(?:[A-Za-z_]\w*(?:::|\.))*\w*(?:Stream|RecordBatchReader)\w*(?:<[^<>]*>)?$",
        ),
        (
            "collection-carrier",
            carrier,
            "collection",
            r"^(?:[A-Za-z_]\w*(?:::|\.))*(?:list\[|Vec<)",
        ),
        ("table-carrier", carrier, "table", r"(?:^|\.)Table$"),
        ("expression-carrier", carrier, "expression", r"(?:^|\W)(?:Expr|Expression)(?:$|\W)"),
        ("stream-document", delivery, "incremental", r"(?i)\breturns? (?:a )?stream\b"),
        (
            "collect-document",
            delivery,
            "collected",
            r"(?i)\bcollect(?:s)? (?:all )?(?:the )?results into memory\b",
        ),
        (
            "construct-summary",
            operation_class,
            "construct-object",
            r"(?i)^\s*(?:creates?|constructs?) (?:a |an )?(?:new|empty)\b",
        ),
        (
            "validate-summary",
            operation_class,
            "validate-input",
            r"(?i)^\s*validates? (?:a |an |the |input |json|python)",
        ),
        (
            "read-summary",
            operation_class,
            "read-data",
            r"(?i)^\s*reads? (?:a |an |the |data |all |records? |batches? )",
        ),
        ("serialize-summary", operation_class, "serialize-data", r"(?i)^\s*serializes?\b"),
        ("deserialize-summary", operation_class, "deserialize-data", r"(?i)^\s*deserializes?\b"),
    )
    for name, predicate, value, pattern in patterns:
        documented = predicate is not carrier
        rules.append(
            Rule(
                logical_id=f"rule:{name}",
                algorithm="document-sentence" if documented else "declaration-pattern",
                source_family="passages" if documented else "operations",
                selector="/text" if documented else "/returns",
                pattern=pattern,
                predicate=revision_of(predicate),
                value=text_value(value),
                condition="",
                quantifier="documented-contract" if documented else "declared-interface",
                domain="the selected operation in its exact profile",
                phase="declared" if predicate is operation_class else "consumption",
                interpretation=Interpretation.UPSTREAM_CONTRACT
                if documented
                else Interpretation.DECLARATION,
                description=predicate.description,
                version="2" if documented else "1",
            )
        )
    registry_kind = Predicate(
        logical_id="predicate:registered-function-kind",
        name="registered_function_kind",
        description="Function category declared by the exact loaded native or SQL registry; wrapper dispatch remains separate.",
        value_kind=ValueKind.TEXT,
        allowed_values=(),
        exclusive=True,
        interpretations=(Interpretation.DECLARATION,),
        template=REGISTRY_KIND_TEMPLATE,
    )
    rules.extend(
        (
            registry_kind,
            Rule(
                logical_id="rule:registry-function-kind",
                algorithm="registry-field",
                source_family="registry_entries",
                selector="/kind",
                pattern=r"^(?:scalar|scalar_aggregate|hash_aggregate|vector|meta|SCALAR|AGGREGATE|WINDOW)$",
                predicate=revision_of(registry_kind),
                value=text_value(""),
                condition="",
                quantifier="observed-registration",
                domain="the exact captured registry context, without a cross-language or unconditional wrapper claim",
                phase="registered",
                interpretation=Interpretation.DECLARATION,
                description=registry_kind.description,
                version="1",
            ),
        )
    )
    schemas = [(name, operation_class, "equal", name) for name in operation_class.allowed_values]
    schemas.extend(
        (
            ("consume-results", delivery, "exists", ""),
            ("registered-function", registry_kind, "exists", ""),
        )
    )
    rules.extend(
        CapabilitySchema(
            logical_id=f"capability-schema:{name}",
            name=name,
            description=predicate.description,
            requirements=(
                Requirement(
                    predicate=revision_of(predicate),
                    value=text_value(value),
                    operator=operator,
                    interpretations=predicate.interpretations,
                    mandatory=True,
                ),
            ),
            any_qualified_support=False,
        )
        for name, predicate, operator, value in schemas
    )
    rules.append(
        CapabilitySchema(
            logical_id="capability-schema:declared-operation",
            name="declared-operation",
            description="An interface with some qualified support; task suitability is not implied",
            requirements=(),
            any_qualified_support=True,
        )
    )
    return tuple(rules)


def approve_rules(
    records: tuple[Record, ...], *, authority: str, rationale: str
) -> tuple[Policy, ...]:
    """Create independently admitted rule approval proposals for exact revisions.

    Returns:
        Policy records requiring the coordinator's policy authority.

    """
    return tuple(
        Policy(
            logical_id=f"approval:{record.logical_id}",
            kind="rule-approval" if isinstance(record, Rule) else "schema-approval",
            subject=revision_of(record),
            authority=authority,
            rationale=rationale,
            allowed_predicates=(record.predicate,)
            if isinstance(record, Rule)
            else tuple(item.predicate for item in record.requirements),
            required_scopes=(),
        )
        for record in records
        if isinstance(record, (Rule, CapabilitySchema))
    )

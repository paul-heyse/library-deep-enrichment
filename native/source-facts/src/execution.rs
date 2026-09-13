//! Owned, role-preserving projection of Ruff nodes from the populated traversal.
//! This is source evidence, not a claim that Python runtime dispatch is closed.
use ruff_python_ast::{Comprehension, ExceptHandler, Expr, Number, Parameters, Stmt};
use ruff_text_size::Ranged;
use schemars::JsonSchema;
use serde::Serialize;

#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Node {
    pub kind: String,
    pub start: usize,
    pub end: usize,
    pub value: String,
    pub fields: Vec<Slot>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Slot {
    pub role: String,
    pub nodes: Vec<Node>,
}
fn slot(role: &str, nodes: Vec<Node>) -> Slot {
    Slot {
        role: role.into(),
        nodes,
    }
}
fn node(kind: &str, value: impl Into<String>, range: &impl Ranged, fields: Vec<Slot>) -> Node {
    Node {
        kind: kind.into(),
        start: range.start().to_usize(),
        end: range.end().to_usize(),
        value: value.into(),
        fields,
    }
}
fn ex(role: &str, expr: &Expr) -> Slot {
    slot(role, vec![expression(expr)])
}
fn opt(role: &str, expr: Option<&Expr>) -> Slot {
    slot(role, expr.map(expression).into_iter().collect())
}
fn exprs(role: &str, values: &[Expr]) -> Slot {
    slot(role, values.iter().map(expression).collect())
}
fn body(role: &str, values: &[Stmt]) -> Slot {
    slot(role, values.iter().map(statement).collect())
}
fn parameters(values: &Parameters) -> Slot {
    let mut result = Vec::new();
    for (kind, group) in [
        ("posonly", &values.posonlyargs),
        ("positional", &values.args),
        ("keyword_only", &values.kwonlyargs),
    ] {
        for item in group {
            result.push(node(
                kind,
                item.parameter.name.to_string(),
                item,
                vec![
                    opt("default", item.default.as_deref()),
                    opt("annotation", item.parameter.annotation.as_deref()),
                ],
            ));
        }
    }
    for (kind, value) in [("vararg", &values.vararg), ("kwarg", &values.kwarg)] {
        if let Some(value) = value {
            result.push(node(
                kind,
                value.name.to_string(),
                value.as_ref(),
                vec![opt("annotation", value.annotation.as_deref())],
            ));
        }
    }
    slot("parameters", result)
}
fn generators(values: &[Comprehension]) -> Slot {
    slot(
        "generators",
        values
            .iter()
            .map(|v| {
                node(
                    "generator",
                    if v.is_async { "async" } else { "sync" },
                    v,
                    vec![
                        ex("target", &v.target),
                        ex("iter", &v.iter),
                        exprs("ifs", &v.ifs),
                    ],
                )
            })
            .collect(),
    )
}
pub fn statement(value: &Stmt) -> Node {
    match value {
        Stmt::FunctionDef(v) => node(
            "function",
            v.name.to_string(),
            v,
            vec![
                slot(
                    "identifier",
                    vec![node("identifier", v.name.to_string(), &v.name, vec![])],
                ),
                parameters(&v.parameters),
                body("body", &v.body),
                opt("returns", v.returns.as_deref()),
                slot(
                    "decorators",
                    v.decorator_list
                        .iter()
                        .map(|d| expression(&d.expression))
                        .collect(),
                ),
                slot(
                    "mode",
                    vec![node(
                        if v.is_async { "async" } else { "sync" },
                        "",
                        v,
                        vec![],
                    )],
                ),
            ],
        ),
        Stmt::Assign(v) => node(
            "assign",
            "",
            v,
            vec![exprs("targets", &v.targets), ex("value", &v.value)],
        ),
        Stmt::AnnAssign(v) => node(
            "annotated_assign",
            "",
            v,
            vec![
                ex("target", &v.target),
                opt("value", v.value.as_deref()),
                ex("annotation", &v.annotation),
            ],
        ),
        Stmt::AugAssign(v) => node(
            "augmented_assign",
            v.op.as_str(),
            v,
            vec![ex("target", &v.target), ex("value", &v.value)],
        ),
        Stmt::Return(v) => node("return", "", v, vec![opt("value", v.value.as_deref())]),
        Stmt::Expr(v) => node("expression", "", v, vec![ex("value", &v.value)]),
        Stmt::If(v) => node(
            "if",
            "",
            v,
            vec![
                ex("test", &v.test),
                body("body", &v.body),
                slot(
                    "alternatives",
                    v.elif_else_clauses
                        .iter()
                        .map(|c| {
                            node(
                                "alternative",
                                "",
                                c,
                                vec![opt("test", c.test.as_ref()), body("body", &c.body)],
                            )
                        })
                        .collect(),
                ),
            ],
        ),
        Stmt::While(v) => node(
            "while",
            "",
            v,
            vec![
                ex("test", &v.test),
                body("body", &v.body),
                body("else", &v.orelse),
            ],
        ),
        Stmt::For(v) => node(
            "for",
            if v.is_async { "async" } else { "sync" },
            v,
            vec![
                ex("target", &v.target),
                ex("iter", &v.iter),
                body("body", &v.body),
                body("else", &v.orelse),
            ],
        ),
        Stmt::Try(v) => node(
            "try",
            if v.is_star {
                "exception_group"
            } else {
                "ordinary"
            },
            v,
            vec![
                body("body", &v.body),
                body("else", &v.orelse),
                body("finally", &v.finalbody),
                slot(
                    "handlers",
                    v.handlers
                        .iter()
                        .map(|h| {
                            let ExceptHandler::ExceptHandler(h) = h;
                            node(
                                "handler",
                                h.name.as_ref().map_or(String::new(), ToString::to_string),
                                h,
                                vec![opt("type", h.type_.as_deref()), body("body", &h.body)],
                            )
                        })
                        .collect(),
                ),
            ],
        ),
        Stmt::With(v) => node(
            "with",
            if v.is_async { "async" } else { "sync" },
            v,
            vec![
                body("body", &v.body),
                slot(
                    "items",
                    v.items
                        .iter()
                        .map(|i| {
                            node(
                                "with_item",
                                "",
                                i,
                                vec![
                                    ex("context", &i.context_expr),
                                    opt("target", i.optional_vars.as_deref()),
                                ],
                            )
                        })
                        .collect(),
                ),
            ],
        ),
        Stmt::Raise(v) => node(
            "raise",
            "",
            v,
            vec![
                opt("exception", v.exc.as_deref()),
                opt("cause", v.cause.as_deref()),
            ],
        ),
        Stmt::Assert(v) => node(
            "assert",
            "",
            v,
            vec![ex("test", &v.test), opt("message", v.msg.as_deref())],
        ),
        Stmt::Delete(v) => node("delete", "", v, vec![exprs("targets", &v.targets)]),
        Stmt::Match(v) => node(
            "match",
            "",
            v,
            vec![
                ex("subject", &v.subject),
                slot(
                    "cases",
                    v.cases
                        .iter()
                        .map(|c| {
                            node(
                                "case",
                                "",
                                c,
                                vec![
                                    slot("pattern", vec![pattern(&c.pattern)]),
                                    opt("guard", c.guard.as_deref()),
                                    body("body", &c.body),
                                ],
                            )
                        })
                        .collect(),
                ),
            ],
        ),
        Stmt::Global(v) => node(
            "global",
            "",
            v,
            vec![slot(
                "names",
                v.names
                    .iter()
                    .map(|n| node("name", n.to_string(), n, vec![]))
                    .collect(),
            )],
        ),
        Stmt::Nonlocal(v) => node(
            "nonlocal",
            "",
            v,
            vec![slot(
                "names",
                v.names
                    .iter()
                    .map(|n| node("name", n.to_string(), n, vec![]))
                    .collect(),
            )],
        ),
        Stmt::ClassDef(v) => node(
            "class",
            v.name.to_string(),
            v,
            vec![
                body("body", &v.body),
                slot(
                    "decorators",
                    v.decorator_list
                        .iter()
                        .map(|d| expression(&d.expression))
                        .collect(),
                ),
            ],
        ),
        Stmt::Pass(v) => node("pass", "", v, vec![]),
        Stmt::Break(v) => node("break", "", v, vec![]),
        Stmt::Continue(v) => node("continue", "", v, vec![]),
        _ => node(
            "unsupported_statement",
            "effects_and_control_unknown",
            value,
            vec![],
        ),
    }
}
pub fn expression(value: &Expr) -> Node {
    match value {
        Expr::Name(v) => node("name", v.id.to_string(), v, vec![]),
        Expr::BooleanLiteral(v) => node("boolean", v.value.to_string(), v, vec![]),
        Expr::NoneLiteral(v) => node("none", "None", v, vec![]),
        Expr::StringLiteral(v) => node("string", v.value.to_str(), v, vec![]),
        Expr::NumberLiteral(v) => match &v.value {
            Number::Int(i) => node("integer", i.to_string(), v, vec![]),
            Number::Float(f) => node("float_bits", f.to_bits().to_string(), v, vec![]),
            Number::Complex { real, imag } => node(
                "complex_bits",
                format!("{}:{}", real.to_bits(), imag.to_bits()),
                v,
                vec![],
            ),
        },
        Expr::Attribute(v) => node(
            "attribute",
            v.attr.to_string(),
            v,
            vec![ex("value", &v.value)],
        ),
        Expr::Subscript(v) => node(
            "subscript",
            "",
            v,
            vec![ex("value", &v.value), ex("index", &v.slice)],
        ),
        Expr::Slice(v) => node(
            "slice",
            "",
            v,
            vec![
                opt("lower", v.lower.as_deref()),
                opt("upper", v.upper.as_deref()),
                opt("step", v.step.as_deref()),
            ],
        ),
        Expr::BoolOp(v) => node(
            "boolean_op",
            v.op.as_str(),
            v,
            vec![exprs("values", &v.values)],
        ),
        Expr::BinOp(v) => node(
            "binary",
            v.op.as_str(),
            v,
            vec![ex("left", &v.left), ex("right", &v.right)],
        ),
        Expr::UnaryOp(v) => node("unary", v.op.as_str(), v, vec![ex("value", &v.operand)]),
        Expr::Compare(v) => node(
            "compare",
            "",
            v,
            vec![
                ex("left", &v.left),
                slot(
                    "comparators",
                    v.ops
                        .iter()
                        .zip(v.comparators.iter())
                        .map(|(op, other)| {
                            node("comparison", op.as_str(), other, vec![ex("value", other)])
                        })
                        .collect(),
                ),
            ],
        ),
        Expr::If(v) => node(
            "if_expression",
            "",
            v,
            vec![
                ex("test", &v.test),
                ex("body", &v.body),
                ex("else", &v.orelse),
            ],
        ),
        Expr::Named(v) => node(
            "named",
            "",
            v,
            vec![ex("target", &v.target), ex("value", &v.value)],
        ),
        Expr::Call(v) => node(
            "call",
            "",
            v,
            vec![
                ex("callee", &v.func),
                exprs("arguments", &v.arguments.args),
                slot(
                    "keywords",
                    v.arguments
                        .keywords
                        .iter()
                        .map(|k| {
                            node(
                                "keyword",
                                k.arg.as_ref().map_or("**".into(), ToString::to_string),
                                k,
                                vec![ex("value", &k.value)],
                            )
                        })
                        .collect(),
                ),
            ],
        ),
        Expr::Tuple(v) => node("tuple", "", v, vec![exprs("items", &v.elts)]),
        Expr::List(v) => node("list", "", v, vec![exprs("items", &v.elts)]),
        Expr::Set(v) => node("set", "", v, vec![exprs("items", &v.elts)]),
        Expr::Dict(v) => node(
            "dict",
            "",
            v,
            vec![slot(
                "items",
                v.items
                    .iter()
                    .map(|i| {
                        node(
                            "entry",
                            "",
                            i,
                            vec![opt("key", i.key.as_ref()), ex("value", &i.value)],
                        )
                    })
                    .collect(),
            )],
        ),
        Expr::Lambda(v) => node(
            "lambda",
            "",
            v,
            vec![
                v.parameters
                    .as_ref()
                    .map_or(slot("parameters", vec![]), |p| parameters(p)),
                ex("body", &v.body),
            ],
        ),
        Expr::Await(v) => node("await", "", v, vec![ex("value", &v.value)]),
        Expr::Yield(v) => node("yield", "", v, vec![opt("value", v.value.as_deref())]),
        Expr::YieldFrom(v) => node("yield_from", "", v, vec![ex("value", &v.value)]),
        Expr::ListComp(v) => node(
            "list_comprehension",
            "",
            v,
            vec![ex("element", &v.elt), generators(&v.generators)],
        ),
        Expr::SetComp(v) => node(
            "set_comprehension",
            "",
            v,
            vec![ex("element", &v.elt), generators(&v.generators)],
        ),
        Expr::DictComp(v) => node(
            "dict_comprehension",
            "",
            v,
            vec![
                opt("key", v.key.as_deref()),
                ex("element", &v.value),
                generators(&v.generators),
            ],
        ),
        Expr::Generator(v) => node(
            "generator_expression",
            "",
            v,
            vec![ex("element", &v.elt), generators(&v.generators)],
        ),
        Expr::Starred(v) => node("starred", "", v, vec![ex("value", &v.value)]),
        _ => node(
            "unsupported_expression",
            "implicit_dispatch_unknown",
            value,
            vec![],
        ),
    }
}
fn pattern(value: &ruff_python_ast::Pattern) -> Node {
    use ruff_python_ast::Pattern;
    match value {
        Pattern::MatchAs(v) => node(
            "pattern_as",
            v.name.as_ref().map_or(String::new(), ToString::to_string),
            v,
            vec![slot(
                "pattern",
                v.pattern.as_deref().map(pattern).into_iter().collect(),
            )],
        ),
        Pattern::MatchValue(v) => node("pattern_value", "", v, vec![ex("value", &v.value)]),
        Pattern::MatchSingleton(v) => node(
            "pattern_singleton",
            match v.value {
                ruff_python_ast::Singleton::None => "None",
                ruff_python_ast::Singleton::True => "True",
                ruff_python_ast::Singleton::False => "False",
            },
            v,
            vec![],
        ),
        Pattern::MatchSequence(v) => node(
            "pattern_sequence",
            "",
            v,
            vec![slot("patterns", v.patterns.iter().map(pattern).collect())],
        ),
        Pattern::MatchOr(v) => node(
            "pattern_or",
            "",
            v,
            vec![slot("patterns", v.patterns.iter().map(pattern).collect())],
        ),
        Pattern::MatchStar(v) => node(
            "pattern_star",
            v.name.as_ref().map_or(String::new(), ToString::to_string),
            v,
            vec![],
        ),
        _ => node(
            "unsupported_pattern",
            "dynamic_pattern_dispatch",
            value,
            vec![],
        ),
    }
}

//! Human-readable declarations; the owned typed value remains citation authority.
use crate::{contract as c, declarations::display_type};

pub fn path(p: &c::Path) -> String {
    format!("{}{}", p.path, args(p.args.as_deref()))
}
fn term(t: &c::Term) -> String {
    match t {
        c::Term::Type(t) => display_type(t),
        c::Term::Constant(c) => c.expr.clone(),
    }
}
pub fn params(p: &[c::GenericParamDef]) -> String {
    let values = p
        .iter()
        .filter_map(|p| {
            let tail = match &p.kind {
                c::GenericParamDefKind::Lifetime { outlives } => {
                    suffix(": ", &outlives.join(" + "))
                }
                c::GenericParamDefKind::Type {
                    bounds: b,
                    default,
                    is_synthetic,
                } => {
                    if *is_synthetic {
                        return None;
                    }
                    format!(
                        "{}{}",
                        suffix(": ", &bounds(b)),
                        default
                            .as_ref()
                            .map(|t| format!(" = {}", display_type(t)))
                            .unwrap_or_default()
                    )
                }
                c::GenericParamDefKind::Const { type_, default } => {
                    return Some(format!(
                        "const {}: {}{}",
                        p.name,
                        display_type(type_),
                        default
                            .as_ref()
                            .map(|v| format!(" = {v}"))
                            .unwrap_or_default()
                    ));
                }
            };
            Some(format!("{}{tail}", p.name))
        })
        .collect::<Vec<_>>();
    if values.is_empty() {
        String::new()
    } else {
        format!("<{}>", values.join(", "))
    }
}
fn suffix(prefix: &str, value: &str) -> String {
    if value.is_empty() {
        String::new()
    } else {
        format!("{prefix}{value}")
    }
}
pub fn binder(p: &[c::GenericParamDef]) -> String {
    let text = params(p);
    if text.is_empty() {
        text
    } else {
        format!("for{text} ")
    }
}
pub fn bounds(b: &[c::GenericBound]) -> String {
    b.iter()
        .map(|b| match b {
            c::GenericBound::Outlives(l) => l.clone(),
            c::GenericBound::Use(args) => format!(
                "use<{}>",
                args.iter()
                    .map(|a| match a {
                        c::PreciseCapturingArg::Lifetime(x) | c::PreciseCapturingArg::Param(x) =>
                            x.clone(),
                    })
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            c::GenericBound::TraitBound {
                trait_,
                generic_params,
                modifier,
            } => format!(
                "{}{}{}",
                binder(generic_params),
                match modifier {
                    c::TraitBoundModifier::None => "",
                    c::TraitBoundModifier::Maybe => "?",
                    c::TraitBoundModifier::MaybeConst => "~const ",
                },
                path(trait_)
            ),
        })
        .collect::<Vec<_>>()
        .join(" + ")
}
pub fn predicates(g: &c::Generics) -> String {
    let values = g
        .where_predicates
        .iter()
        .map(|p| match p {
            c::WherePredicate::Bound {
                type_,
                bounds: b,
                generic_params,
            } => format!(
                "{}{}: {}",
                binder(generic_params),
                display_type(type_),
                bounds(b)
            ),
            c::WherePredicate::Lifetime { lifetime, outlives } => {
                format!("{lifetime}: {}", outlives.join(" + "))
            }
            c::WherePredicate::Equality { lhs, rhs } => {
                format!("{} = {}", display_type(lhs), term(rhs))
            }
        })
        .collect::<Vec<_>>()
        .join(", ");
    suffix(" where ", &values)
}
pub fn args(a: Option<&c::GenericArgs>) -> String {
    match a {
        Some(c::GenericArgs::AngleBracketed { args, constraints }) => {
            let mut values = args
                .iter()
                .map(|a| match a {
                    c::GenericArg::Type(t) => display_type(t),
                    c::GenericArg::Lifetime(l) => l.clone(),
                    c::GenericArg::Const(c) => c.expr.clone(),
                    c::GenericArg::Infer => "_".into(),
                })
                .collect::<Vec<_>>();
            values.extend(constraints.iter().map(|a| {
                format!(
                    "{}{}{}",
                    a.name,
                    self::args(a.args.as_deref()),
                    match &a.binding {
                        c::AssocItemConstraintKind::Equality(t) => format!(" = {}", term(t)),
                        c::AssocItemConstraintKind::Constraint(b) => format!(": {}", bounds(b)),
                    }
                )
            }));
            if values.is_empty() {
                String::new()
            } else {
                format!("<{}>", values.join(", "))
            }
        }
        Some(c::GenericArgs::Parenthesized { inputs, output }) => format!(
            "({}){}",
            inputs
                .iter()
                .map(display_type)
                .collect::<Vec<_>>()
                .join(", "),
            output
                .as_ref()
                .map(|t| format!(" -> {}", display_type(t)))
                .unwrap_or_default()
        ),
        Some(c::GenericArgs::ReturnTypeNotation) => "(..)".into(),
        None => String::new(),
    }
}
pub fn header(h: &c::FunctionHeader) -> String {
    let abi = match &h.abi {
        c::Abi::Rust => None,
        c::Abi::C { unwind } => Some(("C", *unwind)),
        c::Abi::Cdecl { unwind } => Some(("cdecl", *unwind)),
        c::Abi::Stdcall { unwind } => Some(("stdcall", *unwind)),
        c::Abi::Fastcall { unwind } => Some(("fastcall", *unwind)),
        c::Abi::Aapcs { unwind } => Some(("aapcs", *unwind)),
        c::Abi::Win64 { unwind } => Some(("win64", *unwind)),
        c::Abi::SysV64 { unwind } => Some(("sysv64", *unwind)),
        c::Abi::System { unwind } => Some(("system", *unwind)),
        c::Abi::Other(name) => Some((name.as_str(), false)),
    };
    format!(
        "{}{}{}{}",
        if h.is_const { "const " } else { "" },
        if h.is_async { "async " } else { "" },
        if h.is_unsafe { "unsafe " } else { "" },
        abi.map(|(name, unwind)| format!(
            "extern \"{name}{}\" ",
            if unwind { "-unwind" } else { "" }
        ))
        .unwrap_or_default()
    )
}
pub fn function(symbol: &str, f: &c::Function) -> String {
    let mut inputs = f
        .sig
        .inputs
        .iter()
        .map(|(n, t)| format!("{n}: {}", display_type(t)))
        .collect::<Vec<_>>();
    if f.sig.is_c_variadic {
        inputs.push("...".into());
    }
    format!(
        "{}fn {symbol}{}({}) -> {}{}",
        header(&f.header),
        params(&f.generics.params),
        inputs.join(", "),
        f.sig
            .output
            .as_ref()
            .map(display_type)
            .unwrap_or_else(|| "()".into()),
        predicates(&f.generics)
    )
}

//! Typed MIR transfer, control-flow and call evidence; unsupported semantics remain explicit.
use rustc_middle::ty::TypeVisitableExt;
use rustc_public::{
    CrateDef,
    mir::{Body, Operand, Place, ProjectionElem, Rvalue, StatementKind, TerminatorKind},
    ty::{GenericArgKind, GenericArgs, RigidTy, Span, Ty, TyKind},
};
use rustc_public_bridge::IndexedVal;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Source {
    file: String,
    start_line: usize,
    start_col: usize,
    end_line: usize,
    end_col: usize,
    mapping: String,
    byte_start: Option<usize>,
    byte_end: Option<usize>,
    source_digest: Option<String>,
    expansion: bool,
}
fn span(value: Span, tcx: rustc_middle::ty::TyCtxt<'_>) -> Source {
    let line = value.get_lines();
    let raw = rustc_public::rustc_internal::internal(tcx, value);
    let map = tcx.sess.source_map();
    let low = map.lookup_byte_offset(raw.lo());
    let high = map.lookup_byte_offset(raw.hi());
    let file = value.get_filename();
    let bytes = std::fs::read(&file).ok();
    let same = low.sf.start_pos == high.sf.start_pos;
    let start = low.sf.original_relative_byte_pos(raw.lo()).0 as usize;
    let end = high.sf.original_relative_byte_pos(raw.hi()).0 as usize;
    let exact =
        same && bytes.as_ref().is_some_and(|bytes| {
            start <= end
                && end <= bytes.len()
                && rustc_span::SourceFileHash::new_in_memory(low.sf.src_hash.kind, bytes)
                    == low.sf.src_hash
        }) && low.sf.is_real_file();
    Source {
        file,
        start_line: line.start_line,
        start_col: line.start_col,
        end_line: line.end_line,
        end_col: line.end_col,
        mapping: if exact {
            "exact_original_file_bytes"
        } else {
            "unmapped"
        }
        .into(),
        byte_start: exact.then_some(start),
        byte_end: exact.then_some(end),
        source_digest: bytes.map(|bytes| lde_protocol::digest(&bytes)),
        expansion: raw.from_expansion(),
    }
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Type {
    pub kind: String,
    pub nominal: Option<String>,
    pub args: Vec<Type>,
    pub qualifiers: Vec<String>,
}
fn args(values: &GenericArgs, depth: usize) -> Vec<Type> {
    values
        .0
        .iter()
        .map(|value| match value {
            GenericArgKind::Type(value) => ty(*value, depth + 1),
            GenericArgKind::Lifetime(_) => Type {
                kind: "lifetime".into(),
                nominal: None,
                args: vec![],
                qualifiers: vec!["region_identity_not_retained".into()],
            },
            GenericArgKind::Const(_) => Type {
                kind: "const".into(),
                nominal: None,
                args: vec![],
                qualifiers: vec!["constant_value_unmodeled".into()],
            },
        })
        .collect()
}
fn ty(value: Ty, depth: usize) -> Type {
    let mut out = Type {
        kind: "unknown".into(),
        nominal: None,
        args: Vec::new(),
        qualifiers: Vec::new(),
    };
    if depth > 32 {
        out.qualifiers.push("type_depth_limit".into());
        return out;
    }
    let kind = match value.kind() {
        TyKind::Param(p) => {
            out.nominal = Some(p.name);
            "parameter"
        }
        TyKind::Alias(_, _) => {
            out.qualifiers.push("alias_definition_unmodeled".into());
            "alias"
        }
        TyKind::Bound(_, _) => {
            out.qualifiers.push("binder_unmodeled".into());
            "bound"
        }
        TyKind::RigidTy(value) => match value {
            RigidTy::Bool => "bool",
            RigidTy::Char => "char",
            RigidTy::Int(value) => {
                out.nominal = Some(format!("{value:?}"));
                "integer"
            }
            RigidTy::Uint(value) => {
                out.nominal = Some(format!("{value:?}"));
                "unsigned"
            }
            RigidTy::Float(value) => {
                out.nominal = Some(format!("{value:?}"));
                "float"
            }
            RigidTy::Str => "str",
            RigidTy::Never => "never",
            RigidTy::Adt(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "adt"
            }
            RigidTy::FnDef(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "function_definition"
            }
            RigidTy::Closure(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "closure"
            }
            RigidTy::Coroutine(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "coroutine"
            }
            RigidTy::CoroutineClosure(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "coroutine_closure"
            }
            RigidTy::CoroutineWitness(def, values) => {
                out.nominal = Some(def.name());
                out.args = args(&values, depth);
                "coroutine_witness"
            }
            RigidTy::Foreign(def) => {
                out.nominal = Some(def.name());
                "foreign"
            }
            RigidTy::Array(element, _) => {
                out.args.push(ty(element, depth + 1));
                out.qualifiers.push("array_length_unmodeled".into());
                "array"
            }
            RigidTy::Slice(element) => {
                out.args.push(ty(element, depth + 1));
                "slice"
            }
            RigidTy::RawPtr(element, mutability) => {
                out.args.push(ty(element, depth + 1));
                out.qualifiers.push(format!("{mutability:?}"));
                "raw_pointer"
            }
            RigidTy::Ref(_, element, mutability) => {
                out.args.push(ty(element, depth + 1));
                out.qualifiers.push(format!("{mutability:?}"));
                out.qualifiers.push("region_identity_not_retained".into());
                "reference"
            }
            RigidTy::Tuple(values) => {
                out.args = values.iter().map(|value| ty(*value, depth + 1)).collect();
                "tuple"
            }
            RigidTy::FnPtr(_) => {
                out.qualifiers
                    .push("function_pointer_signature_unmodeled".into());
                "function_pointer"
            }
            RigidTy::Dynamic(_, _) => {
                out.qualifiers.push("dynamic_predicates_unmodeled".into());
                "dynamic"
            }
            RigidTy::Pat(base, _) => {
                out.args.push(ty(base, depth + 1));
                out.qualifiers.push("pattern_unmodeled".into());
                "pattern"
            }
        },
    };
    out.kind = kind.into();
    out
}

pub(crate) fn behavior_type(value: Ty) -> Type {
    ty(value, 0)
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Projection {
    Deref,
    Field {
        index: usize,
        ty: Type,
    },
    Index {
        local: usize,
    },
    ConstantIndex {
        offset: u64,
        min_length: u64,
        from_end: bool,
    },
    Subslice {
        from: u64,
        to: u64,
        from_end: bool,
    },
    Downcast {
        variant: usize,
    },
    OpaqueCast {
        ty: Type,
    },
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Location {
    pub local: usize,
    pub projection: Vec<Projection>,
}
pub(crate) fn place(value: &Place) -> Location {
    Location {
        local: value.local,
        projection: value
            .projection
            .iter()
            .map(|p| match p {
                ProjectionElem::Deref => Projection::Deref,
                ProjectionElem::Field(i, t) => Projection::Field {
                    index: *i,
                    ty: ty(*t, 0),
                },
                ProjectionElem::Index(local) => Projection::Index { local: *local },
                ProjectionElem::ConstantIndex {
                    offset,
                    min_length,
                    from_end,
                } => Projection::ConstantIndex {
                    offset: *offset,
                    min_length: *min_length,
                    from_end: *from_end,
                },
                ProjectionElem::Subslice { from, to, from_end } => Projection::Subslice {
                    from: *from,
                    to: *to,
                    from_end: *from_end,
                },
                ProjectionElem::Downcast(v) => Projection::Downcast {
                    variant: v.to_index(),
                },
                ProjectionElem::OpaqueCast(t) => Projection::OpaqueCast { ty: ty(*t, 0) },
            })
            .collect(),
    }
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Value {
    pub mode: String,
    pub place: Option<Location>,
    pub ty: Option<Type>,
    pub unknown: Option<String>,
    #[serde(default)]
    pub literal: Option<crate::values::Literal>,
}
fn operand(value: &Operand, body: &Body) -> Value {
    let literal = match value {
        Operand::Constant(c) => crate::values::literal(&c.const_),
        _ => None,
    };
    let (mode, place, unknown) = match value {
        Operand::Copy(p) => ("copy", Some(place(p)), None),
        Operand::Move(p) => ("move", Some(place(p)), None),
        Operand::Constant(_) => (
            "constant",
            None,
            literal
                .is_none()
                .then(|| "constant_bytes_not_modeled".into()),
        ),
        Operand::RuntimeChecks(_) => ("runtime_checks", None, None),
    };
    Value {
        mode: mode.into(),
        place,
        ty: value.ty(body.locals()).ok().map(|value| ty(value, 0)),
        unknown,
        literal,
    }
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub block: usize,
    pub statement: usize,
    pub kind: String,
    pub destination: Option<Location>,
    pub values: Vec<Value>,
    pub source: Source,
    pub qualifier: Option<String>,
    #[serde(default)]
    pub constructor: Option<crate::values::Constructor>,
}
fn rvalue(value: &Rvalue, body: &Body) -> (String, Vec<Value>, Option<String>) {
    let (kind, values, detail) = match value {
        Rvalue::Use(value, _) => ("use", vec![operand(value, body)], None),
        Rvalue::BinaryOp(op, l, r) => (
            "binary",
            vec![operand(l, body), operand(r, body)],
            Some(format!("{op:?}")),
        ),
        Rvalue::CheckedBinaryOp(op, l, r) => (
            "checked_binary",
            vec![operand(l, body), operand(r, body)],
            Some(format!("{op:?}")),
        ),
        Rvalue::UnaryOp(op, value) => {
            ("unary", vec![operand(value, body)], Some(format!("{op:?}")))
        }
        Rvalue::Cast(kind, value, _) => (
            "cast",
            vec![operand(value, body)],
            Some(format!("{kind:?}")),
        ),
        Rvalue::Aggregate(_, values) => (
            "aggregate",
            values.iter().map(|value| operand(value, body)).collect(),
            None,
        ),
        Rvalue::Ref(_, kind, p) => (
            "borrow",
            vec![Value {
                mode: "place".into(),
                place: Some(place(p)),
                ty: p.ty(body.locals()).ok().map(|v| ty(v, 0)),
                unknown: None,
                literal: None,
            }],
            Some(format!("{kind:?}")),
        ),
        Rvalue::AddressOf(kind, p) => (
            "address_of",
            vec![Value {
                mode: "place".into(),
                place: Some(place(p)),
                ty: p.ty(body.locals()).ok().map(|v| ty(v, 0)),
                unknown: None,
                literal: None,
            }],
            Some(format!("{kind:?}")),
        ),
        Rvalue::Discriminant(p) | Rvalue::Len(p) | Rvalue::CopyForDeref(p) => (
            match value {
                Rvalue::Discriminant(_) => "discriminant",
                Rvalue::Len(_) => "length",
                _ => "copy_for_deref",
            },
            vec![Value {
                mode: "place".into(),
                place: Some(place(p)),
                ty: p.ty(body.locals()).ok().map(|v| ty(v, 0)),
                unknown: None,
                literal: None,
            }],
            None,
        ),
        _ => ("unmodeled_rvalue", vec![], Some("effect_frontier".into())),
    };
    (kind.into(), values, detail)
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Exit {
    pub block: usize,
    pub kind: String,
    pub successors: Vec<usize>,
    pub unwind: Option<String>,
    pub source: Source,
    pub callee: Option<Value>,
    pub args: Vec<Value>,
    pub destination: Option<Location>,
    pub assertion: Option<String>,
    pub dispatch: Option<String>,
    #[serde(default)]
    pub instance: Option<CallInstance>,
    #[serde(default)]
    pub branches: Vec<Branch>,
    #[serde(default)]
    pub otherwise: Option<usize>,
    #[serde(default)]
    pub expected: Option<bool>,
    #[serde(default)]
    pub unwind_block: Option<usize>,
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Branch {
    pub value: String,
    pub target: usize,
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CallInstance {
    Item {
        name: String,
        body_available: bool,
        foreign: bool,
        #[serde(default)]
        local_definition: Option<String>,
    },
    Virtual {
        name: String,
        slot: usize,
    },
    Intrinsic {
        name: String,
        llvm: bool,
    },
    Shim {
        name: String,
        body_available: bool,
    },
    Unresolved {
        reason: String,
    },
}
fn instance(tcx: rustc_middle::ty::TyCtxt<'_>, func: &Operand, body: &Body) -> CallInstance {
    use rustc_public::mir::mono::{Instance, InstanceKind};
    let Ok(ty) = func.ty(body.locals()) else {
        return CallInstance::Unresolved {
            reason: "operand_type_unavailable".into(),
        };
    };
    let internal = rustc_public::rustc_internal::internal(tcx, ty);
    if internal.has_non_region_param()
        || internal.has_non_region_infer()
        || internal.has_escaping_bound_vars()
        || internal.has_non_region_placeholders()
    {
        return CallInstance::Unresolved {
            reason: "generic_or_unresolved_definition_arguments".into(),
        };
    }
    let TyKind::RigidTy(RigidTy::FnDef(def, args)) = ty.kind() else {
        return CallInstance::Unresolved {
            reason: "indirect_operand_requires_flow_analysis".into(),
        };
    };
    let Ok(resolved) = Instance::resolve(def, &args) else {
        return CallInstance::Unresolved {
            reason: "compiler_instance_resolution_unavailable".into(),
        };
    };
    let name = resolved.name();
    let definition = rustc_public::rustc_internal::internal(tcx, resolved.def.def_id());
    match resolved.kind {
        InstanceKind::Item => CallInstance::Item {
            name,
            body_available: resolved.has_body(),
            foreign: resolved.is_foreign_item(),
            local_definition: definition.is_local().then(|| {
                format!(
                    "{:032x}",
                    u128::from_le_bytes(tcx.def_path_hash(definition).0.to_le_bytes())
                )
            }),
        },
        InstanceKind::Virtual { idx } => CallInstance::Virtual { name, slot: idx },
        InstanceKind::Intrinsic | InstanceKind::LlvmIntrinsic => CallInstance::Intrinsic {
            name,
            llvm: resolved.kind == InstanceKind::LlvmIntrinsic,
        },
        InstanceKind::Shim => CallInstance::Shim {
            name,
            body_available: resolved.has_body(),
        },
    }
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Local {
    pub index: usize,
    pub role: String,
    pub ty: Type,
    pub mutability: String,
}
#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Owner {
    pub name: String,
    pub source: Source,
    pub locals: Vec<Local>,
    pub events: Vec<Event>,
    pub exits: Vec<Exit>,
    pub frontier: Vec<String>,
}
pub fn owner(tcx: rustc_middle::ty::TyCtxt<'_>, name: String, body: Body) -> Owner {
    let locals = body
        .local_decls()
        .map(|(index, local)| Local {
            index,
            role: if index == 0 {
                "return"
            } else if index <= body.arg_locals().len() {
                "argument"
            } else {
                "local"
            }
            .into(),
            ty: ty(local.ty, 0),
            mutability: format!("{:?}", local.mutability),
        })
        .collect();
    let mut events = Vec::new();
    let mut exits = Vec::new();
    let mut frontier = Vec::new();
    for (block, basic) in body.blocks.iter().enumerate() {
        for (statement, event) in basic.statements.iter().enumerate() {
            let (kind, destination, values, qualifier) = match &event.kind {
                StatementKind::Assign(p, value) => {
                    let (kind, values, detail) = rvalue(value, &body);
                    (kind, Some(place(p)), values, detail)
                }
                StatementKind::StorageLive(local) => (
                    "storage_live".into(),
                    Some(Location {
                        local: *local,
                        projection: vec![],
                    }),
                    vec![],
                    None,
                ),
                StatementKind::StorageDead(local) => (
                    "storage_dead".into(),
                    Some(Location {
                        local: *local,
                        projection: vec![],
                    }),
                    vec![],
                    None,
                ),
                StatementKind::SetDiscriminant {
                    place: p,
                    variant_index,
                } => (
                    "set_discriminant".into(),
                    Some(place(p)),
                    vec![],
                    Some(variant_index.to_index().to_string()),
                ),
                StatementKind::Nop
                | StatementKind::ConstEvalCounter
                | StatementKind::Coverage(_) => ("non_transfer".into(), None, vec![], None),
                _ => (
                    "unmodeled_statement".into(),
                    None,
                    vec![],
                    Some("effect_frontier".into()),
                ),
            };
            if kind.starts_with("unmodeled") {
                frontier.push(format!("bb{block}:{statement}:{kind}"));
            }
            events.push(Event {
                block,
                statement,
                kind,
                destination,
                values,
                source: span(event.source_info.span, tcx),
                qualifier,
                constructor: match &event.kind {
                    StatementKind::Assign(_, Rvalue::Aggregate(kind, _)) => {
                        Some(crate::values::constructor(kind))
                    }
                    _ => None,
                },
            });
        }
        let term = &basic.terminator;
        let mut exit = Exit {
            block,
            kind: String::new(),
            successors: term.successors(),
            unwind: term.kind.unwind().map(|v| format!("{v:?}")),
            source: span(term.source_info.span, tcx),
            callee: None,
            args: vec![],
            destination: None,
            assertion: None,
            dispatch: None,
            instance: None,
            branches: vec![],
            otherwise: None,
            expected: None,
            unwind_block: match term.kind.unwind() {
                Some(rustc_public::mir::UnwindAction::Cleanup(block)) => Some(*block),
                _ => None,
            },
        };
        exit.kind = match &term.kind {
            TerminatorKind::Call {
                func,
                args,
                destination,
                ..
            } => {
                let value = operand(func, &body);
                exit.instance = Some(instance(tcx, func, &body));
                exit.dispatch = Some(
                    match &exit.instance {
                        Some(CallInstance::Item { .. }) => "compiler_resolved_item",
                        Some(CallInstance::Virtual { .. }) => "virtual_unresolved_implementation",
                        Some(CallInstance::Intrinsic { .. }) => "compiler_intrinsic",
                        Some(CallInstance::Shim { .. }) => "compiler_shim",
                        _ => "unresolved_dispatch",
                    }
                    .into(),
                );
                exit.callee = Some(value);
                exit.args = args.iter().map(|v| operand(v, &body)).collect();
                exit.destination = Some(place(destination));
                frontier.push(format!("bb{block}:callee_effects"));
                "call"
            }
            TerminatorKind::Assert {
                cond,
                msg,
                expected,
                ..
            } => {
                exit.expected = Some(*expected);
                exit.args.push(operand(cond, &body));
                exit.assertion = Some(
                    msg.description()
                        .map(str::to_string)
                        .unwrap_or_else(|_| "unmodeled_assertion".into()),
                );
                "assert"
            }
            TerminatorKind::Drop { place: p, .. } => {
                exit.destination = Some(place(p));
                frontier.push(format!("bb{block}:drop_effects"));
                "drop"
            }
            TerminatorKind::SwitchInt { discr, targets } => {
                exit.args.push(operand(discr, &body));
                exit.branches = targets
                    .branches()
                    .map(|(value, target)| Branch {
                        value: value.to_string(),
                        target,
                    })
                    .collect();
                exit.otherwise = Some(targets.otherwise());
                "switch"
            }
            TerminatorKind::Goto { .. } => "goto",
            TerminatorKind::Return => "return",
            TerminatorKind::Resume => "resume",
            TerminatorKind::Abort => "abort",
            TerminatorKind::Unreachable => "unreachable",
            TerminatorKind::InlineAsm { .. } => {
                frontier.push(format!("bb{block}:inline_asm"));
                "inline_asm"
            }
        }
        .into();
        exits.push(exit);
    }
    Owner {
        name,
        source: span(body.span, tcx),
        locals,
        events,
        exits,
        frontier,
    }
}

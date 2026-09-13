//! Versioned executable identities and typed scalar operations, outside legacy projections.
use rustc_middle::ty::TypeVisitableExt;
use rustc_public::{
    CrateDef,
    mir::{
        BinOp, Body, Operand, Rvalue, StatementKind, TerminatorKind, UnOp,
        mono::{Instance, InstanceKind},
    },
    ty::{GenericArgKind, GenericArgs, RigidTy, TyConstKind, TyKind},
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ScalarOperator {
    Add,
    Subtract,
    Multiply,
    Divide,
    Remainder,
    Xor,
    And,
    Or,
    ShiftLeft,
    ShiftRight,
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
    Compare,
    PointerOffset,
    Not,
    Negate,
    PointerMetadata,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ArithmeticMode {
    Ordinary,
    CheckedPair,
    Unchecked,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Operation {
    pub block: usize,
    pub statement: usize,
    pub operator: ScalarOperator,
    pub mode: ArithmeticMode,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Argument {
    Type {
        ty: crate::projection::Type,
    },
    Constant {
        ty: Option<crate::projection::Type>,
        value: Option<String>,
        encoding: String,
        frontier: Option<String>,
    },
    Lifetime {
        frontier: String,
    },
}

pub(crate) fn arguments(values: &GenericArgs) -> Vec<Argument> {
    values
        .0
        .iter()
        .map(|arg| match arg {
            GenericArgKind::Type(value) => Argument::Type {
                ty: crate::projection::behavior_type(*value),
            },
            GenericArgKind::Lifetime(_) => Argument::Lifetime {
                frontier: "region_identity_not_retained".into(),
            },
            GenericArgKind::Const(value) => match value.kind() {
                TyConstKind::Value(ty, allocation) => {
                    let scalar = match ty.kind() {
                        TyKind::RigidTy(RigidTy::Bool) => allocation
                            .read_bool()
                            .ok()
                            .map(|v| (v.to_string(), "boolean")),
                        TyKind::RigidTy(RigidTy::Int(_)) => allocation
                            .read_int()
                            .ok()
                            .map(|v| (v.to_string(), "signed_integer")),
                        TyKind::RigidTy(RigidTy::Uint(_)) => allocation
                            .read_uint()
                            .ok()
                            .map(|v| (v.to_string(), "unsigned_integer")),
                        _ => None,
                    };
                    let scalar = scalar.filter(|_| allocation.provenance.ptrs.is_empty());
                    Argument::Constant {
                        ty: Some(crate::projection::behavior_type(*ty)),
                        value: scalar.as_ref().map(|v| v.0.clone()),
                        encoding: scalar.as_ref().map_or("unmodeled", |v| v.1).into(),
                        frontier: scalar
                            .is_none()
                            .then(|| "non_scalar_or_provenance_constant".into()),
                    }
                }
                TyConstKind::Param(parameter) => Argument::Constant {
                    ty: None,
                    value: Some(parameter.name.clone()),
                    encoding: "parameter_name".into(),
                    frontier: Some("constant_parameter_requires_substitution".into()),
                },
                _ => Argument::Constant {
                    ty: None,
                    value: None,
                    encoding: "unmodeled".into(),
                    frontier: Some("unevaluated_or_bound_constant".into()),
                },
            },
        })
        .collect()
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Call {
    pub block: usize,
    pub declaration: Option<String>,
    pub target: Option<String>,
    pub substitutions: Vec<Argument>,
    pub instance_kind: String,
    pub complete: bool,
    pub frontier: Vec<String>,
}

pub fn identity(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    definition: rustc_span::def_id::DefId,
) -> String {
    let hash = tcx.def_path_hash(definition);
    format!(
        "definition:{:016x}:{:032x}:{:032x}",
        hash.stable_crate_id().as_u64(),
        u128::from_le_bytes(hash.0.to_le_bytes()),
        tcx.crate_hash(definition.krate).as_u128()
    )
}

pub(crate) fn call(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    body: &Body,
    block: usize,
    func: &Operand,
) -> Call {
    executable_call(tcx, body, block, func, false)
}

pub(crate) fn executable_call(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    body: &Body,
    block: usize,
    func: &Operand,
    shims: bool,
) -> Call {
    let mut out = Call {
        block,
        declaration: None,
        target: None,
        substitutions: vec![],
        instance_kind: "unresolved".into(),
        complete: false,
        frontier: vec![],
    };
    let Ok(ty) = func.ty(body.locals()) else {
        out.frontier.push("operand_type_unavailable".into());
        return out;
    };
    let TyKind::RigidTy(RigidTy::FnDef(def, args)) = ty.kind() else {
        out.frontier
            .push("indirect_dispatch_requires_value_flow".into());
        return out;
    };
    out.declaration = Some(identity(
        tcx,
        rustc_public::rustc_internal::internal(tcx, def.def_id()),
    ));
    out.substitutions = arguments(&args);
    let internal = rustc_public::rustc_internal::internal(tcx, ty);
    if internal.has_non_region_param()
        || internal.has_non_region_infer()
        || internal.has_escaping_bound_vars()
        || internal.has_non_region_placeholders()
    {
        out.frontier
            .push("generic_instance_resolution_not_attempted".into());
        return out;
    }
    let Ok(instance) = Instance::resolve(def, &args) else {
        out.frontier.push("instance_resolution_unavailable".into());
        return out;
    };
    out.substitutions = arguments(&instance.args());
    out.instance_kind = match instance.kind {
        InstanceKind::Item => "item",
        InstanceKind::Virtual { .. } => "virtual",
        InstanceKind::Intrinsic => "intrinsic",
        InstanceKind::LlvmIntrinsic => "llvm_intrinsic",
        InstanceKind::Shim => "shim",
    }
    .into();
    if (instance.kind == InstanceKind::Item || (shims && instance.kind == InstanceKind::Shim))
        && !instance.is_foreign_item()
    {
        out.target = Some(identity(
            tcx,
            rustc_public::rustc_internal::internal(tcx, instance.def.def_id()),
        ));
        out.complete = true;
    } else {
        out.frontier
            .push("non_item_dispatch_requires_qualified_model".into());
    }
    out
}

fn binary(op: BinOp) -> (ScalarOperator, ArithmeticMode) {
    use ArithmeticMode::{Ordinary, Unchecked};
    use ScalarOperator as S;
    match op {
        BinOp::Add => (S::Add, Ordinary),
        BinOp::AddUnchecked => (S::Add, Unchecked),
        BinOp::Sub => (S::Subtract, Ordinary),
        BinOp::SubUnchecked => (S::Subtract, Unchecked),
        BinOp::Mul => (S::Multiply, Ordinary),
        BinOp::MulUnchecked => (S::Multiply, Unchecked),
        BinOp::Div => (S::Divide, Ordinary),
        BinOp::Rem => (S::Remainder, Ordinary),
        BinOp::BitXor => (S::Xor, Ordinary),
        BinOp::BitAnd => (S::And, Ordinary),
        BinOp::BitOr => (S::Or, Ordinary),
        BinOp::Shl => (S::ShiftLeft, Ordinary),
        BinOp::ShlUnchecked => (S::ShiftLeft, Unchecked),
        BinOp::Shr => (S::ShiftRight, Ordinary),
        BinOp::ShrUnchecked => (S::ShiftRight, Unchecked),
        BinOp::Eq => (S::Equal, Ordinary),
        BinOp::Ne => (S::NotEqual, Ordinary),
        BinOp::Lt => (S::Less, Ordinary),
        BinOp::Le => (S::LessEqual, Ordinary),
        BinOp::Gt => (S::Greater, Ordinary),
        BinOp::Ge => (S::GreaterEqual, Ordinary),
        BinOp::Cmp => (S::Compare, Ordinary),
        BinOp::Offset => (S::PointerOffset, Ordinary),
    }
}

fn operation(value: &Rvalue, block: usize, statement: usize) -> Option<Operation> {
    let (operator, mode) = match value {
        Rvalue::BinaryOp(op, _, _) => binary(*op),
        Rvalue::CheckedBinaryOp(op, _, _) => (binary(*op).0, ArithmeticMode::CheckedPair),
        Rvalue::UnaryOp(op, _) => (
            match op {
                UnOp::Not => ScalarOperator::Not,
                UnOp::Neg => ScalarOperator::Negate,
                UnOp::PtrMetadata => ScalarOperator::PointerMetadata,
            },
            ArithmeticMode::Ordinary,
        ),
        _ => return None,
    };
    Some(Operation {
        block,
        statement,
        operator,
        mode,
    })
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Owner {
    pub definition: String,
    pub phase: String,
    pub operators: Vec<Operation>,
    pub calls: Vec<Call>,
    pub frontier: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<crate::shapes::Target>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub nominals: Vec<crate::shapes::Nominal>,
}

pub fn owner(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    definition: rustc_span::def_id::DefId,
    body: &Body,
) -> Owner {
    executable_owner(tcx, definition, body, false)
}

pub(crate) fn executable_owner(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    definition: rustc_span::def_id::DefId,
    body: &Body,
    shims: bool,
) -> Owner {
    let mut operators = Vec::new();
    let mut calls = Vec::new();
    for (block, basic) in body.blocks.iter().enumerate() {
        for (statement, event) in basic.statements.iter().enumerate() {
            if let StatementKind::Assign(_, value) = &event.kind
                && let Some(op) = operation(value, block, statement)
            {
                operators.push(op);
            }
        }
        if let TerminatorKind::Call { func, .. } = &basic.terminator.kind {
            calls.push(if shims {
                executable_call(tcx, body, block, func, true)
            } else {
                call(tcx, body, block, func)
            });
        }
    }
    let (nominals, complete) = crate::shapes::collect(tcx, body);
    let mut frontier = vec![
        "region_binders_and_full_alias_semantics_not_retained".into(),
        "instance_target_does_not_establish_effect_closure".into(),
    ];
    if !complete {
        frontier.push("nominal_type_population_budget".into());
    }
    Owner {
        definition: identity(tcx, definition),
        phase: "rustc_public_generic_definition_body".into(),
        operators,
        calls,
        frontier,
        target: Some(crate::shapes::target()),
        nominals,
    }
}

//! Owned constructor and literal facts; pointer provenance is never interpreted as an integer.
use rustc_public::{
    CrateDef,
    mir::AggregateKind,
    ty::{ConstantKind, MirConst, RigidTy, TyKind},
};
use rustc_public_bridge::IndexedVal;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Constructor {
    kind: String,
    nominal: Option<String>,
    variant: Option<String>,
    variant_index: Option<usize>,
}

pub fn constructor(value: &AggregateKind) -> Constructor {
    let mut result = Constructor {
        kind: String::new(),
        nominal: None,
        variant: None,
        variant_index: None,
    };
    result.kind = match value {
        AggregateKind::Adt(def, index, _, _, _) => {
            result.nominal = Some(def.name());
            result.variant = def.variant(*index).map(|v| v.name());
            result.variant_index = Some(index.to_index());
            "adt"
        }
        AggregateKind::Closure(def, _) => {
            result.nominal = Some(def.name());
            "closure"
        }
        AggregateKind::Coroutine(def, _) => {
            result.nominal = Some(def.name());
            "coroutine"
        }
        AggregateKind::CoroutineClosure(def, _) => {
            result.nominal = Some(def.name());
            "coroutine_closure"
        }
        AggregateKind::Array(_) => "array",
        AggregateKind::Tuple => "tuple",
        AggregateKind::RawPtr(_, _) => "raw_pointer",
    }
    .into();
    result
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Literal {
    kind: String,
    value: String,
}

pub fn literal(value: &MirConst) -> Option<Literal> {
    let ConstantKind::Allocated(allocation) = value.kind() else {
        return None;
    };
    if !allocation.provenance.ptrs.is_empty() {
        return None;
    }
    let (kind, value) = match value.ty().kind() {
        TyKind::RigidTy(RigidTy::Bool) => ("boolean", allocation.read_bool().ok()?.to_string()),
        TyKind::RigidTy(RigidTy::Int(_)) => {
            ("signed_integer", allocation.read_int().ok()?.to_string())
        }
        TyKind::RigidTy(RigidTy::Uint(_)) => {
            ("unsigned_integer", allocation.read_uint().ok()?.to_string())
        }
        TyKind::RigidTy(RigidTy::Float(_)) => {
            ("float_bits", allocation.read_uint().ok()?.to_string())
        }
        TyKind::RigidTy(RigidTy::Char) => {
            ("char_codepoint", allocation.read_uint().ok()?.to_string())
        }
        TyKind::RigidTy(RigidTy::RawPtr(_, _)) if allocation.is_null().ok()? => {
            ("null_pointer", "0".into())
        }
        _ => return None,
    };
    Some(Literal {
        kind: kind.into(),
        value,
    })
}

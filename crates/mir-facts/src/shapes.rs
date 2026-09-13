//! Compiler-owned logical type members and discriminants; no physical layout is inferred.
use rustc_public::{
    CrateDef, CrateDefType,
    mir::Body,
    target::{Endian, MachineInfo},
    ty::{AdtDef, AdtKind, GenericArgKind, GenericArgs, RigidTy, Ty, TyKind},
};
use rustc_public_bridge::IndexedVal;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashSet};

const TYPE_LIMIT: usize = 1024;

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Target {
    pub pointer_bits: usize,
    pub endianness: String,
}

pub fn target() -> Target {
    let machine = MachineInfo::target();
    Target {
        pointer_bits: machine.pointer_width.bits(),
        endianness: match machine.endian {
            Endian::Little => "little",
            Endian::Big => "big",
        }
        .into(),
    }
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Field {
    pub index: usize,
    pub name: String,
    pub definition: String,
    pub ty: crate::projection::Type,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Variant {
    pub index: usize,
    pub name: String,
    pub discriminant_bits: Option<String>,
    pub discriminant_type: Option<crate::projection::Type>,
    pub fields: Vec<Field>,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Nominal {
    pub definition: String,
    pub name: String,
    pub kind: String,
    pub variants: Vec<Variant>,
    pub member_type_policy: String,
}

fn nominal(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    definition: AdtDef,
    pending: &mut Vec<Ty>,
) -> Nominal {
    let variants = definition
        .variants_iter()
        .map(|variant| {
            let discriminant = matches!(definition.kind(), AdtKind::Enum)
                .then(|| definition.discriminant_for_variant(variant.idx()));
            let fields = variant
                .fields()
                .into_iter()
                .enumerate()
                .map(|(index, field)| {
                    let ty = field.ty();
                    pending.push(ty);
                    Field {
                        index,
                        name: field.name.clone(),
                        definition: crate::behavior::identity(
                            tcx,
                            rustc_public::rustc_internal::internal(tcx, field.def_id()),
                        ),
                        ty: crate::projection::behavior_type(ty),
                    }
                })
                .collect();
            Variant {
                index: variant.idx().to_index(),
                name: variant.name(),
                discriminant_bits: discriminant.as_ref().map(|value| value.val.to_string()),
                discriminant_type: discriminant
                    .as_ref()
                    .map(|value| crate::projection::behavior_type(value.ty)),
                fields,
            }
        })
        .collect();
    Nominal {
        definition: crate::behavior::identity(
            tcx,
            rustc_public::rustc_internal::internal(tcx, definition.def_id()),
        ),
        name: definition.name(),
        kind: definition.kind().to_string(),
        variants,
        member_type_policy: "declaration_types_require_observed_generic_substitution".into(),
    }
}

fn arguments(args: GenericArgs, pending: &mut Vec<Ty>) {
    pending.extend(args.0.into_iter().filter_map(|arg| {
        if let GenericArgKind::Type(ty) = arg {
            Some(ty)
        } else {
            None
        }
    }));
}

pub fn collect(tcx: rustc_middle::ty::TyCtxt<'_>, body: &Body) -> (Vec<Nominal>, bool) {
    let mut pending: Vec<Ty> = body.local_decls().map(|(_, local)| local.ty).collect();
    let mut seen = HashSet::new();
    let mut definitions = BTreeMap::new();
    let mut complete = true;
    while let Some(ty) = pending.pop() {
        if seen.contains(&ty) {
            continue;
        }
        if seen.len() >= TYPE_LIMIT {
            complete = false;
            break;
        }
        seen.insert(ty);
        if let TyKind::RigidTy(rigid) = ty.kind() {
            match rigid {
                RigidTy::Adt(def, args) => {
                    let key = crate::behavior::identity(
                        tcx,
                        rustc_public::rustc_internal::internal(tcx, def.def_id()),
                    );
                    definitions
                        .entry(key)
                        .or_insert_with(|| nominal(tcx, def, &mut pending));
                    arguments(args, &mut pending);
                }
                RigidTy::Ref(_, element, _)
                | RigidTy::RawPtr(element, _)
                | RigidTy::Array(element, _)
                | RigidTy::Slice(element)
                | RigidTy::Pat(element, _) => pending.push(element),
                RigidTy::Tuple(elements) => pending.extend(elements),
                RigidTy::FnDef(_, args)
                | RigidTy::Closure(_, args)
                | RigidTy::Coroutine(_, args)
                | RigidTy::CoroutineClosure(_, args)
                | RigidTy::CoroutineWitness(_, args) => arguments(args, &mut pending),
                _ => {}
            }
        }
    }
    (definitions.into_values().collect(), complete)
}

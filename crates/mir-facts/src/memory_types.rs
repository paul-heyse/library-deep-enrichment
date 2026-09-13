//! Owned physical layouts, with instantiated field types and explicit unsupported shapes.
use crate::{behavior, projection};
use rustc_middle::ty::TypeVisitableExt;
use rustc_public::{
    CrateDef,
    abi::{FieldsShape, Primitive, Scalar, TagEncoding, VariantsShape},
    ty::{RigidTy, Ty, TyKind},
};
use rustc_public_bridge::IndexedVal;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

const MAX_TYPES: usize = 1024;
const MAX_FIELDS: usize = 4096;

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Member {
    pub index: usize,
    pub name: String,
    pub definition: Option<String>,
    pub ty: Option<usize>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Variant {
    pub index: usize,
    pub name: String,
    pub members: Vec<Member>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Fields {
    Primitive,
    Union { count: usize },
    Array { stride: usize, count: u64 },
    Arbitrary { offsets: Vec<usize> },
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Tag {
    pub primitive: String,
    pub bits: usize,
    pub signed: Option<bool>,
    pub valid_start: Option<String>,
    pub valid_end: Option<String>,
    pub field: usize,
    pub encoding: String,
    pub untagged_variant: Option<usize>,
    pub niche_variants: Option<[usize; 2]>,
    pub niche_start: Option<String>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Layout {
    pub size: usize,
    pub alignment: u64,
    pub sized: bool,
    pub fields: Fields,
    pub variant_kind: String,
    pub single_variant: Option<usize>,
    pub variant_offsets: Vec<Vec<usize>>,
    pub tag: Option<Tag>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Type {
    pub ty: projection::Type,
    pub definition: Option<String>,
    pub layout: Option<Layout>,
    pub element: Option<usize>,
    pub variants: Vec<Variant>,
    pub frontier: Vec<String>,
    pub signature: Option<Signature>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Signature {
    pub abi: String,
    pub inputs: Vec<Option<usize>>,
    pub output: Option<usize>,
    pub c_variadic: bool,
}

#[derive(Default)]
pub struct Collector {
    ids: HashMap<Ty, usize>,
    pending: Vec<Ty>,
    pub nodes: Vec<Type>,
}
impl Collector {
    pub fn intern(&mut self, ty: Ty) -> Option<usize> {
        if let Some(id) = self.ids.get(&ty) {
            return Some(*id);
        }
        if self.ids.len() >= MAX_TYPES {
            return None;
        }
        let id = self.pending.len();
        self.ids.insert(ty, id);
        self.pending.push(ty);
        Some(id)
    }
    pub fn finish(&mut self, tcx: rustc_middle::ty::TyCtxt<'_>) {
        while self.nodes.len() < self.pending.len() {
            let ty = self.pending[self.nodes.len()];
            let mut node = Type {
                ty: projection::behavior_type(ty),
                definition: None,
                layout: ty.layout().ok().map(layout),
                element: None,
                variants: vec![],
                frontier: vec![],
                signature: None,
            };
            if node.layout.is_none() {
                node.frontier.push("physical_layout_unavailable".into());
            }
            if let Some(signature) = ty.kind().fn_sig() {
                let signature = signature.value;
                let inputs = signature
                    .inputs()
                    .iter()
                    .map(|ty| self.intern(*ty))
                    .collect::<Vec<_>>();
                let output = self.intern(signature.output());
                if inputs.iter().any(Option::is_none) || output.is_none() {
                    node.frontier.push("type_population_budget".into());
                }
                node.signature = Some(Signature {
                    abi: format!("{:?}", signature.abi),
                    inputs,
                    output,
                    c_variadic: signature.c_variadic,
                });
            }
            match ty.kind() {
                TyKind::RigidTy(RigidTy::Adt(def, args)) => {
                    node.definition = Some(behavior::identity(
                        tcx,
                        rustc_public::rustc_internal::internal(tcx, def.def_id()),
                    ));
                    let count: usize = def.variants_iter().map(|v| v.fields().len()).sum();
                    if count > MAX_FIELDS {
                        node.frontier.push("member_population_budget".into());
                    } else {
                        let internal_args = rustc_public::rustc_internal::internal(tcx, args);
                        for variant in def.variants_iter() {
                            let mut members = vec![];
                            for (index, field) in variant.fields().into_iter().enumerate() {
                                let definition =
                                    rustc_public::rustc_internal::internal(tcx, field.def_id());
                                // The public field surface exposes declaration types only. This
                                // pinned bridge instantiates that exact definition, never names.
                                let ty = if internal_args.has_non_region_param()
                                    || internal_args.has_non_region_infer()
                                    || internal_args.has_escaping_bound_vars()
                                {
                                    node.frontier
                                        .push("generic_member_instantiation_unavailable".into());
                                    None
                                } else {
                                    match tcx.try_instantiate_and_normalize_erasing_regions(
                                        internal_args,
                                        rustc_middle::ty::TypingEnv::fully_monomorphized(),
                                        tcx.type_of(definition),
                                    ) {
                                        Ok(field_ty) => {
                                            let selected = self.intern(
                                                rustc_public::rustc_internal::stable(field_ty),
                                            );
                                            if selected.is_none() {
                                                node.frontier.push("type_population_budget".into());
                                            }
                                            selected
                                        }
                                        Err(_) => {
                                            node.frontier
                                                .push("member_normalization_unavailable".into());
                                            None
                                        }
                                    }
                                };
                                members.push(Member {
                                    index,
                                    name: field.name,
                                    definition: Some(behavior::identity(tcx, definition)),
                                    ty,
                                });
                            }
                            node.variants.push(Variant {
                                index: variant.idx().to_index(),
                                name: variant.name(),
                                members,
                            });
                        }
                    }
                }
                TyKind::RigidTy(RigidTy::Tuple(fields)) => {
                    if fields.len() > MAX_FIELDS {
                        node.frontier.push("member_population_budget".into());
                    } else {
                        let members = fields
                            .into_iter()
                            .enumerate()
                            .map(|(index, ty)| Member {
                                index,
                                name: index.to_string(),
                                definition: None,
                                ty: self.intern(ty),
                            })
                            .collect::<Vec<_>>();
                        if members.iter().any(|m| m.ty.is_none()) {
                            node.frontier.push("type_population_budget".into());
                        }
                        node.variants.push(Variant {
                            index: 0,
                            name: "tuple".into(),
                            members,
                        });
                    }
                }
                TyKind::RigidTy(
                    RigidTy::Ref(_, element, _)
                    | RigidTy::RawPtr(element, _)
                    | RigidTy::Array(element, _)
                    | RigidTy::Slice(element),
                ) => {
                    node.element = self.intern(element);
                    if node.element.is_none() {
                        node.frontier.push("type_population_budget".into());
                    }
                }
                TyKind::RigidTy(
                    RigidTy::Closure(_, _)
                    | RigidTy::Coroutine(_, _)
                    | RigidTy::CoroutineClosure(_, _),
                ) => node
                    .frontier
                    .push("environment_physical_members_not_projected".into()),
                _ => {}
            }
            node.frontier.sort();
            node.frontier.dedup();
            self.nodes.push(node);
        }
    }
}

fn layout(value: rustc_public::abi::Layout) -> Layout {
    let shape = value.shape();
    let fields = match shape.fields {
        FieldsShape::Primitive => Fields::Primitive,
        FieldsShape::Union(count) => Fields::Union { count: count.get() },
        FieldsShape::Array { stride, count } => Fields::Array {
            stride: stride.bytes(),
            count,
        },
        FieldsShape::Arbitrary { offsets } => Fields::Arbitrary {
            offsets: offsets.into_iter().map(|s| s.bytes()).collect(),
        },
    };
    let (variant_kind, single_variant, variant_offsets, tag) = match shape.variants {
        VariantsShape::Empty => ("empty", None, vec![], None),
        VariantsShape::Single { index } => ("single", Some(index.to_index()), vec![], None),
        VariantsShape::Multiple {
            tag,
            tag_encoding,
            tag_field,
            variants,
        } => (
            "multiple",
            None,
            variants
                .into_iter()
                .map(|v| v.offsets.into_iter().map(|s| s.bytes()).collect())
                .collect(),
            Some(project_tag(tag, tag_encoding, tag_field)),
        ),
    };
    Layout {
        size: shape.size.bytes(),
        alignment: shape.abi_align,
        sized: !shape.abi.is_unsized(),
        fields,
        variant_kind: variant_kind.into(),
        single_variant,
        variant_offsets,
        tag,
    }
}
fn project_tag(scalar: Scalar, encoding: TagEncoding, field: usize) -> Tag {
    let (value, range) = match scalar {
        Scalar::Initialized { value, valid_range } => (value, Some(valid_range)),
        Scalar::Union { value } => (value, None),
    };
    let (primitive, signed) = match value {
        Primitive::Int { signed, .. } => ("integer", Some(signed)),
        Primitive::Float { .. } => ("float", None),
        Primitive::Pointer(_) => ("pointer", None),
    };
    let mut tag = Tag {
        primitive: primitive.into(),
        bits: value
            .size(&rustc_public::target::MachineInfo::target())
            .bits(),
        signed,
        valid_start: range.map(|r| r.start.to_string()),
        valid_end: range.map(|r| r.end.to_string()),
        field,
        encoding: "direct".into(),
        untagged_variant: None,
        niche_variants: None,
        niche_start: None,
    };
    if let TagEncoding::Niche {
        untagged_variant,
        niche_variants,
        niche_start,
    } = encoding
    {
        tag.encoding = "niche".into();
        tag.untagged_variant = Some(untagged_variant.to_index());
        tag.niche_variants = Some([
            niche_variants.start().to_index(),
            niche_variants.end().to_index(),
        ]);
        tag.niche_start = Some(niche_start.to_string());
    }
    tag
}

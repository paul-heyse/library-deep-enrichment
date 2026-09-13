//! Bounded constant allocation graphs. Pointer provenance is retained, never guessed from bytes.
use crate::{behavior, callables, instances, lifecycle, memory_types, projection};
use rustc_middle::ty::TypeVisitableExt;
use rustc_public::{
    CrateDef,
    mir::{
        Body, Mutability, Operand,
        alloc::{AllocId, GlobalAlloc},
        mono::{Instance, InstanceKind},
    },
    ty::{Allocation, ConstantKind},
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const SCHEMA: &str = "library-guides.mir-memory.v1";
const MAX_BODY_BYTES: usize = 1_048_576;
const MAX_UNIT_BYTES: usize = 33_554_432;
const MAX_NODES: usize = 4096;
const MAX_POINTERS: usize = 32_768;

#[derive(Default)]
pub struct Budget {
    pub bytes: usize,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Root {
    pub point: callables::Point,
    pub ty: Option<usize>,
    pub allocation: Option<usize>,
    pub state: String,
    pub evaluation: String,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Pointer {
    pub offset: usize,
    pub target: Option<usize>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Node {
    Memory {
        bytes: Vec<Option<u8>>,
        alignment: u64,
        mutable: bool,
        pointers: Vec<Pointer>,
    },
    Function {
        definition: String,
        identity: Option<instances::Identity>,
        selection: Option<instances::CallUse>,
        ty: Option<usize>,
        foreign: bool,
    },
    Static {
        definition: String,
        ty: Option<usize>,
        initializer: Option<usize>,
    },
    Unresolved {
        reason: String,
    },
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Uses {
    pub selected: bool,
    pub roots: Vec<Root>,
    pub nodes: Vec<Node>,
    pub types: Vec<memory_types::Type>,
    pub locals: Vec<LocalType>,
    pub retained_bytes: usize,
    pub frontier: Vec<String>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct LocalType {
    pub local: usize,
    pub ty: Option<usize>,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Fact {
    pub id: String,
    pub symbol: String,
    pub kind: String,
    pub payload: projection::Owner,
    pub behavior: behavior::Owner,
    pub execution: instances::Execution,
    pub callables: Vec<callables::Reference>,
    pub lifecycle: lifecycle::Uses,
    pub memory: Uses,
}
impl Fact {
    pub fn new(record: lifecycle::Fact, memory: Uses) -> Self {
        Self {
            id: record.id,
            symbol: record.symbol,
            kind: record.kind,
            payload: record.payload,
            behavior: record.behavior,
            execution: record.execution,
            callables: record.callables,
            lifecycle: record.lifecycle,
            memory,
        }
    }
}

struct Graph<'a> {
    ids: HashMap<AllocId, usize>,
    pending: Vec<(Option<GlobalAlloc>, usize, Option<String>)>,
    nodes: Vec<Node>,
    types: memory_types::Collector,
    bytes: usize,
    pointers: usize,
    unit: &'a mut Budget,
    frontier: Vec<String>,
}
impl Graph<'_> {
    fn insert(&mut self, allocation: GlobalAlloc, block: usize) -> Option<usize> {
        if self.pending.len() >= MAX_NODES {
            self.frontier.push("allocation_node_budget".into());
            return None;
        }
        let id = self.pending.len();
        let rejection = if let GlobalAlloc::Memory(value) = &allocation {
            if value.bytes.len() > MAX_BODY_BYTES - self.bytes
                || value.bytes.len() > MAX_UNIT_BYTES - self.unit.bytes
            {
                Some("constant_byte_budget")
            } else if value.provenance.ptrs.len() > MAX_POINTERS - self.pointers {
                Some("constant_pointer_budget")
            } else {
                self.bytes += value.bytes.len();
                self.unit.bytes += value.bytes.len();
                self.pointers += value.provenance.ptrs.len();
                None
            }
        } else {
            None
        };
        if let Some(reason) = rejection {
            self.frontier.push(reason.into());
            self.pending.push((None, block, Some(reason.into())));
        } else {
            self.pending.push((Some(allocation), block, None));
        }
        Some(id)
    }
    fn intern(&mut self, id: AllocId, block: usize) -> Option<usize> {
        if let Some(index) = self.ids.get(&id) {
            return Some(*index);
        }
        // Resolve only after checking the finite graph bound.
        if self.pending.len() >= MAX_NODES {
            self.frontier.push("allocation_node_budget".into());
            return None;
        }
        let index = self.insert(GlobalAlloc::from(id), block)?;
        self.ids.insert(id, index);
        Some(index)
    }
    fn allocation(&mut self, allocation: Allocation, block: usize) -> Node {
        let pointers = allocation
            .provenance
            .ptrs
            .into_iter()
            .map(|(offset, provenance)| Pointer {
                offset,
                target: self.intern(provenance.0, block),
            })
            .collect();
        Node::Memory {
            bytes: allocation.bytes,
            alignment: allocation.align,
            mutable: allocation.mutability == Mutability::Mut,
            pointers,
        }
    }
}

pub fn collect(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    body: &Body,
    selected: bool,
    unit: &mut Budget,
    mut select: impl FnMut(
        Instance,
        usize,
    ) -> Result<
        (instances::Identity, instances::CallUse),
        Box<dyn std::error::Error>,
    >,
) -> Result<Uses, Box<dyn std::error::Error>> {
    let mut graph = Graph {
        ids: HashMap::new(),
        pending: vec![],
        nodes: vec![],
        types: memory_types::Collector::default(),
        bytes: 0,
        pointers: 0,
        unit,
        frontier: vec![
            "projected_assignment_and_call_operands_only".into(),
            "physical_layout_does_not_establish_runtime_lifetime_or_abi_conformance".into(),
        ],
    };
    let mut roots = vec![];
    let locals = if selected {
        body.local_decls()
            .map(|(local, value)| LocalType {
                local,
                ty: graph.types.intern(value.ty),
            })
            .collect::<Vec<_>>()
    } else {
        vec![]
    };
    if locals.iter().any(|local| local.ty.is_none()) {
        graph.frontier.push("type_population_budget".into());
    }
    for (point, operand, _) in callables::operands(body) {
        let Operand::Constant(constant) = operand else {
            continue;
        };
        if roots.len() >= callables::MAX_REFERENCES {
            return Err("constant root observation budget exhausted".into());
        }
        let mut root = Root {
            point,
            ty: None,
            allocation: None,
            state: "outside_requested_root_closure".into(),
            evaluation: "not_requested".into(),
        };
        if selected {
            root.ty = graph.types.intern(constant.const_.ty());
            if root.ty.is_none() {
                graph.frontier.push("type_population_budget".into());
            }
            let (value, evaluation) = evaluate(tcx, constant);
            root.evaluation = evaluation.into();
            root.state = match value.kind() {
                ConstantKind::Allocated(allocation) => {
                    root.allocation =
                        graph.insert(GlobalAlloc::Memory(allocation.clone()), root.point.block);
                    if root.allocation.is_some() {
                        "allocated"
                    } else {
                        "allocation_node_budget"
                    }
                }
                ConstantKind::ZeroSized => "zero_sized",
                ConstantKind::Ty(_) => "type_constant_not_evaluated",
                ConstantKind::Unevaluated(_) => "unevaluated_constant",
                ConstantKind::Param(_) => "generic_constant",
            }
            .into();
        }
        roots.push(root);
    }
    while graph.nodes.len() < graph.pending.len() {
        // Move bytes out before following edges, so retained allocations are not duplicated.
        let (allocation, block, rejection) = std::mem::take(&mut graph.pending[graph.nodes.len()]);
        let Some(allocation) = allocation else {
            graph.nodes.push(Node::Unresolved {
                reason: rejection.ok_or("missing allocation disposition")?,
            });
            continue;
        };
        let node = match allocation {
            GlobalAlloc::Memory(allocation) => graph.allocation(allocation, block),
            GlobalAlloc::Function(instance) => {
                let definition = behavior::identity(
                    tcx,
                    rustc_public::rustc_internal::internal(tcx, instance.def.def_id()),
                );
                let foreign = instance.is_foreign_item();
                let (identity, selection) = if !foreign
                    && matches!(instance.kind, InstanceKind::Item | InstanceKind::Shim)
                {
                    let (identity, selection) = select(instance, block)?;
                    (Some(identity), Some(selection))
                } else {
                    graph
                        .frontier
                        .push("foreign_or_nonitem_constant_target".into());
                    (None, None)
                };
                Node::Function {
                    definition,
                    identity,
                    selection,
                    ty: graph.types.intern(instance.ty()),
                    foreign,
                }
            }
            GlobalAlloc::Static(definition) => {
                let id = behavior::identity(
                    tcx,
                    rustc_public::rustc_internal::internal(tcx, definition.def_id()),
                );
                let ty = graph.types.intern(definition.ty());
                // Lazy statics preserve identity and cycles. Runtime mutation remains separate.
                let initializer = definition
                    .eval_initializer()
                    .ok()
                    .and_then(|a| graph.insert(GlobalAlloc::Memory(a), block));
                if initializer.is_none() {
                    graph.frontier.push("static_initializer_unavailable".into());
                }
                Node::Static {
                    definition: id,
                    ty,
                    initializer,
                }
            }
            GlobalAlloc::VTable(_, _) => {
                graph.frontier.push("vtable_allocation_not_reified".into());
                Node::Unresolved {
                    reason: "vtable_allocation_not_reified".into(),
                }
            }
            GlobalAlloc::TypeId { .. } => Node::Unresolved {
                reason: "symbolic_type_id".into(),
            },
        };
        graph.nodes.push(node);
    }
    graph.types.finish(tcx);
    graph.frontier.sort();
    graph.frontier.dedup();
    Ok(Uses {
        selected,
        roots,
        nodes: graph.nodes,
        types: graph.types.nodes,
        locals,
        retained_bytes: graph.bytes,
        frontier: graph.frontier,
    })
}

fn evaluate(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    constant: &rustc_public::mir::ConstOperand,
) -> (rustc_public::ty::MirConst, &'static str) {
    use rustc_public::ty::TyConstKind;
    if matches!(
        constant.const_.kind(),
        ConstantKind::Allocated(_) | ConstantKind::ZeroSized
    ) {
        return (constant.const_.clone(), "already_evaluated");
    }
    if !matches!(
        constant.const_.kind(),
        ConstantKind::Unevaluated(_) | ConstantKind::Ty(rustc_public::ty::TyConst { .. })
    ) {
        return (constant.const_.clone(), "unavailable");
    }
    if let ConstantKind::Ty(value) = constant.const_.kind()
        && !matches!(
            value.kind(),
            TyConstKind::Value(_, _) | TyConstKind::ZSTValue(_)
        )
    {
        return (constant.const_.clone(), "generic_or_symbolic");
    }
    let internal = rustc_public::rustc_internal::internal(tcx, constant.const_.clone());
    if internal.has_non_region_param()
        || internal.has_non_region_infer()
        || internal.has_escaping_bound_vars()
        || internal.has_non_region_placeholders()
    {
        return (constant.const_.clone(), "generic_or_symbolic");
    }
    // Public MIR eagerly evaluates instance bodies, but not generic-body constant operands.
    // Use the pinned compiler's evaluator with the exact operand and source span.
    match internal.eval(
        tcx,
        rustc_middle::ty::TypingEnv::fully_monomorphized(),
        rustc_public::rustc_internal::internal(tcx, constant.span),
    ) {
        Ok(value) => (
            rustc_public::rustc_internal::stable(rustc_middle::mir::Const::Val(
                value,
                internal.ty(),
            )),
            "evaluated",
        ),
        Err(_) => (constant.const_.clone(), "unavailable"),
    }
}

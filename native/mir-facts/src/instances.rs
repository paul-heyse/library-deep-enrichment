//! Finite observed item instances; compiler handles never cross the callback boundary.
use crate::{behavior, callables, lifecycle, memory, projection};
use library_guides_protocol::digest;
use rustc_middle::ty::TypeVisitableExt;
use rustc_public::{
    CrateDef,
    mir::{
        AggregateKind, Body, Operand, Rvalue, StatementKind, TerminatorKind,
        mono::{Instance, InstanceKind},
    },
    ty::{RigidTy, TyKind},
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
};

pub const SCHEMA: &str = "library-guides.mir-instances.v1";
const MAX_INSTANCES: usize = 128;
const MAX_DEPTH: usize = 8;
const MAX_CANDIDATES: usize = 4096;

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Options {
    pub max_instances: usize,
    pub max_depth: usize,
    pub max_candidates: usize,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub callable_references: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub lifecycle_uses: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub definition_roots: Vec<String>,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub constant_memory: bool,
}
impl Options {
    pub fn read() -> Result<Option<Self>, Box<dyn std::error::Error>> {
        let Some(value) = env::var_os("LIBRARY_GUIDES_MIR_INSTANCES") else {
            if env::var("LIBRARY_GUIDES_MIR_CALLABLES").ok().as_deref() == Some("1")
                || env::var("LIBRARY_GUIDES_MIR_LIFECYCLE").ok().as_deref() == Some("1")
                || env::var_os("LIBRARY_GUIDES_MIR_INSTANCE_ROOTS").is_some()
                || env::var("LIBRARY_GUIDES_MIR_MEMORY").ok().as_deref() == Some("1")
            {
                return Err("callable acquisition requires explicit instance budgets".into());
            }
            return Ok(None);
        };
        if env::var("LIBRARY_GUIDES_MIR_BEHAVIOR").ok().as_deref() != Some("1") {
            return Err("instance acquisition requires the explicit behavior lane".into());
        }
        let max_instances = value
            .to_str()
            .ok_or("invalid instance limit")?
            .parse::<usize>()?;
        let max_depth = env::var("LIBRARY_GUIDES_MIR_INSTANCE_DEPTH")
            .unwrap_or_else(|_| "2".into())
            .parse::<usize>()?;
        if max_instances == 0 || max_instances > MAX_INSTANCES || max_depth > MAX_DEPTH {
            return Err("instance/depth limit exceeds the owned acquisition bounds".into());
        }
        let callable_references =
            env::var("LIBRARY_GUIDES_MIR_CALLABLES").ok().as_deref() == Some("1");
        let lifecycle_uses = env::var("LIBRARY_GUIDES_MIR_LIFECYCLE").ok().as_deref() == Some("1");
        if lifecycle_uses && !callable_references {
            return Err("lifecycle capture requires callable references".into());
        }
        let constant_memory = env::var("LIBRARY_GUIDES_MIR_MEMORY").ok().as_deref() == Some("1");
        if constant_memory && !lifecycle_uses {
            return Err("constant memory capture requires lifecycle evidence".into());
        }
        let definition_roots = match env::var("LIBRARY_GUIDES_MIR_INSTANCE_ROOTS") {
            Ok(raw) => {
                let mut values: Vec<String> = serde_json::from_str(&raw)?;
                let unique: BTreeSet<_> = values.iter().collect();
                if values.is_empty()
                    || values.len() > MAX_INSTANCES
                    || unique.len() != values.len()
                    || values
                        .iter()
                        .any(|value| !value.starts_with("definition:") || value.len() > 128)
                {
                    return Err(
                        "instance roots require a bounded nonempty unique definition catalog"
                            .into(),
                    );
                }
                values.sort();
                values
            }
            Err(env::VarError::NotPresent) => vec![],
            Err(error) => return Err(error.into()),
        };
        Ok(Some(Self {
            max_instances,
            max_depth,
            max_candidates: MAX_CANDIDATES,
            callable_references,
            lifecycle_uses,
            definition_roots,
            constant_memory,
        }))
    }
    pub fn schema(&self) -> &'static str {
        if self.constant_memory {
            memory::SCHEMA
        } else if self.lifecycle_uses {
            lifecycle::SCHEMA
        } else if self.callable_references {
            callables::SCHEMA
        } else {
            SCHEMA
        }
    }
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Identity {
    pub key: String,
    pub definition: String,
    pub kind: String,
    pub mangled: String,
    pub substitutions: Vec<behavior::Argument>,
    pub phase: String,
}

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CallUse {
    pub block: usize,
    pub instance: Option<String>,
    pub state: String,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Execution {
    pub identity: Option<Identity>,
    pub calls: Vec<CallUse>,
    pub frontier: Vec<String>,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Fact {
    pub id: String,
    pub symbol: String,
    pub kind: String,
    pub payload: projection::Owner,
    pub behavior: behavior::Owner,
    pub execution: Execution,
}

struct Pending {
    instance: Instance,
    identity: Identity,
}

pub struct Collector {
    pub options: Options,
    pub records: Vec<Fact>,
    pub attempted: usize,
    pub captured: usize,
    unit: String,
    pending: BTreeMap<(usize, String), Pending>,
    identities: BTreeMap<String, Instance>,
    states: BTreeMap<String, String>,
    references: BTreeMap<String, Vec<callables::Reference>>,
    reference_count: usize,
    lifecycles: BTreeMap<String, lifecycle::Uses>,
    follow_current: bool,
    observed_roots: BTreeSet<String>,
    memories: BTreeMap<String, memory::Uses>,
    memory_budget: memory::Budget,
}

pub struct Owned {
    pub options: Options,
    pub records: Vec<Fact>,
    pub attempted: usize,
    pub captured: usize,
    pub references: BTreeMap<String, Vec<callables::Reference>>,
    pub lifecycles: BTreeMap<String, lifecycle::Uses>,
    pub memories: BTreeMap<String, memory::Uses>,
}
impl Collector {
    pub fn into_owned(self) -> Owned {
        Owned {
            options: self.options,
            records: self.records,
            attempted: self.attempted,
            captured: self.captured,
            references: self.references,
            lifecycles: self.lifecycles,
            memories: self.memories,
        }
    }
    pub fn new(options: Options, unit: String) -> Self {
        Self {
            options,
            unit,
            records: vec![],
            attempted: 0,
            captured: 0,
            pending: BTreeMap::new(),
            identities: BTreeMap::new(),
            states: BTreeMap::new(),
            references: BTreeMap::new(),
            reference_count: 0,
            lifecycles: BTreeMap::new(),
            follow_current: true,
            observed_roots: BTreeSet::new(),
            memories: BTreeMap::new(),
            memory_budget: memory::Budget::default(),
        }
    }

    pub fn generic(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        definition: rustc_span::def_id::DefId,
        id: String,
        name: String,
        body: Body,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let key = behavior::identity(tcx, definition);
        self.follow_current = self.options.definition_roots.is_empty()
            || self.options.definition_roots.contains(&key);
        if self.follow_current {
            self.observed_roots.insert(key);
        }
        let calls = self.observe(tcx, &body, 0)?;
        if self.options.callable_references {
            let references = self.observe_references(tcx, &body, 0)?;
            self.references.insert(id.clone(), references);
        }
        if self.options.lifecycle_uses {
            let uses = self.observe_lifecycle(tcx, &body, 0)?;
            self.lifecycles.insert(id.clone(), uses);
        }
        if self.options.constant_memory {
            let uses = self.observe_memory(tcx, &body, 0)?;
            self.memories.insert(id.clone(), uses);
        }
        self.records.push(Fact {
            id,
            symbol: name.clone(),
            kind: "mir_owner".into(),
            behavior: behavior::executable_owner(
                tcx,
                definition,
                &body,
                self.options.lifecycle_uses,
            ),
            payload: projection::owner(tcx, name, body),
            execution: Execution {
                identity: None,
                calls,
                frontier: self.frontier(),
            },
        });
        Ok(())
    }

    fn identify(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        instance: Instance,
    ) -> Result<Identity, Box<dyn std::error::Error>> {
        let definition = behavior::identity(
            tcx,
            rustc_public::rustc_internal::internal(tcx, instance.def.def_id()),
        );
        let mangled = instance.mangled_name();
        let substitutions = behavior::arguments(&instance.args());
        let kind = if instance.kind == InstanceKind::Shim {
            "shim"
        } else {
            "item"
        };
        let key = format!(
            "mir-instance:{}:{}",
            self.unit,
            digest(&serde_json::to_vec(&(
                &definition,
                kind,
                &mangled,
                &substitutions
            ))?)
        );
        if self
            .identities
            .get(&key)
            .is_some_and(|prior| *prior != instance)
        {
            return Err("owned instance identity collides for distinct compiler instances".into());
        }
        Ok(Identity {
            key,
            definition,
            kind: kind.into(),
            mangled,
            substitutions,
            phase: "rustc_public_eager_monomorphized_body".into(),
        })
    }

    fn frontier(&self) -> Vec<String> {
        if self.options.lifecycle_uses {
            return [
                "finite_observed_items_shims_drops_and_closure_environments",
                "virtual_foreign_coroutine_layout_and_alias_obligations_remain_open",
                "captured_drop_body_does_not_certify_release_or_cancellation",
            ]
            .map(String::from)
            .to_vec();
        }
        if !self.options.callable_references {
            return frontier();
        }
        [
            "finite_observed_item_instances_not_complete_monomorphization",
            "function_items_in_projected_operands_only_not_all_executable_uses",
            "closure_captures_drop_glue_vtables_foreign_and_shim_uses_remain_unmodeled",
            "source_mapping_alias_lifetime_and_body_model_frontiers_remain_applicable",
        ]
        .map(String::from)
        .to_vec()
    }

    fn observe(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        body: &Body,
        depth: usize,
    ) -> Result<Vec<CallUse>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        for (block, basic) in body.blocks.iter().enumerate() {
            if let TerminatorKind::Call { func, .. } = &basic.terminator.kind {
                let instance = match resolve(tcx, body, func, self.options.lifecycle_uses) {
                    Ok(value) => value,
                    Err(state) => {
                        result.push(CallUse {
                            block,
                            instance: None,
                            state: state.into(),
                        });
                        continue;
                    }
                };
                result.push(self.select(tcx, instance, block, depth)?);
            }
        }
        Ok(result)
    }

    fn select(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        instance: Instance,
        block: usize,
        depth: usize,
    ) -> Result<CallUse, Box<dyn std::error::Error>> {
        let identity = self.identify(tcx, instance)?;
        let state = if !self.follow_current {
            "outside_requested_root_closure"
        } else if self.identities.contains_key(&identity.key) {
            "pending"
        } else if depth >= self.options.max_depth {
            "depth_budget_exhausted"
        } else if self.identities.len() >= self.options.max_candidates {
            "candidate_budget_exhausted"
        } else {
            self.identities.insert(identity.key.clone(), instance);
            self.pending.insert(
                (depth + 1, identity.key.clone()),
                Pending {
                    instance,
                    identity: identity.clone(),
                },
            );
            "pending"
        };
        Ok(CallUse {
            block,
            instance: Some(identity.key),
            state: state.into(),
        })
    }

    fn observe_references(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        body: &Body,
        depth: usize,
    ) -> Result<Vec<callables::Reference>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        for (point, operand, pointer_coercion) in callables::operands(body) {
            if !operand
                .ty(body.locals())
                .is_ok_and(|ty| matches!(ty.kind(), TyKind::RigidTy(RigidTy::FnDef(_, _))))
            {
                continue;
            }
            self.reference_count += 1;
            if self.reference_count > callables::MAX_REFERENCES {
                return Err("function-reference observation budget exhausted".into());
            }
            let mut call = behavior::executable_call(
                tcx,
                body,
                point.block,
                operand,
                self.options.lifecycle_uses,
            );
            let resolution =
                resolve(tcx, body, operand, self.options.lifecycle_uses).and_then(|instance| {
                    if !pointer_coercion {
                        return Ok(instance);
                    }
                    let TyKind::RigidTy(RigidTy::FnDef(definition, args)) = operand
                        .ty(body.locals())
                        .map_err(|_| "operand_type_unavailable")?
                        .kind()
                    else {
                        return Err("operand_type_unavailable");
                    };
                    let pointer = Instance::resolve_for_fn_ptr(definition, &args)
                        .map_err(|_| "instance_resolution_unavailable")?;
                    if pointer.kind != InstanceKind::Item || pointer.is_foreign_item() {
                        return Err("non_item_or_foreign_instance_not_selected");
                    }
                    Ok(pointer)
                });
            let selection = match resolution {
                Ok(instance) => {
                    call.target = Some(behavior::identity(
                        tcx,
                        rustc_public::rustc_internal::internal(tcx, instance.def.def_id()),
                    ));
                    call.substitutions = behavior::arguments(&instance.args());
                    call.complete = true;
                    call.instance_kind = if instance.kind == InstanceKind::Shim {
                        "shim"
                    } else {
                        "item"
                    }
                    .into();
                    self.select(tcx, instance, point.block, depth)?
                }
                Err(state) => {
                    call.complete = false;
                    call.frontier.push(state.into());
                    CallUse {
                        block: point.block,
                        instance: None,
                        state: state.into(),
                    }
                }
            };
            result.push(callables::Reference {
                point,
                call,
                selection,
                pointer_coercion,
            });
        }
        Ok(result)
    }

    fn observe_lifecycle(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        body: &Body,
        depth: usize,
    ) -> Result<lifecycle::Uses, Box<dyn std::error::Error>> {
        let mut uses = lifecycle::Uses {
            spread_arg: body.spread_arg(),
            call_abis: vec![],
            drops: vec![],
            closures: vec![],
            frontier: vec!["drop_observation_is_not_protocol_or_release_proof".into()],
        };
        for (block, basic) in body.blocks.iter().enumerate() {
            if let TerminatorKind::Call { func, .. } = &basic.terminator.kind {
                uses.call_abis.push(lifecycle::call_abi(body, block, func));
            }
            for (statement, event) in basic.statements.iter().enumerate() {
                if let StatementKind::Assign(
                    _,
                    Rvalue::Aggregate(AggregateKind::Closure(definition, args), captures),
                ) = &event.kind
                {
                    uses.closures.push(lifecycle::Closure {
                        block,
                        statement,
                        definition: behavior::identity(
                            tcx,
                            rustc_public::rustc_internal::internal(tcx, definition.def_id()),
                        ),
                        substitutions: behavior::arguments(args),
                        captures: captures.len(),
                    });
                }
            }
            if let TerminatorKind::Drop { place, .. } = &basic.terminator.kind {
                let ty = place.ty(body.locals())?;
                let internal = rustc_public::rustc_internal::internal(tcx, ty);
                let unresolved = internal.has_non_region_param()
                    || internal.has_non_region_infer()
                    || internal.has_escaping_bound_vars()
                    || internal.has_non_region_placeholders();
                let (target, selection, empty_shim) = if unresolved {
                    (
                        None,
                        CallUse {
                            block,
                            instance: None,
                            state: "generic_instance_resolution_not_attempted".into(),
                        },
                        None,
                    )
                } else {
                    let instance = Instance::resolve_drop_in_place(ty);
                    let identity = self.identify(tcx, instance)?;
                    (
                        Some(identity),
                        self.select(tcx, instance, block, depth)?,
                        Some(instance.is_empty_shim()),
                    )
                };
                uses.drops.push(lifecycle::DropUse {
                    block,
                    place: projection::place(place),
                    ty: projection::behavior_type(ty),
                    target,
                    selection,
                    empty_shim,
                });
            }
            if uses.drops.len() + uses.closures.len() > callables::MAX_REFERENCES {
                return Err("lifecycle observation budget exhausted".into());
            }
        }
        Ok(uses)
    }

    fn observe_memory(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
        body: &Body,
        depth: usize,
    ) -> Result<memory::Uses, Box<dyn std::error::Error>> {
        let mut budget = std::mem::take(&mut self.memory_budget);
        let result = memory::collect(
            tcx,
            body,
            self.follow_current,
            &mut budget,
            |instance, block| {
                let identity = self.identify(tcx, instance)?;
                Ok((identity, self.select(tcx, instance, block, depth)?))
            },
        );
        self.memory_budget = budget;
        result
    }

    pub fn finish(
        &mut self,
        tcx: rustc_middle::ty::TyCtxt<'_>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if self
            .options
            .definition_roots
            .iter()
            .any(|root| !self.observed_roots.contains(root))
        {
            return Err("requested instance root is absent from this exact compiler unit".into());
        }
        self.follow_current = true;
        while let Some(((depth, key), pending)) = self.pending.pop_first() {
            if self.attempted >= self.options.max_instances {
                self.states.insert(key, "instance_budget_exhausted".into());
                continue;
            }
            self.attempted += 1;
            if pending.instance.kind != InstanceKind::Shim && !pending.instance.has_body() {
                self.states.insert(key, "body_unavailable".into());
                continue;
            }
            let Some(body) = pending.instance.body() else {
                self.states.insert(key, "body_unavailable".into());
                continue;
            };
            let calls = self.observe(tcx, &body, depth)?;
            if self.options.callable_references {
                let references = self.observe_references(tcx, &body, depth)?;
                self.references.insert(key.clone(), references);
            }
            if self.options.lifecycle_uses {
                let uses = self.observe_lifecycle(tcx, &body, depth)?;
                self.lifecycles.insert(key.clone(), uses);
            }
            if self.options.constant_memory {
                let uses = self.observe_memory(tcx, &body, depth)?;
                self.memories.insert(key.clone(), uses);
            }
            let definition =
                rustc_public::rustc_internal::internal(tcx, pending.instance.def.def_id());
            let mut metadata =
                behavior::executable_owner(tcx, definition, &body, self.options.lifecycle_uses);
            metadata.phase = pending.identity.phase.clone();
            let name = pending.instance.name();
            self.records.push(Fact {
                id: key.clone(),
                symbol: name.clone(),
                kind: "mir_instance".into(),
                behavior: metadata,
                payload: projection::owner(tcx, name, body),
                execution: Execution {
                    identity: Some(pending.identity),
                    calls,
                    frontier: self.frontier(),
                },
            });
            self.captured += 1;
            self.states.insert(key, "captured".into());
        }
        for record in &mut self.records {
            let references = self
                .references
                .get_mut(&record.id)
                .into_iter()
                .flatten()
                .map(|value| &mut value.selection);
            let drops = self
                .lifecycles
                .get_mut(&record.id)
                .into_iter()
                .flat_map(|value| &mut value.drops)
                .map(|value| &mut value.selection);
            let memory_targets = self
                .memories
                .get_mut(&record.id)
                .into_iter()
                .flat_map(|value| &mut value.nodes)
                .filter_map(|node| match node {
                    memory::Node::Function { selection, .. } => selection.as_mut(),
                    _ => None,
                });
            for call in record
                .execution
                .calls
                .iter_mut()
                .chain(references)
                .chain(drops)
                .chain(memory_targets)
            {
                if call.state == "pending" {
                    call.state = call
                        .instance
                        .as_ref()
                        .and_then(|key| self.states.get(key))
                        .ok_or("instance selection lacks a terminal disposition")?
                        .clone();
                } else if call.state == "outside_requested_root_closure"
                    && let Some(state) = call.instance.as_ref().and_then(|key| self.states.get(key))
                {
                    call.state = state.clone();
                }
            }
        }
        Ok(())
    }
}

fn resolve(
    tcx: rustc_middle::ty::TyCtxt<'_>,
    body: &Body,
    operand: &Operand,
    shims: bool,
) -> Result<Instance, &'static str> {
    let ty = operand
        .ty(body.locals())
        .map_err(|_| "operand_type_unavailable")?;
    let TyKind::RigidTy(RigidTy::FnDef(definition, args)) = ty.kind() else {
        return Err("indirect_dispatch_requires_value_flow");
    };
    let internal = rustc_public::rustc_internal::internal(tcx, ty);
    if internal.has_non_region_param()
        || internal.has_non_region_infer()
        || internal.has_escaping_bound_vars()
        || internal.has_non_region_placeholders()
    {
        return Err("generic_instance_resolution_not_attempted");
    }
    let instance =
        Instance::resolve(definition, &args).map_err(|_| "instance_resolution_unavailable")?;
    if (instance.kind != InstanceKind::Item && !(shims && instance.kind == InstanceKind::Shim))
        || instance.is_foreign_item()
    {
        return Err("non_item_or_foreign_instance_not_selected");
    }
    Ok(instance)
}

fn frontier() -> Vec<String> {
    [
        "finite_observed_item_instances_not_complete_monomorphization",
        "source_mapping_alias_lifetime_and_body_model_frontiers_remain_applicable",
        "function_references_drop_glue_vtables_and_shims_not_enumerated",
    ]
    .map(String::from)
    .to_vec()
}

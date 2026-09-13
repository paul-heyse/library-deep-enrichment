//! Declaration projections over the owned typed model, with artifact-local evidence.
use crate::{contract as c, decoder::Document, rendering, wire};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet, VecDeque};

type Error = Box<dyn std::error::Error>;

#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TypeOccurrence {
    pub role: String,
    pub position: usize,
    pub selector: String,
    pub referenced_id: c::Id,
    pub path: String,
    pub resolved_symbol: Option<String>,
    pub direct: bool,
    pub self_owner: Option<c::Id>,
}

#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Declaration<'a> {
    pub id: String,
    pub artifact: &'a str,
    pub local_id: c::Id,
    pub symbol: String,
    pub kind: &'static str,
    pub owner: Option<c::Id>,
    pub owner_contract: Option<&'a c::ItemEnum>,
    pub public_routes: Vec<String>,
    pub route_state: &'static str,
    pub signature: String,
    pub type_occurrences: Vec<TypeOccurrence>,
    pub semantic_digest: String,
    pub item: &'a c::Item,
}

pub fn kind(item: &c::ItemEnum) -> &'static str {
    use c::ItemEnum::*;
    match item {
        Module(_) => "module",
        ExternCrate { .. } => "extern_crate",
        Use(_) => "use",
        Union(_) => "union",
        Struct(_) => "struct",
        StructField(_) => "struct_field",
        Enum(_) => "enum",
        Variant(_) => "variant",
        Function(_) => "function",
        Trait(_) => "trait",
        TraitAlias(_) => "trait_alias",
        Impl(_) => "impl",
        TypeAlias(_) => "type_alias",
        Constant { .. } => "constant",
        Static(_) => "static",
        ExternType => "extern_type",
        Macro(_) => "macro",
        ProcMacro(_) => "proc_macro",
        Primitive(_) => "primitive",
        AssocConst { .. } => "assoc_const",
        AssocType { .. } => "assoc_type",
    }
}

fn children(item: &c::ItemEnum) -> Vec<c::Id> {
    use c::ItemEnum::*;
    match item {
        Module(x) => x.items.clone(),
        Union(x) => x.fields.iter().chain(&x.impls).copied().collect(),
        Struct(x) => {
            let mut ids = match &x.kind {
                c::StructKind::Unit => vec![],
                c::StructKind::Tuple(ids) => ids.iter().flatten().copied().collect(),
                c::StructKind::Plain { fields, .. } => fields.clone(),
            };
            ids.extend(&x.impls);
            ids
        }
        Enum(x) => x.variants.iter().chain(&x.impls).copied().collect(),
        Variant(x) => match &x.kind {
            c::VariantKind::Plain => vec![],
            c::VariantKind::Tuple(ids) => ids.iter().flatten().copied().collect(),
            c::VariantKind::Struct { fields, .. } => fields.clone(),
        },
        Trait(x) => x.items.clone(),
        Impl(x) => x.items.clone(),
        Primitive(x) => x.impls.clone(),
        _ => vec![],
    }
}

pub struct Index {
    pub names: BTreeMap<c::Id, String>,
    pub owners: BTreeMap<c::Id, c::Id>,
    pub routes: BTreeMap<c::Id, BTreeSet<String>>,
    pub unresolved_routes: BTreeSet<String>,
    self_receivers: BTreeMap<c::Id, c::Path>,
    owner_contracts: BTreeMap<c::Id, c::ItemEnum>,
}

impl Index {
    pub fn build(doc: &Document) -> Result<Self, Error> {
        let root = doc
            .index
            .get(&doc.root)
            .ok_or("root absent from rustdoc index")?;
        let root_name = root.name.clone().ok_or("unnamed root")?;
        let mut names = doc
            .paths
            .iter()
            .map(|(id, x)| (*id, x.path.join("::")))
            .collect::<BTreeMap<_, _>>();
        names.insert(doc.root, root_name.clone());
        let mut owners = BTreeMap::new();
        for (id, item) in &doc.index {
            if *id != item.id {
                return Err(format!("index/item identity mismatch {}", id.0).into());
            }
            for child in children(&item.inner) {
                owners.entry(child).or_insert(*id);
            }
        }
        for _ in 0..128 {
            let mut changed = false;
            for (id, item) in &doc.index {
                if names.contains_key(id) {
                    continue;
                }
                let parent = owners.get(id).and_then(|id| names.get(id)).cloned();
                if let (Some(parent), Some(name)) = (parent.as_ref(), item.name.as_ref()) {
                    names.insert(*id, format!("{parent}::{name}"));
                    changed = true;
                } else if let (Some(parent), c::ItemEnum::Use(import)) =
                    (parent.as_ref(), &item.inner)
                {
                    names.insert(
                        *id,
                        format!(
                            "{parent}::<use {} as {}{}>",
                            import.source,
                            import.name,
                            if import.is_glob { "::*" } else { "" }
                        ),
                    );
                    changed = true;
                } else if let c::ItemEnum::Impl(imp) = &item.inner {
                    let receiver = display_type(&imp.for_);
                    let tr = imp
                        .trait_
                        .as_ref()
                        .map(|x| format!(" as {}", rendering::path(x)))
                        .unwrap_or_default();
                    names.insert(
                        *id,
                        format!(
                            "{root_name}::<impl {}{receiver}{tr}>",
                            if imp.is_negative { "!" } else { "" }
                        ),
                    );
                    changed = true;
                }
            }
            if !changed {
                break;
            }
        }
        let mut index = Self {
            names,
            owners,
            routes: BTreeMap::new(),
            unresolved_routes: BTreeSet::new(),
            owner_contracts: doc
                .index
                .iter()
                .filter(|(_, item)| {
                    matches!(item.inner, c::ItemEnum::Impl(_) | c::ItemEnum::Trait(_))
                })
                .map(|(id, item)| (*id, item.inner.clone()))
                .collect(),
            self_receivers: doc
                .index
                .iter()
                .filter_map(|(id, item)| match &item.inner {
                    c::ItemEnum::Impl(imp) => match &imp.for_ {
                        c::Type::ResolvedPath(p) => Some((*id, p.clone())),
                        _ => None,
                    },
                    _ => None,
                })
                .collect(),
        };
        let mut queue = VecDeque::from([(doc.root, root_name, BTreeSet::new())]);
        let mut operations = 0;
        while let Some((id, path, mut ancestors)) = queue.pop_front() {
            operations += 1;
            if operations > 200_000 {
                index
                    .unresolved_routes
                    .insert("route traversal budget".into());
                break;
            }
            if !ancestors.insert(id) {
                index.unresolved_routes.insert(format!("cycle:{path}"));
                continue;
            }
            if !index.routes.entry(id).or_default().insert(path.clone()) {
                continue;
            }
            let Some(item) = doc.index.get(&id) else {
                index.unresolved_routes.insert(format!("external:{path}"));
                continue;
            };
            if let c::ItemEnum::Use(import) = &item.inner {
                if let Some(target) = import.id {
                    if import.is_glob {
                        if let Some(target_item) = doc.index.get(&target) {
                            for child in children(&target_item.inner) {
                                if let Some(child_item) = doc.index.get(&child)
                                    && matches!(child_item.visibility, c::Visibility::Public)
                                    && let Some(name) = &child_item.name
                                {
                                    queue.push_back((
                                        child,
                                        format!("{path}::{name}"),
                                        ancestors.clone(),
                                    ));
                                }
                            }
                        } else {
                            index
                                .unresolved_routes
                                .insert(format!("external_glob:{path}"));
                        }
                    } else {
                        queue.push_back((target, path, ancestors));
                    }
                } else {
                    index
                        .unresolved_routes
                        .insert(format!("primitive_or_unresolved:{path}"));
                }
                continue;
            }
            let inherited = matches!(
                item.inner,
                c::ItemEnum::Trait(_) | c::ItemEnum::Enum(_) | c::ItemEnum::Variant(_)
            );
            for child in children(&item.inner) {
                let Some(member) = doc.index.get(&child) else {
                    index
                        .unresolved_routes
                        .insert(format!("missing:{}", child.0));
                    continue;
                };
                if matches!(member.inner, c::ItemEnum::Impl(_)) {
                    continue;
                }
                if !(matches!(member.visibility, c::Visibility::Public)
                    || inherited && matches!(member.visibility, c::Visibility::Default))
                {
                    continue;
                }
                let name = match &member.inner {
                    c::ItemEnum::Use(u) if u.is_glob => None,
                    c::ItemEnum::Use(u) => Some(u.name.clone()),
                    _ => member.name.clone(),
                };
                if name.is_none() && !matches!(member.inner, c::ItemEnum::Use(_)) {
                    continue;
                }
                let path = name
                    .map(|x| format!("{path}::{x}"))
                    .unwrap_or_else(|| path.clone());
                queue.push_back((child, path, ancestors.clone()));
            }
        }
        // Inherent methods are reachable through every public route of their receiver.
        for (id, item) in &doc.index {
            if let c::ItemEnum::Impl(imp) = &item.inner {
                if imp.trait_.is_some() || imp.is_negative {
                    continue;
                }
                if let c::Type::ResolvedPath(receiver) = &imp.for_ {
                    let routes = index.routes.get(&receiver.id).cloned().unwrap_or_default();
                    for child in &imp.items {
                        if let Some(member) = doc.index.get(child)
                            && matches!(member.visibility, c::Visibility::Public)
                            && let Some(name) = &member.name
                        {
                            for route in &routes {
                                index
                                    .routes
                                    .entry(*child)
                                    .or_default()
                                    .insert(format!("{route}::{name}"));
                            }
                        }
                    }
                }
                let _ = id;
            }
        }
        Ok(index)
    }
}

pub fn display_type(value: &c::Type) -> String {
    use c::Type::*;
    match value {
        ResolvedPath(path) => format!("{}{}", path.path, rendering::args(path.args.as_deref())),
        Generic(x) | Primitive(x) => x.clone(),
        BorrowedRef {
            lifetime,
            is_mutable,
            type_,
        } => format!(
            "&{}{}{}",
            lifetime
                .as_ref()
                .map(|x| format!("{x} "))
                .unwrap_or_default(),
            if *is_mutable { "mut " } else { "" },
            display_type(type_)
        ),
        RawPointer { is_mutable, type_ } => format!(
            "*{} {}",
            if *is_mutable { "mut" } else { "const" },
            display_type(type_)
        ),
        Tuple(xs) => format!(
            "({}{})",
            xs.iter().map(display_type).collect::<Vec<_>>().join(", "),
            if xs.len() == 1 { "," } else { "" }
        ),
        Slice(x) => format!("[{}]", display_type(x)),
        Array { type_, len } => format!("[{}; {len}]", display_type(type_)),
        Infer => "_".into(),
        QualifiedPath {
            name,
            self_type,
            trait_,
            args,
        } => format!(
            "<{}{}>::{}{}",
            display_type(self_type),
            trait_
                .as_ref()
                .map(|x| format!(" as {}", rendering::path(x)))
                .unwrap_or_default(),
            name,
            rendering::args(args.as_deref())
        ),
        FunctionPointer(x) => format!(
            "{}{}fn({}{}) -> {}",
            rendering::binder(&x.generic_params),
            rendering::header(&x.header),
            x.sig
                .inputs
                .iter()
                .map(|(_, t)| display_type(t))
                .collect::<Vec<_>>()
                .join(", "),
            if x.sig.is_c_variadic {
                if x.sig.inputs.is_empty() {
                    "..."
                } else {
                    ", ..."
                }
            } else {
                ""
            },
            x.sig
                .output
                .as_ref()
                .map(display_type)
                .unwrap_or_else(|| "()".into())
        ),
        DynTrait(x) => format!(
            "dyn {}{}",
            x.traits
                .iter()
                .map(|x| format!(
                    "{}{}",
                    rendering::binder(&x.generic_params),
                    rendering::path(&x.trait_)
                ))
                .collect::<Vec<_>>()
                .join(" + "),
            x.lifetime
                .as_ref()
                .map(|s| format!(" + {s}"))
                .unwrap_or_default()
        ),
        ImplTrait(bounds) => format!("impl {}", rendering::bounds(bounds)),
        Pat { type_, .. } => format!("{} is [opaque pattern]", display_type(type_)),
    }
}

fn occurrences(
    value: &Value,
    path: &str,
    base: &str,
    role: &str,
    position: usize,
    out: &mut Vec<TypeOccurrence>,
) {
    match value {
        Value::Object(fields) => {
            if let Some(Value::Object(target)) = fields.get("resolved_path")
                && let (Some(id), Some(name)) = (
                    target.get("id").and_then(Value::as_u64),
                    target.get("path").and_then(Value::as_str),
                )
            {
                out.push(TypeOccurrence {
                    role: role.into(),
                    position,
                    selector: format!("json:{path}"),
                    referenced_id: c::Id(id as u32),
                    path: name.into(),
                    resolved_symbol: None,
                    direct: path == base,
                    self_owner: None,
                });
            }
            for (key, value) in fields {
                occurrences(
                    value,
                    &format!("{path}/{}", key.replace('~', "~0").replace('/', "~1")),
                    base,
                    role,
                    position,
                    out,
                );
            }
        }
        Value::Array(values) => {
            for (i, value) in values.iter().enumerate() {
                occurrences(value, &format!("{path}/{i}"), base, role, position, out);
            }
        }
        _ => {}
    }
}

fn self_occurrences(
    value: &Value,
    path: &str,
    base: &str,
    role: (&str, usize),
    receiver: Option<(c::Id, &c::Path)>,
    out: &mut Vec<TypeOccurrence>,
) {
    let Some((owner, receiver)) = receiver else {
        return;
    };
    match value {
        Value::Object(fields) => {
            if fields.get("generic").and_then(Value::as_str) == Some("Self") {
                out.push(TypeOccurrence {
                    role: role.0.into(),
                    position: role.1,
                    selector: format!("json:{path}"),
                    referenced_id: receiver.id,
                    path: receiver.path.clone(),
                    resolved_symbol: None,
                    direct: path == base,
                    self_owner: Some(owner),
                });
            }
            for (key, value) in fields {
                self_occurrences(
                    value,
                    &format!("{path}/{key}"),
                    base,
                    role,
                    Some((owner, receiver)),
                    out,
                );
            }
        }
        Value::Array(values) => {
            for (i, value) in values.iter().enumerate() {
                self_occurrences(
                    value,
                    &format!("{path}/{i}"),
                    base,
                    role,
                    Some((owner, receiver)),
                    out,
                );
            }
        }
        _ => {}
    }
}

fn semantic(value: &mut Value, names: &BTreeMap<c::Id, String>) {
    match value {
        Value::Object(fields) => {
            fields.remove("span");
            fields.remove("docs");
            fields.remove("links");
            for key in ["id", "parent"] {
                if let Some(id) = fields.get(key).and_then(Value::as_u64)
                    && let Some(name) = names.get(&c::Id(id as u32))
                {
                    fields.insert(key.into(), Value::String(name.clone()));
                }
            }
            for (key, value) in fields {
                if matches!(
                    key.as_str(),
                    "items" | "fields" | "impls" | "implementations" | "variants" | "tuple"
                ) && let Value::Array(ids) = value
                {
                    for id in ids {
                        if let Some(name) = id.as_u64().and_then(|x| names.get(&c::Id(x as u32))) {
                            *id = Value::String(name.clone());
                        }
                    }
                }
                semantic(value, names);
            }
        }
        Value::Array(values) => {
            for value in values {
                semantic(value, names);
            }
        }
        _ => {}
    }
}

pub fn project<'a>(
    item: &'a c::Item,
    artifact: &'a str,
    index: &'a Index,
) -> Result<Declaration<'a>, Error> {
    let symbol = index
        .names
        .get(&item.id)
        .cloned()
        .unwrap_or_else(|| format!("unresolved:{}", item.id.0));
    let mut refs = Vec::new();
    let receiver = index
        .owners
        .get(&item.id)
        .and_then(|owner| index.self_receivers.get(owner).map(|p| (*owner, p)));
    let signature = if let c::ItemEnum::Function(f) = &item.inner {
        for (i, (_, ty)) in f.sig.inputs.iter().enumerate() {
            let base = format!("/item/inner/function/sig/inputs/{i}/1");
            occurrences(
                &serde_json::to_value(ty)?,
                &base,
                &base,
                "input",
                i,
                &mut refs,
            );
            self_occurrences(
                &serde_json::to_value(ty)?,
                &base,
                &base,
                ("input", i),
                receiver,
                &mut refs,
            );
        }
        if let Some(ty) = &f.sig.output {
            let base = "/item/inner/function/sig/output";
            occurrences(
                &serde_json::to_value(ty)?,
                base,
                base,
                "output",
                0,
                &mut refs,
            );
            self_occurrences(
                &serde_json::to_value(ty)?,
                base,
                base,
                ("output", 0),
                receiver,
                &mut refs,
            );
        }
        rendering::function(&symbol, f)
    } else {
        format!("{} {symbol}", kind(&item.inner))
    };
    if !matches!(&item.inner, c::ItemEnum::Function(_)) {
        let role = match &item.inner {
            c::ItemEnum::Impl(_) => "impl_contract",
            c::ItemEnum::Trait(_) => "trait_contract",
            c::ItemEnum::StructField(_) => "field",
            c::ItemEnum::TypeAlias(_) => "alias",
            _ => "declaration",
        };
        let base = "/item/inner";
        occurrences(
            &serde_json::to_value(&item.inner)?,
            base,
            base,
            role,
            0,
            &mut refs,
        );
    }
    for occurrence in &mut refs {
        occurrence.resolved_symbol = index.names.get(&occurrence.referenced_id).cloned();
    }
    let mut normalized = serde_json::to_value(item)?;
    if let Value::Object(fields) = &mut normalized {
        fields.remove("id");
        fields.remove("crate_id");
    }
    semantic(&mut normalized, &index.names);
    let owner_contract = index
        .owners
        .get(&item.id)
        .and_then(|id| index.owner_contracts.get(id));
    let mut parent = serde_json::to_value(owner_contract)?;
    semantic(&mut parent, &index.names);
    if let Value::Object(variants) = &mut parent {
        for contract in variants.values_mut() {
            if let Value::Object(fields) = contract {
                fields.remove("items");
                fields.remove("implementations");
                fields.remove("provided_trait_methods");
            }
        }
    }
    let contract_digest = wire::digest(&serde_json::to_vec(&(normalized, parent))?);
    Ok(Declaration {
        id: format!("decl:{artifact}:{}", item.id.0),
        artifact,
        local_id: item.id,
        symbol,
        kind: kind(&item.inner),
        owner: index.owners.get(&item.id).copied(),
        owner_contract,
        public_routes: index
            .routes
            .get(&item.id)
            .map(|x| x.iter().cloned().collect())
            .unwrap_or_default(),
        route_state: if index.unresolved_routes.is_empty() {
            "complete"
        } else {
            "partial"
        },
        signature,
        type_occurrences: refs,
        semantic_digest: contract_digest,
        item,
    })
}

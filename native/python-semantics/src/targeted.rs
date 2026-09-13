//! Owned targeted TSP type graphs; protocol IDs are local to one fact.
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    Builtin,
    Declared,
    Function,
    Class,
    Union,
    Module,
    TypeVariable,
    Overloaded,
    Synthesized,
    Reference,
    Unknown,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Edge {
    path: String,
    target: i64,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Node {
    id: i64,
    category: Category,
    flags: i64,
    name: Option<String>,
    alias: Option<String>,
    declaration_origin: Option<String>,
    edges: Vec<Edge>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Graph {
    pub nodes: Vec<Node>,
    pub raw_tsp: String,
    pub location_precision: String,
    pub limitations: Vec<String>,
}

fn category(kind: i64) -> Category {
    match kind {
        0 => Category::Builtin,
        1 => Category::Declared,
        2 => Category::Function,
        3 => Category::Class,
        4 => Category::Union,
        5 => Category::Module,
        6 => Category::TypeVariable,
        7 => Category::Overloaded,
        8 => Category::Synthesized,
        9 => Category::Reference,
        _ => Category::Unknown,
    }
}
fn children(value: &Value, path: String, edges: &mut Vec<Edge>) {
    if let Some(id) = value.get("id").and_then(Value::as_i64)
        && value.get("flags").is_some()
    {
        edges.push(Edge { path, target: id });
        return;
    }
    match value {
        Value::Object(fields) => {
            for (key, value) in fields {
                children(value, format!("{path}/{key}"), edges);
            }
        }
        Value::Array(values) => {
            for (index, value) in values.iter().enumerate() {
                children(value, format!("{path}/{index}"), edges);
            }
        }
        _ => {}
    }
}
fn walk(value: &Value, nodes: &mut Vec<Node>) {
    if let (Some(id), Some(kind), Some(flags)) = (
        value.get("id").and_then(Value::as_i64),
        value.get("kind").and_then(Value::as_i64),
        value.get("flags").and_then(Value::as_i64),
    ) {
        let mut edges = Vec::new();
        if let Some(fields) = value.as_object() {
            for (key, value) in fields {
                children(value, format!("/{key}"), &mut edges);
            }
        }
        if let Some(target) = value.get("referencedTypeId").and_then(Value::as_i64) {
            edges.push(Edge {
                path: "/referencedTypeId".into(),
                target,
            });
        }
        nodes.push(Node {
            id,
            category: category(kind),
            flags,
            name: value
                .get("name")
                .and_then(Value::as_str)
                .or_else(|| value.pointer("/declaration/name").and_then(Value::as_str))
                .map(str::to_string),
            alias: value
                .pointer("/typeAliasInfo/fullName")
                .and_then(Value::as_str)
                .map(str::to_string),
            declaration_origin: value
                .pointer("/declaration/kind")
                .and_then(Value::as_i64)
                .map(|x| {
                    if x == 0 {
                        "source_declaration"
                    } else {
                        "synthesized_declaration"
                    }
                    .into()
                }),
            edges,
        });
    }
    match value {
        Value::Object(fields) => {
            for value in fields.values() {
                walk(value, nodes);
            }
        }
        Value::Array(values) => {
            for value in values {
                walk(value, nodes);
            }
        }
        _ => {}
    }
}
pub fn normalize(value: Value) -> Result<Graph, serde_json::Error> {
    let mut nodes = Vec::new();
    walk(&value, &mut nodes);
    Ok(Graph {
        nodes,
        raw_tsp: serde_json::to_string(&value)?,
        location_precision: "transaction_source_resolvers_attempted_per_declaration".into(),
        limitations: vec![
            "TSP declaration-preserving binding types do not guarantee annotation-only types"
                .into(),
            "Synthesized stub text is retained as evidence and never executed".into(),
            "Declaration coordinates are LSP UTF-16 and require a retained source digest join"
                .into(),
            "Unresolved zero ranges and bundled stub URIs are not executable body identities"
                .into(),
            "Raw TSP retains literals and specialization beyond this normalized projection".into(),
        ],
    })
}

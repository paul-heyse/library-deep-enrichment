//! Cargo project observations; package graphs never impersonate compilation units.
use crate::wire;
use cargo_metadata::{DependencyKind, Metadata};
use schemars::JsonSchema;
use serde::Serialize;
use std::{
    collections::BTreeMap,
    fs::File,
    io::{self, BufReader},
    path::Path,
};

#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Target {
    pub name: String,
    pub kinds: Vec<String>,
    pub crate_types: Vec<String>,
    pub source: String,
    pub required_features: Vec<String>,
    pub edition: String,
    pub doc: bool,
    pub doctest: bool,
    pub test: bool,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Dependency {
    pub name: String,
    pub rename: Option<String>,
    pub requirement: String,
    pub source: Option<String>,
    pub kind: String,
    pub platform: Option<String>,
    pub optional: bool,
    pub default_features: bool,
    pub features: Vec<String>,
    pub registry: Option<String>,
    pub path: Option<String>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct EdgeKind {
    pub kind: String,
    pub platform: Option<String>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ResolvedDependency {
    pub alias: String,
    pub package_id: String,
    pub kinds: Vec<EdgeKind>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Package {
    pub id: String,
    pub package_id: String,
    pub symbol: String,
    pub kind: String,
    pub version: String,
    pub source: Option<String>,
    pub manifest: String,
    pub targets: Vec<Target>,
    pub dependencies: Vec<Dependency>,
    pub feature_definitions: BTreeMap<String, Vec<String>>,
    pub resolved_features: Option<Vec<String>>,
    pub resolved_dependencies: Option<Vec<ResolvedDependency>>,
    pub license: Option<String>,
    pub rust_version: Option<String>,
    pub links: Option<String>,
}
fn dependency_kind(kind: DependencyKind) -> String {
    match kind {
        DependencyKind::Normal => "normal",
        DependencyKind::Build => "build",
        DependencyKind::Development => "development",
        _ => "unknown",
    }
    .into()
}

pub fn normalize(path: &Path, request: &str) -> Result<(), Box<dyn std::error::Error>> {
    let metadata: Metadata = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    let input = wire::digest_reader(File::open(path)?)?;
    let count = metadata.packages.len();
    let nodes = metadata.resolve.as_ref().map(|x| {
        x.nodes
            .iter()
            .map(|n| (&n.id, n))
            .collect::<BTreeMap<_, _>>()
    });
    let mut stream = wire::Stream::new(
        io::stdout().lock(),
        serde_json::json!({
            "request_id":request,"input_digest":input,"schema":"library-guides.cargo.v1","producer":"cargo_metadata-0.23.1",
            "expected_records":count,"workspace_root":metadata.workspace_root,"workspace_members":metadata.workspace_members,
            "workspace_default_members":metadata.workspace_default_members,"target_directory":metadata.target_directory,
            "build_directory":metadata.build_directory,"resolve_available":metadata.resolve.is_some(),
            "root":metadata.resolve.as_ref().and_then(|x|x.root.as_ref()),"unit_context":"not_observed"
        }),
    )?;
    let mut packages = metadata.packages.iter().collect::<Vec<_>>();
    packages.sort_by_key(|p| &p.id);
    for p in packages {
        let node = nodes.as_ref().and_then(|ns| ns.get(&p.id));
        let record = Package {
            id: format!("package:{input}:{}", p.id.repr),
            package_id: p.id.repr.clone(),
            symbol: p.name.to_string(),
            kind: "package".into(),
            version: p.version.to_string(),
            source: p.source.as_ref().map(ToString::to_string),
            manifest: p.manifest_path.to_string(),
            targets: p
                .targets
                .iter()
                .map(|t| Target {
                    name: t.name.clone(),
                    kinds: t.kind.iter().map(ToString::to_string).collect(),
                    crate_types: t.crate_types.iter().map(ToString::to_string).collect(),
                    source: t.src_path.to_string(),
                    required_features: t.required_features.clone(),
                    edition: t.edition.to_string(),
                    doc: t.doc,
                    doctest: t.doctest,
                    test: t.test,
                })
                .collect(),
            dependencies: p
                .dependencies
                .iter()
                .map(|d| Dependency {
                    name: d.name.clone(),
                    rename: d.rename.clone(),
                    requirement: d.req.to_string(),
                    source: d.source.as_ref().map(ToString::to_string),
                    kind: dependency_kind(d.kind),
                    platform: d.target.as_ref().map(ToString::to_string),
                    optional: d.optional,
                    default_features: d.uses_default_features,
                    features: d.features.clone(),
                    registry: d.registry.clone(),
                    path: d.path.as_ref().map(ToString::to_string),
                })
                .collect(),
            feature_definitions: p.features.clone(),
            resolved_features: node.map(|n| n.features.iter().map(ToString::to_string).collect()),
            resolved_dependencies: node.map(|n| {
                n.deps
                    .iter()
                    .map(|d| ResolvedDependency {
                        alias: d.name.clone(),
                        package_id: d.pkg.repr.clone(),
                        kinds: d
                            .dep_kinds
                            .iter()
                            .map(|k| EdgeKind {
                                kind: dependency_kind(k.kind),
                                platform: k.target.as_ref().map(ToString::to_string),
                            })
                            .collect(),
                    })
                    .collect()
            }),
            license: p.license.clone(),
            rust_version: p.rust_version.as_ref().map(ToString::to_string),
            links: p.links.clone(),
        };
        stream.record(record)?;
    }
    stream.finish(serde_json::json!({"state":"complete","packages":count,"resolve_state":if nodes.is_some() {"complete"} else {"not_requested"},"compilation_units":"not_observed"}))?;
    Ok(())
}

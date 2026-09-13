//! Frozen-environment bulk type and call evidence from the pinned upstream solver.
use lde_protocol::{Stream, digest};
use pyrefly::query::{IndexedTypeShapeKind, Query, TypeShapeTrait};
use pyrefly_config::{config::ConfigFile, finder::ConfigFinder};
use pyrefly_python::{
    module_name::ModuleName,
    module_path::ModulePath,
    sys_info::{PythonPlatform, PythonVersion, SysInfo},
};
use pyrefly_util::{arc_id::ArcId, lined_buffer::PythonASTRange, thread_pool::ThreadCount};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, fs, io, path::PathBuf};

type Error = Box<dyn std::error::Error>;
mod targeted;

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct InputFile {
    path: String,
    digest: String,
    module: Option<String>,
}
#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct SubtypeQuery {
    module: String,
    left: String,
    right: String,
}
#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct MemberQuery {
    module: String,
    class: String,
}
#[derive(Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
enum QueryRole {
    Computed,
    Declared,
    Expected,
}
#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct TargetedQuery {
    module: String,
    start: u32,
    end: u32,
    role: QueryRole,
}
#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Request {
    profile: String,
    root: PathBuf,
    files: Vec<InputFile>,
    search_paths: Vec<String>,
    python_version: String,
    python_platform: String,
    #[serde(default)]
    subtype_queries: Vec<SubtypeQuery>,
    #[serde(default)]
    member_queries: Vec<MemberQuery>,
    #[serde(default)]
    targeted_queries: Vec<TargetedQuery>,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Anchor {
    start: usize,
    end: usize,
    coordinate: String,
}
#[derive(Serialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Shape {
    Named {
        name: String,
        args: Vec<usize>,
        unspecified_type_arg_count: Option<usize>,
        traits: Vec<String>,
    },
    Callable {
        params: Vec<usize>,
        return_type: usize,
        is_staticmethod: bool,
    },
    TypeVariable {
        name: String,
        bounds: Vec<usize>,
    },
}
#[derive(Serialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Payload {
    Shape {
        index: usize,
        shape: Shape,
    },
    TypeAt {
        type_index: usize,
        anchor: Anchor,
    },
    Call {
        anchor: Anchor,
        target: String,
        callable_kind: String,
        class: Option<String>,
        target_origin: String,
        identity: String,
        dispatch: String,
    },
    FileState {
        types: Option<usize>,
        callees: Option<usize>,
        body_origin: String,
    },
    Subtype {
        left: String,
        right: String,
        result: Option<bool>,
        error: Option<String>,
        semantics: String,
    },
    Member {
        class: String,
        name: String,
        annotation: String,
        member_kind: Option<String>,
        is_final: bool,
        completeness: String,
    },
    Targeted {
        role: String,
        anchor: Anchor,
        tsp: Option<targeted::Graph>,
        expected_fallback: bool,
        protocol: String,
    },
    OpaqueFile {
        role: String,
        reason: String,
    },
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Fact {
    id: String,
    symbol: String,
    file: String,
    source_digest: String,
    profile: String,
    payload: Payload,
}

fn anchor(source: &str, lines: &[usize], range: &PythonASTRange) -> Result<Anchor, Error> {
    let offset = |line: u32, col: u32| -> Result<usize, Error> {
        let base = *lines
            .get(line.checked_sub(1).ok_or("zero source line")? as usize)
            .ok_or("source line outside file")?;
        let value = base + col as usize;
        if value > source.len()
            || !source.is_char_boundary(value)
            || value > *lines.get(line as usize).unwrap_or(&source.len())
        {
            return Err("invalid UTF-8 source coordinate".into());
        }
        Ok(value)
    };
    let start = offset(range.start_line.get(), range.start_col)?;
    let end = offset(range.end_line.get(), range.end_col)?;
    if end < start {
        return Err("reversed source coordinate".into());
    }
    Ok(Anchor {
        start,
        end,
        coordinate: "utf8_bytes".into(),
    })
}

fn owned_shape(kind: IndexedTypeShapeKind) -> Shape {
    match kind {
        IndexedTypeShapeKind::Named {
            name,
            args,
            unspecified_type_arg_count,
            traits,
        } => Shape::Named {
            name,
            args,
            unspecified_type_arg_count,
            traits: traits
                .into_iter()
                .map(|t| {
                    match t {
                        TypeShapeTrait::TypedDict => "typed_dict",
                        TypeShapeTrait::PartialTypedDict => "partial_typed_dict",
                        TypeShapeTrait::Tuple => "tuple",
                    }
                    .into()
                })
                .collect(),
        },
        IndexedTypeShapeKind::Callable {
            params,
            return_type,
            is_staticmethod,
        } => Shape::Callable {
            params,
            return_type,
            is_staticmethod,
        },
        IndexedTypeShapeKind::TypeVariable { name, bounds } => Shape::TypeVariable { name, bounds },
    }
}

fn source(request: &Request, file: &InputFile) -> Result<(PathBuf, String), Error> {
    let root = request.root.canonicalize()?;
    let path = root.join(&file.path).canonicalize()?;
    if !path.starts_with(root) {
        return Err("source escapes frozen environment".into());
    }
    let bytes = fs::read(&path)?;
    if digest(&bytes) != file.digest {
        return Err(format!("source digest mismatch: {}", file.path).into());
    }
    Ok((
        path,
        if file.module.is_some() {
            String::from_utf8(bytes)?
        } else {
            String::new()
        },
    ))
}
fn config(request: &Request) -> Result<ConfigFile, Error> {
    let mut config = ConfigFile {
        disable_search_path_heuristics: true,
        enable_fallback_search_path: false,
        ..ConfigFile::default()
    };
    config.interpreters.skip_interpreter_query = true;
    config.python_environment.python_version =
        Some(request.python_version.parse::<PythonVersion>()?);
    config.python_environment.python_platform = Some(PythonPlatform::new(&request.python_platform));
    config.python_environment.site_package_path = Some(Vec::new());
    config
        .python_environment
        .interpreter_site_package_path
        .clear();
    config.python_environment.interpreter_stdlib_path.clear();
    let root = request.root.canonicalize()?;
    for path in &request.search_paths {
        let path = root.join(path).canonicalize()?;
        if !path.starts_with(&root) {
            return Err("search path escapes frozen environment".into());
        }
        config.search_path_from_args.push(path);
    }
    let errors = config.configure();
    if !errors.is_empty() {
        return Err(format!(
            "frozen Python configuration failed: {}",
            errors
                .iter()
                .map(|error| error.get_message())
                .collect::<Vec<_>>()
                .join("; ")
        )
        .into());
    }
    Ok(config)
}
fn collect(request: &Request) -> Result<(Vec<Fact>, Vec<String>), Error> {
    if request.files.is_empty() || request.search_paths.is_empty() {
        return Err("empty semantic environment".into());
    }
    if request.targeted_queries.len() > 100 {
        return Err("targeted type query budget exceeded".into());
    }
    let config = config(request)?;
    let sys_info = SysInfo::new(config.python_version(), config.python_platform().clone());
    let query = Query::new_with_sys_info(
        ConfigFinder::new_constant(ArcId::new(config)),
        ThreadCount::Inline,
        sys_info,
    );
    let mut modules = BTreeMap::new();
    for file in &request.files {
        let (path, bytes) = source(request, file)?;
        if let Some(name) = &file.module
            && modules.insert(name.clone(), (file, path, bytes)).is_some()
        {
            return Err(
                "duplicate selected module; resolve stub/source precedence explicitly".into(),
            );
        }
    }
    let diagnostics = query.add_files(
        modules
            .iter()
            .map(|(name, (_, path, _))| {
                (
                    ModuleName::from_str(name),
                    ModulePath::filesystem(path.clone()),
                )
            })
            .collect(),
    );
    let mut facts = Vec::new();
    for (name, (file, path, bytes)) in &modules {
        let mut lines = vec![0];
        lines.extend(
            bytes
                .bytes()
                .enumerate()
                .filter_map(|(i, b)| (b == b'\n').then_some(i + 1)),
        );
        let mut sequence = 0;
        let mut push = |payload| {
            facts.push(Fact {
                id: format!(
                    "py:{}:{}:{}:{}",
                    request.profile,
                    digest(file.path.as_bytes()),
                    file.digest,
                    sequence
                ),
                symbol: name.clone(),
                file: file.path.clone(),
                source_digest: file.digest.clone(),
                profile: request.profile.clone(),
                payload,
            });
            sequence += 1;
        };
        let module = ModuleName::from_str(name);
        let module_path = ModulePath::filesystem(path.clone());
        let table = query.get_type_table_in_file(module, module_path.clone(), None);
        let callees = query.get_callees_with_location(module, module_path, None);
        push(Payload::FileState {
            types: table.as_ref().map(|t| t.types.len()),
            callees: callees.as_ref().map(Vec::len),
            body_origin: if file.path.ends_with(".pyi") {
                "stub_interface"
            } else {
                "source_body"
            }
            .into(),
        });
        if let Some(table) = table {
            for (index, entry) in table.type_table.into_iter().enumerate() {
                push(Payload::Shape {
                    index,
                    shape: owned_shape(entry.kind),
                });
            }
            for located in table.types {
                push(Payload::TypeAt {
                    type_index: located.type_index,
                    anchor: anchor(bytes, &lines, &located.location)?,
                });
            }
        }
        if let Some(callees) = callees {
            for (range, callee) in callees {
                let origin = modules
                    .iter()
                    .filter(|(module, _)| callee.target.starts_with(&format!("{module}.")))
                    .max_by_key(|(module, _)| module.len())
                    .map_or("external_source_not_selected", |(_, (target, _, _))| {
                        if target.path.ends_with(".pyi") {
                            "stub_interface"
                        } else {
                            "source_body"
                        }
                    });
                push(Payload::Call {
                    anchor: anchor(bytes, &lines, &range)?,
                    target: callee.target,
                    callable_kind: callee.kind,
                    class: callee.class_name,
                    target_origin: origin.into(),
                    identity: "engine_resolved".into(),
                    dispatch: "heuristic".into(),
                });
            }
        }
        for pair in request
            .subtype_queries
            .iter()
            .filter(|pair| pair.module == *name)
        {
            let result = query.is_subtype(module, path.clone(), &pair.left, &pair.right);
            let (value, error) = match result {
                Ok(value) => (Some(value), None),
                Err(error) => (None, Some(error)),
            };
            push(Payload::Subtype {
                left: pair.left.clone(),
                right: pair.right.clone(),
                result: value,
                error,
                semantics: "gradual_static_compatibility_not_runtime_conformance".into(),
            });
        }
        for member in request
            .member_queries
            .iter()
            .filter(|member| member.module == *name)
        {
            if let Some(attributes) =
                query.get_attributes(module, ModulePath::filesystem(path.clone()), &member.class)
            {
                for attr in attributes {
                    push(Payload::Member {
                        class: member.class.clone(),
                        name: attr.name,
                        annotation: attr.annotation,
                        member_kind: attr.kind,
                        is_final: attr.is_final,
                        completeness: "query_member_summary_not_complete_mro".into(),
                    });
                }
            }
        }
        for target in request
            .targeted_queries
            .iter()
            .filter(|target| target.module == *name)
        {
            let start = target.start as usize;
            let end = target.end as usize;
            if start > end
                || end > bytes.len()
                || !bytes.is_char_boundary(start)
                || !bytes.is_char_boundary(end)
            {
                return Err("targeted query is not an exact UTF-8 source range".into());
            }
            let role = match target.role {
                QueryRole::Computed => "computed",
                QueryRole::Declared => "declared",
                QueryRole::Expected => "expected",
            };
            let result = query.lde_tsp(
                module,
                ModulePath::filesystem(path.clone()),
                target.start,
                target.end,
                role,
            );
            let (tsp, fallback) = match result {
                Some((value, fallback)) => (
                    Some(targeted::normalize(serde_json::to_value(value)?)?),
                    fallback,
                ),
                None => (None, false),
            };
            push(Payload::Targeted {
                role: role.into(),
                anchor: Anchor {
                    start,
                    end,
                    coordinate: "utf8_bytes".into(),
                },
                tsp,
                expected_fallback: fallback,
                protocol: "TSP 0.4.1 type conversion in pinned frozen transaction".into(),
            });
        }
    }
    for file in request.files.iter().filter(|file| file.module.is_none()) {
        facts.push(Fact {id:format!("py-opaque:{}:{}:{}",request.profile,digest(file.path.as_bytes()),file.digest),symbol:file.path.clone(),file:file.path.clone(),source_digest:file.digest.clone(),profile:request.profile.clone(),payload:Payload::OpaqueFile {role:if file.path.ends_with(".so") || file.path.ends_with(".pyd"){"native_boundary"}else if file.path.ends_with(".pyx") || file.path.ends_with(".pxd"){"cython_boundary"}else{"not_selected_module"}.into(),reason:"Acquired exact bytes; no Python module body was selected for this source role or encoding".into()}});
    }
    for file in &request.files {
        source(request, file)?;
    }
    Ok((facts, diagnostics))
}
fn main() -> Result<(), Error> {
    let args: Vec<_> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("schema") => {
            println!("{}", serde_json::to_string(&schemars::schema_for!(Fact))?);
        }
        Some("request-schema") => {
            println!(
                "{}",
                serde_json::to_string(&schemars::schema_for!(Request))?
            );
        }
        Some("normalize") => {
            let bytes = fs::read(args.get(2).ok_or("request path missing")?)?;
            let request: Request = serde_json::from_slice(&bytes)?;
            let (facts, diagnostics) = collect(&request)?;
            let mut output = Stream::new(
                io::stdout().lock(),
                serde_json::json!({"request_id":args.get(3).ok_or("request id missing")?,"input_digest":digest(&bytes),"expected_records":facts.len(),"schema":"library-guides.python-semantics.v1","producer":"pyrefly-1.2.0+context-patch.1","profile":request.profile,"python_version":request.python_version,"python_platform":request.python_platform,"position_encoding":"utf8_bytes","typeshed":"upstream_bundled_pinned_by_worker","environment_files":request.files.len()}),
            )?;
            for fact in facts {
                output.record(fact)?;
            }
            output.finish(serde_json::json!({"state":"complete","files":request.files.len(),"diagnostics":diagnostics,"semantic_closed":false,"dispatch":"heuristic","missing_calls":"requires_join_to_syntax_inventory","type_precision":"bulk_collapsed_shapes","runtime_availability":"not_established"}))?;
        }
        _ => return Err("expected schema, request-schema or normalize REQUEST REQUEST_ID".into()),
    }
    Ok(())
}

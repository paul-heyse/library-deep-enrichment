//! Owned source facts; syntax, lexical resolution and runtime behavior stay distinct.
mod execution;
mod lexical;
use lde_protocol::{Stream, digest};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{fs, io, path::PathBuf};
use tree_sitter::{Parser, Query, QueryCursor, StreamingIterator};
type Error = Box<dyn std::error::Error>;

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct InputFile {
    path: String,
    digest: String,
    language: String,
}
#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Request {
    profile: String,
    root: PathBuf,
    files: Vec<InputFile>,
    python_minor: u8,
    lexical: bool,
    #[serde(default)]
    execution: bool,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Field {
    name: String,
    start: usize,
    end: usize,
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Syntax {
    node_kind: String,
    role: String,
    start: usize,
    end: usize,
    owner: Option<String>,
    name: Option<String>,
    signature: Option<String>,
    fields: Vec<Field>,
    source_digest: String,
    syntax_valid: bool,
    documentation: Option<String>,
    documentation_text: Option<String>,
}
#[derive(Serialize, JsonSchema)]
#[serde(tag = "family", rename_all = "snake_case", deny_unknown_fields)]
enum Payload {
    Syntax(Syntax),
    Lexical(lexical::Lexical),
    Execution(execution::Node),
    FileState {
        language: String,
        parse_state: String,
        lexical_state: String,
        reason: Option<String>,
    },
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct Fact {
    id: String,
    symbol: String,
    kind: String,
    file: String,
    profile: String,
    payload: Payload,
}
fn language(name: &str) -> Option<(tree_sitter::Language, &'static str)> {
    match name {
        "rust" => Some((
            tree_sitter_rust::LANGUAGE.into(),
            include_str!("../../../src/library_deep_enrichment/assets/queries/rust/evidence.scm"),
        )),
        "python" => Some((
            tree_sitter_python::LANGUAGE.into(),
            include_str!("../../../src/library_deep_enrichment/assets/queries/python/evidence.scm"),
        )),
        "markdown" => Some((
            tree_sitter_md::LANGUAGE.into(),
            include_str!("../../../src/library_deep_enrichment/assets/queries/markdown/evidence.scm"),
        )),
        _ => None,
    }
}
fn definition(node: tree_sitter::Node<'_>) -> bool {
    matches!(
        node.kind(),
        "function_item"
            | "function_signature_item"
            | "struct_item"
            | "enum_item"
            | "trait_item"
            | "impl_item"
            | "mod_item"
            | "function_definition"
            | "class_definition"
    )
}
fn node_text<'a>(node: tree_sitter::Node<'_>, bytes: &'a [u8]) -> Result<&'a str, Error> {
    Ok(std::str::from_utf8(&bytes[node.byte_range()])?)
}
fn documentation(node: tree_sitter::Node<'_>, file: &InputFile, bytes: &[u8]) -> Option<String> {
    if file.language == "rust" && node.kind() == "line_comment" {
        let text = &bytes[node.byte_range()];
        if (text.starts_with(b"///") && !text.starts_with(b"////")) || text.starts_with(b"//!") {
            return Some("rust_line".into());
        }
    }
    if file.language == "python" && node.kind() == "string" {
        let expression = node.parent()?;
        let suite = expression.parent()?;
        if expression.kind() != "expression_statement"
            || !matches!(suite.kind(), "module" | "block")
        {
            return None;
        }
        if suite.kind() == "block"
            && !suite
                .parent()
                .is_some_and(|p| matches!(p.kind(), "function_definition" | "class_definition"))
        {
            return None;
        }
        let mut cursor = suite.walk();
        if suite
            .named_children(&mut cursor)
            .find(|n| n.kind() != "comment")
            == Some(expression)
        {
            return Some("python_docstring".into());
        }
    }
    None
}
fn syntax(file: &InputFile, bytes: &[u8]) -> Result<(Vec<Syntax>, bool), Error> {
    let (language, query) = language(&file.language).ok_or("unsupported source language")?;
    let mut parser = Parser::new();
    parser.set_language(&language)?;
    let tree = parser.parse(bytes, None).ok_or("parser interrupted")?;
    let valid = !tree.root_node().has_error();
    let query = Query::new(&language, query)?;
    let mut cursor = QueryCursor::new();
    let mut matches = cursor.matches(&query, tree.root_node(), bytes);
    let mut result = Vec::new();
    while let Some(matched) = matches.next() {
        for capture in matched.captures {
            let node = capture.node;
            let role = query.capture_names()[capture.index as usize].to_string();
            let name = node
                .child_by_field_name("name")
                .map(|n| node_text(n, bytes).map(String::from))
                .transpose()?;
            let mut owner = node.parent();
            while owner.is_some_and(|node| !definition(node)) {
                owner = owner.and_then(|n| n.parent());
            }
            let owner = owner.map(|n| {
                format!(
                    "syntax:{}:{}:{}:{}:{}",
                    digest(file.path.as_bytes()),
                    file.digest,
                    n.start_byte(),
                    n.end_byte(),
                    n.kind()
                )
            });
            let signature = if role == "definition" {
                let end = node
                    .child_by_field_name("body")
                    .map_or(node.end_byte(), |body| body.start_byte());
                Some(
                    std::str::from_utf8(&bytes[node.start_byte()..end])?
                        .trim()
                        .to_string(),
                )
            } else {
                None
            };
            let fields = (0..node.child_count())
                .filter_map(|i| {
                    node.field_name_for_child(i as u32)
                        .zip(node.child(i as u32))
                        .map(|(name, child)| Field {
                            name: name.into(),
                            start: child.start_byte(),
                            end: child.end_byte(),
                        })
                })
                .collect();
            result.push(Syntax {
                node_kind: node.kind().into(),
                role,
                start: node.start_byte(),
                end: node.end_byte(),
                owner,
                name,
                signature,
                fields,
                source_digest: file.digest.clone(),
                syntax_valid: valid,
                documentation: documentation(node, file, bytes),
                documentation_text: if documentation(node, file, bytes).is_some() {
                    Some(node_text(node, bytes)?.into())
                } else {
                    None
                },
            });
        }
    }
    result.sort_by_key(|x| (x.start, x.end, x.role.clone()));
    Ok((result, valid))
}
fn main() -> Result<(), Error> {
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).is_some_and(|x| x == "schema") {
        println!("{}", serde_json::to_string(&schemars::schema_for!(Fact))?);
        return Ok(());
    }
    if args.get(1).is_some_and(|x| x == "request-schema") {
        println!(
            "{}",
            serde_json::to_string(&schemars::schema_for!(Request))?
        );
        return Ok(());
    }
    if !args.get(1).is_some_and(|x| x == "normalize") {
        return Err("expected normalize REQUEST REQUEST_ID".into());
    }
    let input = fs::read(args.get(2).ok_or("missing request")?)?;
    let request: Request = serde_json::from_slice(&input)?;
    if request.files.is_empty() {
        return Err("empty selected source universe".into());
    }
    let root = request.root.canonicalize()?;
    let mut facts = Vec::new();
    let mut limitations = Vec::new();
    for file in &request.files {
        let path = root.join(&file.path).canonicalize()?;
        if !path.starts_with(&root) {
            return Err("source path escapes snapshot".into());
        }
        let bytes = fs::read(&path)?;
        if digest(&bytes) != file.digest {
            return Err("snapshot changed".into());
        }
        let mut push = |payload: Payload, id: String, symbol: String, kind: String| {
            facts.push(Fact {
                id,
                symbol,
                kind,
                file: file.path.clone(),
                profile: request.profile.clone(),
                payload,
            })
        };
        let (parse_state, lexical_state, reason) =
            if language(&file.language).is_some() && std::str::from_utf8(&bytes).is_ok() {
                let (records, valid) = syntax(file, &bytes)?;
                for item in records {
                    let id = format!(
                        "syntax:{}:{}:{}:{}:{}",
                        digest(file.path.as_bytes()),
                        file.digest,
                        item.start,
                        item.end,
                        item.node_kind
                    );
                    let symbol = item.name.clone().unwrap_or_else(|| file.path.clone());
                    let kind = item.role.clone();
                    push(Payload::Syntax(item), id, symbol, kind);
                }
                let mut lexical_state = "not_requested";
                if file.language == "python" && (request.lexical || request.execution) && valid {
                    match lexical::extract(
                        std::str::from_utf8(&bytes)?,
                        &path,
                        request.python_minor,
                        request.execution,
                    ) {
                        Ok(records) => {
                            for record in records.execution {
                                let id = format!(
                                    "execution:{}:{}:{}:{}",
                                    digest(file.path.as_bytes()),
                                    file.digest,
                                    record.start,
                                    record.end
                                );
                                let symbol = record.value.clone();
                                push(Payload::Execution(record), id, symbol, "execution".into());
                            }
                            for (i, record) in records.lexical.into_iter().enumerate() {
                                let symbol = record.name.clone();
                                push(
                                    Payload::Lexical(record),
                                    format!(
                                        "lexical:{}:{}:{i}",
                                        digest(file.path.as_bytes()),
                                        file.digest
                                    ),
                                    symbol,
                                    "lexical".into(),
                                );
                            }
                            lexical_state = "complete";
                        }
                        Err(error) => {
                            limitations.push(format!("{}: {error}", file.path));
                            lexical_state = "unavailable";
                        }
                    }
                }
                (
                    if valid { "complete" } else { "partial" },
                    lexical_state,
                    None,
                )
            } else {
                (
                    "unsupported",
                    "not_requested",
                    Some(
                        "language/native body or non-UTF8 source not analyzed; raw bytes retained"
                            .to_string(),
                    ),
                )
            };
        if parse_state != "complete" {
            limitations.push(format!("{}: {parse_state}", file.path));
        }
        push(
            Payload::FileState {
                language: file.language.clone(),
                parse_state: parse_state.into(),
                lexical_state: lexical_state.into(),
                reason,
            },
            format!("file:{}:{}", file.digest, file.path),
            file.path.clone(),
            "file_state".into(),
        );
        if digest(&fs::read(&path)?) != file.digest {
            return Err("source changed during extraction".into());
        }
    }
    let mut output = Stream::new(
        io::stdout().lock(),
        serde_json::json!({"request_id":args.get(3).ok_or("missing request id")?,"input_digest":digest(&input),"expected_records":facts.len(),"schema":if request.execution {"library-guides.source-execution.v1"} else {"library-guides.source-facts.v1"},"producer":"tree-sitter-0.26.12+ruff-0.16.1-facade.2","profile":request.profile,"files":request.files.len(),"position_encoding":"utf8_bytes","python_minor":request.python_minor}),
    )?;
    for fact in facts {
        output.record(fact)?;
    }
    output.finish(serde_json::json!({"state":"complete","files":request.files.len(),"limitations":limitations,"semantic_closed":false,"rust_resolution":"syntax_only","python_resolution":"ruff_lexical","runtime_availability":"not_established"}))?;
    Ok(())
}

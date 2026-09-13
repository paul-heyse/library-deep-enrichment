//! Validate compiler schemas before Python consumes the complete item graph.

use std::{
    env, fs,
    io::{self, Write},
    process::ExitCode,
};

mod cargo_messages;
mod cargo_model;
mod contract;
mod declarations;
mod decoder;
mod rendering;
mod wire;

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let path = env::args()
        .nth(1)
        .ok_or("usage: lde-rustdoc-facts FILE")?;
    if path == "schema" {
        serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(declarations::Declaration),
        )?;
        return Ok(());
    }
    if path == "cargo-messages-schema" {
        serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(cargo_messages::Record),
        )?;
        return Ok(());
    }
    if path == "cargo-messages" {
        let input = env::args().nth(2).ok_or("cargo-messages requires FILE")?;
        let request = env::args()
            .nth(3)
            .ok_or("cargo-messages requires REQUEST")?;
        return cargo_messages::normalize(std::path::Path::new(&input), &request);
    }
    if path == "cargo-schema" {
        serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(cargo_model::Package),
        )?;
        return Ok(());
    }
    if path == "cargo-normalize" {
        let input = env::args()
            .nth(2)
            .ok_or("cargo-normalize requires FILE REQUEST")?;
        let request = env::args()
            .nth(3)
            .ok_or("cargo-normalize requires REQUEST")?;
        return cargo_model::normalize(std::path::Path::new(&input), &request);
    }
    if path == "normalize" {
        let input = env::args().nth(2).ok_or("inspect requires FILE")?;
        let document = decoder::read(std::path::Path::new(&input))?;
        let artifact = wire::digest_reader(fs::File::open(&input)?)?;
        let request = env::args().nth(3).unwrap_or_else(|| artifact.clone());
        let index = declarations::Index::build(&document)?;
        let mut stream = wire::Stream::new(
            io::stdout().lock(),
            serde_json::json!({"request_id": request, "input_digest":artifact, "producer":"rustdoc-types", "schema":"library-guides.declaration.v1", "format": document.format, "root": document.root, "version": document.version, "target": document.target, "includes_private":document.includes_private, "external":document.external, "paths":document.paths, "expected_records":document.index.len()}),
        )?;
        let count = document.index.len();
        for item in document.index.values() {
            stream.record(declarations::project(item, &artifact, &index)?)?;
        }
        stream.finish(serde_json::json!({"state":"complete","items":count,"route_state":if index.unresolved_routes.is_empty() {"complete"} else {"partial"}, "unresolved_routes":index.unresolved_routes, "not_represented": match document.format {57=>vec!["stability","const_stability","default_unstable"],59=>vec!["default_unstable"],_=>vec![]}, "body_availability":"not_represented", "generation_purpose":"documentation"}))?;
        return Ok(());
    }
    let payload = fs::read_to_string(&path)?;
    let mut document: serde_json::Value = serde_json::from_str(&payload)?;
    let version = document["format_version"]
        .as_u64()
        .ok_or("missing format_version")?;
    match version {
        57 => {
            let _: rustdoc_types_57::Crate = serde_json::from_str(&payload)?;
        }
        59 => {
            let _: rustdoc_types_59::Crate = serde_json::from_str(&payload)?;
        }
        60 => {
            let _: rustdoc_types_60::Crate = serde_json::from_str(&payload)?;
        }
        61 => {
            let _: rustdoc_types_61::Crate = serde_json::from_str(&payload)?;
        }
        _ => return Err(format!("unsupported rustdoc format {version}").into()),
    }
    // Public-api is a readable secondary view. Its format support can lag the
    // typed decoder; report that separately and retain all compiler structure.
    let public_view = match public_api::Builder::from_rustdoc_json(&path).build() {
        Ok(api) => serde_json::json!({"state": "complete", "items": api.to_string()}),
        Err(error) => serde_json::json!({"state": "unavailable", "reason": error.to_string()}),
    };
    document["library_guides_public_api"] = public_view;
    serde_json::to_writer(io::stdout().lock(), &document)?;
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let _ = writeln!(io::stderr().lock(), "{error}");
            ExitCode::FAILURE
        }
    }
}

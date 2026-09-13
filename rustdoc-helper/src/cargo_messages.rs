//! Compatible upstream Cargo intake with strict owned observations and raw audit lines.
use crate::{cargo_model::Target, wire};
use cargo_metadata::Message;
use schemars::JsonSchema;
use serde::Serialize;
use std::{
    fs::File,
    io::{self, BufRead, BufReader},
    path::Path,
};
#[derive(Serialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Observation {
    Artifact {
        package_id: String,
        target: Target,
        features: Vec<String>,
        filenames: Vec<String>,
        executable: Option<String>,
        fresh: bool,
        opt_level: String,
        debuginfo: String,
        debug_assertions: bool,
        overflow_checks: bool,
        test: bool,
    },
    Diagnostic {
        package_id: String,
        target: Target,
        message: String,
        level: String,
        code: Option<String>,
        rendered: Option<String>,
    },
    BuildScript {
        package_id: String,
        linked_libs: Vec<String>,
        linked_paths: Vec<String>,
        cfgs: Vec<String>,
        env: Vec<(String, String)>,
        out_dir: String,
    },
    BuildFinished {
        success: bool,
    },
    Unrecognized {
        reason: Option<String>,
        critical: bool,
    },
}
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Record {
    id: String,
    symbol: String,
    kind: String,
    line: usize,
    raw: String,
    observation: Observation,
}
fn target(t: cargo_metadata::Target) -> Target {
    Target {
        name: t.name,
        kinds: t.kind.iter().map(ToString::to_string).collect(),
        crate_types: t.crate_types.iter().map(ToString::to_string).collect(),
        source: t.src_path.to_string(),
        required_features: t.required_features,
        edition: t.edition.to_string(),
        doc: t.doc,
        doctest: t.doctest,
        test: t.test,
    }
}
fn normalize_message(raw: &str) -> Observation {
    match serde_json::from_str::<Message>(raw) {
        Ok(Message::CompilerArtifact(a)) => Observation::Artifact {
            package_id: a.package_id.repr,
            target: target(a.target),
            features: a.features,
            filenames: a.filenames.iter().map(ToString::to_string).collect(),
            executable: a.executable.map(|v| v.to_string()),
            fresh: a.fresh,
            opt_level: a.profile.opt_level,
            debuginfo: a.profile.debuginfo.to_string(),
            debug_assertions: a.profile.debug_assertions,
            overflow_checks: a.profile.overflow_checks,
            test: a.profile.test,
        },
        Ok(Message::CompilerMessage(d)) => Observation::Diagnostic {
            package_id: d.package_id.repr,
            target: target(d.target),
            message: d.message.message,
            level: format!("{:?}", d.message.level),
            code: d.message.code.map(|c| c.code),
            rendered: d.message.rendered,
        },
        Ok(Message::BuildScriptExecuted(s)) => Observation::BuildScript {
            package_id: s.package_id.repr,
            linked_libs: s.linked_libs.iter().map(ToString::to_string).collect(),
            linked_paths: s.linked_paths.iter().map(ToString::to_string).collect(),
            cfgs: s.cfgs,
            env: s.env,
            out_dir: s.out_dir.to_string(),
        },
        Ok(Message::BuildFinished(f)) => Observation::BuildFinished { success: f.success },
        _ => {
            let reason = serde_json::from_str::<serde_json::Value>(raw)
                .ok()
                .and_then(|v| v.get("reason").and_then(|s| s.as_str()).map(str::to_string));
            let malformed_json = raw.trim_start().starts_with('{')
                && serde_json::from_str::<serde_json::Value>(raw).is_err();
            let critical = malformed_json
                || reason.as_deref().is_some_and(|r| {
                    matches!(
                        r,
                        "compiler-artifact"
                            | "compiler-message"
                            | "build-script-executed"
                            | "build-finished"
                    )
                });
            Observation::Unrecognized { reason, critical }
        }
    }
}
pub fn normalize(path: &Path, request: &str) -> Result<(), Box<dyn std::error::Error>> {
    let count = BufReader::new(File::open(path)?)
        .lines()
        .try_fold(0usize, |count, line| line.map(|_| count + 1))?;
    let input = wire::digest_reader(File::open(path)?)?;
    let mut stream = wire::Stream::new(
        io::stdout().lock(),
        serde_json::json!({"request_id":request,"input_digest":input,"expected_records":count,"schema":"library-guides.cargo-messages.v1","producer":"cargo_metadata-0.23.1","unit_context":"requires_wrapper_reconciliation"}),
    )?;
    let mut critical = 0;
    let mut unknown = 0;
    let mut finished = Vec::new();
    for (line, raw) in BufReader::new(File::open(path)?).lines().enumerate() {
        let raw = raw?;
        let observation = normalize_message(&raw);
        if let Observation::Unrecognized { critical: c, .. } = &observation {
            unknown += 1;
            if *c {
                critical += 1;
            }
        }
        if let Observation::BuildFinished { success } = observation {
            finished.push(success);
        }
        stream.record(Record {
            id: format!("cargo-message:{input}:{line}"),
            symbol: format!("cargo-line-{line}"),
            kind: "cargo_message".into(),
            line,
            raw,
            observation,
        })?;
    }
    stream.finish(serde_json::json!({"state":if critical==0 {"complete"}else{"partial"},"critical_errors":critical,"unrecognized":unknown,"build_finished":finished,"compiler_invocations":"not_observed"}))?;
    Ok(())
}

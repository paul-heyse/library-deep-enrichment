//! Cargo-compatible compiler wrapper; only owned evidence leaves the compiler callback.
#![feature(rustc_private)]
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_public;
extern crate rustc_public_bridge;
extern crate rustc_span;
mod behavior;
mod callables;
mod instances;
mod invocation;
mod lifecycle;
mod memory;
mod memory_types;
mod projection;
mod shapes;
mod values;
use library_guides_protocol::{Stream, digest};
use rustc_public::CrateDef;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{
    env, fs, io,
    path::PathBuf,
    process::{Command, ExitCode},
};

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Fact {
    pub id: String,
    pub symbol: String,
    pub kind: String,
    pub payload: projection::Owner,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub behavior: Option<behavior::Owner>,
}

#[derive(Serialize, Deserialize)]
#[serde(untagged)]
enum WireFact {
    Legacy(Fact),
    Instances(instances::Fact),
    Callables(callables::Fact),
    Lifecycle(lifecycle::Fact),
    Memory(memory::Fact),
}
fn wrapper(args: Vec<String>) -> Result<(), Box<dyn std::error::Error>> {
    let real = args
        .get(1)
        .ok_or("Cargo wrapper requires compiler executable")?;
    if args.iter().any(|x| x == "-vV" || x.starts_with("--print"))
        || env::var("LIBRARY_GUIDES_MIR_OUTPUT").is_err()
    {
        let status = Command::new(real).args(&args[2..]).status()?;
        if !status.success() {
            return Err(format!("compiler failed: {status}").into());
        }
        return Ok(());
    }
    if let Ok(selected) = env::var("LIBRARY_GUIDES_MIR_PACKAGES") {
        let package = format!(
            "{}@{}",
            env::var("CARGO_PKG_NAME").unwrap_or_default(),
            env::var("CARGO_PKG_VERSION").unwrap_or_default()
        );
        if !selected.split(',').any(|value| value == package)
            || args.iter().any(|arg| arg == "build_script_build")
        {
            return invocation::delegate(args[1..].to_vec(), "check", "not_selected_for_bodies");
        }
    }
    let directory = PathBuf::from(env::var("LIBRARY_GUIDES_MIR_OUTPUT")?);
    fs::create_dir_all(&directory)?;
    let context = env::var("LIBRARY_GUIDES_MIR_CONTEXT")?;
    let behavior_requested =
        env::var("LIBRARY_GUIDES_MIR_BEHAVIOR").is_ok_and(|value| value == "1");
    let invocation = invocation::Invocation::new(args[1..].to_vec(), "mir")?;
    let unit = invocation.id.clone();
    let options = instances::Options::read()?;
    let mut collected = None;
    let mut collection_error = None;
    let mut records: Vec<Fact> = Vec::new();
    let result = rustc_public::run_with_tcx!(&args[1..], |tcx| {
        let mut collector = options
            .clone()
            .map(|value| instances::Collector::new(value, unit.clone()));
        for item in rustc_public::all_local_items() {
            let name = item.name();
            if let Some(body) = item.body() {
                let internal = rustc_public::rustc_internal::internal(tcx, item.def_id());
                let identity = u128::from_le_bytes(tcx.def_path_hash(internal).0.to_le_bytes());
                if let Some(collector) = &mut collector {
                    if let Err(error) = collector.generic(
                        tcx,
                        internal,
                        format!("mir:{unit}:{identity:032x}"),
                        name,
                        body,
                    ) {
                        collection_error = Some(error.to_string());
                        break;
                    }
                    continue;
                }
                records.push(Fact {
                    id: format!("mir:{unit}:{identity:032x}"),
                    symbol: name.clone(),
                    kind: "mir_owner".into(),
                    behavior: behavior_requested.then(|| behavior::owner(tcx, internal, &body)),
                    payload: projection::owner(tcx, name, body),
                });
            }
        }
        if collection_error.is_none()
            && let Some(collector) = &mut collector
            && let Err(error) = collector.finish(tcx)
        {
            collection_error = Some(error.to_string());
        }
        collected = collector.map(instances::Collector::into_owned);
        std::ops::ControlFlow::<(), ()>::Continue(())
    });
    if let Err(error) = result {
        invocation.retain(false, "failed")?;
        return Err(format!("compiler/extraction failure: {error:?}").into());
    }
    if let Some(error) = collection_error {
        invocation.retain(false, "failed")?;
        return Err(format!("instance collection failed: {error}").into());
    }
    records.sort_by(|a, b| a.id.cmp(&b.id));
    if let Some(collector) = &mut collected {
        collector.records.sort_by(|a, b| a.id.cmp(&b.id));
    }
    let count = collected
        .as_ref()
        .map_or(records.len(), |value| value.records.len());
    let temporary = directory.join(format!("{unit}.partial"));
    let file = fs::File::create(&temporary)?;
    let mut header = serde_json::json!({"request_id":unit,"input_digest":digest(context.as_bytes()),"expected_records":count,"schema":if let Some(options) = &options {options.schema()} else if behavior_requested {"library-guides.mir-execution.v1"} else {"library-guides.mir.v1"},"producer":"rustc-public-8fa1c96c","context":context,"argv":&args[1..],"phase":if options.is_some() {"generic_and_observed_concrete_instances"} else {"rustc_public_definition_body"},"sysroot":env!("LIBRARY_GUIDES_BUILD_SYSROOT")});
    if let Some(options) = &options {
        header["instance_options"] = serde_json::to_value(options)?;
    }
    let mut stream = Stream::new(file, header)?;
    for record in records {
        stream.record(record)?;
    }
    if let Some(mut collector) = collected {
        let coverage = serde_json::json!({"state":"complete","owners":count,"generic_owners":count-collector.captured,"instance_attempts":collector.attempted,"captured_instances":collector.captured,"instance_options":collector.options,"empty_reason":if count==0 {Some("selected compiler unit exposes no body-bearing items")}else{None},"semantic_closed":false,"body":"generic_and_observed_item_instances","monomorphized":"finite_observed_selection","effect_model":"local_mir_events_with_frontiers"});
        for record in collector.records {
            if collector.options.lifecycle_uses {
                let references = collector
                    .references
                    .remove(&record.id)
                    .ok_or("missing function-reference denominator")?;
                let uses = collector
                    .lifecycles
                    .remove(&record.id)
                    .ok_or("missing lifecycle denominator")?;
                let fact = lifecycle::Fact::new(record, references, uses);
                if collector.options.constant_memory {
                    let memory = collector
                        .memories
                        .remove(&fact.id)
                        .ok_or("missing constant memory denominator")?;
                    stream.record(memory::Fact::new(fact, memory))?;
                } else {
                    stream.record(fact)?;
                }
            } else if collector.options.callable_references {
                let references = collector
                    .references
                    .remove(&record.id)
                    .ok_or("missing function-reference denominator")?;
                stream.record(callables::Fact::new(record, references))?;
            } else {
                stream.record(record)?;
            }
        }
        stream.finish(coverage)?;
    } else {
        stream.finish(serde_json::json!({"state":"complete","owners":count,"empty_reason":if count==0 {Some("selected compiler unit exposes no body-bearing items")}else{None},"semantic_closed":false,"body":"generic_definition","monomorphized":"not_requested","effect_model":"local_mir_events_with_frontiers"}))?;
    }
    fs::rename(temporary, directory.join(format!("{unit}.frames")))?;
    invocation.retain(true, "complete")?;
    Ok(())
}
fn main() -> ExitCode {
    let args: Vec<_> = env::args().collect();
    if args.get(1).is_some_and(|x| x == "toolchain") {
        println!(
            "{}",
            serde_json::json!({"sysroot":env!("LIBRARY_GUIDES_BUILD_SYSROOT"),"compiler_commit":"8fa1c96cfd489e4c27654c144ae871ce2c4db6c6"})
        );
        return ExitCode::SUCCESS;
    }
    if args.get(1).is_some_and(|x| x == "normalize") {
        let result = (|| -> Result<(), Box<dyn std::error::Error>> {
            let input = args.get(2).ok_or("normalize requires input")?;
            let request = args.get(3).ok_or("normalize requires request")?;
            let digest = library_guides_protocol::digest_reader(fs::File::open(input)?)?;
            library_guides_protocol::replay::<WireFact>(
                fs::File::open(input)?,
                io::stdout().lock(),
                request,
                &digest,
            )
        })();
        return match result {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if let Ok(real) = env::var("LIBRARY_GUIDES_RUSTDOC_REAL") {
        let argv = std::iter::once(real)
            .chain(args[1..].iter().cloned())
            .collect();
        return match invocation::delegate(
            argv,
            "documentation",
            "documented_present_not_body_evidence",
        ) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if args.get(1).is_some_and(|x| x == "schema") {
        return match serde_json::to_writer(io::stdout().lock(), &schemars::schema_for!(Fact)) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if args.get(1).is_some_and(|x| x == "instance-schema") {
        return match serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(instances::Fact),
        ) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if args.get(1).is_some_and(|x| x == "callable-schema") {
        return match serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(callables::Fact),
        ) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if args.get(1).is_some_and(|x| x == "lifecycle-schema") {
        return match serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(lifecycle::Fact),
        ) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    if args.get(1).is_some_and(|x| x == "memory-schema") {
        return match serde_json::to_writer(
            io::stdout().lock(),
            &schemars::schema_for!(memory::Fact),
        ) {
            Ok(()) => ExitCode::SUCCESS,
            Err(error) => {
                eprintln!("{error}");
                ExitCode::FAILURE
            }
        };
    }
    match wrapper(args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}

//! Exact compiler/rustdoc process observations, separate from body extraction.
use library_guides_protocol::digest;
use serde::Serialize;
use std::{collections::BTreeMap, env, fs, path::PathBuf, process::Command};

#[derive(Serialize)]
pub struct Invocation {
    pub id: String,
    pub context: String,
    pub purpose: String,
    pub argv: Vec<String>,
    pub environment: BTreeMap<String, String>,
    pub inputs: BTreeMap<String, String>,
    pub compiler_digest: String,
    pub source_observation: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub execution_context: Option<ExecutionContext>,
}

#[derive(Serialize)]
pub struct ExecutionContext {
    pub working_directory: String,
    pub schema: String,
    pub provider_digest: String,
    pub selected_packages: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub instance_options: Option<crate::instances::Options>,
}
impl Invocation {
    pub fn new(argv: Vec<String>, purpose: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let context = env::var("LIBRARY_GUIDES_MIR_CONTEXT")?;
        let environment = env::vars()
            .filter(|(key, _)| {
                key.starts_with("CARGO_PKG_")
                    || key.starts_with("CARGO_FEATURE_")
                    || matches!(
                        key.as_str(),
                        "CARGO_MANIFEST_DIR"
                            | "OUT_DIR"
                            | "OPT_LEVEL"
                            | "DEBUG"
                            | "PROFILE"
                            | "HOST"
                            | "TARGET"
                            | "CARGO_PRIMARY_PACKAGE"
                    )
            })
            .collect::<BTreeMap<_, _>>();
        let mut inputs = BTreeMap::new();
        for arg in &argv[1..] {
            let path = arg.strip_prefix('@').unwrap_or(arg);
            if (arg.starts_with('@') || arg.ends_with(".rs")) && PathBuf::from(path).is_file() {
                inputs.insert(path.to_string(), digest(&fs::read(path)?));
            }
        }
        let compiler_digest = digest(&fs::read(&argv[0])?);
        let legacy_id = digest(&serde_json::to_vec(&(
            &context,
            purpose,
            &argv,
            &environment,
            &inputs,
            &compiler_digest,
        ))?);
        let instance_options = crate::instances::Options::read()?;
        let execution_context =
            if env::var("LIBRARY_GUIDES_MIR_BEHAVIOR").is_ok_and(|value| value == "1") {
                Some(ExecutionContext {
                    working_directory: env::current_dir()?.to_string_lossy().into_owned(),
                    schema: if let Some(options) = &instance_options {
                        options.schema()
                    } else {
                        "library-guides.mir-execution.v1"
                    }
                    .into(),
                    provider_digest: library_guides_protocol::digest_reader(fs::File::open(
                        env::current_exe()?,
                    )?)?,
                    selected_packages: env::var("LIBRARY_GUIDES_MIR_PACKAGES").ok(),
                    instance_options,
                })
            } else {
                None
            };
        let id = match &execution_context {
            Some(execution) => digest(&serde_json::to_vec(&(&legacy_id, execution))?),
            None => legacy_id,
        };
        Ok(Self {id,context,purpose:purpose.into(),argv,environment,inputs,compiler_digest,execution_context,source_observation:"primary input/response files only; module/include/generated closure requires source snapshots and unit reconciliation".into()})
    }
    pub fn retain(&self, success: bool, state: &str) -> Result<(), Box<dyn std::error::Error>> {
        let directory = PathBuf::from(env::var("LIBRARY_GUIDES_MIR_OUTPUT")?);
        fs::create_dir_all(&directory)?;
        let path = directory.join(format!("{}.invocation.json", self.id));
        let temporary = directory.join(format!("{}.invocation.partial", self.id));
        fs::write(
            &temporary,
            serde_json::to_vec(
                &serde_json::json!({"invocation":self,"success":success,"extraction":state}),
            )?,
        )?;
        fs::rename(temporary, path)?;
        Ok(())
    }
}
pub fn delegate(
    argv: Vec<String>,
    purpose: &str,
    state: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let invocation = Invocation::new(argv, purpose)?;
    let status = Command::new(&invocation.argv[0])
        .args(&invocation.argv[1..])
        .status()?;
    invocation.retain(status.success(), state)?;
    if !status.success() {
        return Err(format!("{purpose} failed: {status}").into());
    }
    Ok(())
}

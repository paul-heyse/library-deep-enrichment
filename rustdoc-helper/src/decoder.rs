//! Version dispatch before semantic normalization; no whole-document Value.
use crate::contract;
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, fs::File, io::BufReader, path::Path};

type Error = Box<dyn std::error::Error>;

#[derive(Deserialize)]
struct Header {
    format_version: u32,
}

pub struct Document {
    pub format: u32,
    pub root: contract::Id,
    pub version: Option<String>,
    pub includes_private: bool,
    pub target: contract::Target,
    pub index: BTreeMap<contract::Id, contract::Item>,
    pub paths: BTreeMap<contract::Id, contract::ItemSummary>,
    pub external: BTreeMap<u32, ExternalCrate>,
}

#[derive(Serialize, Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ExternalCrate {
    pub name: String,
    pub html_root_url: Option<String>,
    pub path: Option<std::path::PathBuf>,
}

fn owned<T: Serialize, U: serde::de::DeserializeOwned>(value: &T) -> Result<U, Error> {
    // One bounded item at a time. No compiler-owned type crosses the wire.
    Ok(serde_json::from_slice(&serde_json::to_vec(value)?)?)
}

fn owned_item<T: Serialize>(value: &T, format: u32) -> Result<contract::Item, Error> {
    if !matches!(format, 59 | 60) {
        return owned(value);
    }
    // Formats 59/60 flatten StabilityLevel into the stability object. The owned
    // wire contract follows format 61's nested enum; retain its feature and since
    // fields explicitly instead of treating populated old metadata as unsupported.
    let mut item = serde_json::to_value(value)?;
    for field in ["stability", "const_stability"] {
        if let Some(serde_json::Value::Object(stability)) = item.get_mut(field)
            && stability.get("level").and_then(serde_json::Value::as_str) == Some("stable")
        {
            let since = stability.remove("since").unwrap_or(serde_json::Value::Null);
            stability.insert(
                "level".into(),
                serde_json::json!({"stable": {"since": since}}),
            );
        }
    }
    Ok(serde_json::from_value(item)?)
}

macro_rules! decode {
    ($name:ident, $engine:ident) => {
        fn $name(path: &Path) -> Result<Document, Error> {
            let source: $engine::Crate =
                serde_json::from_reader(BufReader::new(File::open(path)?))?;
            let index = source
                .index
                .into_iter()
                .map(|(id, item)| {
                    Ok((
                        contract::Id(id.0),
                        owned_item(&item, source.format_version)?,
                    ))
                })
                .collect::<Result<_, Error>>()?;
            let paths = source
                .paths
                .into_iter()
                .map(|(id, item)| Ok((contract::Id(id.0), owned(&item)?)))
                .collect::<Result<_, Error>>()?;
            Ok(Document {
                format: source.format_version,
                root: contract::Id(source.root.0),
                version: source.crate_version,
                includes_private: source.includes_private,
                target: owned(&source.target)?,
                index,
                paths,
                external: source
                    .external_crates
                    .into_iter()
                    .map(|(id, item)| Ok((id, owned(&item)?)))
                    .collect::<Result<_, Error>>()?,
            })
        }
    };
}
decode!(v57, rustdoc_types_57);
decode!(v59, rustdoc_types_59);
decode!(v60, rustdoc_types_60);
decode!(v61, rustdoc_types_61);

pub fn read(path: &Path) -> Result<Document, Error> {
    let header: Header = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    match header.format_version {
        57 => v57(path),
        59 => v59(path),
        60 => v60(path),
        61 => v61(path),
        version => {
            Err(format!("unsupported rustdoc format {version}; supported: 57,59,60,61").into())
        }
    }
}

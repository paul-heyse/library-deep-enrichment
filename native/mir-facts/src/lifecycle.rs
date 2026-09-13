//! Exact compiler drop uses and closure environments, separate from public protocol meaning.
use crate::{behavior, callables, instances, projection};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

pub const SCHEMA: &str = "library-guides.mir-lifecycle.v1";

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct DropUse {
    pub block: usize,
    pub place: projection::Location,
    pub ty: projection::Type,
    pub target: Option<instances::Identity>,
    pub selection: instances::CallUse,
    pub empty_shim: Option<bool>,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Closure {
    pub block: usize,
    pub statement: usize,
    pub definition: String,
    pub substitutions: Vec<behavior::Argument>,
    pub captures: usize,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Uses {
    pub spread_arg: Option<usize>,
    pub call_abis: Vec<CallAbi>,
    pub drops: Vec<DropUse>,
    pub closures: Vec<Closure>,
    pub frontier: Vec<String>,
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CallAbi {
    pub block: usize,
    pub abi: Option<String>,
    pub inputs: Vec<projection::Type>,
    pub output: Option<projection::Type>,
}

pub fn call_abi(
    body: &rustc_public::mir::Body,
    block: usize,
    operand: &rustc_public::mir::Operand,
) -> CallAbi {
    let signature = operand
        .ty(body.locals())
        .ok()
        .and_then(|ty| ty.kind().fn_sig());
    match signature {
        Some(signature) => CallAbi {
            block,
            abi: Some(format!("{:?}", signature.value.abi)),
            inputs: signature
                .value
                .inputs()
                .iter()
                .map(|ty| projection::behavior_type(*ty))
                .collect(),
            output: Some(projection::behavior_type(signature.value.output())),
        },
        None => CallAbi {
            block,
            abi: None,
            inputs: vec![],
            output: None,
        },
    }
}

#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Fact {
    pub id: String,
    pub symbol: String,
    pub kind: String,
    pub payload: projection::Owner,
    pub behavior: behavior::Owner,
    pub execution: instances::Execution,
    pub callables: Vec<callables::Reference>,
    pub lifecycle: Uses,
}
impl Fact {
    pub fn new(
        record: instances::Fact,
        callables: Vec<callables::Reference>,
        lifecycle: Uses,
    ) -> Self {
        Self {
            id: record.id,
            symbol: record.symbol,
            kind: record.kind,
            payload: record.payload,
            behavior: record.behavior,
            execution: record.execution,
            callables,
            lifecycle,
        }
    }
}

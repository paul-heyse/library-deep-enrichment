//! Owned function-item operands at exact projected positions, not address/name guesses.
use crate::{behavior, instances, projection};
use rustc_public::mir::{
    Body, CastKind, Operand, PointerCoercion, Rvalue, StatementKind, TerminatorKind,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

pub const SCHEMA: &str = "library-guides.mir-callables.v1";
pub const MAX_REFERENCES: usize = 100_000;

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Point {
    pub block: usize,
    pub statement: Option<usize>,
    pub role: String,
    pub operand: usize,
}
#[derive(Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Reference {
    pub point: Point,
    pub call: behavior::Call,
    pub selection: instances::CallUse,
    pub pointer_coercion: bool,
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
    pub callables: Vec<Reference>,
}
impl Fact {
    pub fn new(record: instances::Fact, callables: Vec<Reference>) -> Self {
        Self {
            id: record.id,
            symbol: record.symbol,
            kind: record.kind,
            payload: record.payload,
            behavior: record.behavior,
            execution: record.execution,
            callables,
        }
    }
}

pub fn operands(body: &Body) -> Vec<(Point, &Operand, bool)> {
    let mut result = Vec::new();
    for (block, basic) in body.blocks.iter().enumerate() {
        for (statement, item) in basic.statements.iter().enumerate() {
            let StatementKind::Assign(_, value) = &item.kind else {
                continue;
            };
            let values: Vec<&Operand> = match value {
                Rvalue::Use(value, _) | Rvalue::UnaryOp(_, value) | Rvalue::Cast(_, value, _) => {
                    vec![value]
                }
                Rvalue::BinaryOp(_, left, right) | Rvalue::CheckedBinaryOp(_, left, right) => {
                    vec![left, right]
                }
                Rvalue::Aggregate(_, values) => values.iter().collect(),
                _ => vec![],
            };
            let coercion = matches!(
                value,
                Rvalue::Cast(
                    CastKind::PointerCoercion(PointerCoercion::ReifyFnPointer(_)),
                    _,
                    _
                )
            );
            result.extend(values.into_iter().enumerate().map(|(operand, value)| {
                (
                    Point {
                        block,
                        statement: Some(statement),
                        role: "event_value".into(),
                        operand,
                    },
                    value,
                    coercion,
                )
            }));
        }
        if let TerminatorKind::Call { func, args, .. } = &basic.terminator.kind {
            result.push((
                Point {
                    block,
                    statement: None,
                    role: "callee".into(),
                    operand: 0,
                },
                func,
                false,
            ));
            result.extend(args.iter().enumerate().map(|(operand, value)| {
                (
                    Point {
                        block,
                        statement: None,
                        role: "call_argument".into(),
                        operand,
                    },
                    value,
                    false,
                )
            }));
        }
    }
    result
}

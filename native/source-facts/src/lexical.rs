//! Observe Ruff's populated upstream traversal instead of imitating its scope rules.
use ruff_python_ast::{
    Expr, PythonVersion, Stmt,
    visitor::{Visitor, walk_expr},
};
use ruff_python_semantic::{BindingKind, SemanticModel};
use ruff_text_size::Ranged;
use schemars::JsonSchema;
use serde::Serialize;
use std::path::Path;
#[derive(Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Lexical {
    pub name: String,
    pub event: String,
    pub start: usize,
    pub end: usize,
    pub target: Option<String>,
    pub scope: String,
    pub binding: Option<String>,
    pub typing_only: Option<bool>,
    pub resolution: String,
}
fn kind(value: &BindingKind<'_>) -> &'static str {
    match value {
        BindingKind::Annotation => "annotation",
        BindingKind::Argument => "argument",
        BindingKind::NamedExprAssignment => "named_expression",
        BindingKind::Assignment => "assignment",
        BindingKind::TypeParam => "type_parameter",
        BindingKind::LoopVar => "loop",
        BindingKind::WithItemVar => "with",
        BindingKind::Global(_) => "global",
        BindingKind::Nonlocal(..) => "nonlocal",
        BindingKind::Builtin => "builtin",
        BindingKind::ClassDefinition(_) => "class",
        BindingKind::FunctionDefinition(_) => "function",
        BindingKind::Export(_) => "export",
        BindingKind::FutureImport => "future_import",
        BindingKind::Import(_) => "import",
        BindingKind::FromImport(_) => "from_import",
        BindingKind::SubmoduleImport(_) => "submodule_import",
        BindingKind::Deletion => "deletion",
        BindingKind::BoundException => "bound_exception",
        BindingKind::UnboundException(_) => "unbound_exception",
        BindingKind::DunderClassCell => "class_cell",
    }
}
struct Calls<'model, 'ast> {
    model: &'model SemanticModel<'ast>,
    rows: Vec<Lexical>,
}
pub struct Projection {
    pub lexical: Vec<Lexical>,
    pub execution: Vec<crate::execution::Node>,
}
impl<'ast> Visitor<'ast> for Calls<'_, 'ast> {
    fn visit_expr(&mut self, expr: &'ast Expr) {
        if let Expr::Call(call) = expr {
            let target = self
                .model
                .resolve_qualified_name(&call.func)
                .map(|name| name.to_string());
            self.rows.push(Lexical {
                name: target.clone().unwrap_or_default(),
                event: "callee_expression".into(),
                start: call.func.start().to_usize(),
                end: call.func.end().to_usize(),
                target,
                scope: "callsite".into(),
                binding: None,
                typing_only: None,
                resolution: "lexical_not_runtime_dispatch".into(),
            });
        }
        walk_expr(self, expr);
    }
}
pub fn extract(
    source: &str,
    path: &Path,
    minor: u8,
    execution: bool,
) -> Result<Projection, String> {
    let version = match minor {
        9 => PythonVersion::PY39,
        10 => PythonVersion::PY310,
        11 => PythonVersion::PY311,
        12 => PythonVersion::PY312,
        13 => PythonVersion::PY313,
        14 => PythonVersion::PY314,
        _ => return Err("unsupported Python target version".into()),
    };
    ruff_linter::library_guides_semantic(source, path, version, |model, body: &[Stmt]| {
        let mut rows = Vec::new();
        for (id, binding) in model.bindings.iter_enumerated() {
            let target = match &binding.kind {
                BindingKind::Import(x) => Some(x.qualified_name.to_string()),
                BindingKind::FromImport(x) => Some(x.qualified_name.to_string()),
                BindingKind::SubmoduleImport(x) => Some(x.qualified_name.to_string()),
                _ => None,
            };
            rows.push(Lexical {
                name: binding.name(source).to_string(),
                event: kind(&binding.kind).into(),
                start: binding.start().to_usize(),
                end: binding.end().to_usize(),
                target,
                scope: format!("{:?}", binding.scope),
                binding: Some(format!("{id:?}")),
                typing_only: Some(binding.context.is_typing()),
                resolution: "lexical_binding".into(),
            });
            for reference in binding.references() {
                let reference = model.reference(reference);
                rows.push(Lexical {
                    name: source[reference.range()].into(),
                    event: if reference.is_load() {
                        "load"
                    } else {
                        "non_load_reference"
                    }
                    .into(),
                    start: reference.start().to_usize(),
                    end: reference.end().to_usize(),
                    target: None,
                    scope: format!("{:?}", reference.scope_id()),
                    binding: Some(format!("{id:?}")),
                    typing_only: Some(reference.in_typing_context()),
                    resolution: "lexical_resolved".into(),
                });
            }
        }
        for reference in model.unresolved_references() {
            rows.push(Lexical {
                name: reference.name(source).into(),
                event: "unresolved_reference".into(),
                start: reference.range().start().to_usize(),
                end: reference.range().end().to_usize(),
                target: None,
                scope: "unresolved".into(),
                binding: None,
                typing_only: None,
                resolution: "unresolved".into(),
            });
        }
        let mut calls = Calls { model, rows };
        for stmt in body {
            calls.visit_stmt(stmt);
        }
        Projection {
            lexical: calls.rows,
            execution: if execution {
                body.iter().map(crate::execution::statement).collect()
            } else {
                Vec::new()
            },
        }
    })
}

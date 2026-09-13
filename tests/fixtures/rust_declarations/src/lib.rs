//! Deliberate declaration contracts for normalization, profiles and public routes.
#![feature(negative_impls)]

mod private {
    /// A schema carries its explicit field count.
    #[derive(Clone)]
    pub struct Schema {
        /// The declared field count; this is not a row count.
        pub fields: usize,
    }

    impl Schema {
        /// Construct a schema with the supplied field count.
        pub const fn new(fields: usize) -> Self { Self { fields } }
        /// Inspect a schema without consuming it.
        pub fn count(&self) -> usize { self.fields }
    }
}

pub use private::Schema;
pub use private::Schema as Layout;
pub mod facade { pub use crate::Schema; }

/// Consumers implement one required method; description has a default.
pub trait Consumer<T: Clone> {
    type Output;
    const LIMIT: usize = 4;
    fn consume(&mut self, value: T) -> Self::Output;
    fn description(&self) -> &'static str { "consumer" }
}

pub struct Holder<T>(pub T);
impl<T: Clone> Consumer<T> for Holder<T> {
    type Output = T;
    fn consume(&mut self, value: T) -> T { value }
}

pub struct LocalOnly;
impl !Send for LocalOnly {}

pub enum Choice<T> { Empty, Pair(T, usize), Named { value: T } }
pub union Bits { pub unsigned: u32, pub signed: i32 }
pub type Names<'a> = &'a [&'a str];
pub const DEFAULT_FIELDS: usize = 3;
pub static LABEL: &str = "fixture";

/// The declared return is Result; a schema occurs in its success parameter.
pub fn try_schema(fields: usize) -> Result<Schema, &'static str> {
    if fields == 0 { Err("empty") } else { Ok(Schema::new(fields)) }
}
pub fn callback(run: for<'a> fn(&'a Schema) -> usize, schema: &Schema) -> usize { run(schema) }
pub unsafe extern "C" fn pointer(value: *const u8) -> *const u8 { value }
pub fn array<const N: usize>(values: [u8; N]) -> [u8; N] { values }
pub async fn asynchronously(schema: Schema) -> Schema { schema }
pub fn opaque() -> impl Iterator<Item = u8> { [1, 2].into_iter() }
pub trait Label { fn description(&self) -> &'static str; }
pub fn dynamic(consumer: &dyn Label) -> &'static str { consumer.description() }
#[cfg(feature = "fast")]
pub fn fast_only() {}
#[cfg(doc)]
pub fn documentation_only() {}
#[doc(hidden)]
pub fn hidden_contract() {}

/// Run a small schema construction.
///
/// ```
/// use reference_fixture::Schema;
/// # let fields = 2;
/// assert_eq!(Schema::new(fields).count(), fields);
/// ```
pub fn example_anchor() {}

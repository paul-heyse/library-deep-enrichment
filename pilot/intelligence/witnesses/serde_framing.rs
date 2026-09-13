use serde::Deserialize;
use serde_json::Value;
use std::io::{self, Read};

// A finite nonblocking IO fixture: one complete object is available, but EOF
// has not occurred. WouldBlock is a negative control, not a real socket probe.
struct RemainsOpen { remaining: &'static [u8] }
impl Read for RemainsOpen {
    fn read(&mut self, output: &mut [u8]) -> io::Result<usize> {
        if self.remaining.is_empty() {
            return Err(io::Error::from(io::ErrorKind::WouldBlock));
        }
        let size = output.len().min(self.remaining.len());
        output[..size].copy_from_slice(&self.remaining[..size]);
        self.remaining = &self.remaining[size..];
        Ok(size)
    }
}

fn main() {
    let whole_document = serde_json::from_reader::<_, Value>(RemainsOpen { remaining: b"{}" });
    assert!(whole_document.is_err());
    let mut decoder = serde_json::Deserializer::from_reader(RemainsOpen { remaining: b"{}" });
    let prefix = Value::deserialize(&mut decoder).expect("one object is available before EOF");
    assert_eq!(prefix, serde_json::json!({}));
    let text: Value = serde_json::from_str("{}").unwrap();
    assert_eq!(prefix, text);
    println!("{{\"environment\":{{\"serde\":\"1.0.228\",\"serde_json\":\"1.0.151\"}},\"whole_document_before_eof\":false,\"prefix_before_eof\":true}}");
}

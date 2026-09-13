//! Length-prefixed, digest-committed extraction transport.
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::io::{self, Read, Write};

pub struct Stream<W: Write> {
    output: W,
    digest: Sha256,
    records: usize,
}

impl<W: Write> Stream<W> {
    pub fn new(output: W, header: impl Serialize) -> io::Result<Self> {
        let mut stream = Self {
            output,
            digest: Sha256::new(),
            records: 0,
        };
        stream.frame(&serde_json::json!({"kind":"header", "protocol":"library-guides.facts.v1", "header":header}))?;
        Ok(stream)
    }

    fn frame(&mut self, value: &impl Serialize) -> io::Result<Vec<u8>> {
        let bytes = serde_json::to_vec(value).map_err(io::Error::other)?;
        if bytes.len() > 32_000_000 {
            return Err(io::Error::other("record exceeds protocol frame budget"));
        }
        let size = u32::try_from(bytes.len()).map_err(io::Error::other)?;
        self.output.write_all(&size.to_be_bytes())?;
        self.output.write_all(&bytes)?;
        Ok(bytes)
    }

    pub fn record(&mut self, record: impl Serialize) -> io::Result<()> {
        let bytes = self.frame(
            &serde_json::json!({"kind":"record", "sequence":self.records, "record":record}),
        )?;
        self.digest.update((bytes.len() as u64).to_be_bytes());
        self.digest.update(bytes);
        self.records += 1;
        Ok(())
    }

    pub fn finish(mut self, coverage: impl Serialize) -> io::Result<()> {
        let digest = format!("{:x}", self.digest.clone().finalize());
        self.frame(&serde_json::json!({"kind":"terminal", "records":self.records, "digest":digest, "coverage":coverage}))?;
        self.output.flush()
    }
}

pub fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

pub fn digest_reader(mut input: impl Read) -> io::Result<String> {
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let count = input.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

#[derive(serde::Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Frame<T> {
    Header {
        protocol: String,
        header: serde_json::Value,
    },
    Record {
        sequence: usize,
        record: T,
    },
    Terminal {
        records: usize,
        digest: String,
        coverage: serde_json::Value,
    },
}

/// Revalidate a persisted unit stream while projecting only the owned record type.
pub fn replay<T: serde::de::DeserializeOwned + Serialize>(
    mut input: impl Read,
    output: impl Write,
    request: &str,
    input_digest: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut output = Some(output);
    let mut stream = None;
    let mut original_header = None;
    let mut count = 0;
    let mut hash = Sha256::new();
    let mut terminal = false;
    loop {
        let mut prefix = [0u8; 4];
        if input.read(&mut prefix[..1])? == 0 {
            break;
        }
        input.read_exact(&mut prefix[1..])?;
        if terminal {
            return Err("data after terminal".into());
        }
        let length = u32::from_be_bytes(prefix) as usize;
        if !(1..=32_000_000).contains(&length) {
            return Err("unit frame exceeds protocol budget".into());
        }
        let mut bytes = vec![0; length];
        input.read_exact(&mut bytes)?;
        serde_json::from_slice::<UniqueJson>(&bytes)?;
        let frame: Frame<T> = serde_json::from_slice(&bytes)?;
        match frame {
            Frame::Header { protocol, header } => {
                if stream.is_some() || protocol != "library-guides.facts.v1" {
                    return Err("invalid unit handshake".into());
                }
                let mut projection = header.clone();
                projection["original_request"] = header["request_id"].clone();
                projection["request_id"] = request.into();
                projection["input_digest"] = input_digest.into();
                original_header = Some(header);
                stream = Some(Stream::new(
                    output.take().ok_or("duplicate unit header")?,
                    projection,
                )?);
            }
            Frame::Record { sequence, record } => {
                if sequence != count {
                    return Err("unit sequence mismatch".into());
                }
                hash.update((bytes.len() as u64).to_be_bytes());
                hash.update(&bytes);
                count += 1;
                stream
                    .as_mut()
                    .ok_or("unit record before header")?
                    .record(record)?;
            }
            Frame::Terminal {
                records,
                digest,
                coverage,
            } => {
                if records != count
                    || digest != format!("{:x}", hash.clone().finalize())
                    || original_header
                        .as_ref()
                        .and_then(|h| h["expected_records"].as_u64())
                        != Some(count as u64)
                {
                    return Err("invalid unit terminal".into());
                }
                stream
                    .take()
                    .ok_or("unit terminal before header")?
                    .finish(coverage)?;
                terminal = true;
            }
        }
    }
    if !terminal {
        return Err("truncated unit stream".into());
    }
    Ok(())
}

/// Validate all JSON object keys, including open upstream header/coverage maps.
struct UniqueJson;
impl<'de> serde::Deserialize<'de> for UniqueJson {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct Visitor;
        impl<'de> serde::de::Visitor<'de> for Visitor {
            type Value = UniqueJson;
            fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
                formatter.write_str("JSON without repeated object keys")
            }
            fn visit_map<M: serde::de::MapAccess<'de>>(
                self,
                mut map: M,
            ) -> Result<UniqueJson, M::Error> {
                let mut seen = std::collections::BTreeSet::new();
                while let Some(key) = map.next_key::<String>()? {
                    if !seen.insert(key) {
                        return Err(serde::de::Error::custom("duplicate JSON key"));
                    }
                    map.next_value::<UniqueJson>()?;
                }
                Ok(UniqueJson)
            }
            fn visit_seq<S: serde::de::SeqAccess<'de>>(
                self,
                mut seq: S,
            ) -> Result<UniqueJson, S::Error> {
                while seq.next_element::<UniqueJson>()?.is_some() {}
                Ok(UniqueJson)
            }
            fn visit_bool<E: serde::de::Error>(self, _: bool) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_i64<E: serde::de::Error>(self, _: i64) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_u64<E: serde::de::Error>(self, _: u64) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_f64<E: serde::de::Error>(self, _: f64) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_str<E: serde::de::Error>(self, _: &str) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_unit<E: serde::de::Error>(self) -> Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
        }
        deserializer.deserialize_any(Visitor)
    }
}

#[cfg(test)]
mod tests {
    use super::UniqueJson;
    #[test]
    fn duplicate_keys_are_rejected_at_any_depth() {
        assert!(
            serde_json::from_str::<UniqueJson>(r#"{"header":{"profile":"a","profile":"b"}}"#)
                .is_err()
        );
        assert!(serde_json::from_str::<UniqueJson>(r#"[null,true,1,-1,1.5,"x",{"a":2}]"#).is_ok());
    }
}

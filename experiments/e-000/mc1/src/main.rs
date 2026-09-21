use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

const COPY_BLOCK: usize = 8 * 1024 * 1024;
const BLAKE3_CHUNK: usize = 1024;
const EXPECTED_REGISTRY_DIGEST: &str =
    "ebc222cf4b4134a3414494532e35852f704d79367b2d564d71a0a1b13fc655cd";

#[derive(Clone, Debug)]
struct Tensor {
    name: String,
    path: PathBuf,
    sha256: String,
    rows: usize,
    cols: usize,
    bytes: usize,
}

struct HashingSink {
    sha256: Sha256,
    blake3: blake3::Hasher,
    count: usize,
}

impl HashingSink {
    fn new(key: &[u8; 32]) -> Self {
        Self {
            sha256: Sha256::new(),
            blake3: blake3::Hasher::new_keyed(key),
            count: 0,
        }
    }

    fn update(&mut self, bytes: &[u8]) {
        self.sha256.update(bytes);
        self.blake3.update(bytes);
        self.count += bytes.len();
    }

    fn finish(mut self) -> (String, String, usize) {
        let raw_count = self.count;
        let padding = (BLAKE3_CHUNK - self.count % BLAKE3_CHUNK) % BLAKE3_CHUNK;
        if padding != 0 {
            self.blake3.update(&vec![0_u8; padding]);
        }
        (
            encode_hex(&self.sha256.finalize()),
            self.blake3.finalize().to_hex().to_string(),
            raw_count,
        )
    }
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}

fn encode_hex(bytes: &[u8]) -> String {
    const TABLE: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(TABLE[(byte >> 4) as usize] as char);
        output.push(TABLE[(byte & 15) as usize] as char);
    }
    output
}

fn decode_hex(value: &str) -> Result<Vec<u8>, String> {
    require(value.len() % 2 == 0, "hex input has odd length")?;
    value
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let text = std::str::from_utf8(pair).map_err(|_| "invalid UTF-8 hex".to_string())?;
            u8::from_str_radix(text, 16).map_err(|_| format!("invalid hex byte {text:?}"))
        })
        .collect()
}

fn sha256_bytes(bytes: &[u8]) -> String {
    encode_hex(&Sha256::digest(bytes))
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let metadata =
        fs::symlink_metadata(path).map_err(|error| format!("stat {}: {error}", path.display()))?;
    require(
        metadata.is_file() && !metadata.file_type().is_symlink(),
        format!("regular non-symlink file required: {}", path.display()),
    )?;
    let mut source =
        File::open(path).map_err(|error| format!("open {}: {error}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; COPY_BLOCK];
    loop {
        let count = source
            .read(&mut buffer)
            .map_err(|error| format!("read {}: {error}", path.display()))?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(encode_hex(&digest.finalize()))
}

fn load_json(path: &Path) -> Result<Value, String> {
    let bytes = fs::read(path).map_err(|error| format!("read {}: {error}", path.display()))?;
    let value: Value = serde_json::from_slice(&bytes)
        .map_err(|error| format!("decode {}: {error}", path.display()))?;
    require(
        value.is_object(),
        format!("JSON object required: {}", path.display()),
    )?;
    Ok(value)
}

fn prefixed_digest(value: &Value, label: &str) -> Result<String, String> {
    let text = value
        .as_str()
        .ok_or_else(|| format!("{label} must be a string"))?;
    let digest = text
        .strip_prefix("sha256:")
        .ok_or_else(|| format!("{label} lacks sha256 prefix"))?;
    require(
        digest.len() == 64
            && digest
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase()),
        format!("invalid digest for {label}"),
    )?;
    Ok(digest.to_string())
}

fn safe_leaf(value: &str) -> bool {
    !value.is_empty()
        && !value.contains('/')
        && !value.contains('\\')
        && value != "."
        && value != ".."
}

fn load_inventory(roots: &[PathBuf]) -> Result<(BTreeMap<String, Tensor>, Vec<String>), String> {
    let mut tensors = BTreeMap::new();
    let mut receipt_digests = Vec::new();
    for root in roots {
        let receipt_path = root.join("extraction/receipt.json");
        let receipt = load_json(&receipt_path)?;
        require(
            receipt["candidate_inspected"] == Value::Bool(false),
            "candidate-labelled extraction",
        )?;
        require(
            receipt["stream"]["full_digest_verified"] == Value::Bool(true),
            "unverified source stream",
        )?;
        require(
            receipt["stream"]["sha256"] == receipt["stream"]["expected_sha256"],
            "source stream digest mismatch",
        )?;
        require(
            receipt["trust"]["tier"] == "T0",
            "extraction must remain T0",
        )?;
        receipt_digests.push(sha256_file(&receipt_path)?);
        let items = receipt["same_stream_extractions"]
            .as_array()
            .ok_or("extraction list absent")?;
        for item in items {
            let name = item["name"]
                .as_str()
                .ok_or("tensor name absent")?
                .to_string();
            let relative = item["path"].as_str().ok_or("tensor path absent")?;
            require(
                !tensors.contains_key(&name),
                format!("duplicate tensor: {name}"),
            )?;
            require(
                safe_leaf(relative) && relative == format!("{name}.i8"),
                format!("unsafe tensor path: {relative}"),
            )?;
            require(item["dtype"] == "I8", format!("non-I8 tensor: {name}"))?;
            let shape = item["shape"].as_array().ok_or("tensor shape absent")?;
            require(shape.len() == 2, format!("invalid tensor shape: {name}"))?;
            let rows = shape[0].as_u64().ok_or("invalid tensor rows")? as usize;
            let cols = shape[1].as_u64().ok_or("invalid tensor cols")? as usize;
            let bytes = rows
                .checked_mul(cols)
                .ok_or("tensor byte length overflow")?;
            require(
                item["bytes"].as_u64() == Some(bytes as u64),
                format!("tensor length descriptor differs: {name}"),
            )?;
            let path = root.join("extraction").join(relative);
            let metadata = fs::symlink_metadata(&path)
                .map_err(|error| format!("stat tensor {name}: {error}"))?;
            require(
                metadata.is_file()
                    && !metadata.file_type().is_symlink()
                    && metadata.len() == bytes as u64,
                format!("tensor file boundary differs: {name}"),
            )?;
            let sha256 = item["sha256"]
                .as_str()
                .ok_or("tensor digest absent")?
                .to_string();
            tensors.insert(
                name.clone(),
                Tensor {
                    name,
                    path,
                    sha256,
                    rows,
                    cols,
                    bytes,
                },
            );
        }
    }
    receipt_digests.sort();
    Ok((tensors, receipt_digests))
}

fn selected_slabs(registry: &Value, prereg: &Value) -> Result<Vec<Value>, String> {
    require(
        registry["candidate_inspected"] == Value::Bool(false),
        "candidate-labelled registry",
    )?;
    require(
        registry["candidate_keyed_roots_computed"] == Value::Bool(false),
        "candidate roots present",
    )?;
    let slabs = registry["slabs"]
        .as_array()
        .ok_or("registry slabs absent")?;
    let mut sorted = slabs.clone();
    sorted.sort_by_key(|record| record["slab_id"].as_str().unwrap_or_default().to_string());
    let mut groups = BTreeMap::<(String, usize, usize), Value>::new();
    for record in sorted {
        let family = record["family"]
            .as_str()
            .ok_or("slab family absent")?
            .to_string();
        let shape = record["shape_n_k"].as_array().ok_or("slab shape absent")?;
        require(shape.len() == 2, "slab shape length differs")?;
        let n = shape[0].as_u64().ok_or("invalid slab n")? as usize;
        let k = shape[1].as_u64().ok_or("invalid slab k")? as usize;
        groups.entry((family, n, k)).or_insert(record);
    }
    let expected = prereg["expected_shape_classes"]
        .as_array()
        .ok_or("expected shape classes absent")?;
    let expected_keys: BTreeSet<(String, usize, usize)> = expected
        .iter()
        .map(|record| {
            let family = record["family"]
                .as_str()
                .ok_or("expected family absent")?
                .to_string();
            let shape = record["shape_n_k"]
                .as_array()
                .ok_or("expected shape absent")?;
            Ok((
                family,
                shape[0].as_u64().ok_or("invalid expected n")? as usize,
                shape[1].as_u64().ok_or("invalid expected k")? as usize,
            ))
        })
        .collect::<Result<_, String>>()?;
    require(
        groups.keys().cloned().collect::<BTreeSet<_>>() == expected_keys,
        "shape-class universe differs",
    )?;
    require(groups.len() == 15, "selected slab count differs from 15")?;
    Ok(groups.into_values().collect())
}

fn parse_two_digits(value: &str, prefix: &str) -> Result<usize, String> {
    value
        .strip_prefix(prefix)
        .ok_or_else(|| format!("identity component lacks {prefix}"))?
        .parse::<usize>()
        .map_err(|error| format!("invalid identity component {value}: {error}"))
}

fn parse_slab(record: &Value) -> Result<(usize, String, usize, usize), String> {
    let identity = record["slab_id"].as_str().ok_or("slab identity absent")?;
    let parts: Vec<&str> = identity.split(':').collect();
    require(
        parts.len() == 4,
        format!("invalid slab identity: {identity}"),
    )?;
    let layer = parse_two_digits(parts[0], "layer-")?;
    let family = parts[1].to_string();
    require(
        matches!(family.as_str(), "gate_up_proj" | "o_proj" | "qkv_proj")
            && record["family"] == family,
        "slab family identity mismatch",
    )?;
    Ok((
        layer,
        family,
        parse_two_digits(parts[2], "tp-")?,
        parse_two_digits(parts[3], "rank-")?,
    ))
}

fn verify_tensor(tensor: &Tensor, cache: &mut BTreeSet<String>) -> Result<(), String> {
    if cache.insert(tensor.name.clone()) {
        require(
            sha256_file(&tensor.path)? == tensor.sha256,
            format!("tensor digest mismatch: {}", tensor.name),
        )?;
    }
    Ok(())
}

fn hash_region(
    tensor: &Tensor,
    offset: usize,
    length: usize,
    sink: &mut HashingSink,
) -> Result<(), String> {
    require(
        offset <= tensor.bytes && length <= tensor.bytes - offset,
        format!("tensor region outside {}", tensor.name),
    )?;
    let mut file =
        File::open(&tensor.path).map_err(|error| format!("open {}: {error}", tensor.name))?;
    file.seek(SeekFrom::Start(offset as u64))
        .map_err(|error| format!("seek {}: {error}", tensor.name))?;
    let mut remaining = length;
    let mut buffer = vec![0_u8; COPY_BLOCK.min(length.max(1))];
    while remaining != 0 {
        let want = remaining.min(buffer.len());
        let count = file
            .read(&mut buffer[..want])
            .map_err(|error| format!("read {}: {error}", tensor.name))?;
        require(count != 0, format!("unexpected EOF: {}", tensor.name))?;
        sink.update(&buffer[..count]);
        remaining -= count;
    }
    Ok(())
}

fn tensor<'a>(inventory: &'a BTreeMap<String, Tensor>, name: &str) -> Result<&'a Tensor, String> {
    inventory
        .get(name)
        .ok_or_else(|| format!("tensor absent: {name}"))
}

fn reconstruct(
    record: &Value,
    inventory: &BTreeMap<String, Tensor>,
    sink: &mut HashingSink,
) -> Result<Vec<String>, String> {
    let (layer, family, degree, rank) = parse_slab(record)?;
    let base = format!("model.layers.{layer}");
    let mut used = Vec::new();
    match family.as_str() {
        "gate_up_proj" => {
            require(14336 % degree == 0, "gate/up degree is not divisible")?;
            let local = 14336 / degree;
            for suffix in ["mlp.gate_proj.weight", "mlp.up_proj.weight"] {
                let name = format!("{base}.{suffix}");
                let value = tensor(inventory, &name)?;
                require(
                    (value.rows, value.cols) == (14336, 4096),
                    format!("unexpected shape: {name}"),
                )?;
                hash_region(value, rank * local * 4096, local * 4096, sink)?;
                used.push(name);
            }
        }
        "o_proj" => {
            require(4096 % degree == 0, "o_proj degree is not divisible")?;
            let name = format!("{base}.self_attn.o_proj.weight");
            let value = tensor(inventory, &name)?;
            require(
                (value.rows, value.cols) == (4096, 4096),
                format!("unexpected shape: {name}"),
            )?;
            let local = 4096 / degree;
            let start = rank * local;
            let mut file =
                File::open(&value.path).map_err(|error| format!("open {name}: {error}"))?;
            let mut row = vec![0_u8; local];
            for row_index in 0..4096 {
                file.seek(SeekFrom::Start((row_index * 4096 + start) as u64))
                    .map_err(|error| format!("seek {name}: {error}"))?;
                file.read_exact(&mut row)
                    .map_err(|error| format!("read {name}: {error}"))?;
                sink.update(&row);
            }
            used.push(name);
        }
        "qkv_proj" => {
            require(4096 % degree == 0, "q projection degree is not divisible")?;
            let q_rows = 4096 / degree;
            let (kv_rows, replicas) = if degree >= 8 {
                require(degree % 8 == 0, "KV replica degree differs")?;
                (128, degree / 8)
            } else {
                require(1024 % degree == 0, "KV degree is not divisible")?;
                (1024 / degree, 1)
            };
            let specs = [
                ("q_proj", rank * q_rows, q_rows, 4096),
                ("k_proj", (rank / replicas) * kv_rows, kv_rows, 1024),
                ("v_proj", (rank / replicas) * kv_rows, kv_rows, 1024),
            ];
            for (projection, start, rows, total_rows) in specs {
                let name = format!("{base}.self_attn.{projection}.weight");
                let value = tensor(inventory, &name)?;
                require(
                    (value.rows, value.cols) == (total_rows, 4096),
                    format!("unexpected shape: {name}"),
                )?;
                hash_region(value, start * 4096, rows * 4096, sink)?;
                used.push(name);
            }
        }
        _ => return Err(format!("unsupported family: {family}")),
    }
    Ok(used)
}

fn atomic_write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    require(
        !path.exists(),
        format!("refusing to overwrite {}", path.display()),
    )?;
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent).map_err(|error| format!("create output directory: {error}"))?;
    let temporary = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("output"),
        std::process::id()
    ));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(|error| format!("create temporary output: {error}"))?;
    file.write_all(bytes)
        .and_then(|_| file.sync_all())
        .map_err(|error| format!("write temporary output: {error}"))?;
    drop(file);
    fs::rename(&temporary, path).map_err(|error| format!("publish output: {error}"))
}

fn run() -> Result<Value, String> {
    let arguments: Vec<String> = env::args().skip(1).collect();
    require(
        arguments.len() == 5,
        "usage: aeye-e000-mc1-rust-lane PREREGISTRY REGISTRY BUNDLE_1 BUNDLE_2 OUTPUT",
    )?;
    let prereg_path = PathBuf::from(&arguments[0]);
    let registry_path = PathBuf::from(&arguments[1]);
    let roots = [PathBuf::from(&arguments[2]), PathBuf::from(&arguments[3])];
    let output_path = PathBuf::from(&arguments[4]);
    let prereg = load_json(&prereg_path)?;
    let registry = load_json(&registry_path)?;
    require(
        prereg["status"] == "preregistered_pre_candidate",
        "preregistration state differs",
    )?;
    require(
        prereg["candidate_inspected"] == Value::Bool(false),
        "candidate-labelled preregistration",
    )?;
    let registry_digest = sha256_file(&registry_path)?;
    require(
        registry_digest == EXPECTED_REGISTRY_DIGEST,
        "reviewed registry digest differs from compiled expectation",
    )?;
    require(
        prefixed_digest(
            &prereg["inputs"]["reviewed_rust_registry"],
            "reviewed registry",
        )? == registry_digest,
        "preregistered registry digest differs",
    )?;
    let manifest_digest = prefixed_digest(
        &prereg["inputs"]["reviewed_real_byte_packet_manifest"],
        "reviewed packet manifest",
    )?;
    let domain_hex = prereg["inputs"]["synthetic_key_derivation"]["domain_hex"]
        .as_str()
        .ok_or("synthetic-key domain absent")?;
    let mut preimage = decode_hex(domain_hex)?;
    preimage.extend_from_slice(&decode_hex(&manifest_digest)?);
    let key_vec = Sha256::digest(&preimage).to_vec();
    let key: [u8; 32] = key_vec
        .try_into()
        .map_err(|_| "key length differs".to_string())?;
    require(
        encode_hex(&key) == prereg["inputs"]["synthetic_key_derivation"]["result_hex"],
        "synthetic key derivation differs",
    )?;
    let (inventory, extraction_receipts) = load_inventory(&roots)?;
    let selected = selected_slabs(&registry, &prereg)?;
    let mut verified = BTreeSet::new();
    let mut records = Vec::new();
    for record in selected {
        let mut sink = HashingSink::new(&key);
        let used = reconstruct(&record, &inventory, &mut sink)?;
        for name in &used {
            verify_tensor(tensor(&inventory, name)?, &mut verified)?;
        }
        let (slab_sha256, rust_root, bytes) = sink.finish();
        require(
            record["bytes"].as_u64() == Some(bytes as u64),
            "reconstructed byte count differs",
        )?;
        require(
            record["slab_sha256"] == slab_sha256,
            format!("registry digest mismatch: {}", record["slab_id"]),
        )?;
        records.push(json!({
            "bytes": bytes,
            "family": record["family"],
            "rust_root": rust_root,
            "shape_n_k": record["shape_n_k"],
            "slab_id": record["slab_id"],
            "slab_sha256": slab_sha256,
            "source_tensors": used
        }));
    }
    let signed: [i8; 5] = [-128, -1, 0, 1, 127];
    let unsigned: Vec<u8> = signed.iter().map(|value| *value as u8).collect();
    require(
        unsigned == [128, 255, 0, 1, 127],
        "Rust int8-to-uint8 bit preservation failed",
    )?;
    let result = json!({
        "candidate_inspected": false,
        "claim_ceiling": prereg["claim_ceiling"],
        "controls": {
            "MC1-I8-U8-BIT-PRESERVATION": {
                "signed_values": signed,
                "status": "PASS",
                "unsigned_bytes_hex": encode_hex(&unsigned)
            },
            "MC1-REAL-SLAB-KEYED-ROOT-PARITY": {
                "selected_shape_classes": records.len(),
                "status": "RUST_LANE_COMPLETE"
            }
        },
        "implementation": {
            "blake3_crate_version": "1.8.4",
            "cargo_lock_sha256": sha256_bytes(include_bytes!("../Cargo.lock")),
            "cargo_toml_sha256": sha256_bytes(include_bytes!("../Cargo.toml")),
            "executable_sha256": sha256_file(&std::env::current_exe().map_err(|error| format!("resolve current executable: {error}"))?)?,
            "imports_python_generator": false,
            "imports_semantic_audit": false,
            "language": "Rust",
            "reconstruction_and_hashing_code_path": "owner-rust-mc1-v0",
            "rust_toolchain_sha256": sha256_bytes(include_bytes!("../rust-toolchain.toml")),
            "source_sha256": sha256_bytes(include_bytes!("main.rs"))
        },
        "inputs": {
            "extraction_receipt_sha256": extraction_receipts,
            "preregistration_sha256": format!("sha256:{}", sha256_file(&prereg_path)?),
            "reviewed_registry_sha256": format!("sha256:{registry_digest}")
        },
        "records": records,
        "schema_version": "aeye.private.e000-mc1-rust-result.v0",
        "status": "supported_pre_candidate_calibration",
        "synthetic_key_hex": encode_hex(&key),
        "synthetic_key_is_candidate_job_key": false
    });
    let mut encoded =
        serde_json::to_vec_pretty(&result).map_err(|error| format!("encode output: {error}"))?;
    encoded.push(b'\n');
    atomic_write(&output_path, &encoded)?;
    Ok(json!({
        "candidate_inspected": false,
        "ok": true,
        "output_sha256": sha256_bytes(&encoded),
        "selected_shape_classes": 15
    }))
}

fn main() {
    match run() {
        Ok(value) => println!(
            "{}",
            serde_json::to_string(&value).expect("completion serialization")
        ),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signed_int8_wrap_is_bit_preserving() {
        let signed: [i8; 5] = [-128, -1, 0, 1, 127];
        let unsigned: Vec<u8> = signed.iter().map(|value| *value as u8).collect();
        assert_eq!(unsigned, [128, 255, 0, 1, 127]);
    }

    #[test]
    fn chunk_padding_matches_pearl_rule() {
        for (length, padding) in [(1, 1023), (1023, 1), (1024, 0), (1025, 1023)] {
            assert_eq!(
                (BLAKE3_CHUNK - length % BLAKE3_CHUNK) % BLAKE3_CHUNK,
                padding
            );
        }
    }

    #[test]
    fn synthetic_key_is_frozen() {
        let domain =
            decode_hex("414559452d453030302d4d43312d53594e5448455449432d4b45592d563000").unwrap();
        let manifest =
            decode_hex("ef509fe79c23925aef83f9518d92d6f9b81feba3647c92c22addfa2549bd28b6").unwrap();
        let mut preimage = domain;
        preimage.extend_from_slice(&manifest);
        assert_eq!(
            sha256_bytes(&preimage),
            "4dd34a1010992d93d26f7a80cd6013f523cd67f6f8f3759cc1c50f2aa8d0f779"
        );
    }
}

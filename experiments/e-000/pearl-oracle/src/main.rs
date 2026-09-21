use pearl_blake3::{blake3_digest, pad_to_chunk_boundary, MerkleTree};
use std::env;
use std::fs;
use std::process::ExitCode;
use zk_pow::api::proof::{
    IncompleteBlockHeader, MMAType, MiningConfiguration, PeriodicPattern, PublicProofParams,
};
use zk_pow::api::seed::SeedDerivation;

fn decode_hex(value: &str) -> Result<Vec<u8>, String> {
    if value.len() % 2 != 0 {
        return Err("hex input has odd length".to_string());
    }
    value
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let text = std::str::from_utf8(pair).map_err(|_| "hex input is not UTF-8")?;
            u8::from_str_radix(text, 16).map_err(|_| format!("invalid hex byte {text:?}"))
        })
        .collect()
}

fn encode_hex(value: &[u8]) -> String {
    value.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn decode_hash(value: &str, field: &str) -> Result<[u8; 32], String> {
    decode_hex(value)?
        .try_into()
        .map_err(|bytes: Vec<u8>| format!("{field} must be 32 bytes, got {}", bytes.len()))
}

fn parse_u32(value: &str, field: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .map_err(|error| format!("invalid {field} {value:?}: {error}"))
}

fn noise_seeds(
    derivation: SeedDerivation,
    hash_a: [u8; 32],
    hash_b: [u8; 32],
    m: u32,
    n: u32,
    job_key: [u8; 32],
) -> (Vec<u8>, Vec<u8>) {
    let singleton_pattern = PeriodicPattern {
        shape: [(0, 1), (0, 1), (0, 1)],
    };
    let params = PublicProofParams {
        block_header: IncompleteBlockHeader {
            version: 0,
            prev_block: [0; 32],
            merkle_root: [0; 32],
            timestamp: 0,
            nbits: 0,
        },
        seed_derivation: derivation,
        mining_config: MiningConfiguration {
            common_dim: 1,
            rank: 1,
            mma_type: MMAType::Int7xInt7ToInt32,
            rows_pattern: singleton_pattern,
            cols_pattern: singleton_pattern,
            moe: None,
        },
        hash_a,
        hash_b,
        hash_jackpot: [0; 32],
        m,
        n,
        t_rows: 0,
        t_cols: 0,
        moe: None,
    };
    let (b_noise_seed, a_noise_seed) = params.commitment_hash(job_key);
    (b_noise_seed.to_vec(), a_noise_seed.to_vec())
}

fn run() -> Result<String, String> {
    let arguments: Vec<String> = env::args().collect();
    match arguments.as_slice() {
        [_, mode, header_path, config_path] if mode == "job-key" => {
            let header = fs::read(header_path).map_err(|error| format!("read header: {error}"))?;
            let config = fs::read(config_path).map_err(|error| format!("read config: {error}"))?;
            if header.len() != 76 {
                return Err(format!(
                    "incomplete header must be 76 bytes, got {}",
                    header.len()
                ));
            }
            if config.len() != 52 {
                return Err(format!(
                    "mining config must be 52 bytes, got {}",
                    config.len()
                ));
            }
            let mut preimage = Vec::with_capacity(128);
            preimage.extend_from_slice(&header);
            preimage.extend_from_slice(&config);
            Ok(encode_hex(&blake3_digest(&preimage, None)))
        }
        [_, mode, version, prev_block_display_hex, merkle_root_display_hex, timestamp, nbits, config_path]
            if mode == "job-key-fields" =>
        {
            let config_bytes =
                fs::read(config_path).map_err(|error| format!("read config: {error}"))?;
            let config = MiningConfiguration::from_bytes(&config_bytes)
                .map_err(|error| format!("E000-REJ-MINING-CONFIG: {error}"))?;
            let header = IncompleteBlockHeader {
                version: parse_u32(version, "version")?,
                prev_block: decode_hash(prev_block_display_hex, "prev_block")?,
                merkle_root: decode_hash(merkle_root_display_hex, "merkle_root")?,
                timestamp: parse_u32(timestamp, "timestamp")?,
                nbits: parse_u32(nbits, "nbits")?,
            };
            let header_bytes = header.to_bytes();
            let config_bytes = config.to_bytes();
            let mut preimage = Vec::with_capacity(128);
            preimage.extend_from_slice(&header_bytes);
            preimage.extend_from_slice(&config_bytes);
            Ok(format!(
                "{}:{}:{}",
                encode_hex(&header_bytes),
                encode_hex(&config_bytes),
                encode_hex(&blake3_digest(&preimage, None))
            ))
        }
        [_, mode, slab_path, key_hex] if mode == "matrix-root" => {
            let slab = fs::read(slab_path).map_err(|error| format!("read slab: {error}"))?;
            if slab.is_empty() {
                return Err("matrix slab must be non-empty".to_string());
            }
            let key_bytes = decode_hex(key_hex)?;
            let key: [u8; 32] = key_bytes.try_into().map_err(|value: Vec<u8>| {
                format!("job key must be 32 bytes, got {}", value.len())
            })?;
            let padded = pad_to_chunk_boundary(&slab);
            Ok(encode_hex(&MerkleTree::new(&padded, key).root()))
        }
        [_, mode, derivation, hash_a_hex, hash_b_hex, m, n, job_key_hex]
            if mode == "noise-seeds" =>
        {
            let derivation = match derivation.as_str() {
                "salted" => SeedDerivation::Salted,
                "legacy" => SeedDerivation::Legacy,
                _ => return Err("derivation must be salted or legacy".to_string()),
            };
            let (b_noise_seed, a_noise_seed) = noise_seeds(
                derivation,
                decode_hash(hash_a_hex, "hash_a")?,
                decode_hash(hash_b_hex, "hash_b")?,
                parse_u32(m, "m")?,
                parse_u32(n, "n")?,
                decode_hash(job_key_hex, "job_key")?,
            );
            Ok(format!(
                "{}:{}",
                encode_hex(&b_noise_seed),
                encode_hex(&a_noise_seed)
            ))
        }
        _ => Err("usage: aeye-e000-pearl-oracle job-key HEADER CONFIG | \
             job-key-fields VERSION PREV_BLOCK_DISPLAY_HEX MERKLE_ROOT_DISPLAY_HEX \
             TIMESTAMP NBITS CONFIG | matrix-root SLAB KEY_HEX | \
             noise-seeds salted|legacy HASH_A_HEX HASH_B_HEX M N JOB_KEY_HEX"
            .to_string()),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(value) => {
            println!("{value}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}

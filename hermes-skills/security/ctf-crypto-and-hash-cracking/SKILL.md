---
name: ctf-crypto-and-hash-cracking
description: Use when solving CTF cryptography or hash cracking tasks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ctf, cryptography, hashcat, john, steganography, hash-cracking]
---

# CTF Cryptography & Hash Cracking Orchestration

Playbook for rapidly triaging and solving CTF Cryptography, Hash Cracking, and Steganography challenges using high-throughput local hardware and agent delegation.

## 1. Immediate User Cadence & Responsiveness
- **Spawn-and-Report Cadence:** When kicking off multi-agent workers (e.g. Codex CLI) on complex problems, **immediately return status** (PID, session ID, target challenge, current working hypothesis) to the user before diving into deeper local script analysis. Never remain silent during long operations.
- **Never Idle While Background Agents Run:** While background jobs or subagents are processing, continue active parallel analysis: decompile bytecode, inspect ASN.1 structures, run mathematical tests, query scoreboard APIs, or formulate alternative hypotheses.
- **Zero-Token-Waste Workspace Prep:** Before launching Codex CLI, scaffold `README.md`, `tasks/plan.md`, and `tasks/todo.md`, configure virtual environments (`uv venv`) with pre-installed libraries, commit the scaffold to git, write a deterministic `verify.py` test harness, and ensure the directory is marked `trust_level = "trusted"` in `~/.codex/config.toml`.
- **Progress Visibility:** Surface visual proof (e.g. screenshots of CTFd solve modals) and keep the Google Docs writeup synchronized as each flag is captured.

## 2. High-Throughput Cracking Strategy
- **Layered Archives (Matryoshka Zips):**
  - Standard Python `zipfile` / `pyzipper` is single-threaded and slow for multi-layer dictionaries.
  - Compile an optimized parallel Rust cracker (`rayon` + `zip` crate) or use compiled native tools. Verify CRC/decompression on each candidate before proceeding to the next layer.
- **Hardware Acceleration (Hashcat on Local GPU):**
  - For standalone hashes (SHA-512, Whirlpool, Skein, Keccak), use local NVIDIA GPUs (`hashcat -m <mode> -d <gpu_id>`).
  - OpenCL backend (`-d 2` on CUDA OpenCL) bypasses ptxas toolchain version mismatches on bleeding-edge driver setups.
  - Combine wordlists (`rockyou.txt`) with standard mutation rules (`best66.rule`, `toggles1.rule`).
- **Encrypted PDFs (`pdf2john` + John the Ripper):**
  - Extract the hash with `pdf2john.py` (requires `pyhanko` or `pyhanko-certvalidator`).
  - Run `john --format=pdf --wordlist=rockyou.txt`.
  - Once cracked, use Ghostscript (`gs -sPDFPassword=...`) or `pikepdf` to extract high-resolution XObjects.

## 3. Cryptanalysis & Decoder Pitfalls
- **Avoid Fixating on Author Handles / Meta Clues:**
  - When encountering author names (e.g. `takanami`), do not waste substantial effort auditing personal accounts, social profiles, or registration dates unless explicitly instructed or when direct stego hints exist.
  - Prioritize **pure logical deduction**: deconstruct the mathematical structure of the ciphertext, verify encoding shifts, analyze known plaintext headers (e.g. `PK\x03\x04` for docx/zip), and test protocol specifications first.
- **Solve Rate & Scoreboard Reality Check:**
  - In active CTFs, constantly poll scoreboard solve timestamps (`/api/v1/challenges/<id>/solves`). If other competitors solve a challenge in under an hour (e.g. 30–50 minutes), **stop all massive multi-day brute-forces immediately**.
  - A fast solve by peers proves the solution is a clean, accessible logical inference (e.g. visible metadata, UI inspect element, standard RFC mechanism, or direct cross-challenge link), not an obscure mathematical zero-day or massive key-space scan.
- **Multi-Stage Text Obfuscation & ROT18 Gotcha:**
  - Common CTF sequence: Base64 $\rightarrow$ Unicode code point offset (e.g. CJK radical shifts like `-31753` / `0x7C09` into the Rice radical block `0x7C00..0x7CFF`) $\rightarrow$ Classical substitution (ROT13, Caesar).
  - **ROT18 (ROT13 + ROT5) Digit Shift:** Classical ROT13 only transforms letters `[a-z]`, leaving digits `[0-9]` untouched. If ROT13 successfully reveals clean labels (e.g. `cnffcuenfr unfu:` $\rightarrow$ `passphrase hash:`), but the accompanying hex hash fails all lookups, check for **ROT18** (ROT13 on letters + ROT5 on digits: `0<->5, 1<->6, 2<->7, 3<->8, 4<->9`). Without ROT5, digits remain inverted and the hash cannot be cracked.
  - Check for hex artifacting: in ROT13, letters `[a-f]` correspond to `[n-s]`. If ciphertext contains digits mixed with `[n-s]`, apply ROT13 to recover valid hexadecimal hashes.
  - **16-Symbol Frequency Check:** If a decrypted or shifted segment contains exactly 16 unique characters split into 10 consecutive digits (`0x30..0x39`) and 6 consecutive characters, it is an encoded hex digest.
- **OpenSSL 3.0+ KDF Default (`-md sha256` vs `-md md5`):**
  - Legacy OpenSSL used MD5 for `EVP_BytesToKey` derivation (`openssl enc -pass file:...`).
  - Modern OpenSSL (3.0+) defaults to SHA-256 (`-md sha256`) when `-pbkdf2` is omitted. Always test both `-md sha256` and legacy `-md md5` when reconstructing OpenSSL CLI commands.
- **Office DOCX XML Steganography ("Plain in Sight"):**
  - In Word `.docx` documents (ZIP archives containing `word/document.xml`), text can be hidden in plain sight via font color tags: e.g. `<w:color w:val="FFFFFF"/>` (white text on white background) or microscopic font sizing.
  - Always unpack `.docx` and grep raw XML for flag strings and suspicious color/size styling attributes.
- **Hash Identification ("IDENTIFY" Clues):**
  - Capitalized keywords like "IDENTIFY" usually signal `hash-identifier` or `hashid`.
  - Always inspect both "Possible Hashes" and "Least Possible Hashes" (e.g. HMAC variants, Whirlpool, Skein).
- **Direct Dictionary Rejection via Known Plaintext:**
  - Instead of solely attacking the hash, if an encryption toolchain like OpenSSL (`openssl enc -aes-256-cbc -pass file:pass.txt`) is known, write a fast multi-threaded C scanner (`EVP_BytesToKey` + `AES_cbc_encrypt`) testing words directly against known plaintext magic bytes (`PK\x03\x04`). An exhaustive failure on 14M+ words (`rockyou.txt`) definitively proves the secret is not a common dictionary word.
  - **OpenSSL `file:` Passphrase Quirk:** When using OpenSSL's `-pass file:<path>`, OpenSSL only reads the file up to the first newline (`\n` or `\r\n`). If trailing text, multiple lines, or comments exist, only the first line is treated as the passphrase input.
- **Padding Assumption Bug & Base64 Plaintext:**
  - When writing custom AES decryptors (especially AES-ECB / AES-CBC), do not discard candidates solely because standard PKCS#7 unpadding fails. CTF authors frequently encrypt exact 16-byte block multiples, null-padded strings, or raw unpadded flag buffers.
  - Check whether the decrypted plaintext was Base64-encoded prior to cipher block padding. If AES-ECB/CBC produces valid Base64 ASCII characters rather than immediate `flag{...}`, decode Base64 before discarding the candidate key.
- **Timestamp / RFC 3161 Tokens ("Chronological Digest"):**
  - Inspect ASN.1 DER with `openssl ts -reply -in <file>.tsr -text` and `openssl asn1parse`.
  - Distinguish message imprint from key material: the message imprint inside the TSR is often the SHA-256 of the ciphertext (signed after encryption).
  - Key derivation candidates: Integer Unix epoch timestamp strings (e.g. `hashlib.sha256(b"1792355352").digest()`), `GeneralizedTime` (`YYYYMMDDHHMMSSZ`), formatted strings (`b"Oct 18 ..."`), unix epoch integers/floats, signing certificates, or signed attributes (`id-messageDigest` at tag `0xa0` transformed to `SET 0x31`).

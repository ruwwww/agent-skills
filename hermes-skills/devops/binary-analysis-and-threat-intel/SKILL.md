---
name: binary-analysis-and-threat-intel
description: Use when analyzing binaries, malware, or threat intel.
---

# Binary Analysis and Threat Intelligence

Class-level workflow for safely analyzing binary samples (PE, Mach-O, ELF), extracting metadata, performing static disassembly without executing untrusted code, and retrieving threat intelligence telemetry.

## 1. Safe Sample Ingestion & Triage
- **Never Execute Untrusted Malware Binaries Directly:** Always triage samples via static analysis in isolated directories (e.g. `/tmp/`).
- **Encrypted Archives (e.g. password: `infected`):** Standard `unzip` fails on AES-encrypted zip archives. Use `pyzipper` via `uv run --with pyzipper python`:
  ```python
  import pyzipper, hashlib
  with pyzipper.AESZipFile("sample.zip") as zf:
      zf.setpassword(b"infected")
      data = zf.read(zf.namelist()[0])
      sha256 = hashlib.sha256(data).hexdigest()
  ```

## 2. Programmatic Threat Intelligence (VirusTotal)
When official API keys are unavailable or rate-limited:
- **VirusTotal Public Web UI Endpoint:**
  - Endpoint: `https://www.virustotal.com/ui/files/<sha256_or_md5>`
  - Required Headers:
    - `X-Tool`: `vt-ui-main`
    - `Accept`: `application/json`
    - `X-VT-Anti-Abuse-Header`: Computed via the client token generator.
- **Anti-Abuse Token Formula:**
  ```python
  import time, random, base64

  def compute_vt_anti_abuse():
      t = time.time()
      e = (1 + random.random() % 50000) * 1e10
      e_str = "-1" if e < 50 else f"{e:.0f}"
      raw = f"{e_str}-ZG9udCBiZSBldmls-{t}"
      return base64.b64encode(raw.encode()).decode()
  ```
- **Extracted Fields & Normalization:**
  - `names` & `meaningful_name`: Identifies original malware filenames vs hash names.
  - `popular_threat_classification`: Threat categories (`trojan`, `miner`, `dropper`) and suggested labels.
  - `first_submission_date`: Unix epoch timestamp. Format to `DD-MM-YYYY hh:mm:ss` (UTC or local timezone as requested).

## 3. Static Binary Analysis & Reverse Engineering
- **PE Metadata Extraction (Windows Executables):**
  - Use `pefile` (`uv run --with pefile python`).
  - Inspect `FILE_HEADER.TimeDateStamp`, `imphash`, and `StringTable` entries under `FileInfo` (`CompanyName`, `FileTitle`, `OriginalFilename`, `ProductName`).
- **Mach-O Analysis (macOS / ARM64):**
  - Use `macholib` (`uv run --with macholib python`).
  - Parse headers and sections: `__text` (code), `__cstring` (string formats/literals), `__data` (globals/constants).
  - Resolve symbol tables via `LC_SYMTAB` / `SymbolTable` to locate function entry points (`_main`, helper functions).
- **Static Disassembly with Capstone:**
  - Disassemble isolated bytecode without executing: `uv run --with capstone python`.
  - Architecture modes: `capstone.CS_ARCH_ARM64` / `CS_ARCH_X86`.
  - Reconstruct immediate constants in ARM64:
    - Example: `mov w8, #0xaa5f` followed by `movk w8, #0x408, lsl #16` $\rightarrow$ `(0x408 << 16) | 0xaa5f = 0x0408aa5f` ($67676767_{10}$).
  - Trace conditional jumps (`subs`, `b.ne`, `cbnz`) to identify validation logic and corresponding output strings.

## Supporting Files
- `references/virustotal-api.md`: Deep dive on VirusTotal UI endpoints, response schema, and field mappings.
- `scripts/vt_query.py`: Ready-to-run script to query sample attributes by hash.

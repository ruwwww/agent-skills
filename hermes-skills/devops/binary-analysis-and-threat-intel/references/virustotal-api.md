# VirusTotal UI API Reference

## Endpoint
`GET https://www.virustotal.com/ui/files/{hash}`
Accepts SHA-256, SHA-1, or MD5 hash strings.

## Headers Required
- `User-Agent`: Modern browser User-Agent string.
- `Accept`: `application/json`
- `X-Tool`: `vt-ui-main`
- `X-VT-Anti-Abuse-Header`: Base64 encoded string generated from `compute_vt_anti_abuse()`.

## Anti-Abuse Token Mechanics
The frontend client generates the token by combining a pseudo-random floating point value multiplied by $10^{10}$, the literal base64 string `ZG9udCBiZSBldmls` ("dont be evil"), and the current epoch timestamp in seconds:
`b64encode("{val}-ZG9udCBiZSBldmls-{timestamp}")`

## Key Response JSON Schema (`data.attributes`)
- `meaningful_name`: The primary display name determined by VT.
- `names`: List of filenames reported by submitting sources.
- `popular_threat_classification`:
  - `popular_threat_category`: Array of `{value, count}` tuples (e.g. `trojan`, `miner`, `dropper`).
  - `suggested_threat_label`: Consolidated detection label (e.g. `trojan.reflo/fwem`).
- `first_submission_date`: Integer epoch timestamp of first upload.
- `last_submission_date`: Integer epoch timestamp of most recent upload.
- `pe_info`: Machine type, imphash, compilation timestamp, and import table.
- `signature_info`: Publisher, file version, and copyright strings.

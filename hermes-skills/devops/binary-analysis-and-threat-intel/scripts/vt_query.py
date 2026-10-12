#!/usr/bin/env python3
"""
Query VirusTotal file telemetry without requiring an API key via UI proxy.
Usage: python3 vt_query.py <sha256_or_md5>
"""
import sys
import time
import random
import base64
import json
import urllib.request
import datetime

def compute_anti_abuse():
    t = time.time()
    e = (1 + random.random() % 50000) * 1e10
    e_str = "-1" if e < 50 else f"{e:.0f}"
    raw = f"{e_str}-ZG9udCBiZSBldmls-{t}"
    return base64.b64encode(raw.encode()).decode()

def query_vt(file_hash):
    url = f"https://www.virustotal.com/ui/files/{file_hash}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Ianguage": "en-US,en;q=0.9",
        "X-Tool": "vt-ui-main",
        "X-VT-Anti-Abuse-Header": compute_anti_abuse()
    })
    try:
        resp = urllib.request.urlopen(req).read().decode()
        data = json.loads(resp)
        attr = data.get("data", {}).get("attributes", {})
        
        first_sub = attr.get("first_submission_date")
        utc_str = datetime.datetime.fromtimestamp(first_sub, datetime.timezone.utc).strftime("%d-%m-%Y %H:%M:%S") if first_sub else "N/A"
        
        output = {
            "hash": file_hash,
            "names": attr.get("names", []),
            "meaningful_name": attr.get("meaningful_name"),
            "popular_threat_classification": attr.get("popular_threat_classification", {}),
            "first_submission_utc": utc_str,
            "first_submission_epoch": first_sub,
            "tags": attr.get("tags", [])
        }
        print(json.dumps(output, indent=2))
    except Exception as e:
        print(f"Error querying VirusTotal: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 vt_query.py <file_hash>", file=sys.stderr)
        sys.exit(1)
    query_vt(sys.argv[1].strip())

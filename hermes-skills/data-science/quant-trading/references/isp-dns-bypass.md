# ISP DNS Poisoning Bypass via DNS-over-HTTPS (DoH)

In regions where regulatory bodies or local ISPs poison DNS records for crypto exchanges (redirecting `api.binance.com`, `api.bybit.com`, `api.kraken.com`, or `api.exchange.coinbase.com` to ISP portal IPs), standard HTTPS and WSS connections fail with:
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch
```

## Production In-Memory Socket Patch

This patch intercepts `socket.getaddrinfo` and resolves hostnames via Cloudflare DoH (`https://cloudflare-dns.com/dns-query`) or Google DoH (`https://dns.google/resolve`), transparently fixing `requests`, `urllib3`, `ccxt`, `websockets`, and `aiohttp` without requiring root or system config changes.

```python
import socket
import urllib.request
import json
import logging

_dns_cache = {}

def doh_resolve(hostname: str):
    if hostname in _dns_cache:
        return _dns_cache[hostname]
    
    if hostname in ("localhost", "127.0.0.1", "::1") or hostname.replace(".", "").isdigit():
        return None

    providers = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A"
    ]
    for url in providers:
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/dns-json", "User-Agent": "QuantLab/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                ips = [ans["data"] for ans in data.get("Answer", []) if ans.get("type") == 1]
                if ips:
                    _dns_cache[hostname] = ips
                    return ips
        except Exception:
            continue
    return None

_orig_getaddrinfo = socket.getaddrinfo

def enable_doh_patch():
    """Call once at application startup before importing exchange network clients."""
    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if isinstance(host, str) and not host.replace(".", "").isdigit():
            ips = doh_resolve(host)
            if ips:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ips[0], port))]
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = patched_getaddrinfo
```

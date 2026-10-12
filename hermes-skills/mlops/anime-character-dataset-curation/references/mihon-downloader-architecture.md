# Resilient Manga & Manhwa Downloader Architecture (Mihon Reference)

Extracted from `mihonapp/mihon` (Mihon Download System and HTTP Source Integration) via DeepWiki MCP for building robust, high-throughput manga and manhwa scraping and ingestion pipelines.

## 1. Core Component Separation

Mihon separates queue orchestration, network execution, and storage caching into dedicated layers:

- **`DownloadManager` (Singleton Orchestrator):**
  - Manages high-level queue state: `downloadChapters`, `reorderQueue`, `clearQueue`.
  - Exposes query APIs (e.g. `isChapterDownloaded`) backed by `DownloadCache` (in-memory index of on-disk archives) to prevent blocking on filesystem scans.
- **`Downloader` (Execution Engine):**
  - Coroutine/async worker processing downloads grouped per source domain.
  - Enforces `parallelSourceLimit` (per-host concurrency cap) to prevent overwhelming upstream servers.
- **`Download` Lifecycle State Machine:**
  - `QUEUE` -> `DOWNLOADING` -> `DOWNLOADED` (or `ERROR`).
- **`DownloadCache`:**
  - Persisted index cache (`dl_index_cache_v3`) avoiding repeated disk directory traversal.

## 2. Two-Phase Resilient Download Pipeline

### Phase A: Page List Resolution
- Separate chapter metadata retrieval from image downloads:
  1. Call source scraper/resolver (`getPageList(chapter)`).
  2. Normalize and validate image URLs before enqueuing downloads.

### Phase B: Concurrent Page Streaming & Exponential Backoff
- Download pages concurrently using pooled workers or coroutines.
- **3-Stage Exponential Retry Mechanism:**
  - Upon HTTP error, timeout, or dropped connection, retry up to 3 times.
  - Progressive delays: **2 seconds**, **4 seconds**, and **8 seconds** before marking a page failed.
  - Preserves partial progress if individual pages need redownloading.

## 3. Storage Hierarchy & CBZ Packaging

### Storage Structure:
```
Downloads / <Source_Name> / <Series_Title> / <Chapter_Directory_or_CBZ>
```
- Sanitize chapter names and append a URL hash to eliminate naming collisions.

### Direct In-Memory Streaming to CBZ:
- Stream downloaded image bytes directly into a `zipfile.ZipFile` archive without writing temporary image files to disk.
- Generate and embed standard **`ComicInfo.xml`** inside the root of each `.cbz`:
  - Contains series title, chapter number, writer, artist, and publication year.
  - Compatible with Manga readers (Kavita, Komga, Tachiyomi/Mihon, Calibre).

## 4. Network Interceptors & Anti-Scraping Defense

- **Rate Limiting (`RateLimitInterceptor`):**
  - Maintain a rolling timestamp queue or token-bucket per host (e.g. max 2 requests/sec).
  - Pauses outgoing requests when host limits are exceeded.
- **Header & Session Normalization (`UserAgentInterceptor`):**
  - Inject realistic desktop/mobile User-Agents and maintain persistent cookie jars across requests.
- **Cloudflare & WAF Handling (`CloudflareInterceptor`):**
  - Intercept 403 / 503 challenge responses.
  - Trigger automated headless browser / curl_cffi session to harvest `cf_clearance` cookies and session tokens.

## 5. Python Reference Blueprint (Asyncio + Httpx)

```python
import asyncio
import io
import time
import zipfile
import httpx
from typing import List, Dict

class ResilientDownloader:
    def __init__(self, per_host_limit: int = 2):
        self.semaphore = asyncio.Semaphore(per_host_limit)
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 ..."},
            timeout=30.0,
            follow_redirects=True
        )

    async def fetch_page_with_retry(self, url: str, max_retries: int = 3) -> bytes:
        delays = [2.0, 4.0, 8.0]
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    resp = await self.client.get(url)
                    resp.raise_for_status()
                    return resp.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(delays[attempt])

    async def download_chapter_to_cbz(self, page_urls: List[str], output_cbz_path: str, comic_info_xml: str):
        tasks = [self.fetch_page_with_retry(url) for url in page_urls]
        pages_data = await asyncio.gather(*tasks)

        with zipfile.ZipFile(output_cbz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("ComicInfo.xml", comic_info_xml)
            for idx, data in enumerate(pages_data):
                ext = "png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "jpg"
                zf.writestr(f"p{idx+1:03d}.{ext}", data)
```

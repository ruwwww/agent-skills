---
name: tech-career-monitor
description: "Track and curate tech jobs and contracts from ATS APIs."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Jobs, Careers, MLOps, System-Software, Monitoring, Cron, ATS]
---

# Tech Career & Job Board Monitor

Automate tracking, scraping, and smart curation of engineering roles, silicon software stack positions, and remote contracts across enterprise ATS platforms and startup hiring boards.

## When to Use

- "Monitor careers for Company X, Y, Z (e.g. NVIDIA, AMD, AWS Trainium, Tenstorrent, Huawei)."
- "Track remote contract/freelance or B2B opportunities for ML Systems, MLOps, or Kernel engineers."
- "Build an automated alert system for new job postings matching specific technical keywords."
- Setting up a scheduled recurring job scout via Hermes `cronjob`.

## Architecture & Principles

### 1. Bypass Fragile Web Scraping via Direct ATS APIs
Most tech companies expose public JSON endpoints through their Applicant Tracking Systems (ATS) or internal career search gateways. Querying these directly is 100x faster, resilient to bot/Cloudflare blocks, and requires no headless browser.

- **Greenhouse Boards API:**
  `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`
  (Used by: Tenstorrent, Together AI, SambaNova)
- **Ashby Job Board API:**
  `GET https://api.ashbyhq.com/posting-api/job-board/{slug}`
  (Used by: Cerebras, d-Matrix, Anyscale, Fireworks AI, Modal, RunPod, Etched)
- **Workday CXS Gateway:**
  `POST https://{tenant}.myworkdayjobs.com/wday/cxs/{slug}/{site}/jobs`
  Payload: `{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "query"}`
  (Used by: NVIDIA `nvidia.wd5`/`NVIDIAExternalCareerSite`, Intel `intel.wd1`/`External`, Sony Global `sonyglobal.wd1`/`SonyGlobalCareers`)
- **Phenom People API:**
  `GET https://{career_domain}/api/jobs?keywords={query}&page=1&limit=20`
  (Used by: AMD `careers.amd.com`)
- **Amazon.jobs REST API:**
  `GET https://www.amazon.jobs/en/search.json?base_query={query}&result_limit=25`
  (Used for: AWS Annapurna Labs, Trainium, Inferentia, Neuron SDK)
- **Hacker News 'Who is Hiring' (Direct Contract/Founder stream):**
  - Monthly thread ID discovery via Algolia:
    `GET https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1`
  - Comment extraction via Firebase:
    `GET https://hacker-news.firebaseio.com/v0/item/{story_id}.json`

### 2. Smart Scoring & Curation Engine
Raw keyword matching produces noisy alerts. Apply tiered scoring:
- **Tier 1 (+25 pts):** Core specialization keywords in title/body (e.g. `CUDA`, `Triton`, `Kernel`, `MLIR`, `Compiler`, `PTQ`, `Quantization`, `vLLM`, `Trainium`, `Neuron`, `Ascend`, `CANN`, `ROCm`).
- **Tier 2 (+15 pts):** Systems & low-level fundamentals (`Runtime`, `Distributed Inference`, `C++`, `SIMD`, `Hardware Bringup`).
- **Tier 3 (+10 pts):** Infrastructure & MLOps (`MLOps`, `Slurm`, `Ray`, `Model Deployment`).
- **Work Arrangement Boost (+20 to +30 pts):** `Contract / B2B`, `Remote Worldwide`, `Anywhere`.
- **Negative Exclusions (-50 pts / Hard Drop):** Non-engineering roles (`Sales`, `Account Executive`, `HR`, `Recruiter`, `Marketing`, `Legal`, `Administrative`).

### 3. Persistent State & Deduplication (SQLite)
Maintain a local SQLite database (`jobs.db`) with schema:
`(id, source, company, title, location, is_remote, is_contract, url, score, tags, first_seen, notified)`.
- Use deterministic composite primary keys: `{source}_{company}_{job_id}`.
- New postings trigger alerts; existing ones only update scores if criteria change.
- Mark postings as `notified = 1` once delivered to avoid notification spam.

### 4. Zero-Token Background Scheduling (Watchdog Cron)
Schedule automated scans via Hermes `cronjob` with `no_agent: true`:
```bash
cronjob(action="create",
        name="ML Systems & Accelerator Job Scout",
        schedule="every 12h",
        script="run_job_tracker.sh",
        no_agent=true,
        deliver="origin")
```
When `no_agent: true` is set, Hermes runs the bash script directly. If no new qualifying jobs are found, the script exits quietly with empty stdout (0 tokens used, no spam). When new positions match the score threshold, stdout is delivered verbatim as markdown to the target channel.

## Reference Files

- See `references/ats-apis.md` for endpoint specifications, request payloads, and response parsing guidelines across ATS providers.

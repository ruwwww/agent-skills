# ATS API Reference & Query Patterns

Quick reference for querying Applicant Tracking Systems (ATS) and job search backends directly.

---

## 1. Greenhouse
- **Base Endpoint:** `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- **Method:** `GET`
- **Headers:** `{"User-Agent": "Mozilla/5.0"}`
- **Response Structure:**
  ```json
  {
    "jobs": [
      {
        "id": 1234567,
        "title": "Kernel Engineer",
        "absolute_url": "https://...",
        "location": {"name": "Remote / Warsaw, Poland"},
        "updated_at": "2026-09-01T..."
      }
    ]
  }
  ```

---

## 2. Ashby
- **Base Endpoint:** `https://api.ashbyhq.com/posting-api/job-board/{slug}`
- **Method:** `GET`
- **Headers:** `{"User-Agent": "Mozilla/5.0"}`
- **Response Structure:**
  ```json
  {
    "jobs": [
      {
        "id": "uuid-here",
        "title": "Staff Inference Engineer",
        "jobUrl": "https://jobs.ashbyhq.com/...",
        "location": "Sunnyvale, CA",
        "isRemote": true
      }
    ]
  }
  ```

---

## 3. Workday CXS Gateway
- **Endpoint:** `https://{tenant}.myworkdayjobs.com/wday/cxs/{slug}/{site}/jobs`
- **Method:** `POST`
- **Headers:** `{"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}`
- **Payload:**
  ```json
  {
    "appliedFacets": {},
    "limit": 20,
    "offset": 0,
    "searchText": "compiler"
  }
  ```
- **Known Target Tenants:**
  - NVIDIA: `nvidia.wd5` / `nvidia` / `NVIDIAExternalCareerSite`
  - Intel: `intel.wd1` / `intel` / `External`
  - Sony Global: `sonyglobal.wd1` / `sonyglobal` / `SonyGlobalCareers`
- **Job URL Construction:**
  `https://{tenant}.myworkdayjobs.com/{site}{externalPath}`

---

## 4. Amazon.jobs (AWS Trainium / Annapurna Labs)
- **Endpoint:** `https://www.amazon.jobs/en/search.json?base_query={query}&result_limit=25`
- **Method:** `GET`
- **Headers:** `{"User-Agent": "Mozilla/5.0"}`
- **Job URL Construction:**
  `https://www.amazon.jobs{job_path}`

---

## 5. Phenom People (AMD Careers)
- **Endpoint:** `https://careers.amd.com/api/jobs?keywords={query}&page=1&limit=20`
- **Method:** `GET`
- **Response Structure:**
  Jobs are under `data.jobs[].data` with keys: `title`, `city`, `country`, `apply_url`, `req_id`.

---

## 6. Hacker News 'Who Is Hiring' (Direct Contract & Startup Roles)
- **Thread Discovery:**
  `GET https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1`
- **Item Extraction:**
  `GET https://hacker-news.firebaseio.com/v0/item/{item_id}.json`
  First line typically follows: `Company | Role | Location | Remote/Contract status`.

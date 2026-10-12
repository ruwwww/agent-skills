---
name: moodle-coursework-operations
description: Automate Moodle coursework, deadlines, and deliverables.
---

# Moodle Coursework Operations

Workflow and automation practices for handling academic coursework, deadlines, and multi-format deliverable generation on Moodle-based LMS (such as myITS Classroom).

## 1. Deadlines & Assignment Discovery Patterns
When querying assignments in Moodle instances where standard API endpoints return empty lists or truncated data:
- **Inspect Course HTML Directly:** Parse `/course/view.php?id=<course_id>` or `/calendar/view.php?view=upcoming` with authenticated session cookies. Moodle renders activity links containing `/mod/assign/view.php?id=<cmid>`.
- **Extract CMID Metadata:** For each assignment CMID, scrape:
  1. Title and instruction text (`#intro` or `.box.generalbox`).
  2. Submission status (`.generaltable` rows: `Submission status`, `Due date`, `Time remaining`, `File submissions`).
  3. Linked resources (e.g. YouTube lecture links in `/mod/url/view.php?id=<cmid>`).

## 2. YouTube Lecture Sourcing & Multimodal Transcription
When course assignments reference external video lectures (e.g., YouTube URLs in `/mod/url/view.php?id=<cmid>`):
- **Caption Availability:** Many instructor-provided YouTube videos have automatic captions / subtitles disabled, causing `youtube-transcript-api` and `yt-dlp --list-subs` to fail.
- **Multimodal AI Extraction Prompting:** In such cases, leverage multimodal models with native YouTube audio ingestion (Gemini Web / AI Studio or NotebookLM) to extract full lecture transcripts, structured case breakdowns, and financial tables.
- **Precision Prompt Structure:** Provide explicit prompt templates targeting: (1) core thesis & background, (2) specific case forensics with numerical tables, (3) red flags & diagnostic indicators, (4) practical step-by-step methodologies, and (5) critical academic discussion questions.

## 3. Authentication & Silent Refresh Pitfalls
- **DOM Event vs Networkidle:** When refreshing SSO sessions via headless Playwright through OpenID Connect / Microsoft Entra ID callback pages (`/authorize/callback`), avoid `wait_until='networkidle'`. Continuous background telemetry pings prevent the network from reaching idle, triggering 30-second timeouts.
- **Reliable Handshake:** Use `wait_until='domcontentloaded'` with a short timeout (15s), followed by polling for target origin domain (`classroom.its.ac.id`) outside `/login/` and `/auth/oidc/`.

## 4. Multi-Format Deliverable Standards & Content Guidelines
When tasked with preparing academic assignments (such as resumes, case studies, or business model analyses):
- **Video Walkthroughs & Think-Out-Loud (TOL) Scripts:**
  - **Structure Per-Tahap (Bukan Outline Monolitik di Awal):** Jangan menumpuk seluruh outline atau penjelasan strategi sekaligus di awal video. Gunakan siklus terpisah per-tahap: `[Mental Model & Outline]` (bedah ancaman, pertimbangan arsitektur, trade-off, dan jebakan urutan rule di kepala) $\rightarrow$ lalu langsung `[Aksi & Live Commentary]` (eksekusi taktis di terminal/GUI diiringi monolog spontan saat mengetik). Ulangi siklus ini di setiap tahap/tugas.
  - **Candid Stream of Consciousness:** Gunakan bahasa lisan natural seorang engineer (inner monologue murni saat menganalisis sistem), bukan membaca teks tutorial atau instruksi lab.
  - **Verifikasi Kritis & Sanity Check:** Uji hipotesis secara mendalam (termasuk membongkar mengapa hasil tertentu seperti ping RTO justru merupakan bukti valid bahwa filter anti-spoofing bekerja).
- **Written Lab Reports & Academic Deliverables (.docx / narrative):**
  - **Connected Paragraphs Over Bulleted Lists:** Default to cohesive, flowing narrative paragraphs ("pure connected paragraphs") rather than bullet point lists for essay questions, analytical evaluations, situational breakdowns, and reflections, unless an explicit table or bullet list is requested by the prompt/rubric.
  - **Direct & Actionable Phrasing:** Keep analysis clear, assertive, and grounded in domain context without verbose padding or artificial transitions.
  - **Explicit Table Retention:** When a question specifically requests a field matrix, comparison, or tabular data (e.g. record field observations), format strictly as a clean structured table.
- **Slide Presentations (.pptx):**
  - Use 16:9 widescreen format (13.333 x 7.5 in).
  - Heading / card title font size: 14pt (bold).
  - Body font size: 12pt (line spacing 1.15).
  - Table cells: 10.5pt – 12pt.
  - Clean card container styling (e.g. dark navy / slate blue); avoid excessive decorative graphics or clipart.
- **Content Purity (Anti-Pattern to Avoid):**
  - **Do NOT force artificial course relevancy sections:** When summarizing an academic paper, video lecture, or corporate case study, keep the deck 100% focused on the actual subject matter (paper findings, corporate strategy, financial metrics, case forensics). Never insert arbitrary "Relevansi dengan Mata Kuliah X" or invented "Diskursus Pertanyaan Kritis" slides unless the prompt/assignment brief explicitly mandates them.
  - **Case-Focused Conclusions:** Final slides should provide genuine strategic conclusions, managerial takeaways, and operational lessons from the case itself, not meta-academic commentary.
- **Approval Workflow for New Assignments:**
  - When asked for an overview of an assignment (e.g. paper resume), first inspect the source paper/requirements, synthesize a structured overview, and present the proposed slide outline.
  - **Wait for explicit user approval** before executing document and PPTX generation scripts.
- **Sync to Cloud & Local Docs:**
  - Maintain paired local `.docx` / `.md` files alongside generated `.pptx`.
  - Sync markdown content to cloud docs (e.g. Google Docs) for fast mobile access.
  - **Isolated Google Drive Folder for Coursework Deliverables:** When creating and syncing academic deliverables (GDocs reports, test evidence screenshots, architecture diagrams) to Google Drive, always initialize or target a dedicated assignment folder (e.g., `Tugas <N> <MataKuliah> - <Topic>`) via Composio (`GOOGLEDRIVE_CREATE_FOLDER`), upload all supporting media/figures directly into that folder, and keep all related artifacts grouped together rather than dispersing them across the root Drive directory.
  - **Empirical Evidence & Failure Mode Inclusion:** In Computer Vision and applied engineering lab reports, always capture and document failure cases or adversarial presentations (e.g., 2D presentation spoofing via mobile phone screens, illumination variance, angle dropoffs) alongside positive verification, extracting theoretical framework diagrams from the foundational papers (e.g. ArcFace, SCRFD) to enrich the methodology section.

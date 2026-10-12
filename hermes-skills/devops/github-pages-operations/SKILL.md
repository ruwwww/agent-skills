---
name: github-pages-operations
description: Use when managing or debugging GitHub Pages deployments.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [GitHub, Pages, Jekyll, Static Sites, DNS, CI/CD]
---

# GitHub Pages Operations & Troubleshooting

Practical guide for deploying, managing, and debugging GitHub Pages sites (Jekyll, Hugo, Astro, al-folio, or static HTML) via GitHub CLI (`gh`) and REST API.

## Core Architecture & Routing Rules

GitHub Pages handles two distinct site types:

1. **User/Organization Apex Site (`<username>.github.io`):**
   - Served at the root domain: `https://<username>.github.io/`
   - Configured with `baseurl: ""`
2. **Project Sites (`<username>/<reponame>`):**
   - Served at subpath: `https://<username>.github.io/<reponame>/`
   - Configured with `baseurl: "/<reponame>"`

---

## Essential CLI Operations

### 1. Inspecting Pages Configuration

```bash
# Check deployment status, source branch, and build type (legacy vs workflow)
gh api repos/$OWNER/$REPO/pages

# Check the latest build status and error reports
gh api repos/$OWNER/$REPO/pages/builds/latest
```

### 2. Triggering and Monitoring Builds

```bash
# Request an immediate rebuild on GitHub Pages
gh api -X POST repos/$OWNER/$REPO/pages/builds

# List recent Pages build & deployment workflow runs
gh run list --repo $OWNER/$REPO --workflow=pages-build-deployment --limit 5

# Watch active build run until completion
gh run watch <RUN_ID> --repo $OWNER/$REPO --exit-status
```

---

## Critical Pitfalls & Solutions

### Pitfall 1: Sub-Repository Route Shadowing Trap

**Symptom:**
A subpath on the apex site (e.g., `https://username.github.io/blog/`) serves stale content, an old template, or a 404, even though the source files in `username.github.io` are updated and rebuilt.

**Root Cause:**
GitHub Pages prioritizes standalone project repositories over subdirectories in the apex site. If a separate repository named `username/blog` exists with Pages enabled, GitHub routes all traffic for `/blog/` to that repository, completely shadowing `username.github.io/blog/`.

**Diagnosis:**
```bash
# Check if a conflicting repo exists and has Pages enabled
gh api repos/$OWNER/<subpath>/pages
```

**Resolution:**
1. If deactivating Pages via `gh api -X DELETE repos/$OWNER/<repo>/pages` returns HTTP 422:
   - Delete the source branch: `gh api -X DELETE repos/$OWNER/<repo>/git/refs/heads/gh-pages`
   - Or rename the colliding repo: `gh repo rename <repo>-archive -R $OWNER/<repo> --yes`
2. Trigger an immediate rebuild on the apex repository:
   ```bash
   gh api -X POST repos/$OWNER/$OWNER.github.io/pages/builds
   ```

---

### Pitfall 2: CSS Stacking Context with Lightboxes & Modals

**Symptom:**
Clicking a thumbnail inside a blurred or transformed container (e.g. content-warning disclaimer) causes the lightbox overlay or zoomed image to render cropped, off-screen, or trapped inside the container.

**Root Cause:**
Applying `filter: blur(...)` or `transform` on any ancestor creates a new stacking context and containing block for `position: fixed` elements. Lightboxes relying on fixed positioning break.

**Resolution:**
Remove the filter style entirely on consent rather than keeping an active filter property:
```javascript
function acceptWarning() {
  document.getElementById('gallery-container').classList.remove('is-blurred');
}
```

---

### Pitfall 3: In-Place Zoom vs Modal Lightbox for Tall Portraits

**Symptom:**
Inline image zoom (`medium-zoom`) on tall portrait images (e.g., 9:16 aspect ratio) stretches off the screen, causing ugly scrollbars and cropped headers.

**Resolution:**
- Use dedicated modal lightbox libraries (such as **Spotlight.js** via `images.spotlight: true` in al-folio).
- Wrap items with `<a class="spotlight" href="...">` for viewport-constrained zoom, pan/drag, and keyboard navigation.
- Implement pure visual masonry via native CSS columns (`column-count: 2; column-gap: 1.5rem; break-inside: avoid;`) to prevent layout shift and maintain full vertical composition without hard crops.

---

### Pitfall 4: al-folio CI Prettier Formatting Failures

**Symptom:**
Pushing modified `.md`, `.liquid`, or `.js` files causes the GitHub Actions `Prettier code formatter` workflow to fail.

**Root Cause:**
al-folio enforces strict Prettier code formatting on every PR and push to `main`/`master` via `@shopify/prettier-plugin-liquid`.

**Resolution:**
Always run Prettier formatting before committing changes in an al-folio workspace:
```bash
# Format specific modified files or the entire repo
npm install --save-dev --save-exact prettier @shopify/prettier-plugin-liquid
npx prettier _pages/gallery.md _projects/*.md --write
```

---

### Pitfall 5: Heavy Unoptimized Image Previews in Static Galleries

**Symptom:**
Loading image galleries or portfolios is sluggish, with excessive initial page weight (tens of megabytes) and laggy scrolling.

**Root Cause:**
Referencing full-resolution master assets (e.g., 1.2–1.5MB PNGs) directly in `<img>` tags with `loading="eager"` forces the browser to download all images simultaneously at full resolution on page load.

**Resolution:**
1. **Responsive WebP Generation:**
   Ensure Jekyll/al-folio's `imagemagick` plugin is enabled (`widths: [480, 800, 1400]`).
2. **Dual-Tier Asset Delivery:**
   - Use `<picture>` with `srcset` pointing to generated `-480.webp` and `-800.webp` thumbnails for the gallery grid (~25–35 KB each, a 30×+ reduction).
   - Point the `<a>` link (`class="spotlight"`) to the full-resolution master asset for fullscreen modal viewing.
3. **Lazy Loading & Async Decoding:**
   Add `loading="lazy"`, `decoding="async"`, and `content-visibility: auto` to prevent main-thread decoding jank and maintain 60/120 fps scrolling.
4. **Layout Shift Prevention:**
   Set a `min-height` and subtle placeholder gradient on `.gallery-item` so the layout remains stable (CLS = 0) while images load.
5. **DRY Front Matter Structure:**
   Store gallery items in page front matter (`artworks: [...]`) and render via a Liquid loop instead of repeating manual HTML markup.

See `templates/gallery_masonry.md` for a production-ready boilerplate incorporating responsive WebP thumbnails, Spotlight lightbox, and disclaimer modal.

---

### Pitfall 6: al-folio CV Configuration & RenderCV Schema Traps

**Symptom:**
Updating the CV on al-folio either renders empty sections, keeps showing the default template (e.g. Albert Einstein placeholder), or causes Jekyll/CI build failures.

**Root Cause:**
al-folio's `_layouts/cv.liquid` expects a specific schema depending on `cv_format` in `_pages/cv.md`:
1. `cv_format: rendercv` reads `site.data.cv.cv` defined in `_data/cv.yml`.
2. Section names in `_data/cv.yml` are case-sensitive and match exact includes: `Education`, `Experience`, `Projects`, `Skills`, `Languages`, `Interests`, `Awards`, `Certificates`, `Publications`.
3. In `Experience`, fields must use `company`, `position`, `start_date`, `end_date`, `summary`, and `highlights`.
4. In `Projects`, fields must use `name`, `summary`, `url`, and `highlights`.
5. In `Education`, fields must use `institution`, `area`, `studyType`, `start_date`, `end_date`, and `highlights`.

**Resolution:**
- Update `_data/cv.yml` following the strict RenderCV YAML structure.
- Always run Prettier on `_data/cv.yml` and `_pages/cv.md` before committing:
  ```bash
  npx prettier _data/cv.yml _pages/cv.md --write
  ```

### Quick Pattern: Generating Clean ATS Single-Page PDF Resumes via Headless Chromium

When compiling standalone printable / ATS-compliant PDF resumes from Markdown/HTML:
1. **Strip Browser Headers/Footers:**
   Always use `--no-pdf-header-footer` to prevent date, URL, and page number overlays from ruining the clean ATS layout:
   ```bash
   /snap/bin/chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer --print-to-pdf=/path/to/CV_ATS.pdf /path/to/cv_render.html
   ```
2. **Strict Single-Page Geometry Budget:**
   Undergraduate/entry-level ATS resumes must target exactly 1 page:
   - Margins: `@page { size: A4; margin: 6mm 9mm; }`
   - Typography: Body font `8.2pt` to `8.4pt`, line height `1.22` to `1.25`, section headers `9.4pt` to `9.8pt`.
   - Entry spacing: `margin-bottom: 2.5px;` and tight list padding (`padding-left: 13px;`).
3. **Verify PDF Page Count Deterministically:**
   Check the raw PDF stream to guarantee it did not spill into page 2:
   ```bash
   grep -a "/Count" /path/to/CV_ATS.pdf # Ensure it outputs /Count 1
   ```
4. **Metrics Grounding in AI / Systems Experience:**
   When documenting sovereign LLM deployment and inference optimizations, state pure token generation / decode throughput (e.g. `1,300 tokens/sec decode throughput on Qwen 27B-35B`) rather than ambiguous blended request rates.

---

### Pitfall 7: YAML Front Matter Unquoted Colons & Unescaped Quotes Cause Silent Page Drops (404)

**Symptom:**
After adding or editing a page in al-folio (e.g. `_pages/gallery.md`), the URL returns 404 "Page not found" or redirects home, despite the GitHub Actions deploy job passing with green status (`exit 0`).

**Root Cause:**
1. **Unquoted colons with spaces:** Any unquoted scalar containing `: ` (e.g. `alt: Hirara (Mobile Legends: Bang Bang)`) is parsed as an invalid nested mapping key:
   `YAML Exception: (<unknown>): mapping values are not allowed in this context`.
2. **Unescaped nested quotes:** Using unescaped double quotes inside double-quoted strings (e.g. `alt: "Selena "Silverbolt" Raiko (The Aspirants - Mobile Legends: Bang Bang)"`) breaks YAML parser syntax:
   `YAML Exception reading .../_pages/gallery.md: (<unknown>): did not find expected key while parsing a block mapping`.

In both cases, Jekyll logs a warning during `Install and Build` and skips generating the affected page entirely into `_site/`, while the subsequent `Deploy` step still succeeds and pushes the missing page state to `gh-pages`.

**Resolution:**
1. **Proper Quoting & Naming Rules:**
   - **Never use quotation marks (`""`) in character names or alt descriptions:** Character titles, aliases, skins, and nicknames must NOT be wrapped in quotes (e.g., write `Selena Silverbolt Raiko`, NOT `Selena "Silverbolt" Raiko`). This completely avoids nested quote syntax collisions and respects user portfolio conventions.
   - Always wrap values containing colons `: ` in outer double quotes:
     ```yaml
     artworks:
       - name: selena_silverbolt_raiko
         alt: "Selena Silverbolt Raiko (The Aspirants - Mobile Legends: Bang Bang)"
     ```
   - Quote any scalar containing colons `: `, brackets `[]`, braces `{}`, or question marks `?`.
2. **Pre-commit sanity check:**
   Validate YAML front matter using Python before committing/pushing:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('_pages/gallery.md').read().split('---')[1])"
   ```
3. **Verify live permalink:**
   Always verify the live page with `curl -s -I https://<user>.github.io/<path>/` to ensure HTTP 200 OK and check `<title>` to confirm it did not render a 404.

---

### Pitfall 8: Adding Custom Socials (Hugging Face, X/Twitter) in al-folio via `jekyll-socials`

**Symptom:**
Adding custom social platforms like Hugging Face with local SVG logos causes build errors:
`Liquid Exception: undefined local variable or method 'relative_url' for an instance of Jekyll::SocialLinksTag`
or the icon fails to appear in the header/footer social row.

**Root Cause:**
1. Older versions of `jekyll-socials` (v0.0.6) had a bug where custom socials with local SVG logos attempted to call `relative_url` inside Ruby string interpolation without proper method scoping (`logo_value | relative_url`). This was resolved in `jekyll-socials >= 0.0.7`.
2. Twitter / X is a built-in platform in `jekyll-socials`, configured via `x_username: <handle>` (uses `fa-brands fa-x-twitter`).
3. For custom platforms without built-in keys (e.g. Hugging Face):
   `jekyll-socials` expects:
   ```yaml
   huggingface:
     title: Hugging Face
     url: https://huggingface.co/<username>
     logo: assets/img/huggingface_logo.svg # or full https:// URL, or font class
   ```
   SVGs used as logos must have a valid `viewBox` (e.g. `viewBox="0 0 95 88"`) so browsers and inline CSS render them with correct aspect ratio inside `<svg><image xlink:href="..."/></svg>`.

**Resolution:**
1. Ensure `Gemfile.lock` uses `jekyll-socials (>= 0.0.7)`.
2. Configure `_data/socials.yml`:
   ```yaml
   github_username: ruwwww
   huggingface:
     title: Hugging Face
     url: https://huggingface.co/ruwwww
     logo: assets/img/huggingface_logo.svg
   x_username: izzuddinalfaruq
   ```
3. In `_data/cv.yml`, RenderCV's strict validator does not recognize unlisted social networks. Keep RenderCV networks to supported names (`GitHub`, `LinkedIn`, `X`) or omit non-standard names from `_data/cv.yml` to prevent `.github/workflows/render-cv.yml` validation failures.

---

### Quick Pattern: Fast Batch Asset Ingestion into al-folio Gallery

When users provide a batch of images (or a `.zip` archive) to add to an al-folio visual gallery:
1. Extract or copy assets into `assets/img/art/<name>.png` (or `.jpg`).
2. Append entries directly into `artworks:` front matter list in `_pages/gallery.md` (e.g. via a fast Python script) rather than hand-crafting repetitive HTML.
3. Verify ImageMagick will automatically generate multi-width WebP thumbnails on build.
4. Run `npx prettier _pages/gallery.md --write` and deploy via Git push.

---

### Quick Pattern: Linking External Model Hubs (Hugging Face / LoRAs) in al-folio

When linking model checkpoints, dataset repos, or LoRA weights (e.g., `https://huggingface.co/ruwwww/diffusion_loras`) across al-folio:
1. **Gallery Header Banner (`_pages/gallery.md`):**
   Add a prominent callout with external link inside `.gallery-intro`:
   ```html
   Explore published weights and datasets on Hugging Face: <a href="https://huggingface.co/username/repo" target="_blank" rel="noopener"><strong>username/repo</strong> <i class="fa-solid fa-arrow-up-right-from-square fa-xs"></i></a>.
   ```
2. **Dedicated Project Entry (`_projects/<order>_<name>.md`):**
   Create a standard project card categorized under `Machine Learning & Generative Models`:
   - Include direct buttons linking to Hugging Face (`btn btn-primary btn-sm`), GitHub code/recipe, and cross-link to `/gallery/`.
   - Run `npx prettier _projects/*.md --write` to maintain repo formatting compliance.



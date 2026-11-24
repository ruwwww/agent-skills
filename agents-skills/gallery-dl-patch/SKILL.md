---
name: gallery-dl-patch
description: Patch and build on gallery-dl with external extractor modules that live outside site-packages and survive pip upgrades. Use when adding a new site/manga/image-host extractor to gallery-dl, debugging a gallery-dl extractor, or when the user mentions gallery-dl, gallery-dl extractors, or downloading mangak.io through gallery-dl.
---

# gallery-dl patching

gallery-dl loads **external extractor modules** from any directory — no edits to
site-packages, so the patch survives `pip install --upgrade gallery-dl`.

## Layout

- Patch dir: `C:/Coding3/gallery-dl-patch/extractors/` — one `<site>.py` per site
- Wired in `%APPDATA%/gallery-dl/config.json`:
  `"extractor": {"module-sources": ["C:/Coding3/gallery-dl-patch/extractors", false]}`
  — the `false` entry re-adds the built-in modules; **removing it disables every
  built-in extractor**.
- One-off override: `gallery-dl -X <dir> URL`

## Quick verify

```bash
gallery-dl --list-extractors <category>   # is my extractor registered?
gallery-dl -s <URL>                       # dry-run: prints would-be filenames
gallery-dl -d outdir <URL>                # real download
```

## Add a new site extractor

1. **Find the data source.** Inspect the site's HTML/JS: `curl -sL URL`, then grep
   its JS bundles for API paths (`grep -o '"(/api[^"]*)"' *.js`). Prefer the JSON
   API the frontend uses over HTML scraping. Confirm endpoints with curl before
   writing code (check required headers like Origin/Referer).
2. **Pick the base class** (from `gallery_dl.extractor.common`):
   - `GalleryExtractor` — one gallery → images (override `metadata()`, `images()`)
   - `ChapterExtractor(GalleryExtractor)` — manga chapter (adds `manga`,
     `chapter`, `chapter_minor`, `volume` fields; `images()` returns
     `[(url, None), ...]`)
   - `MangaExtractor` — manga title → queues chapter URLs (override
     `chapters(page)`; set `chapterclass`)
3. **Write the module** in the patch dir. Shape:
   ```python
   from gallery_dl import exception, text
   from gallery_dl.extractor.common import ChapterExtractor, MangaExtractor

   BASE_PATTERN = r"(?:https?://)?(?:www\.)?example\.com"

   class ExampleChapter(ChapterExtractor):
       category = "example"
       root = "https://example.com"
       pattern = BASE_PATTERN + r"/manga/([^/?#]+)/([^/?#]+)"
       example = "https://example.com/manga/NAME/ch-1"
       def metadata(self, page): ...
       def images(self, page): ...
   ```
   Any class in the module with a `pattern` attribute registers automatically —
   no registry file to edit.
4. **Test**: `-s` first, then one real chapter download, then the full URL.

## Hard-won gotchas

- The loader imports the file as a **top-level module** (`__import__("mangak")`),
  so use absolute imports (`from gallery_dl import ...`); relative imports fail.
- `MangaExtractor.chapters()` must **return a list** — the base class calls
  `chapters.reverse()` on it (a generator raises `AttributeError`).
- gallery-dl's image downloader sends **no Referer header** (the class attr
  `referer = True` only affects API `request()` calls). For CDN-gated hosts put
  `"_http_headers": {"Referer": "https://site/"}` in each image's metadata dict.
- Don't set `"count"` in `metadata()` unless it equals the real image count —
  `GalleryExtractor` zips page numbers against it.
- `pattern` is a **substring-matched** regex anchored only where you anchor it;
  order matters in `extractor.find()` (first match wins), so define the more
  specific class first or anchor with `$`.
- Page-level endpoints sometimes return a **preview** (mangak's
  `/chapters/<id>/images` gives 3 of ~30 pages) — verify the count you get back
  against expectations.

## Updating gallery-dl

```bash
python -m pip install --upgrade gallery-dl
gallery-dl --version
gallery-dl --list-extractors <category>   # re-verify after upgrade
```

Base-class APIs can move between versions; the re-verify step catches it.

## Reference

Site API notes and extractor internals: see [REFERENCE.md](REFERENCE.md)

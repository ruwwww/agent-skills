# gallery-dl patch reference

## How external modules load

`gallery_dl/__init__.py` → `initialize()`:

- CLI `-X/--extractors PATH` (append) sets `extractor.module-sources` for one run
  (it appends `None` → also load built-ins).
- Config `extractor.module-sources: [<path>, false, {"from": dir, "import": [...]}]`
  - `str` → every `*.py` in that directory
  - `dict` → named modules from `from` dir
  - anything else (`false`) → the built-in module list
- Loader `extractor._modules_path(path, files)` does `sys.path.insert(0, path)`
  then `__import__(name)` — modules are top-level, and each `*.py` in the dir is
  imported, so keep the dir free of stray/helper files (or they get imported too).
- `_get_classes(module)` picks up every class where `hasattr(cls, "pattern")`
  and `cls.__module__ == module.__name__`; string patterns are compiled at load.
- `extractor.find(url)` walks classes in registration order; **first regex
  match wins**.

## Message flow (job.py)

An extractor's `items()` yields:

- `Message.Directory, "", data` — create output directory from `directory_fmt`
- `Message.Url, url, data` — download `url` as filename from `filename_fmt`
- `Message.Queue, url, data` — spawn a child job for `url`; `data["_extractor"]`
  forces a specific class (bypasses `find()`), and `data` merges into the child's
  metadata depending on `parent`/`parent-metadata` config (default: nested under
  the `_parent` key).

`Job.update_kwdict()` injects `category`/`subcategory` and `extr.kwdict` into
every metadata dict, so don't set those yourself.

## Base classes (`gallery_dl/extractor/common.py`)

| class | override | notes |
|---|---|---|
| `Extractor` | `items()` | full control; `initialize()` sets up session/cookies first |
| `GalleryExtractor` | `metadata(page)`, `images(page)` | `images()` → `[(url, meta-or-None), ...]`; page = `self.request(self.page_url).text` only if `groups[0]` starts with `/` |
| `ChapterExtractor` | same | adds manga fmts: dir `{category}/{manga}/{volume...}c{chapter:>03}{chapter_minor:?//}{title:?: //}`, file `{manga}_c{chapter:>03}{chapter_minor:?//}_{page:>03}.{extension}` |
| `MangaExtractor` | `chapters(page)` → **list** of `(url, data)` | queues children; `reverse = True` default (list is reversed in place) |

Key attrs: `category`, `subcategory`, `root`, `pattern`, `example`,
`directory_fmt`, `filename_fmt`, `archive_fmt`, `referer`.

`chapter_minor` is a literal suffix (e.g. `".5"` → `c017.5`).
`volume` renders as `v/ 01` in the directory format when set.

## Headers for gated CDNs

- `self.request_json(url)` automatically sends `Referer`/`Origin`/`Sec-Fetch-*`
  based on `self.root` — good for API calls.
- The **image downloader** (`downloader/http.py`) sends only `Accept`,
  `_http_headers` from the metadata dict, and config `downloader.headers`.
  → put the required gate header in `data["_http_headers"]` per image.

## Common config keys

- `extractor.<category>.<subcategory>.<key>` via `self.config("key")`
- `directory-format`, `filename-format`, `archive-format`
- `request-interval`, `request-retries`, `http-headers` (`"headers"`)
- `skip` predicates: `file`, `image`, `post`, `child`
- `parent: true` merges parent (manga) metadata into chapter metadata dicts

## Worked example: mangak.io (installed)

Site: client-rendered SPA; JSON API at `https://api.mangak.io`:

```
GET /titles/by-slug/<slug>                          → {"data":{"new_url":"/titles/W2W4WR8P-slug"}}
GET /titles/<id>                                    → {"data":{"title":{...}}}
GET /titles/<id>/chapters                           → {"data":{"chapters":[{id,url,name,slug,number,views,updated_at}]}}
GET /titles/by-slug/<slug>/chapters/<ch>?include=details  → {"data":{"new_url":..., "chapter":{..., "images":[url,...]}}}
GET /titles/<id>/chapters/<ch-id>                   → {"data":{"chapter":{..., "images":[url,...]}}}
```

Traps: `chapters/<id>/images` (no include) returns only **3 preview pages**;
`title.id` is an **alphanumeric Sqid** (`W2W4WR8P`), never
`W2W4WR8P-slug`; chapter `number` is a sequence index (ch 17.5 → number 18),
so parse it from `name` with `(?:Vol\.(\d+) )?Chapter (\d+)(?:\.(\d+))?$`.
Image CDN `rx.*.org` → **403 without `Referer: https://mangak.io/`**.
API needs browser-like `Origin`/`Referer` headers (handled by `request_json`).

Module: `C:/Coding3/gallery-dl-patch/extractors/mangak.py`
(URL forms: `https://mangak.io/<slug>`, `.../<slug>/<chapter-slug>`,
`https://mangak.io/titles/<id>` and `/titles/<id>/<chapter-id>`).

### Skeleton for a new API-driven extractor

```python
from gallery_dl import exception, text
from gallery_dl.extractor.common import ChapterExtractor, MangaExtractor

BASE_PATTERN = r"(?:https?://)?(?:www\.)?example\.com"
API = "https://api.example.com"


class Base:
    category = "example"
    root = "https://example.com"

    def _api(self, path, **kwargs):
        data = self.request_json(API + path, **kwargs)
        if not data.get("success"):
            raise exception.ExtractionError(data.get("message") or path)
        return data["data"]


class ExampleChapter(Base, ChapterExtractor):
    pattern = BASE_PATTERN + r"/manga/([^/?#]+)/([^/?#]+)/?$"
    example = "https://example.com/manga/NAME/ch-1"

    def metadata(self, page):
        ch = self._api(f"/chapters/{self.groups[1]}", notfound="chapter")
        return {"manga": ..., "chapter": ..., "language": "eng"}

    def images(self, page):
        return [(url, None) for url in self._api(...)["images"]]


class ExampleManga(Base, MangaExtractor):
    chapterclass = ExampleChapter
    pattern = BASE_PATTERN + r"/manga/([^/?#]+)/?$"
    example = "https://example.com/manga/NAME"

    def chapters(self, page):
        return [(f"{self.root}/manga/NAME/{c['slug']}", {"manga": "NAME"})
                for c in self._api("/chapters")["list"]]
```

Test sequence: `--list-extractors example` → `-s URL` (filenames) → one chapter
URL real download → full title URL.

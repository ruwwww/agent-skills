# Curator Web UI & Intelligence Stack Architecture

Detailed technical specification for the FastAPI Human-in-the-Loop Web UI, Anatomy Verification, ISNet Matting, and WD14 Captioning Engine.

## 1. Web UI Architecture (`server.py`)

- **Backend:** FastAPI serving static thumbnails, full crops, segmented PNGs, and JSON metadata.
- **Port / Host:** `0.0.0.0:8288` (accessible over localhost, LAN, and Tailscale).
- **Metadata Cache:** `dataset_metadata.json` stores image dimensions, CCIP diff, status (`pending`, `approved`, `rejected`), anatomy results, and tags.

### Key API Endpoints
- `GET /api/items?status=&framing=&max_diff=&search=&sort_by=`: Query filtered items for fast rendering (framing options: `all`, `full_body`, `cowboy_shot`, `upper_body`, `portrait`).
- `GET /api/stats`: Real-time counts of total, pending, approved, rejected, segmented, tagged.
- `POST /api/item/{id}/status`: Set status (`approved`, `rejected`, `pending`).
- `POST /api/item/{id}/analyze`: Runs anatomy detection and WD14 tagging on demand.
- `POST /api/item/{id}/segment`: Runs ISNet background removal on demand.
- `POST /api/item/{id}/caption`: Updates and saves the `.txt` caption sidecar.
- `POST /api/export`: Copies/hardlinks approved images and `.txt` files directly into the Anima training folder (e.g. `data_root_<concept>/10_<concept>`).

## 2. Practical Ergonomics & Hotkeys

To curate hundreds of images in minutes, the UI enforces zero-click keyboard navigation:
- `1` or `A`: Approve current item and advance.
- `2` or `R`: Reject current item and advance.
- `3` or `P`: Reset current item to pending.
- `Space` or `→`: Next item.
- `←`: Previous item.
- `S`: Run ISNet anime matting on selected item.
- `T`: Run WD14 tagging on selected item.

## 3. Intelligence Stack Modules

### A. Anatomy & Landmark Inspection
```python
from imgutils.detect import detect_eyes, detect_faces, detect_hands, detect_with_booru_yolo

eyes = detect_eyes(pil_image)      # Bounding boxes for eyes (open vs closed)
faces = detect_faces(pil_image)    # Face boundaries
hands = detect_hands(pil_image)    # Hand positions (quality triage)
booru = detect_with_booru_yolo(pil_image) # ['head', 'bust', 'hair_ornament']
```

### B. Background Matting (ISNet-Anime)
```python
from imgutils.segment import segment_rgba_with_isnetis

mask, rgba = segment_rgba_with_isnetis(pil_image)
rgba.save("character_clean_trans.png")
```

### C. WD14 v3 SwinV2 Captioning & Noise Filter
```python
from imgutils.tagging import get_wd14_tags

DROPPED_NOISE = {
    "speech_bubble", "comic", "english_text", "chinese_text",
    "monochrome", "greyscale", "scan", "watermark", "signature"
}

def generate_clean_caption(pil_image, trigger_tags=["concept_name", "1girl"]):
    _, gen, _ = get_wd14_tags(pil_image, model_name="SwinV2_v3", general_threshold=0.35)
    clean_tags = [t.replace(" ", "_") for t, _ in sorted(gen.items(), key=lambda x: -x[1]) if t not in DROPPED_NOISE]
    return ", ".join(trigger_tags + clean_tags)
```

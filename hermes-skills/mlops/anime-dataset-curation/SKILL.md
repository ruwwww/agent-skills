---
name: anime-dataset-curation
description: "Use when curating anime datasets or mining characters."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [anime, dataset, curation, imgutils, waifuc, ccip, yolo, deduplication, manhua, lora]
---

# Anime Dataset Curation & Character Mining Playbook

End-to-end framework for autonomous character detection, identity clustering, sliding-window comic slicing, and visual deduplication using `deepghs/imgutils` and perceptual hashing.

## 1. Environment & Setup

- Recommended isolated venv: Python 3.11 with `dghs-imgutils[gpu]` and `onnxruntime-gpu`.
- In-memory archive extraction: Stream `.cbz` / `.zip` pages directly via `zipfile` and `io.BytesIO` to eliminate disk I/O bottlenecks.

## 2. Detection & Framing Pipeline

### A. Gutter Panel Decomposition vs. Fixed Sliding Windows
**The Pitfall of Fixed Sliding Windows:**
Using a fixed-height sliding window (e.g. 1,000 px height with 700 px stride) on 4,000+ px vertical manhua strips arbitrarily slices tall characters in half. Full-body illustrations are typically 1,200–1,800 px tall; a fixed window forces detectors to see severed fragments and prevents capturing full attires, flowing skirts, and footwear.

**The Solution — Natural Gutter Decomposition:**
1. Manhua strips are naturally partitioned by horizontal white, black, or low-variance gutter bars between scenes.
2. Calculate row-wise standard deviation $\sigma_{\text{row}}$ and mean intensity $\mu_{\text{row}}$:
   - Gutter condition: $\sigma_{\text{row}} < 5.0$ or $\mu_{\text{row}} > 250$ (white gutter) or $\mu_{\text{row}} < 10$ (black gutter).
3. Group contiguous gutter rows $\ge 15\text{px}$ and split the long strip at gutter midpoints.
4. Each extracted panel represents a complete scene where full-body characters and sweeping robes reside intact.
5. Fallback for seamless bleed strips: Use multi-scale large windows (e.g. 2,000 px with 50% overlap) instead of small 1,000 px windows.

### B. Flexible Framing Classification (Attire vs. Portrait Separation)
To flexibly collect complete attires without heuristic truncation (`never force detect_halfbody or 0.65*bh crop when attires are needed`), classify every crop via multi-signal geometry and landmark ratios:
```python
def determine_framing(img, face_box=None):
    w, h = img.size
    ar = h / w
    if face_box:
        fh = face_box[3] - face_box[1]
        face_ratio = fh / h
    else:
        face_ratio = 0.25 # fallback
        
    if face_ratio <= 0.18 or ar >= 1.75:
        return 'full_body'     # Complete attire, dress, sash, footwear
    elif face_ratio <= 0.32 or ar >= 1.30:
        return 'cowboy_shot'   # Mid-thigh / waist / seated pose
    elif face_ratio <= 0.48:
        return 'upper_body'    # Chest / shoulders / collarbone
    else:
        return 'portrait'      # Face, facial expressions, hair ornaments
```

### C. Smart Sliding-Window NMS (Boundary Truncation Fix)
**The Pitfall:** When a character spans the window boundary (e.g. window 1 ends at y=1000, window 2 starts at y=700), window 1 truncates the lower body while window 2 captures the full body. Standard IoU between the two boxes is often only ~0.20–0.26, causing standard NMS (`iou_threshold=0.40`) to miss it and produce identical scene duplicates with slightly shifted crops.

**The Solution:** Suppress redundant crops using Intersection over Smaller Box (IoS) and horizontal alignment:
```python
def calculate_overlap(b1, b2):
    # b = (x0, y0, x1, y1)
    ix0, iy0, ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1]), min(b1[2], b2[2]), min(b1[3], b2[3])
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter_area = iw * ih
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter_area
    iou = inter_area / union if union > 0 else 0
    ios = inter_area / min(area1, area2) if min(area1, area2) > 0 else 0
    x_overlap = iw / min(b1[2] - b1[0], b2[2] - b2[0])
    return iou, ios, x_overlap, ih

# Suppress candidate if:
# (iou >= 0.35) or (ios >= 0.45) or (x_overlap >= 0.65 and ih >= 150)
```
Always prioritize non-truncated boxes over boxes that contact the top/bottom boundary of a sliding window.

### C. Head & Bun Padding
Manhua heroines and fantasy characters frequently feature ornate hair buns (*guan*), pins, or tall headpieces that get trimmed by tight bounding boxes.
- Add **+15% top padding** relative to crop height.
- Add **+8% horizontal padding** relative to crop width for shoulders.

## 3. Character Identity Verification (CCIP)

Use Contrastive Anime Character Image Pre-Training (`imgutils.metrics.ccip`):
1. Extract 3–5 representative character anchors and compute a merged reference vector:
   ```python
   from imgutils.metrics import ccip_extract_feature, ccip_merge, ccip_difference
   merged_ref = ccip_merge([ccip_extract_feature(p) for p in reference_paths])
   ```
2. **Threshold Guide:**
   - `diff <= 0.08` (**Tier 1 Pristine**): Pure target character matches (100% precision).
   - `0.08 < diff <= 0.12` (**Tier 2 Strong Candidates**): Valid character variations (action lines, night shading, or partial occlusion).
   - `diff > 0.18` (**False Positive Zone**): Rejects background extras, villainous characters, and abstract VFX.

## 4. Multi-Tier Deduplication

### A. Intra-Page Deduplication
Resolve sliding-window twins using the Smart NMS criteria above.

### B. Cross-Chapter Perceptual Deduplication
Scanlation watermarks, recap panels, and promotional covers frequently recur across dozens of chapters.
- Compute dual hashes: difference hash (`dHash`) and discrete cosine transform perceptual hash (`pHash`).
- If `hamming_dist(dhash1, dhash2) <= 6` and `hamming_dist(phash1, phash2) <= 8`:
  Mark as duplicate artwork.
- Group into duplicate clusters and preserve solely the earliest appearance with the highest resolution.

## 5. Intelligence Stack & Quality Gates

### A. Anatomy Landmarks (`imgutils.detect`)
- `detect_eyes`: Verify clear eye contact (`eyes_count >= 2`), flag closed/winking eyes.
- `detect_faces` & `detect_hands`: Isolate face crops and detect hand integrity for quality triage.
- `detect_with_booru_yolo`: Detect anime features (`head`, `bust`, `hair_ornament`).

### B. Background Isolation Matting (`imgutils.segment`)
- **ToonOut (`joelseytre/toonout`) — SOTA for Anime:** BiRefNet fine-tuned on custom anime data (arXiv:2509.06839). Achieves **99.5% Pixel Accuracy** and **95.6% Boundary IoU**, excelling at delicate hair strands, hairpins, and transparent sleeves without background edge bleed.
- **ISNet-Anime (`imgutils.segment.segment_rgba_with_isnetis`):** Fast ONNX baseline (~1s per image). Cleanly separates character from backgrounds into RGBA transparent PNGs to prevent background style leakage into LoRA weights.
- **ViTMatte:** True continuous alpha matting ($\alpha \in [0, 1]$), ideal for ethereal auras, sheer robes, and sub-pixel hair decontaminating when paired with a coarse mask.

### C. Automated WD14 v3 SwinV2 Tagging & Captioning Sidecars
- Extract Danbooru tags via `get_wd14_tags(model_name='SwinV2_v3')`.
- Prepend trigger tokens (e.g. `yuemingkong, 1girl`).
- Automatically filter noise tags: `speech_bubble`, `english_text`, `watermark`, `comic`.
- Write sidecar `.txt` files directly alongside images.

## 6. Human-in-the-Loop Web UI & Ergonomics

Serve a lightweight FastAPI application on LAN/Tailscale (`0.0.0.0:8288`):
- Single-key hotkeys: `1`/`A` (approve), `2`/`R` (reject), `Space`/`→` (next), `←` (prev), `S` (segment), `T` (tag).
- Canvas overlay rendering detected eyes, face, and hand bounding boxes.
- Side-by-side original vs segmented transparency toggle.
- One-click export of approved items and `.txt` captions to the LoRA training directory (`data_root/10_<concept>/`).
- See [references/curator_webui_and_intelligence.md](references/curator_webui_and_intelligence.md) for full server and API implementation.

## 7. Discord Delivery UX Pattern

When delivering visual dataset digests to Discord:
- Place `MEDIA:/path/to/showcase.jpg` as the very first line of the message.
- Discord displays the visual media card prominently above the text briefing.

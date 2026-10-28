---
name: anime-character-dataset-curation
description: "Use when mining anime or manhua datasets for LoRA training."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [anime, manhua, dataset, curation, ccip, imgutils, waifuc, lora, segmentation]
---

# Anime & Manhua Character Dataset Curation

End-to-end architecture for mining characters, attires, and full-body illustrations from raw comic/manhua strip archives (`.cbz`, `.zip`, directories) using DeepGHS tools (`imgutils`, `waifuc`).

## 1. Gutter Panel Decomposition vs. Naive Sliding Window

### The Flaw of Fixed Sliding Windows:
Fixed-height sliding windows (e.g. 1,000px height with 700px step) arbitrarily cut tall vertical characters (full-body drawings in webtoons are typically 1,200px – 1,800px tall). This forces detectors to see only severed fragments, resulting in missing legs/robes or fragmented crops.

### Gutter Decomposition Strategy:
1. Webtoon strips are structured into panels separated by horizontal white, black, or monotone gutter lines.
2. Calculate row-wise standard deviation $\sigma_{\text{row}}$ and mean intensity $\mu_{\text{row}}$:
   - Gutter condition: $\sigma_{\text{row}} < 5.0$ or $\mu_{\text{row}} > 250$ (white) or $\mu_{\text{row}} < 10$ (black).
3. Group contiguous gutter rows $\ge 15\text{px}$ and split the 4,000px+ strip at gutter midpoints.
4. Each panel represents an author-composed scene where full-body characters and flowing robes reside in one unsegmented canvas.

### Webtoon Sliced Archives: Sliding Pair Seam Boundary Inspection
Many webtoon rip archives (`.cbz`, `.zip`) contain pre-sliced vertical chunks (e.g. fixed ~1,100px height per image) rather than full unbroken strips. In such archives, characters often have heads on page $N$ and torsos/legs on page $N+1$ (or even $N+2$), causing single-page detectors to see only severed foreheads or headless bodies.
- **Sliding Pair Buffer Strategy**:
  - Maintain a bounded seam canvas between consecutive pages $N$ and $N+1$:  
    $$\text{Canvas Seam} = [\text{Bottom } B\text{px of Page } N] + [\text{Top } B\text{px of Page } N+1]$$
    where $B \approx 600\text{--}800\text{px}$ (e.g. $B=700\text{px}$).
  - **Zero-Overlap Abutting Seam Verification**: Ripped webtoons typically follow a strict tile split with uniform width and zero vertical overlap between page $N$ bottom and page $N+1$ top. Verify with NCC or line continuity before complex warping.
  - **Crossing Rule**: Run person detection on the seam canvas, but ONLY accept candidates where bounding box strictly crosses the seam cut: $y_0 < B < y_1$.
  - **Intra-Page Safety**: During individual page scanning, suppress candidate bounding boxes touching extreme page borders ($y_0 \le 15\text{px}$ or $y_1 \ge H - 15\text{px}$) to avoid extracting fragmented cuts; the sliding seam buffer will reconstruct the complete subject whole.
  - **Memory Efficiency**: Avoids stitching entire chapters (200+ pages) into RAM at once; memory footprint stays bounded to single 2-page seam slices.


## 2. Character Identification via CCIP

- Model: `ccip-caformer-24-randaug-pruned` (`imgutils.metrics.ccip`).
- Multi-Reference Embedding:
  1. Extract embeddings for 3–5 clean reference images using `ccip_extract_feature(img)`.
  2. Merge into a unified target vector using `ccip_merge(ref_feats)`.
  3. Calculate visual difference for candidate crops using `ccip_difference(candidate_feat, merged_ref)`.
- Empirically Verified Thresholds:
  - `diff <= 0.05`: Exact 1:1 match across art style shifts.
  - `diff <= 0.08`: Pristine character matches with zero false-positive leakage.
  - `0.08 < diff <= 0.12`: Action shots, extreme lighting, heavy masks/silhouettes.
  - `diff > 0.18`: Distinct characters, antagonists, and environmental false positives.

## 3. Two-Tier Deduplication Architecture

### Tier 1: Intra-Page Overlapping Crops (Sliding Window Twins)
When multiple windows overlap or bounding boxes slightly shift around the same subject on the same page:
- Calculate **Intersection over Smaller Box** ($\text{IoS} = \frac{\text{Area}(\text{Inter})}{\min(\text{Area}_1, \text{Area}_2)}$) and horizontal overlap ($X\text{-overlap}$).
- If $\text{IoS} \ge 0.45$ and $X\text{-overlap} \ge 0.65$: flag as duplicate.
- Keep the candidate with higher resolution and complete padding; purge the truncated twin.

### Tier 2: Cross-Chapter Repeated Art & Cover Recaps
Manga scanlations repeatedly re-use credit banners, cover illustrations, and flashback panels across dozens of chapters:
- Compute perceptual hashes (`dHash` + `pHash`).
- Compare Hamming distance: if $\text{dist} \le 6$, group into a duplicate cluster.
- Retain the earliest chronological appearance (or highest resolution instance) and purge recurring copies.

## 4. Full-Body & Attire-Complete Preservation

To capture complete robes, dresses, sashes, and footwear without heuristic truncation:
1. **Remove artificial cropping**: Never force `detect_halfbody` or hardcoded height limits (`0.65 * bh`) when curating for costume/attire learning.
2. **DWPose Keypoint Verification**:
   - Run `dwpose_estimate(im)` to inspect OpenPose 18 keypoints.
   - Detect knees (indices 9, 12), ankles (10, 13), and feet.
   - If foot/ankle keypoints are detected, mark framing as `full_body`.
3. **Boundary Snapping**:
   - If the dress or robe hem bleeds toward the bottom border of the panel, snap the bounding box to the panel gutter to prevent cutting the dress hemline.

## 5. Intra-Framing Duplication & Dynamic Virtual Framing

### Character Tagging SOP: Appearance Absorption vs. Dedicated Attire Triggers
When preparing caption `.txt` files for character LoRAs:
1. **Appearance (Intrinsic Physical Features) -> OMIT FROM CAPTIONS (ABSORB):**
   - Permanent bodily anatomy, signature creature features, skin color, natural hair length/color, horn/tail/fin shapes, and facial features (e.g. `covered_eyes`, `mermaid`, `fish_tail`, `long_hair`, `white_hair`, `pointy_ears`, `breasts`, `navel`).
   - By omitting these from caption text, no separate token steals cross-attention weight; the features bind **100% directly to the character trigger**. The trigger alone reliably reproduces the full character appearance without requiring lengthy descriptive prompts.
2. **Attire & Props -> Dedicated Attire Triggers vs. Monolithic Tag Dropout:**
   - **Multi-Attire Datasets:** When the character has distinct multiple outfits (e.g. `miabodysuit` vs casual hoodie, or `pulsar_suit` vs swimsuit), absorb the canonical signature attire into an explicit trigger token (compound binding with `keep_tokens = 2`), omitting the attire trigger on casual/nude images.
   - **Monolithic / Single-Attire Datasets:** If the dataset features only a single canonical attire across all or nearly all images, **DO NOT create an artificial attire trigger**. Use a single character trigger (`keep_tokens = 1`), retain all attire/prop tags (`helmet`, `armor`, `trident`, `polearm`, `scales`) in the captions, and use **moderate tag dropout** (`--caption_tag_dropout_rate = 0.3 - 0.5`) across both attire and appearance descriptors.
   - **Props Invariant:** Ensure signature weapons/props (`trident`, `polearm`, `weapon`) are never omitted from captions when visible.
3. **Strict Artist Tag Prohibition:**
   - **NEVER** inject artist tags (e.g. `@artist`, `drawn_by_*`) or web meta-tags (`watermark`, `sample`) into training dataset captions. Strip Danbooru artist strings entirely during caption generation. Artist style tags (e.g. `@ciloranko`, `@ratatatat74`) are applied strictly at inference/generation time.
4. **Pre-Curated Retention Invariant:**
   - Pre-curated or user-restored image archives (`staging_images/<concept>`) require **100% retention**. Do not drop or purge images (e.g. via automatic multi-person filters). If secondary characters appear, caption them instead of discarding the image.

### The Intra-Framing Duplicate Problem:
When extracting both a Full-Body crop, a Cowboy shot, and a Close-up crop from the *exact same scene drawing*, the character's face and pose are repeated multiple times across the training set, causing epoch bias and overfitting.

### Zero-Duplication Architecture (Single Master Crop):
1. **One Master Crop per Scene**: Store only the largest unconstrained boundary as the physical master file.
2. **Facial Metadata Anchoring**: Store detected face coordinates (`faces_boxes`) in the item's metadata.
3. **Virtual Framing Hierarchy**:
   - A `full_body` master entity naturally encompasses `cowboy_shot`, `upper_body`, and `portrait`.
   - When filtering by `portrait`, full-body images with valid face boxes remain visible and accessible.
   - The UI provides an on-the-fly `[Full Attire] ⟷ [Portrait Zoom]` viewer without creating duplicate files on disk.
4. **On-the-Fly Export**: If a portrait-only LoRA is needed, crop to the face box during export without cluttering the master dataset with static twin crops.

### Character & Attire Crop Disentanglement (Breaking Spatial Co-occurrence Bleed):
When training a character with a signature outfit (e.g. `toolmia` + `miabodysuit`), if the head/face and outfit always appear together in full-scene crops, the model entangles the two, causing outfit bleed into casual prompts.
- **Disentanglement Ratio**:
  - **~40% Portrait / Face Crops**: Tagged with `[char_trigger], 1girl, solo, portrait, close-up, upper_body...` without the attire trigger. Teaches the model that identity resides solely in facial features, hair, and eyes.
  - **~30% Torso / Attire Crops**: Tagged with `[attire_trigger], bodysuit, gloves, headless, crop...` without the character trigger. Teaches the model the clothing construct in isolation.
  - **~30% Complete Upper Body / Cowboy Shot**: Tagged with both `[char_trigger]` and `[attire_trigger]`. Bridges identity and proportion.
- **DeepGHS Detached BBoxes Pitfall**:
  In `imgutils.detect`, functions return tuples containing the label and confidence:
  - `detect_faces`, `detect_eyes`: `((x0, y0, x1, y1), label, conf)` — unpack as `[b for b, l, s in faces]`, NEVER `[b, s in faces]`.
  - `detect_with_booru_yolo`: `((x0, y0, x1, y1), label, conf)` — unpack as `[b for b, l, s in booru]`.

## 6. Background Matting & Separation Model Landscape

1. **ToonOut (`joelseytre/toonout`) - SOTA for Anime:**
   - Architecture: BiRefNet fine-tuned on custom anime dataset (1,228 images).
   - Pixel Accuracy: **99.5%**, Boundary IoU: **95.6%**.
   - Preserves fine line art, delicate hair strands, hairpins, and transparent sleeves far better than general-purpose matting models.
2. **ISNet-Anime (`imgutils.segment.segment_rgba_with_isnetis`):**
   - Fast ONNX inference (~1s per image). Good baseline, but can bleed complex background architectural edges into hair boundaries.
3. **ViTMatte:**
   - True continuous alpha matting ($\alpha \in [0, 1]$). Ideal for semi-transparent fabrics, veils, and ethereal aura effects when supplied with a coarse mask.

## 7. Human-in-the-Loop Web UI Ergonomics

Host a dedicated FastAPI curator server:
- **Pre-Curated vs. Raw Archives Rule**:
  - When the user directs you to prepare a staging folder containing an already curated/restored set of images (e.g. `/mnt/data/finetune-anima/staging_images/<concept>` where images are already hand-picked or cleaned): **DO NOT route it to Curator WebUI**. The user has already performed manual curation; proceed directly to tag generation (`smart_tagger` / WD14), trigger decoupling, `dataset.toml`, and training preparation.
  - Reserve Curator WebUI strictly for raw, unfiltered comic/manhua strip extractions where candidate cuts need interactive visual screening and manual approval.
- **Single-Key Hotkeys**:
  - `1` / `A`: Approve and advance.
  - `2` / `R`: Reject and advance.
  - `Space` / `→`: Next image.
  - `←`: Previous image.
  - `S`: Run background matting (ISNet/ToonOut).
  - `T`: Run WD14 tagging.
- **Dynamic BBox Overlay**: Toggle canvas bounding boxes for eyes, hands, and faces.
- **Dynamic Portrait Toggle**: `[Full Attire] ⟷ [Portrait Zoom]` previewing face crops on the fly.
- **Interactive Canvas Reader & Live Cropper Tool**:
  - Expose original comic chapter/page anchors in item metadata (`chapter`, `page`).
  - Provide an interactive reading modal with live drag-and-drop bounding box selection over the full unsegmented page (or stitched sliding seam pair).
  - Include an instant endpoint `POST /api/custom_crop` to cut rect coordinates directly from source CBZ/ZIP canvas, generate thumbnails, save `.txt` sidecars, and register directly into the approved dataset gallery without manual external image editing.
- **One-Click Export**: Sync approved images and `.txt` sidecars directly to the Kohya LoRA training folder.
- **Master-Derived Non-Destructive Annotation Suite (Label Studio)**:
  - For preserving uncropped master artworks/spreads while annotating multi-crop regions, see `references/label-studio-bbox-workflow.md` (Label Studio local storage setup, XML labeling template for framing, and automated export script).
- **Macro Close-Up Bias Prevention (Framing Expansion)**:
  - When annotating focused concepts, items, or attire details, training solely on tight macro bounding boxes causes severe close-up bias on inference.
  - Annotate an expanded bounding box (`<Label> Expanded`) covering character upper-body / cowboy shot context.
  - During captioning, strip synonymous/adjacent concepts from target crops so the trigger token absorbs the concept, while retaining adjacent tags on non-target or hybrid devices.
- **Manga Monochrome Decoupling Invariant**:
  When processing manga datasets with black-and-white art, never strip `monochrome` or `greyscale` from captions. Keeping them ensures the character trigger does not entangle permanently with monochrome drawing style, allowing clean cross-style and color rendering.

## 8. Inference Profiling & Optimization Stack

When running large-scale mining (hundreds of chapters), serial single-sample ONNX inference causes high kernel launch overhead and GPU underutilization:

### Profiling Workload Distribution (Empirical Baseline):
- **Anatomy Detection Stack (54.2% runtime):** Running 4 independent detector sessions (`detect_faces`, `detect_eyes`, `detect_hands`, `detect_with_booru_yolo`) serially creates 4x redundant CUDA stream launches per match.
- **WD14 Tagging (20.6% runtime):** Single-sample SwinV2-v3 transformer forward pass ($B=1$) underutilizes Tensor Cores.
- **YOLO Person Detection (19.3% runtime):** Serial panel inference ($B=1$) across 4–6 panels per webtoon page.

### High-Throughput Optimization Recipes:
1. **Unified Anatomy Fusion (`UnifiedAnatomy`):**
   - Extract face box, hands, and booru landmarks in ONE single `booru_yolo` inference pass instead of 4 separate detector sessions.
   - **Performance:** Slashes anatomy latency from 78.5ms to 12.7ms (**6.20x speedup**, saving ~66ms per character match).
2. **Vectorized Panel Batching (`BatchedYOLOPerson`):**
   - Letterbox multiple panels across pages into a contiguous tensor `(B, 3, 640, 640)` and execute a single batched ORT forward pass.
   - **Performance:** Slashes detection latency from 39.3ms to 7.8ms per panel (**5.03x speedup** at $B=8$).
3. **Batched Tagging (`BatchedWD14Tagger`):**
   - Stack matched character crops into `(B, 448, 448, 3)` arrays for batched SwinV2 evaluation.
4. Reference Implementation:
   - Production engine located at `/mnt/data/finetune-anima/opt-curator-engine/curator_opt.py`.

## 9. Series & Manhwa Ingestion Architecture (Mihon Reference)

For building high-throughput, ban-resistant downloaders to fetch raw series/manhwa archives:
- See `references/mihon-downloader-architecture.md` for Mihon's core execution model (`DownloadManager`, `Downloader`, `RateLimitInterceptor`, 3-stage backoff retry 2s/4s/8s, in-memory CBZ streaming, and `ComicInfo.xml` generation).


# Non-Destructive BBox Annotation & Multi-Crop Dataset Generation

## Overview
When curating datasets where master artworks/manga spreads are precious, cropping images destructively causes permanent loss of high-resolution context. The recommended workflow is **Master-Derived Dataset Generation**:
1. Keep full-resolution master images intact in an archive/master directory (`/mnt/data/.../raw_masters`).
2. Annotate multiple non-destructive bounding boxes (e.g., cowboy shot, portrait, costume detail) with category labels and tag sidecars in a web annotation suite (Label Studio).
3. Run an automated Python exporter to extract pixel crops into a downstream Kohya/Anima dataset directory on demand.

## Label Studio Setup & Exposure
- **Virtualenv & Port**: Run under a dedicated venv on a clean port (e.g. `8085` if `8080` is taken by FileBrowser/Docker).
- **Environment Flags for Local Files**:
  ```bash
  export LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
  export LOCAL_FILES_SERVING_ENABLED=true
  export LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/mnt/data
  export LOCAL_FILES_DOCUMENT_ROOT=/mnt/data
  export DISABLE_SIGNUP_WITHOUT_LINK=false
  ```
- **Service Supervision**: Supervise via systemd user unit (`~/.config/systemd/user/label-studio.service`) bound to `0.0.0.0` for LAN (`192.168.1.X`) and Tailscale (`100.X.X.X`) access.

## Anime / Manga Multi-Crop XML Template
In Label Studio **Project Settings -> Labeling Interface -> Code**:
```xml
<View>
  <Image name="image" value="$image" zoom="true" zoomBy="1.2"/>
  
  <Header value="Select Crop / Framing Type"/>
  <RectangleLabels name="label" toName="image">
    <Label value="cowboy_shot" background="#3b82f6"/>
    <Label value="portrait" background="#10b981"/>
    <Label value="upper_body" background="#8b5cf6"/>
    <Label value="full_body" background="#64748b"/>
    <Label value="attire_focus" background="#f59e0b"/>
    <Label value="detail_close_up" background="#ec4899"/>
  </RectangleLabels>

  <Header value="Caption & Tags for this BBox"/>
  <TextArea name="caption" toName="image" editable="true" displayMode="tag"
            rows="2" maxSubmissions="5" placeholder="Optional Danbooru tags, trigger, or description for this crop..."/>
</View>
```

## Storage Connection
1. In Project Settings -> **Cloud Storage** -> **Add Source Storage**.
2. **Storage Type**: `Local files`.
3. **Absolute local path**: `/mnt/data/finetune-anima/raw_masters` (or your master directory).
4. Check **Treat every bucket object as a source file** -> Click **Sync Storage**.

## Exporting to Training Dataset
Export project as JSON from Label Studio UI, then run the extractor script:
```bash
/mnt/data/label-studio/venv/bin/python /mnt/data/label-studio/export_crops_to_dataset.py \
  --json /path/to/project_export.json \
  --output /mnt/data/finetune-anima/data_root_target/10_charname \
  --min-size 64
```
- Automatically resolves both local source directories (`/data/local-files/?d=...`) and direct Label Studio web uploads (`/data/upload/...`).
- Converts percentages `[x, y, w, h]` back to original master image pixels.
- Supports affine rotation transforms for boxes with non-zero rotation angles (`rot != 0`).
- Converts transparent alpha channels (RGBA) cleanly to RGB on solid white background to avoid black background artifacts.
- Emits paired `<crop_name>.png` and `<crop_name>.txt` containing framing tag and user-specified caption tokens.
- Filters out accidental micro-clicks (`--min-size 64`).

## Macro Close-Up Bias Prevention & Concept Isolation Protocol

1. **The Close-Up Pitfall:**
   - When curating specific accessories, devices, or focused garments (e.g. chastity cages, rings, belts, shoes), training exclusively on tight macro crops forces the LoRA to entangle the trigger token with macro close-up framing. On inference, generating normal character compositions (cowboy shot, portrait, full body) becomes impossible.
2. **Two-Box Strategy (Expanded Framing BBox):**
   - In Label Studio, annotate an expanded bounding box (`<Label> Expanded`) covering normal character context (e.g. cowboy shot, upper body, environment) in addition to or in place of the tight detail box.
3. **Concept Isolation vs. Negative Variant Retention:**
   - **Target Concept Crops:** Strip synonymous/adjacent concept tags (e.g. `chastity_cage`, `chastity`, `cage`, `lock`, `padlock`, `sex_toy`, `restraints`) from captions. This forces the model's cross-attention to bind the visual feature 100% to your custom trigger token (e.g. `flat chastity cage`).
   - **Edge Cases & Non-Target Devices:** If a sample in the dataset depicts an adjacent or different device (e.g. a cock ring or non-flat cage), **retain** its adjacent tags so the model learns to attribute that non-target device to its respective tag rather than polluting the primary trigger.


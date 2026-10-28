---
name: label-studio-dataset-curation
description: "Use when annotating or exporting crops with Label Studio."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [label-studio, bounding-box, dataset, curation, cropping, lora, export]
---

# Label Studio Dataset Curation Playbook

Best practices and automated workflows for using Label Studio to create non-destructive multi-crop training datasets from raw master images.

## 1. Environment & Architecture

- **Host Service:** Managed via systemd user unit `label-studio.service`.
- **Ports & Bindings:** Internal host `0.0.0.0`, port `8085` (avoids port 8080 used by FileBrowser).
  - LAN: `http://192.168.1.23:8085`
  - Tailscale: `http://100.91.215.116:8085`
  - Local: `http://localhost:8085`
- **Data Root & Storage:** Database and uploads reside in `/mnt/data/label-studio/data`.
- **Environment Flags for Local Files:**
  ```bash
  LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
  LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/mnt/data
  ```

## 2. Minimal Single-Label XML Config (e.g. `FCC`)

For simple bounding-box cropping where each box is a single crop type:

```xml
<View>
  <Image name="image" value="$image" zoom="true" zoomBy="1.2"/>
  
  <RectangleLabels name="label" toName="image">
    <Label value="FCC" background="#3b82f6"/>
  </RectangleLabels>

  <TextArea name="caption" toName="image" editable="true" displayMode="tag"
            rows="2" maxSubmissions="5" placeholder="Optional tags or notes for this crop..."/>
</View>
```

### Key UI Features:
- **Hotkeys:** Press `1` to activate the `FCC` rectangle tool.
- **Multi-BBox:** Multiple rectangles can be drawn on the same image canvas.
- **Non-Destructive:** Master files are left untouched; coordinates are stored as percentages in JSON tasks.

## 3. Connecting Master Archives (Local Storage)

1. Open project in browser -> **Settings** -> **Cloud Storage** -> **Add Source Storage**.
2. **Storage Type:** `Local files`.
3. **Absolute local path:** Target image directory (e.g. `/mnt/data/finetune-anima/raw_masters`).
4. Check **Treat every bucket object as a source file**.
5. Click **Sync Storage**.

## 4. Exporting BBoxes to Training Dataset

To extract bounding boxes into individual `.png` files with corresponding `.txt` captions:

1. In Label Studio UI, click **Export** -> select **JSON**.
2. Run the dedicated extractor script:
   ```bash
   /mnt/data/label-studio/venv/bin/python /mnt/data/label-studio/export_crops_to_dataset.py \
     --json /path/to/project_export.json \
     --output /mnt/data/finetune-anima/data_root_target/10_triggername \
     --trigger fcc \
     --prefix crop
   ```

### Script Behavior:
- Automatically resolves both local source directories (`/data/local-files/?d=...`) and direct Label Studio web uploads (`/data/upload/...`).
- Supports affine rotation transforms for boxes with non-zero rotation angles.
- Converts percentage coordinates `[x, y, w, h]` into high-precision pixel crops.
- Automatically handles RGBA/palette images with clean white backgrounds.
- Parses tags from the `<TextArea>` component into comma-separated sidecar `.txt` files.
- Filters out accidental micro-clicks (`--min-size 64`).

# Figma GUI Storyboard Extraction & Traceability

This guide details how AI agents connect to Figma design files to inspect prototypes, extract screen hierarchies, and maintain consistency with UML models (ICONIX Domain Model, Use Cases, and Boundary Objects).

## 1. Connecting to Figma via Composio CLI

When Composio is authenticated with the `figma` toolkit (check via `composio search figma` or `composio whoami`):

### A. Extract File Hierarchy & Screen Names
To get top-level frames, sections, and canvas screens:
```bash
# Get file metadata and canvas sections (depth 1 or 2)
composio execute FIGMA_GET_FILE_JSON -d '{"file_key": "<FILE_KEY>", "depth": 2}'

# Target specific section IDs (e.g. Task flows, Subflows)
composio execute FIGMA_GET_FILE_JSON -d '{"file_key": "<FILE_KEY>", "ids": "12:718,12:1072", "depth": 2}'
```
*Note: Extract the `<FILE_KEY>` from the URL: `figma.com/design/<FILE_KEY>/<TITLE>?...`*

### B. Render Screen Frames to Direct Image URLs
To visually inspect a screen without launching a desktop browser:
```bash
composio execute FIGMA_RENDER_IMAGES_OF_FILE_NODES -d '{
  "file_key": "<FILE_KEY>",
  "ids": "12:812,12:719",
  "scale": 1,
  "format": "png"
}'
```
The response returns signed AWS S3 image URLs (`data.images["<node_id>"]`) valid for direct download via `curl` and previewing in chat via `MEDIA:`.

---

## 2. Generating the Screen List Artifact for Submissions

Academic and enterprise projects (e.g., PPPL assignments) frequently require:
- A text file containing the exact list of screens present in the GUI Storyboard / Hi-Fi Prototype.

### Extraction Pattern in Python:
```python
import json

# Process output from FIGMA_GET_FILE_JSON
with open('figma_nodes.json') as f:
    data = json.load(f)

screens = []
for node in data.get('data', {}).get('nodes', []):
    section_name = node.get('name')
    for child in node.get('children', []):
        if child.get('type') == 'FRAME':
            screens.append(f"{section_name} -> {child.get('name')}")

with open('daftar_screen_gui_storyboard.txt', 'w') as f:
    f.write('\n'.join(screens))
```

---

## 3. Mapping Figma Screens to ICONIX Modeling Artifacts

To maintain strict consistency across design phases:

1. **Boundary Objects in Robustness Analysis:**
   - Every user-facing Figma screen maps to a `boundary` element in the Robustness Diagram.
   - Example: `Login Page - Log in` in Figma -> `boundary "LoginBoundary"` in PlantUML.
   - Example: `Top Up - Balance` in Figma -> `boundary "TopUpBalanceBoundary"` in PlantUML.

2. **Domain Model Entity Discovery:**
   - Read the input fields, table columns, and cards displayed on the Figma screens.
   - Real-world nouns displayed in the UI (e.g., `Saldo`, `MetodePembayaran`, `LaporanKejadian`, `StatusLaluLintas`) become the core classes in the Initial Domain Model.

3. **Use Case Alignment:**
   - Every primary interactive button or navigation flow (e.g., "Submit Laporan", "Top Up Saldo", "Lacak LRT") must correspond to a distinct Use Case.

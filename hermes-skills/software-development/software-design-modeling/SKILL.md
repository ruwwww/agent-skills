---
name: software-design-modeling
description: Use when designing software architectures or UML diagrams.
---

# Software Design & UML Modeling

A class-level skill for producing formal software architecture designs, system models, and design documentation (SRS / SDD) using Diagram-as-Code (DaC) with seamless bridges to visual modeling suites like Visual Paradigm.

## When to Use

- Designing software services, microservices, or full-stack architectures.
- Generating formal UML 2.5 models: Use Case, Class Diagram, Sequence Diagram, Activity Diagram, Component Diagram, Deployment Diagram.
- Designing relational database schemas (ERD / Chen / Crow's Foot).
- Authoring Software Requirements Specifications (SRS) or Software Design Documents (SDD).
- Bridging AI agent designs to enterprise/academic desktop modeling tools like Visual Paradigm Community Edition.

## The Diagram-as-Code (DaC) Core Standard

AI agents must **never** attempt to construct proprietary binary project files (such as `.vpp` from Visual Paradigm) directly. The agent standard is **text-first Diagram-as-Code**:

1. **PlantUML (`.puml`):** The primary standard for formal UML 2.5, C4 models, and enterprise architecture. Preserves strict semantics (visibility, stereotypes, interfaces, associations, multiplicities).
2. **Mermaid.js (`.mmd`):** The standard for inline Markdown documentation (GitHub, GitLab, Notion, PR previews). Best for high-level flows, fast sequences, and READMEs.
3. **Structurizr / C4 DSL:** For multi-tier software system architecture (Context, Container, Component, Code).

## Visual Paradigm Interoperability Bridge

Academic and enterprise environments often require submissions in Visual Paradigm. Do **not** try to automate VP via unstable third-party MCP plugins (e.g. `orgatex/visual-paradigm-mcp-plugin` has unimplemented stub tools and requires an active desktop GUI).

Use the official, friction-free interoperability paths:

### Method 1: VPasCode & VP Pipeline (Recommended)
1. Agent generates syntactically valid PlantUML or Mermaid code.
2. In browser, open **Visual Paradigm VPasCode** (or AI Chatbot in VP Online).
3. Paste the code, verify rendering, and click **Export > Send to Pipeline**.
4. In Visual Paradigm Desktop, open **Project > Import > Visual Paradigm Pipeline**.
5. Select the diagram. VP will convert the text code into native, interactive model elements that can be repositioned and styled.

### Method 2: Code Reverse Engineering
1. Agent writes skeleton code (e.g. Java interfaces/POJOs, TypeScript interfaces, Python dataclasses).
2. In Visual Paradigm Desktop: **Tools > Code > Reverse Java / C++ Code**.
3. VP automatically generates the Class Diagram and model elements.

*See `references/visual-paradigm-interop.md` for detailed gotchas on Community Edition watermarks and CLI limitations.*

## Diagram Selection Guide

| Need | Recommended Diagram | Syntax |
|---|---|---|
| User interactions & system boundaries | Use Case Diagram | PlantUML |
| Preliminary design / BCE analysis (ICONIX) | Robustness Diagram | PlantUML |
| System logic & business workflows | Activity Diagram | PlantUML / Mermaid |
| Business processes & multi-actor swimlanes | BPMN 2.0 Diagram | PlantUML / SVG / Kroki |
| Object interactions & API call flows | Sequence Diagram | PlantUML / Mermaid |
| Domain model, entities, OOP design | Class Diagram | PlantUML |
| Relational data model & keys | ER Diagram (Crow's Foot) | PlantUML / Mermaid |
| Service components & dependencies | Component Diagram / C4 Container | PlantUML |
| Infrastructure, Docker, servers | Deployment Diagram | PlantUML |

## Headless Rendering & Discord Delivery

When delivering designs in conversations:
1. Save the `.puml`, `.mmd`, or `.svg` source file to the project directory so the user owns the editable source.
2. Render to PNG/SVG using either:
   - **Local CLI Helper:** `puml-render <file.puml> [png|svg] [output_path]` (pre-installed at `~/.hermes/bin/puml-render`).
   - **Local Java Compiler:** `java -jar ~/.hermes/bin/plantuml.jar input.puml` (for sequence diagrams).
   - **Kroki HTTP API:** Zero-dependency HTTP POST to `https://kroki.io/plantuml/png` or `https://kroki.io/bpmn/svg`.
   - **Headless Chromium for SVG/BPMN:** `/snap/bin/chromium --headless --disable-gpu --window-size=1550,890 --default-background-color=ffffffff --screenshot=/home/<user>/out.png file:///home/<user>/in.svg`. *Crucial pitfall:* Snap AppArmor blocks `/tmp/` paths—always keep source SVGs and target PNGs inside the user's home directory.
3. **Pre-delivery Visual Verification:** Run `vision_analyze` on the generated diagram to verify text legibility, gateway labeling, and ensure connector lines do not slice through task boxes.
4. **Layout & Aspect Ratio Optimization (1:1 Square Balance):**
   - For presentation decks, slide embeds, and Discord, avoid panoramic runaway sprawl (e.g. 5:1 wide strips caused by unconstrained `left to right direction`).
   - Use top-center root anchoring, symmetrical vertical tiering, and hidden directional constraints (`-[hidden]down->`) to enforce compact, balanced ~1:1 square layouts.
5. **Discord Delivery Robustness:**
   - Avoid multiple `MEDIA:` lines in a single response message; Discord bot integrations often drop subsequent attachments or fail to render preview tiles. Prefer delivering one primary diagram per turn.
   - **Delivery Mode:** When the user asks for updated renders or visual reviews, provide the rendered visual artifacts directly with concise architectural explanations. Omit raw diagram code blocks (`.puml`, `.mmd`) from the message body unless the user explicitly asks for the raw source code.
   - Always commit and track diagram source files (`.puml`, `.drawio`) and rendered outputs (`.png`) in local Git version control within the project directory.

## Linked References & Templates

- `references/drawio-mcp-and-interop.md` — Draw.io MCP server (`@drawio/mcp`), 1-click interactive URL generation (`#R<deflate_b64>`), ELK automated layouts, obstacle-avoiding edge routing (`libavoid`), and native `.drawio` XML generation.
- `references/iconix-process.md` — Complete ICONIX Process guide: 4 phases, 3 milestones, BCE rules, noun extraction & filtering pipeline (Class vs Attribute vs Instance), 1:1 aspect ratio layout optimization, and Laravel MVC backend controller mapping for simplified As-Is Figma robustness models.
- `references/figma-storyboard-extraction.md` — Extracting GUI storyboards and screen hierarchies from Figma via Composio CLI and mapping them to UML boundary objects.
- `references/pppl-prerequisite-review-patterns.md` — Course patterns connecting ASD (OOP), SBD (DB/ERD), DPP (Figma UI/UX), and RKPL (Use Case scenarios).
- `references/bpmn-modeling-and-rendering.md` — BPMN 2.0 standards, swimlane gutter rules, Snap Chromium headless rendering, and vision verification.
- `references/visual-paradigm-interop.md` — Visual Paradigm CE limitations, VPasCode bridge, and MCP plugin landscape.
- `references/plantuml-cheatsheet.md` — OMG UML 2.5 syntax templates for Use Case, Sequence, Class, ERD, and Robustness diagrams.
- `references/software-review-presentation-scripts.md` — Segmented presentation and video review scripts bridging prerequisites (OOP, DB/ERD, UI/UX Figma, and SRS Use Cases).
- `templates/software-design-document.md` — Comprehensive SRS/SDD markdown template.
- `scripts/puml-render.py` — Zero-dependency Python CLI to render `.puml` files to PNG/SVG via Kroki HTTP API (requires explicit User-Agent header to avoid Cloudflare 403).

## Cloud Document & Asset Delivery (Google Docs & Drive via Composio)

When users request to export or save software design deliverables, domain models, or architecture specs directly to Google Docs or Google Drive:
- Do NOT perform raw manual Drive API uploads.
- **Embedded Visuals in Google Docs:** Use Composio CLI action `composio execute GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN -d @/path/to/payload.json`.
  To embed rendered diagrams directly inline, supply the `image_assets` array:
  ```json
  {
    "title": "Document Title",
    "markdown_text": "# Use Case UC01\n\n![UC01](attachment://UC01.png)\n",
    "image_assets": [
      {"name": "UC01.png", "file": "/home/user/path/to/UC01.png"}
    ]
  }
  ```
- **Standalone Diagram Folders in Google Drive:**
  1. Create a dedicated folder: `composio execute GOOGLEDRIVE_CREATE_FOLDER -d '{"name": "Project_Robustness_Diagrams"}'` -> retrieve `data.id`.
  2. Batch upload diagram files: `composio execute GOOGLEDRIVE_UPLOAD_FILE -d '{"file_to_upload": "/path/to/diagram.png", "folder_to_upload_to": "<FOLDER_ID>"}'`.
- **Complete Suite Execution:** When penning preliminary design deliverables for a multi-use-case project (e.g. 21 use cases), script the batch generation of all `.puml` files, compile with `puml-render`, upload all PNGs to Google Drive, and embed them into the master Google Docs so every team member can immediately review or submit their assigned diagram.

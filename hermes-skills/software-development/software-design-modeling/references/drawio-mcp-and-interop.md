# Draw.io MCP Server & Diagram Interoperability

## Overview

Draw.io (diagrams.net) is a versatile, web-and-desktop visual diagramming suite. Unlike Visual Paradigm's proprietary `.vpp` binary format, Draw.io uses an open, human-readable XML format (`.drawio` / `mxGraphModel`) and offers official MCP integration via `jgraph/drawio-mcp`.

## Draw.io MCP Server Architecture

The official Draw.io MCP repository (`https://github.com/jgraph/drawio-mcp`) provides two integration vectors:

### 1. MCP Tool Server (`@drawio/mcp` on npm)
- **Runtime:** Node.js stdio MCP server (`npx -y @drawio/mcp`).
- **Tools Provided:**
  - `open_drawio_xml`: Opens the diagram directly in the user's browser editor (`app.diagrams.net`) or desktop app.
  - `search_shapes`: Searches across 10,000+ draw.io shape libraries (AWS, GCP, Azure, Cisco, UML, BPMN, ERD).
- **Automated Layout & Routing:**
  - `postLayout: "elk"`: Runs server-side Eclipse Layout Kernel (ELK) to position vertices and route edges automatically.
  - `routing: "libavoid"`: Runs obstacle-avoiding orthogonal edge-routing to prevent connector lines from cutting through boxes.

### 2. Hermes Native MCP Client Integration
Add to `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  drawio:
    command: "npx"
    args: ["-y", "@drawio/mcp"]
    timeout: 60
```

## When to Use Draw.io vs PlantUML vs Visual Paradigm

| Use Case | Recommended Tool | Rationale |
|---|---|---|
| **Domain Modeling (ICONIX)** | Draw.io / PlantUML | Focuses on pure business concepts, generalisation (`is-a`), and aggregation (`has-a`) without enforcing rigid programming language types or database foreign keys. |
| **Formal UML 2.5 (Use Case, Sequence, Class)** | PlantUML (`.puml`) | Strict syntax, automatic sequence lifeline activation, exact stereotype notations. Easily imported into VP via VPasCode. |
| **Academic Deliverable / `.vpp` Submission** | Visual Paradigm Desktop | Import `.puml` via VP Pipeline or open `.drawio` in Draw.io. |

## 1-Click Interactive Browser URL Generation (`#R<deflate_b64>`)

Rather than requiring users to manually download and drag-and-drop `.drawio` files, agents can generate a direct 1-click URL that opens the full, editable vector diagram in `app.diagrams.net`:

```python
import base64
import urllib.parse
import zlib

# Draw.io URL format uses raw deflate without zlib header/checksum ([2:-4])
compressed = zlib.compress(drawio_xml.encode('utf-8'))[2:-4]
b64 = base64.b64encode(compressed).decode('utf-8')
encoded_url = urllib.parse.quote(b64)
direct_url = f'https://app.diagrams.net/#R{encoded_url}'
```

Clicking this link automatically decodes and launches the diagram on `app.diagrams.net` in the user's browser ready for editing or export.

## Generating Native `.drawio` XML

A standard `.drawio` file is XML enclosing `mxGraphModel`. Example minimal template:

```xml
<mxfile host="app.diagrams.net" agent="HermesAgent" version="24.0.0">
  <diagram id="diagram-1" name="Domain Model">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="c1" value="Pengguna" style="swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="140" height="40" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Files saved with the `.drawio` extension can be opened directly by dragging into `https://app.diagrams.net` or opening with Draw.io Desktop.

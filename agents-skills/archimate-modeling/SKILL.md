---
name: archimate-modeling
description: Connect to and manipulate ArchiMate 3.2 enterprise architecture models in Archi via MCP or CLI. Use when the user wants to inspect, query, create, update, auto-layout, or diagram architecture models, elements, relationships, or views in Archi.
---

# ArchiMate Modeling Skill (Archi MCP Integration)

Connect to and manipulate **Archi** (ArchiMate Modeling Tool) in real-time via the embedded Archi MCP server (`http://127.0.0.1:18090/mcp`).

## CLI Utility (Preferred for Deterministic Execution)

Run commands using the bundled CLI script at `scripts/archi.py` relative to this skill:

```bash
ARCHI_CLI="$HOME/.agents/skills/archimate-modeling/scripts/archi.py"

# Model inspection
python "$ARCHI_CLI" info
python "$ARCHI_CLI" views
python "$ARCHI_CLI" view-contents <viewId>
python "$ARCHI_CLI" search "Pasien"

# Concept & Relationship mutations
python "$ARCHI_CLI" create-element --type ApplicationComponent --name "Payment Gateway" --doc "Sistem Pembayaran"
python "$ARCHI_CLI" create-rel --type ServingRelationship --source <id1> --target <id2>

# Diagram composition & ELK layout
python "$ARCHI_CLI" create-view --name "Payment Architecture"
python "$ARCHI_CLI" add-to-view --view-id <viewId> --element-id <elId> --auto-connect
python "$ARCHI_CLI" auto-connect <viewId>
python "$ARCHI_CLI" auto-layout <viewId> --direction DOWN
python "$ARCHI_CLI" export-view <viewId> diagram.png

# Raw MCP tool invocation (for any of the 70 Archi MCP tools)
python "$ARCHI_CLI" call <toolName> '{"param": "val"}'
```

## Standard Workflows

### 1. Model Inspection
1. Call `info` to verify active model, version, and element counts.
2. Call `views` to see available diagrams.
3. Call `search <query>` to locate existing concepts before creating new ones.

### 2. Element & Relationship Creation
Follow ArchiMate 3.2 layers (see [references/archimate-layers.md](references/archimate-layers.md)):
- **Business Layer**: `BusinessActor`, `BusinessRole`, `BusinessProcess`, `BusinessService`, `BusinessObject`
- **Application Layer**: `ApplicationComponent`, `ApplicationInterface`, `ApplicationService`, `DataObject`
- **Technology Layer**: `Node`, `Device`, `SystemSoftware`, `TechnologyService`, `Artifact`
- **Motivation Layer**: `Stakeholder`, `Driver`, `Goal`, `Requirement`

Follow metamodel rules (see [references/archimate-relationships.md](references/archimate-relationships.md)):
- `ServingRelationship` (A serves B)
- `RealizationRelationship` (Component realizes Service, Node realizes SystemSoftware)
- `AccessRelationship` (Process/Service accesses BusinessObject/DataObject)
- `AssignmentRelationship` (Actor assigned to Role/Process)
- `TriggeringRelationship` (Event triggers Process, Process triggers Process)

### 3. Diagram Generation & Layout
1. Call `create-view` with `name` and `connectionRouterType: "manhattan"`.
2. Add elements to view via `add-to-view` with `--auto-connect`.
3. Call `auto-layout <viewId> --direction DOWN` for automated ELK layered layout.
4. Export high-res diagram with `export-view <viewId> <output.png>`.

## Recipes & Patterns
See bundled guides in `references/`:
- [references/recipes/index.md](references/recipes/index.md) - Common architecture recipe catalog
- [references/recipes/application-integration.md](references/recipes/application-integration.md) - Application integration patterns
- [references/recipes/technology-deployment.md](references/recipes/technology-deployment.md) - Infrastructure & deployment views
- [references/recipes/behaviour-process-flow.md](references/recipes/behaviour-process-flow.md) - Business process & flow modeling

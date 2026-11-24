---
name: archimate-solution-design
description: Design and generate end-to-end ArchiMate 3.2 enterprise architecture models and diagrams in Archi from business requirements or technical specifications. Use when the user asks to design architecture for a new system, create multi-layer ArchiMate views, map business processes to applications and infrastructure, or model enterprise solutions in Archi.
---

# ArchiMate Solution Design

A structured workflow for translating system requirements into compliant, well-formed ArchiMate 3.2 architecture models in Archi.

## 4-Phase Architecture Workflow

### Phase 1: Requirements & Layer Decomposition
Break down the system into the standard 3-tier EA stack:
1. **Business Layer** (Yellow `#ffffb5`):
   - Actors & Roles (who interacts? e.g. Customer, Admin, Cashier)
   - Business Services & Processes (what capabilities/workflows are exposed? e.g. Order Placement, Payment Verification)
   - Business Objects (what core business data? e.g. Invoice, Order, Patient Record)
2. **Application Layer** (Blue `#b5ffff`):
   - Application Components (what software modules/apps exist? e.g. Mobile App, Payment Gateway API, Core Banking)
   - Application Services (what technical functionality is served? e.g. Payment Processing Service, Auth Service)
   - Data Objects (data structures realized by components)
3. **Technology Layer** (Green `#c9e7b7`):
   - Nodes & Devices (servers, Kubernetes clusters, mobile devices)
   - System Software (Docker, PostgreSQL, Redis, Envoy)
   - Technology Services (Hosting Service, Database Storage, Message Queue Service)

### Phase 2: Metamodel Validation
Ensure semantic integrity before creating in Archi:
- **Serving**: `ApplicationComponent` / `ApplicationService` serves `BusinessProcess` / `BusinessActor`
- **Realization**: `ApplicationComponent` realizes `ApplicationService`; `Node` realizes `TechnologyService`
- **Access**: `BusinessProcess` accesses `BusinessObject`; `ApplicationComponent` accesses `DataObject`
- **Assignment**: `BusinessActor` is assigned to `BusinessRole` / `BusinessProcess`

### Phase 3: Automated Creation via Archi CLI
Execute deterministically using `~/.agents/skills/archimate-modeling/scripts/archi.py`:

```bash
ARCHI_CLI="$HOME/.agents/skills/archimate-modeling/scripts/archi.py"

# 1. Create Elements (Business -> Application -> Tech)
python "$ARCHI_CLI" create-element --type BusinessActor --name "Pelanggan"
python "$ARCHI_CLI" create-element --type BusinessProcess --name "Proses Pembayaran"
python "$ARCHI_CLI" create-element --type ApplicationService --name "Payment API Service"
python "$ARCHI_CLI" create-element --type ApplicationComponent --name "Payment Service"
python "$ARCHI_CLI" create-element --type Node --name "Kubernetes Worker Node"

# 2. Create Relationships
python "$ARCHI_CLI" create-rel --type AssignmentRelationship --source <actor_id> --target <proc_id>
python "$ARCHI_CLI" create-rel --type ServingRelationship --source <app_svc_id> --target <proc_id>
python "$ARCHI_CLI" create-rel --type RealizationRelationship --source <comp_id> --target <app_svc_id>
python "$ARCHI_CLI" create-rel --type RealizationRelationship --source <node_id> --target <comp_id>
```

### Phase 4: View Generation & Visual Layout
1. **Create View**:
   ```bash
   python "$ARCHI_CLI" create-view --name "<System Name> - Solution Architecture" --router manhattan
   ```
2. **Place Elements**:
   Add all created elements with `--auto-connect`:
   ```bash
   python "$ARCHI_CLI" add-to-view --view-id <viewId> --element-id <elId> --auto-connect
   ```
3. **Run ELK Auto-Layout**:
   ```bash
   python "$ARCHI_CLI" auto-layout <viewId> --direction DOWN
   ```
4. **Export Image & Present**:
   ```bash
   python "$ARCHI_CLI" export-view <viewId> "./solution-architecture.png"
   ```

## Design Principles
- **No Orphan Elements**: Every element must connect to at least one relationship.
- **Top-Down Flow**: Business layer on top, Application in middle, Technology at the bottom.
- **Minimal Complexity**: Start with the core happy path before adding auxiliary logging, monitoring, or edge cases.

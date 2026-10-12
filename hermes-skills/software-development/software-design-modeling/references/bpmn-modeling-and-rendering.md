# BPMN 2.0 Modeling & Headless Rendering Guide

A practical reference for generating publication-grade BPMN 2.0 diagrams, modeling multi-stakeholder collaboration across swimlanes, and rendering crisp images in headless Linux environments.

---

## 1. BPMN 2.0 vs. UML Activity Diagrams

Do not confuse BPMN with UML Activity Diagrams when users request BPMN:

| Feature | BPMN 2.0 Standard | UML Activity Diagram |
|---|---|---|
| **Start Event** | Thin open circle (often green outline) | Solid filled circle |
| **End Event** | Thick/double circular border (often red outline) | Bullseye (circled dot) |
| **Gateways** | Diamonds with explicit markers: Exclusive (`X`), Parallel (`+`), Inclusive (`O`) | Plain diamonds without inner markers |
| **Pools vs Lanes** | Separate Pools represent distinct organizations/systems; Lanes represent internal departments/roles | Partitions/swimlanes without strict message flow semantics |
| **Flow Semantics** | Solid sequence flows strictly inside a pool; dashed open-arrow message flows across pools | Solid arrows across all partitions |
| **Annotations** | Open bracket `[` with dotted callout line | Dog-eared rectangle or note box |

---

## 2. Multi-Stakeholder Swimlane Layout Principles

When modeling university or enterprise service processes (e.g. course registration, incident response, order fulfillment):

1. **Order of Lanes:** Place the primary end-user (e.g. Mahasiswa / Customer) at the top lane, followed by the automated platform/core database, then technical ops/service providers, policy makers (e.g. BAAK/Kaprodi), and finally approvers/management (e.g. Dosen Wali).
2. **Dedicated Gutters for Flow Lines:**
   - Never allow vertical or horizontal connector lines to pass through any task rectangle or text label.
   - Ensure a minimum gutter of 30–50px between tasks in the same lane so vertical transition arrows can travel cleanly.
3. **Return & Revision Loops:**
   - Rejections and retry loops must route cleanly around all activities (e.g. using the outer boundary gutter of the pool or an explicit intermediate event), terminating at the top/bottom port of the target task.
4. **Marking Critical Moments (*Moments of Truth*):**
   - Highlight high-risk or bottleneck tasks (e.g. peak traffic submit) with distinctive semantic styling (e.g. soft red fill, bold border, and a BPMN annotation bracket).

---

## 3. Headless SVG to PNG Rendering via Chromium

When rendering high-resolution diagrams for Discord or Markdown embedding:

### Critical Linux / Snap Confinement Pitfall:
On Ubuntu distributions where Chromium is installed via Snap (`/snap/bin/chromium`):
- **Snap AppArmor strictly denies access to `/tmp/`**. Rendering a file like `/tmp/diagram.svg` or writing `--screenshot=/tmp/out.png` will fail silently or throw `No such file or directory`.
- **Always use paths inside the user home directory** (`/home/<user>/...`), e.g.:
  ```bash
  /snap/bin/chromium --headless --disable-gpu \
    --window-size=1550,890 \
    --default-background-color=ffffffff \
    --screenshot=/home/kuroko/output.png \
    file:///home/kuroko/input.svg 2>/dev/null
  ```

---

## 4. Visual Quality Verification via `vision_analyze`

Before sharing the rendered image with the user, always inspect with `vision_analyze`:
1. Check for lines slicing through text boxes or labels.
2. Verify that gateways have proper labels (`Valid?`, `Overload?`, `Disetujui?`) without overlapping adjacent lines.
3. Ensure the final End Event is unobstructed and clearly labeled.

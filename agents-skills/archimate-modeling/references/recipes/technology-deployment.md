# Recipe Family — Technology / Deployment

Topology archetype: **nodes as large containers with their deployed software/artifacts nested inside, wired by network links**. Apply the invariant build sequence from the index; only the deltas below change.

This recipe exists because the deployment shape is carried by *containment*, not by drawn deployment arrows: the generic principles know "nest parts" but not that an entire deployment view is built from node-containers joined by network links. Match the topology block.

## Technology / Deployment View (ArchiMate "Technology" / "Implementation and Deployment" viewpoint)

- **When to use:** show *what runs where* — application components and artifacts deployed onto infrastructure nodes, the system software hosting them, and the networks between nodes. Used for infrastructure, hosting, and deployment-topology diagrams.
- **`viewpoint` parameter:** use your tool's identifier for the ArchiMate *Technology* viewpoint (or *Implementation and Deployment* when the view includes deployed application elements — commonly `technology` / `implementation_deployment`); if the tool rejects it, omit `viewpoint` and build a general-purpose view. The topology below is what matters, not the viewpoint tag.
- **Element subset:** `Node`, `Device`, `SystemSoftware`, `Artifact`, `TechnologyService`, and the deployed `ApplicationComponent` when the view shows app-to-infra deployment. `CommunicationNetwork` and `Path` are themselves Technology-layer **elements** (not relationships) — place one on the view only when the network itself is worth showing. The **node is the container**; software, artifacts, and deployed components are its nested members.
- **Relationship subset:**
  - **Draw:** `AssociationRelationship` for the node-to-node network link — ArchiMate has **no "Path" relationship**; a network connection between nodes is an `AssociationRelationship` (or, when a `CommunicationNetwork`/`Path` *element* is placed, an `AssociationRelationship` from each `Node` to that element). `ServingRelationship` from a `TechnologyService` up to what it serves.
  - **Imply by nesting, exclude from the filter:** `AssignmentRelationship` Node→Artifact / Node→SystemSoftware / Node→deployed-`ApplicationComponent` — deployment **is** the containment, so nest the deployed member inside its node and never draw the assignment. `CompositionRelationship` (a `Device` composed of sub-devices, a `Node` composed of sub-nodes) — nest the part. `RealizationRelationship` `Artifact`→`ApplicationComponent`: draw only when the view's purpose is the app↔infra mapping; otherwise omit.
- **Topology:**

```text
┌ Zone: DMZ ───────────────────┐        ┌ Zone: Internal ──────────────────┐
│ ┌ Node: WebServer ─────────┐ │        │ ┌ Node: AppServer ─────────────┐ │
│ │  SystemSoftware: nginx    │ │        │ │  SystemSoftware: JBoss        │ │
│ │  Artifact: portal.war     │ │        │ │  Artifact: core.ear           │ │
│ └───────────────────────────┘ │        │ │  ApplicationComponent:        │ │
│            │                   │        │ │     CoreBanking (deployed)    │ │
│            │ Association        │        │ └───────────────────────────────┘ │
│            └───────────────────┼───────▶│ ┌ Node: DBServer ──────────────┐ │
│                                │ Assoc. │ │  SystemSoftware: PostgreSQL   │ │
└────────────────────────────────┘        │ └───────────────────────────────┘ │
                                           └────────────────────────────────────┘

Rule: each infrastructure NODE is a container box; its SystemSoftware,
Artifacts, and deployed ApplicationComponents are NESTED inside it
(deployment is shown by containment, never by a drawn Assignment). Nodes
are grouped by environment/zone (DMZ, Internal, Cloud) and wired
left-to-right by AssociationRelationship connectors between the node boxes.
If a CommunicationNetwork/Path element is shown, place it between the zones
and associate the nodes to it instead of drawing node-to-node links —
`arrange-groups arrangement: "topology"` honours this by auto-placing the
element in the reserved inter-zone lane when it connects to elements in
≥ 2 of the arranged zone groups. A top-level `Node` or `Device` wired
to ≥ 2 zone groups likewise qualifies.
```

- **Deltas vs. the invariant sequence:**
  - Step 1: `create-view` with the Technology / Implementation-and-Deployment `viewpoint` (or none — see above).
  - Step 2: one `Grouping` per environment/zone ("DMZ", "Internal", "Cloud"); the nodes sit inside their zone.
  - Step 3: nest `SystemSoftware`, `Artifact`, and any deployed `ApplicationComponent` inside their hosting `Node` (or `Device`) via `parentViewObjectId` on `add-to-view` — the `Node` is an *element* acting as a container, not a Grouping. Size the node generously (it holds its deployed members, like a swimlane).
  - Step 4: `relationshipTypes: ["AssociationRelationship", "ServingRelationship"]` — relationship type names only; Assignment/Composition excluded (conveyed by nesting), and there is no `PathRelationship` to list.
  - Step 6: `layout-within-group` applies to the **zone `Grouping`s** (use `grid` when a zone holds several nodes) — *not* to a `Node` (a Node is an element; its nested members are positioned by `parentViewObjectId` + `autoSize`, not by `layout-within-group`).
  - Step 7: `arrange-groups` `arrangement: "topology"`, `direction: "horizontal"` (network traffic reads left-to-right across zones). A top-level `Node`/`Device`/`Path`/`CommunicationNetwork` element (e.g. a `Site-to-Site VPN` Path) connected to elements in ≥ 2 of the arranged zone groups is auto-placed in the reserved inter-zone lane — no manual `update-view-object` reposition needed. If no qualifier exists, zone arrangement is unchanged (back-compat). The qualifier predicate is automatic; there is no opt-in parameter. (Topology+columns produces a 2D grid where "between" semantics are not well-defined; lane placement skipped for that path.)
  - Step 8: a `CommunicationNetwork`/`Path` element (or a `Node`) wired to many other nodes is the expected hub — resize it before routing if `detect-hub-elements` flags it.
- **Source:** Cookbook "Technology / Deployment" pattern; reference [17].

# Recipe Family — Application Integration

Topology archetype: **hub-and-spoke** around an integration component. Apply the invariant build sequence from the index; only the deltas below change.

(For a flat application *landscape* inventory with no integration hub, no recipe is needed — the "ArchiMate Modelling & Aesthetic Best Practices" principles in `archimate://reference/archimate-view-patterns` already cover the regular clustered-grid layout. Use a recipe only when there is a real integration hub.)

## Application Cooperation View (`viewpoint: "application_cooperation"`)

- **When to use:** show how applications integrate and exchange data, usually around an integration component (ESB / API gateway / broker).
- **Element subset:** `ApplicationComponent`, `ApplicationService`, `ApplicationInterface`; the integration component is the **hub**. **Always omit `ApplicationCollaboration` / team elements and their Assignment to the hub.** The model containing an `Assignment` from a team/collaboration to the hub is *not* a reason to show it — that is ownership metadata, and a cooperation view shows data exchange. Include the owning collaboration *only* when the user's request itself contains an explicit instruction to depict ownership/governance (e.g. the user writes "show who owns/operates the integration"); in that case nest the hub inside the collaboration and still do not draw the Assignment. Default and tie-breaker: omit.
- **Relationship subset:**
  - **Draw:** `FlowRelationship`, `ServingRelationship`.
  - **Imply by nesting, exclude from the filter:** `CompositionRelationship` (a sub-component that is part of a larger component → nest it inside the parent, do not draw the composition arrow); `AssignmentRelationship` from a collaboration/team to a component (omit the team, or nest).
- **Topology:**

```text
        [Channel cluster]              [Partner cluster]
         WebPortal  MobileApp           PartnerGW
              \            \             /
               \            ▼           ▼
                ┌─────────────────────────────┐
                │   Integration hub (ESB)      │  ← detect-hub-elements
                │   sized for fan-out (>6)     │     → update-view-object resize
                └─────────────────────────────┘
               /            ▲           ▲
              /            /             \
        [Core cluster]                 [Data cluster]
         CoreBanking                    DataWarehouse
          └ PaymentEngine (nested:       CustomerMDM
            Composition, not drawn)

Rule: the integration component is central and the largest; everything else
is grouped into domain clusters around it; flows run cluster → hub → cluster.
```

- **Deltas vs. the invariant sequence:**
  - Step 2: one `Grouping` per domain cluster (e.g. "Channel", "Core", "Data"); the hub sits on the view between them (not inside a cluster).
  - Step 3: nest a part-component inside its parent (e.g. `PaymentEngine` inside `CoreBanking`) via `parentViewObjectId`.
  - Step 4: `relationshipTypes: ["FlowRelationship", "ServingRelationship"]` (Composition/Assignment excluded — conveyed by nesting / omitted).
  - Step 7: `arrange-groups` `arrangement: "topology"`, `direction: "horizontal"` (producer → hub → consumer reads left-to-right). The integration hub (a top-level `Node`/`Device`/`Path`/`CommunicationNetwork` element connected to elements in ≥ 2 of the arranged groups) is auto-placed in the reserved inter-group lane between the producer and consumer clusters — no manual `update-view-object` reposition needed. If no qualifier exists, group arrangement is unchanged (back-compat). The qualifier predicate is automatic; there is no opt-in parameter.
  - Step 8: the integration component is the expected hub — resize it before routing.
- **Source:** Cookbook "Application Cooperation / Integration" pattern; reference [17].

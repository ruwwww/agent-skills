# ArchiMate Viewpoint Recipes — Index

Read this page first. It does two things: it states the **invariant build sequence once**, and it routes you to the **one** thing the generic guidance cannot give per viewpoint — the **topology** (the spatial shape).

Most ArchiMate viewpoints lay out well from the modelling and aesthetic principles already shipped in `archimate://reference/archimate-view-patterns` plus the element-type decision aid in `archimate://reference/archimate-layers`. Empirically (clean-context measurement, 2026-05-19) a capable model produces near-faithful plans for the *conventional* shapes — layered band-stack, clustered grid, hierarchy/tree, object bands — from those principles alone. A **recipe exists only where a real topology gap was measured**: the non-conventional shapes whose spatial form the principles cannot encode.

## Step 0 — is your diagram conventional or non-conventional?

| Your diagram's shape | Action |
|---|---|
| **Layered** (Business→Application→Technology bands) | **No recipe.** Apply `archimate://reference/archimate-view-patterns` best-practice rules 1 (layer top-to-bottom), 4 (nest parts), 8 (viewpoint element subset); `arrange-groups arrangement:"column"`. |
| **Application landscape / inventory** (estate grouped by domain, no integration hub) | **No recipe.** Clustered grid: one Grouping per domain, `arrange-groups arrangement:"grid"`. Do **not** invent a hub. |
| **Specialization hierarchy** (a type tree via SpecializationRelationship) | **No recipe.** `tree` layout algorithm, root at top; draw only `SpecializationRelationship`. |
| **Organization structure** (org units / roles by containment) | **No recipe.** Nested-containment hierarchy; exclude Composition/owner-Assignment by nesting (rule 4); `tree`/column. |
| **Information structure** (business objects + data objects) | **No recipe.** Two stacked bands (BusinessObjects above, DataObjects below), `arrange-groups arrangement:"column"`; draw Realization. |
| **Anything below** | **Fetch the one matching recipe page.** Its topology block is the payload — match it. |

If your diagram is conventional, stop here and apply the principles — you do not need a recipe.

## Step 1 — the invariant build sequence (every recipe runs this)

A recipe gives only the per-family **deltas** — the parameters that change. Do not re-derive this; apply it as the engine.

1. `create-view` (with the family's `viewpoint` param, or none for general-purpose).
2. `add-group-to-view` once per group the topology calls for.
3. `add-to-view` each element with `parentViewObjectId` set per the topology, `autoSize: true`. Nest a part inside its parent; never draw the part-of relationship (`archimate://reference/archimate-view-patterns` best-practice rule 4).
4. `auto-connect-view` filtered to the family's **draw** relationship types only.
5. `get-view-contents` `format=tree` to discover group viewObjectIds.
6. `layout-within-group` per group.
7. `arrange-groups` with the family's arrangement + direction.
8. `detect-hub-elements`; resize any hub via `update-view-object` (never `resize-elements-to-fit`).
9. `apply-spacing-recommendations` `scope: "both"` → `auto-route-connections` `autoNudge: true` → `assess-layout`. On `terminationReason: density_floor_reflow_required`, surface the `densityFloorDiagnosis` and the consent-gated reflow per `archimate://prompts/routing-preconditions-checklist` — do not loop the spacing tools, do not auto-reflow.

## Step 2 — fetch your non-conventional family page

| What the diagram must communicate | Family page to fetch | Covers |
|---|---|---|
| How applications integrate around an integration component (ESB / API gateway / broker) | `archimate://recipes/application-integration` | Application Cooperation / Integration |
| A process flow, its hand-offs, who performs each step; or an outside-in customer journey over support layers | `archimate://recipes/behaviour-process-flow` | Business Process Cooperation; Service Design / Customer Journey |
| Why the architecture exists — stakeholders, drivers, goals, requirements and their influence chain | `archimate://recipes/motivation` | Motivation |
| What runs where — software deployed onto infrastructure nodes | `archimate://recipes/technology-deployment` | Technology / Deployment |
| Change over time — current/target states, what moves between them | `archimate://recipes/roadmap-migration` | Implementation & Migration / Roadmap |

Fetch **only** the one page that matches. You do not need to read the others, and there is no per-viewpoint page for the conventional shapes in Step 0 by design.

## How to read a family page

Each recipe has the same five parts:

- **When to use** — the concern the diagram answers.
- **Element subset** — the ArchiMate element types to place (the Cookbook "80% rule").
- **Relationship subset** — which types to `auto-connect-view`, and which to **imply by nesting and exclude** from the filter.
- **Topology** — a text block diagram of the spatial shape. **This is the payload — match it.**
- **Deltas vs. the invariant sequence** — the 2–3 step parameters that differ (arrangement, direction, the relationship filter, nesting parentage).

Source for the patterns: the *ArchiMate Cookbook* (reference [17] in `docs/bibliography.md`). The recipes are this project's curated, version-pinned interpretation — self-contained; no external document needs to be fetched.

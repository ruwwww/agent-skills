# PPPL Prerequisite Course Artifacts & Review Patterns

In PPPL (Perancangan dan Pengembangan Perangkat Lunak) courses (such as at ITS Information Systems), assignments often require reviewing and integrating past artifacts across 4 prerequisite disciplines:

## 1. ASD (Algoritma & Struktur Data) / Pemrograman OOP
- **Focus:** Object-oriented modeling, class responsibilities, and relationships.
- **Key Relationships to Highlight:**
  - **Composition:** Whole-part relationship where parts cannot exist independently (e.g., `Board` *-- `Cell[][]`).
  - **Aggregation / Association:** Referencing entities without strict ownership (e.g., `Cell` o-- `Seed`, `GameMain` ..> `LoginDialog`).
  - **Inheritance:** Extending framework classes (e.g., `extends JPanel`, `extends JDialog`).
- **PlantUML Class Diagram:** Always include attributes (visibility `-`, `#`, `+`), method signatures, and multiplicities.

## 2. SBD (Sistem Basis Data)
- **Focus:** Relational schema, entity integrity, and secure query execution.
- **Key Points:**
  - Entity-Relationship Diagram (ERD) with primary and foreign keys.
  - Integration with application layer via parameterized queries (`PreparedStatement`) to prevent SQL Injection.

## 3. DPP (Desain Pengalaman Pengguna / UI-UX)
- **Focus:** User-centered design methodology and interactive prototyping in Figma.
- **Artifact Layers in Figma:**
  - **Design System:** Color palette (e.g., dark mode barbershop theme), typographic scale, reusable master components (buttons, badges, navbars).
  - **Fidelity Progression:** Low-Fidelity wireframes (layout exploration) -> Mid-Fidelity (wireflow logic & 3D guides) -> High-Fidelity (final visual Polish & interactive micro-interactions).
  - **Flow Demonstration:** Walkthrough of key user journeys (e.g., Questionnaire -> 3D AR Scan -> Recommendation Results -> Checkout/Action).

## 4. RKPL (Rekayasa Kebutuhan Perangkat Lunak)
- **Focus:** Formal requirements specification and behavioral modeling.
- **Artifacts:**
  - Functional vs. Non-Functional Requirements.
  - UML Use Case Diagram: Use `<<include>>` for mandatory sub-flows and `<<extend>>` for optional/conditional branches.
  - Structured Use Case Scenario table: Pre-conditions, Trigger, Main Flow (numbered steps), Alternative Flows (exception handling), Post-conditions.

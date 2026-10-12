# Software Review & Prerequisite Video Presentation Guide

Patterns for structuring and scripting student/engineering review presentations that evaluate prerequisite software artifacts across 4 core dimensions: Object-Oriented Design (ASD), Database Modeling (SBD), UI/UX Interaction (DPP), and Requirements Engineering (RKPL).

## Modular Presentation Structure (4-5 Minutes)

When recording video presentations (especially when recording in cut-per-segment style), adhere to strict modular timeboxes:

### 1. Segment 0: Opening (~20s)
- State identity (Name, Student ID / NRP, Class / Role).
- State objective: Reviewing 4 prerequisite software engineering pillars before commencing formal design (e.g., ICONIX Process).

### 2. Segment 1: Object-Oriented Architecture / ASD (~50s)
- **Visual:** Class Diagram with strict UML 2.5 notation + IDE code walkthrough.
- **Key Concepts to Articulate:**
  - Separation of Concerns.
  - Strong Composition (`*--`, lifecycle ownership, e.g. Board owning Cells).
  - State enumeration and association (`o--`, e.g. Cell holding Seed / Enum states).
  - GUI Framework inheritance (`<|--`, extending JPanel / JDialog).

### 3. Segment 2: Database Modeling / SBD (~50s)
- **Visual:** Relational ERD / EER Diagram.
- **Key Concepts to Articulate:**
  - Normalization level achieved (typically 3NF).
  - Many-to-many pivot tables with composite primary keys (`paket_item`).
  - Extended ERD (EER) concepts: Generalization / Specialization (`ISA` hierarchy, e.g. Employee -> Manager / Operational Staff).
  - Database security: Parameterized queries (`PreparedStatement`) preventing SQL Injection.

### 4. Segment 3: UI/UX & Interaction Design / DPP (~60s)
- **Visual:** Figma canvas walkthrough (Lo-Fi -> Design System -> Hi-Fi Prototype).
- **Key Concepts to Articulate:**
  - Visual hierarchy, design tokens, and components.
  - User journeys and task flows (e.g. Survey -> 3D Face Scan -> AR Try-On -> Recommendations).
  - Micro-interactions, feedback states, and validation guidance.

### 5. Segment 4: Requirements Engineering / RKPL (~60s)
- **Visual:** Formal Use Case Diagram + Use Case Scenario table from SRS.
- **Key Concepts to Articulate:**
  - Actor definitions (Human users vs External / Hardware Systems like BLE IoT sensors).
  - Use case relationships (`<<include>>` for mandatory sub-flows like Data Persistence, `<<extend>>` for conditional branches).
  - Explicit Walkthrough of 1 Scenario: Pre-conditions, Main Flow, Alternative Flows (exception handling), and Post-conditions.

### 6. Segment 5: Closing (~15s)
- Summarize how the 4 pillars form the required foundation for the target design methodology (e.g. ICONIX Process: Domain Model -> Robustness Analysis -> Sequence -> Class).

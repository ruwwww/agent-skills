# ICONIX Process Guide (Agile Modeling with UML)

The ICONIX Process is a minimalist, use case driven object modeling approach developed by Doug Rosenberg & Matt Stephens (*Agile Development with ICONIX Process*). It bridges the gap between requirements and code via 4 iterative phases and 3 major milestones.

## 1. The 4 Phases

### Phase 1: Requirements
- **Functional Requirements:** Declarative "The system shall..." statements.
- **Domain Modeling (The "Cast of Characters"):**
  - Identify key problem-domain concepts and real-world business entities (classes without methods or database types).
  - *Golden Rule:* **Domain Model != ER Diagram**. No primary keys, foreign keys, or SQL data types (`INT`, `VARCHAR`). Only business vocabulary and relationships (`is-a` generalization, `has-a` aggregation).
- **GUI Storyboarding:** Mockups/wireframes (Figma) to anchor concrete user interactions.
- **First-Draft Use Cases:** Describe interaction between actor and system following:
  - *Two-Paragraph Rule:* Paragraph 1 describes the Basic Course (happy path); Paragraph 2 describes Alternate Courses (errors/exceptions).
  - *Active Voice & Event/Response:* Alternate explicitly between actor action and system response.
  - *Reference Domain Classes by Name:* Nouns in use case text must match domain class names verbatim.
- **Milestone 1: Requirements Review:** Verify that the "Golden Triangle" (Domain Model <-> GUI Storyboard <-> Use Case Text) is 100% consistent.

### Phase 2: Analysis / Preliminary Design
- **Robustness Analysis (BCE Modeling):** Bridge between "what" (use case) and "how" (code).
  - **Boundary:** Screen, form, UI component, or API gateway.
  - **Control:** Business logic, coordinator, workflow handler, or service.
  - **Entity:** Domain objects, database records, or data structures.
- **Rules of Robustness Analysis:**
  1. Actors only communicate with Boundaries.
  2. Boundaries only communicate with Controls and Actors.
  3. Controls communicate with Boundaries, Controls, and Entities.
  4. Entities communicate with Controls and other Entities.
  5. **NEVER** connect Boundary directly to Entity!
- **Domain Model Update:** Add missing attributes and discover omitted domain classes.
- **Use Case Rewrite:** Refine text into clear, unambiguous actor-system steps.
- **Milestone 2: Preliminary Design Review (PDR):** Review robustness diagrams and updated use cases.

### Phase 3: Detailed Design
- **Sequence Diagramming:** Draw exactly one Sequence Diagram per Use Case.
  - Allocate responsibilities and concrete methods/operations to classes.
  - Validate continuity of message flows (no leaps of logic).
- **Class Diagram Finalization:** Transform domain model into static class diagram.
  - Add visibility (`+`, `-`, `#`), method signatures, parameter types, return types.
  - Specify formal associations, aggregations, compositions, and multiplicities.
- **Milestone 3: Critical Design Review (CDR):** Validate design quality before coding.

### Phase 4: Implementation
- **Coding & Unit Testing:** Write code and unit tests verified against sequence diagrams.
- **Integration & Scenario Testing:** Test both basic course and alternate/error courses.
- **Code Review & Model Update:** Keep design diagrams synchronized with code.

## 2. Robustness Diagram in PlantUML (The BCE Model)

Robustness Analysis bridges the gap between text use cases and sequence diagrams. In PlantUML, declare elements using native keywords: `actor`, `boundary`, `control`, `entity`.

### The 4 Valid Connection Rules (Strict BCE Grammar)
1. **Actor $\leftrightarrow$ Boundary:** An actor can ONLY communicate with boundary objects (screens/forms).
2. **Boundary $\leftrightarrow$ Control:** Boundaries communicate with controllers to trigger logic or receive rendered data.
3. **Control $\leftrightarrow$ Control:** Controllers can delegate tasks, coordinate workflows, or trigger error handlers.
4. **Control $\leftrightarrow$ Entity:** Controllers read from or write to domain entities.
5. **FORBIDDEN (Immediate Design Failure):**
   - `Actor <--> Control` or `Actor <--> Entity` (Actor must go through UI).
   - `Boundary <--> Entity` (Direct DB access from UI is prohibited; must go via controller).
   - `Boundary <--> Boundary` (Screen transitions must be orchestrated by a controller).
   - `Entity <--> Entity` (Data objects do not talk directly to each other in robustness analysis).

### PlantUML Layout Pitfall: Avoid `linetype ortho` with Feedback Loops
When modeling validation failure loops (e.g. `Controller -> Error Controller -> Boundary`), PlantUML's `skinparam linetype ortho` frequently breaks into floating, disconnected line fragments.
- **Fix:** Omit `skinparam linetype ortho` or use smooth polyline routing (`--`) for continuous, perfectly attached connections.
- **Traceability Guideline (ICONIX Rule #1 & #10):** Include a note block containing the verbatim Use Case text (Basic Course + Alternate Courses) to maintain 100% traceability.

```plantuml
@startuml
skinparam style strictuml
skinparam defaultFontName "Helvetica"
skinparam defaultFontSize 11
skinparam shadowing false
skinparam nodesep 30
skinparam ranksep 35

header ICONIX Robustness Analysis
title Robustness Diagram: Melakukan Pelaporan

actor "Pengguna" as User
boundary "FormPelaporanUI" as FormUI
boundary "KonfirmasiSuksesUI" as SuccessUI

control "BukaFormPelaporan" as CtrlOpen
control "ValidasiInputLaporan" as CtrlValidate
control "TampilkanErrorValidasi" as CtrlError
control "SimpanDataLaporan" as CtrlSave

entity "LokasiJalan" as EntLokasi
entity "LaporanInsiden" as EntLaporan

' Valid BCE flows
User -- FormUI
FormUI -- CtrlOpen
CtrlOpen -- EntLokasi
CtrlOpen -- FormUI

FormUI -- CtrlValidate
CtrlValidate -- CtrlError
CtrlError -- FormUI

CtrlValidate -- CtrlSave
CtrlSave -- EntLaporan
CtrlSave -- SuccessUI
@enduml
```

## 3. Use Case Scoping & Common UML Anti-Patterns

### Use Case Scoping: The "Coffee Break Test" (Elementary Business Process)
A Use Case represents an end-to-end user goal that delivers measurable business value. After completing it, the user can walk away and take a coffee break with their goal achieved.
- **Valid Use Case:** `Melakukan Live Report Insiden` (User reports an event, public is notified, contributor points awarded).
- **Invalid Use Case (Too Granular):** `Mengunggah Foto Bukti`, `Memberikan Detail Lokasi`. These are not standalone business goals; they are form input steps inside the use case's event flow.

### Handling Login & Authentication (Avoid the Spiderweb Anti-Pattern)
- **Do NOT** draw `<<include>>` arrows from every single use case to `Login`. This turns the diagram into an unreadable spiderweb.
- **Do NOT** create `Mengakses Halaman Utama` as a use case. Navigating to a page is an interaction/UI boundary, not a user goal.
- **Best Practice:** Model `Melakukan Login` as a single standalone use case connected to the Actor. For all other authenticated use cases, document login as a **Pre-condition** in the use case specification text:
  > *Pre-condition: User is authenticated with an active session.*
- Only use `<<include>>` for authentication if a specific workflow strictly enforces immediate re-authentication (e.g. entering a PIN or biometric before funds transfer).

### Three Fatal UML Modeling Mistakes to Avoid
1. **Functional Decomposition (Form Fields as Use Cases):** Do not break a single screen's input fields into separate use cases linked via `<<include>>`. Keep input details in the event flow text.
2. **Solid Association Lines Between Use Cases (Illegal UML):** Plain solid lines (`---`) only connect **Actors to Use Cases**. Use cases can only connect to other use cases via `<<include>>` (dashed arrow), `<<extend>>` (dashed arrow), or Generalization (solid line with open triangle arrowhead).
3. **Misusing `<<extend>>` for UI Menus or Feature Lists:** Buttons or tabs inside a screen are UI navigation, not extensions. An `<<extend>>` relationship represents conditional intercept behavior where an optional scenario inserts into the base flow (`Extending Use Case` $\dashrightarrow$ `Base Use Case`).

### Workflow & Presentation Preference
- When delivering updated diagram revisions, prioritize rendered visual artifacts (`MEDIA:` path) and concise architectural rationale. Do not dump lengthy raw diagram code blocks unless the user explicitly requests the code.
- Always preserve diagram sources (`.puml`, `.drawio`) in Git version control alongside project documentation.
- **Team Consensus Ground Truth Rule:** In group project coursework, once team members finalize and lock a Domain Model diagram (e.g. collaborative Draw.io canvas or shared screenshot), treat that artifact as immutable ground truth. Do not independently redesign or deviate from their domain class vocabulary; lock it and strictly derive entity objects (`O_`) from it for the subsequent Robustness Analysis and Sequence Diagramming phases.

## 4. Noun Extraction & Filtering Pipeline ("Not Every Noun is a Class")

A common failure mode in domain modeling is turning every noun found in use case descriptions into a separate class box in the domain model. In Object-Oriented Analysis (OOA) and ICONIX:

### The 4 Criteria for a True Domain Class
A candidate noun qualifies as a Domain Class if and only if it:
1. **Has complex state/data:** Holds multiple attributes, not merely a single primitive value.
2. **Has candidate behavior/operations:** Encapsulates actions, state transitions, or business calculations (even if method signatures are deferred until Sequence Diagrams).
3. **Has distinct identity and system role:** Represents an identifiable, independent business entity rather than an ephemeral value.
4. **Is directly relevant to the problem domain:** Governs core business requirements, not transient UI or environmental mechanics.

### When Does a Category Become a Subclass (`is-a`) vs an Enum/Attribute?
- **Case 1: Enum / Attribute Value (Identical Data Structures):** If categories or options share the exact same attributes and behaviors (e.g. `BTN`, `BCA`, `ApplePay` under `MetodePembayaran`), do NOT make them separate classes. Model them as enum values or instance data under a single parent class.
- **Case 2: Specialized Subclasses via `is-a` (Distinct Attribute Sets):** If each category requires **fundamentally different attributes** that have no meaning for other categories, they **MUST** be modeled as specialized subclasses inheriting (`is-a`) from the parent class to avoid sparse/nullable data pollution:
  - Example: `TrafficNews` specialized into:
    - `AccidentNews` (`vehiclesInvolved: int`, `severityLevel: String`, `hasCasualties: boolean`)
    - `FloodNews` (`waterLevelCm: int`, `passableVehicleType: String`, `drainageStatus: String`)
    - `RoadworksNews` (`contractorName: String`, `estimatedCompletionDate: Date`, `detourRoute: String`)
    - `MaintenanceNews` (`facilityType: String`, `responsibleDepartment: String`, `scheduleHours: String`)

### Why Not Every Noun is a Class (The "Nominal" Principle)
A critical rule in Object-Oriented Analysis (OOA):
- **Class:** Represents an entity that has state, candidate behavior, and an independent role in the domain (e.g. `Akun` has `email`, `password`, `login()`, `logout()`; `Transaksi` has `nominal`, `tanggal`, `proses()`).
- **Attribute:** If a noun only represents a primitive value (single number, text string, status state) that describes another entity, it **must** become an attribute:
  - `NominalTransaksi` (e.g. Rp 500.000) $\to$ `double nominal` inside `Transaksi`. Not `class Nominal`.
  - `KataSandi` $\to$ `String password` inside `Akun`.
  - `StatusLaporan` (Pending, Valid, Resolved) $\to$ `Enum status` inside `LiveReport`.
  - `KoordinatGPS` (Lat, Long) $\to$ `double latitude, longitude` inside `LokasiJalan`.
- **Value / Enum (Brands & Concrete Channels):** Concrete payment options like `BTN`, `BCA`, `ApplePay`, `BST` are instances or enum values of a unified class `MetodePembayaran`, not separate classes.
- **Actor:** External human operators (`User`, `Admin`) reside outside the system boundary; their system representation is captured via domain entities (`Akun`, `ProfilPengguna`).
- **Feature / Action:** `LiveTracking` is a feature/use case (backed by `LokasiJalan`); `TelfonDarurat` is an action/invocation on `LaporanPolisi`.

### Visual Blueprint Rules for Domain Models
- **Single-Compartment Clean Boxes:** Use `hide empty members` and `hide circle` in PlantUML so boxes show only the class name without blank attribute/method divider lines.
- **Strictly `is-a` and `has-a`:**
  - `is-a`: Generalization/inheritance using hollow triangular arrowheads (e.g., `TopUp is-a Transaksi`, `DigitalReport is-a LaporanPolisi`).
  - `has-a`: Composition/aggregation using diamond terminators with explicit multiplicity annotations (`1`, `0..1`, `0..*`, `1..*`).
- **No Orphan Classes:** Every domain entity must be integrated into the network graph with clear ownership or association pathways.

## 5. Layout & 1:1 Aspect Ratio Optimization for Architecture Diagrams

When delivering diagrams for presentations, slides, or Discord embeds, users often request a balanced **1:1 square aspect ratio** instead of ultra-wide panoramic banners:

### The Problem: Horizontal Sprawl
- PlantUML's default `left to right direction` or unconstrained orthogonal routing on diagrams with 15–25 classes often stretches into a 5:1 or 6:1 horizontal strip, making text unreadable when scaled to fit standard screens.

### How to Achieve a Clean 1:1 Balanced Layout in PlantUML
1. **Remove `left to right direction`** to allow natural vertical-horizontal balance.
2. **Anchor the Central Domain Root at Top-Center:** Place the primary root entity (e.g. `Akun`, `UserAccount`, or `Order`) at the top, and fan out child subsystems symmetrically (Left: User & Finance; Center: Core Workflow / Reporting; Right: Communication & Support).
3. **Enforce Vertical Tiering with Hidden Constraints:**
   ```plantuml
   ' Force multi-row grid layout to maintain ~1:1 aspect ratio
   ProfilPengguna -[hidden]down-> Transaksi
   Transaksi -[hidden]down-> TopUp
   LiveReport -[hidden]down-> LokasiJalan
   Chat -[hidden]down-> LaporanPolisi
   LaporanPolisi -[hidden]down-> DigitalReport
   ```
4. **Tune Spacing Parameters:**
   ```plantuml
   skinparam nodesep 28
   skinparam ranksep 35
   skinparam linetype ortho
   ```
5. **Verify with `vision_analyze`:** Ensure aspect ratio is between 1:1 and 4:3, lines do not cross through boxes, and text labels do not collide.

## 6. Chained End-to-End Robustness Analysis & Explicit Control Documentation

### Chained Workflow Storyboards (Endpoint-to-Startpoint Sequence)
When users or evaluators require an end-to-end, ordered robustness flow across multiple use cases (e.g. from onboarding to deep feature subflows):
1. **Endpoint as Startpoint:** Connect the exit boundary screen of the preceding use case directly as the entry boundary screen of the subsequent use case (e.g. `IntroScreen` $\to$ `LoginPage` $\to$ `HomePage (MAIN)` $\to$ `TopUpScreen` / `ChatRoomScreen` $\to$ `PoliceReportMainScreen`).
2. **Explicit Action Trigger Notes on Arrows:** Every directional transition arrow connecting boundaries and controllers must carry an explicit user action or system event label (e.g. `[klik tombol 'Masuk']`, `[klik card Saldo / 'Top Up']`, `[klik shortcut 'Laporan Polisi']`, `[tekan tombol panik SOS]`).
3. **Strict As-Is UI Hierarchy:** Never rearrange or invent standalone entry points if the prototype (Figma) routes them through specific parent screens or chat shortcut drawers. Honor the As-Is journey strictly.
4. **Master Multi-Page Draw.io Architecture:** When delivering multi-use-case suites (e.g. 21 use cases), provide:
   - **Tab 00:** Master Chained Flow (global end-to-end storyboard connecting all endpoints to startpoints).
   - **Tabs 01–N:** Isolated, detailed robustness diagrams per individual use case.
   - Deliver both as a 1-click interactive URL (`https://app.diagrams.net/#R...`) and as a committed `.drawio` file uploaded to Google Drive.

### Explicit Separation of Basic vs Alternate Controls
Academic evaluations and formal reviews strictly check for exception handling. In documentation and specification tables:
- Never lump all controllers into a single generic list.
- Explicitly partition controls into:
  - **`Control (Basic Course):`** Normal happy-path processing and data commitment.
  - **`Control (Alternate Course / Alt):`** Form validation failures, duplicates, offline states, and fallbacks, explicitly tagged with scenario codes: `(Alt 1a)`, `(Alt 1b)`, `(Alt 2a)`, etc.

## 7. MVC Backend Controller Mapping & Simplified As-Is Figma Alignment

In modern software engineering curricula and practical software teams (e.g. Laravel / Spring / NestJS projects), teams often align ICONIX Robustness Analysis directly with their target backend MVC architecture:

### 1. Controllers as Backend Functions & Methods (Not Frontend Clicks)
- **Eliminate Frontend Interactivity in Controllers:** Never label controllers with physical UI gestures such as *"Mengklik tombol masuk"*, *"Memilih nominal"*, or *"Mengisi form"*. Physical gestures reside entirely at the Boundary.
- **Controllers Represent Backend Methods:** Each controller bubble directly translates to an action or method in a backend controller:
  - `Memproses permintaan [action]`: The HTTP entrypoint method (e.g. `AuthController@login`, `TopUpController@store`, `LiveReportController@store`).
  - `Memvalidasi [kredensial/input]`: Form Request validation or domain service verification (e.g. `LoginRequest`, `validateCredentials`).
  - `Men-redirect Ke [halaman/screen tujuan]`: HTTP redirect response / routing logic (e.g. `return redirect('/home')`).
  - `Muat Data [entity]`: ORM query or View Composer populating the landing screen (e.g. `Auth::user()->load('profile')`).
  - `Menyimpan data / Mencatat order [entity]`: Persistence layer / Eloquent mutation.

### 2. Simplified As-Is Figma Scope Alignment
- When tasked with matching a preliminary Figma prototype: **If error dialogs, fallbacks, or alternate branch screens have not yet been designed in Figma, do NOT include speculative alternate flows.**
- Stick strictly to the clean, linear As-Is happy path represented in the GUI storyboard.

### 3. Standardized Boundary Naming
- Format: `[PageName] - [Screen / Frame Figma]` (e.g., `LoginPage - login`, `HomePage - Main`, `TopUpPage - top up`, `LiveReportPage - live report form`).

### 4. Canonical 5-Column Horizontal + 2-Row Vertical Robustness Pattern
To ensure maximum consistency, readability, and immediate grading clarity across large use-case suites, adhere to the standard architectural layout:
```text
[Actor] ──> [Boundary 1] ──> [Ctrl: Memproses] ──> [Ctrl: Memvalidasi] ──> [Ctrl: Men-redirect] ──> [Boundary 2]
                                                          │   ▲                                      ▲
                                           meload data    │   │ mengembalikan status                 │
                                                          ▼   │                                [Ctrl: Muat Data]
                                                      [Entity 1]                                     ▲
                                                                                                     │
                                                                                                [Entity 2]
```
- **Bidirectional Entity Communication:** The validation/processing controller queries `Entity 1` (`meload data...` downward) and receives verification (`mengembalikan status...` upward).
- **Secondary Data Loading:** When the destination screen requires auxiliary context (e.g. `HomePage - Main` rendering avatar and username from `Profil Pengguna`), route `Entity 2` $\to$ `Ctrl: Muat Data` $\to$ `Boundary 2`.
- **Canvas Presentation:** Use a clean dark charcoal theme (`#111113`) with crisp white outlines (`#FFFFFF`) and header author metadata for high-contrast academic defense.





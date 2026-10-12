---
name: psti-archimate-ea
description: Use when building or editing ArchiMate EA models for PSTI.
---

# PSTI ArchiMate EA Workflow

This skill guides the automated creation and validation of ArchiMate 3.2 Enterprise Architecture models using `pyArchimate` and `archimate-mcp` in `/home/kuroko/kuliah/PSTI/`.

## Environment
* Python venv: `/home/kuroko/kuliah/PSTI/.venv/bin/python`
* Models directory: `/home/kuroko/kuliah/PSTI/models/`
* Output directory: `/home/kuroko/kuliah/PSTI/output/`

## ArchiMate Metamodel Rules & Elements
Use exact element types:
* Motivation: `Stakeholder`, `Driver`, `Assessment`, `Goal`, `Outcome`, `Principle`, `Requirement`, `Constraint`
* Strategy: `Resource`, `Capability`, `CourseOfAction`, `ValueStream`
* Business: `BusinessActor`, `BusinessRole`, `BusinessCollaboration`, `BusinessInterface`, `BusinessProcess`, `BusinessFunction`, `BusinessService`, `BusinessObject`
* Application: `ApplicationComponent`, `ApplicationInterface`, `ApplicationFunction`, `ApplicationService`, `DataObject`
* Technology: `Node`, `Device`, `SystemSoftware`, `TechnologyService`, `CommunicationNetwork`, `Artifact`
* Implementation: `WorkPackage`, `Deliverable`, `Plateau`, `Gap`

Relationships:
* `Association`, `Assignment`, `Realization`, `Serving`, `Composition`, `Aggregation`, `Access`, `Influence`, `Triggering`, `Flow`, `Specialization`

## Standard TOGAF Assignment Breakdown
1. EA Vision (Motivation & Strategy)
2. Business Architecture (Business Layer)
3. Data Architecture (Data Objects & CRUD)
4. Application Architecture (App Components & Services)
5. Infrastructure / Technology Architecture (Nodes & Infrastructure)
6. Security Architecture (Constraints, Principles, Security Requirements)
7. Roadmap / Transition (Plateaus & Work Packages)

---
name: archimate-modeling
description: Use when creating or editing Archi (.archimate) EA models.
---

# ArchiMate & Archi Tool Modeling Skill

Guide for agents to interact with ArchiMate models, the Archi tool (.archimate XML EMF structure), and TOGAF ADM phase mapping.

## Archi XML File Format (.archimate)
Archi files are standard XML files adhering to the ArchiMate tool EMF schema (`xmlns:archimate="http://www.archimatetool.com/archimate"`).

### Core Folder Hierarchy
A standard Archi repository contains folders categorized by architecture layer:
* `Strategy` (type: `strategy`): `CourseOfAction`, `Capability`, `Resource`, `ValueStream`
* `Business` (type: `business`): `BusinessActor`, `BusinessRole`, `BusinessProcess`, `BusinessFunction`, `BusinessService`
* `Application` (type: `application`): `ApplicationComponent`, `ApplicationInterface`, `ApplicationService`, `DataObject`
* `Technology & Physical` (type: `technology`): `Node`, `Device`, `SystemSoftware`, `TechnologyService`, `Artifact`
* `Motivation` (type: `motivation`): `Stakeholder`, `Driver`, `Assessment`, `Goal`, `Outcome`, `Principle`, `Requirement`, `Constraint`
* `Implementation & Migration` (type: `implementation_migration`): `WorkPackage`, `Deliverable`, `Plateau`, `Gap`
* `Relations` (type: `relations`): `AssociationRelationship`, `AggregationRelationship`, `CompositionRelationship`, `RealizationRelationship`, `AssignmentRelationship`, `ServingRelationship`, `AccessRelationship`, `InfluenceRelationship`, `FlowRelationship`, `TriggeringRelationship`
* `Views` (type: `diagrams`): `ArchimateDiagramModel` elements containing `child` elements and `sourceConnection` tags.

### Relationships Reference (ArchiMate 3.2)
* `AssociationRelationship`: Untyped or directed semantic connection (e.g. Stakeholder -> Driver).
* `InfluenceRelationship`: Qualitative influence (+/-) on Goals, Drivers, or Assessments.
* `RealizationRelationship`: Requirement/Principle/Capability realizing a Goal/Outcome/Service.
* `AggregationRelationship`: Composed parts (e.g. Goal containing Sub-Goals).
* `AssignmentRelationship`: Active structure assigned to behavior (e.g. Actor to Role).
* `ServingRelationship`: Application/Technology service serving a business process or upper layer.
* `FlowRelationship`: Information or value flow between components or resources.

## TOGAF ADM Phase A Required Views (Architecture Vision)
1. **Stakeholder View:** Stakeholders (Board, Customers, Partners), Drivers, Assessments, Initial Goals.
2. **Business Driver and Business Goals View:** Drivers -> Goals -> Aggregation of Sub-Goals -> Outcomes.
3. **Principles View:** Principles realizing Goals, with positive/negative influence across principles.
4. **Goal Refinement View:** Goals -> Sub-Goals -> Realized by Requirements, bounded by Constraints.
5. **Strategy View:** Courses of Action realizing Capabilities and Resources to achieve Outcomes.
6. **Solution Concept View:** High-level Target Architecture (Application Components, Data Flows, and External Ingestion).

## Automation & Inspection via Python
Read and inspect diagrams directly:
```python
import xml.etree.ElementTree as ET
tree = ET.parse("model.archimate")
root = tree.getroot()
ns = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
diagrams = root.findall('.//element[@xsi:type="archimate:ArchimateDiagramModel"]', ns)
for d in diagrams:
    print(d.attrib['name'], "Nodes:", len(d.findall('.//child')))
```

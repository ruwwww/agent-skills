# ArchiMate Layers and Element Types

## Layer Overview

ArchiMate organises architecture into layers that represent different levels of abstraction. Elements belong to exactly one layer based on their type.

## Choosing the Right Element Type (Decision Aid)

Picking the wrong element type is the most common modelling mistake. Before calling `create-element` or `search-and-create`, map the plain-English concept to a type by asking the disambiguating question for the pair it most resembles. The rule of thumb across every layer: **active structure** = *who/what performs* (Actor, Role, Component, Node); **behaviour** = *what is done* (Process, Function, Service); **passive structure** = *what is acted on* (BusinessObject, DataObject, Artifact).

### Component vs. Service

| | A **Component / active-structure thing** | A **Service (behaviour)** |
|---|---|---|
| Ask | "Is it a deployable, identifiable *thing that does the work*?" | "Is it the *exposed capability* offered to a consumer, named by its outcome?" |
| Looks like | `LoanApp`, `ESB`, `Payment Gateway` | `Loan Scoring Service`, `Payment API`, `Customer Notification` |
| Type | `ApplicationComponent` (Business: `BusinessRole`/`BusinessActor`; Technology: `Node`/`SystemSoftware`) | `ApplicationService` / `BusinessService` / `TechnologyService` |

A component **realizes** a service; the service is *what other elements depend on*. Pick the one the diagram's concern needs: an integration/cooperation view shows **components**; a capability/contract view shows **services**.

### Process vs. Function

| | A **Process** | A **Function** |
|---|---|---|
| Ask | "Is it a *sequence with a trigger, a flow, and a specific end result*?" | "Is it *ongoing behaviour grouped by required skill/capability*, with no inherent end?" |
| Looks like | `Assess Application`, `Ship Order`, `Onboard Customer` (verb + object) | `Claims Management`, `Marketing`, `Risk Analysis` (a capability area) |
| Type | `BusinessProcess` / `ApplicationProcess` / `TechnologyProcess` | `BusinessFunction` / `ApplicationFunction` / `TechnologyFunction` |

Triggering / Flow relationships chain **processes**; a **function** is what an organizational unit is *responsible for*, not a step in a flow.

### Node vs. ApplicationComponent

| | A **Node** | An **ApplicationComponent** |
|---|---|---|
| Ask | "Is it *infrastructure that hosts or runs* software (where it runs)?" | "Is it the *software that runs on* infrastructure (what runs)?" |
| Looks like | `AppServer`, `Kubernetes Cluster`, `Database Server` | `LoanApp`, `RulesEngine`, `CustomerPortal` |
| Type | `Node` (Technology layer) | `ApplicationComponent` (Application layer) |

A component is **deployed on** a node. An OS / middleware / runtime (e.g. `JBoss`, Linux) is `SystemSoftware`, nested inside its `Node`.

### Actor vs. Role

| | A **BusinessActor** | A **BusinessRole** |
|---|---|---|
| Ask | "Is it the *concrete entity, person, or org unit* (the who)?" | "Is it the *capacity or responsibility* an actor acts in (the as-what)?" |
| Looks like | `Acme Bank`, `Finance Department`, `Jane Smith` | `Loan Officer`, `Approver`, `Customer` |
| Type | `BusinessActor` | `BusinessRole` |

An **actor is assigned to a role**; the **role performs the process**. On a process / swimlane view the swimlane is usually the **role** (the responsibility), not the actor.

> When a concept is genuinely a *part of* a larger element (a sub-component, a module), it is still the **same type as its parent** (e.g. a sub-`ApplicationComponent`). Convey the part-of by **nesting it in the view**, not by drawing a Composition/Assignment connector — see `archimate://reference/archimate-view-patterns`, best-practice rule 4.

## Strategy Layer

Strategic elements that model the enterprise's direction and capabilities.

| Element Type | Description |
|-------------|-------------|
| Resource | An asset or resource owned by or under the control of the enterprise |
| Capability | An ability that an active structure element possesses |
| ValueStream | A sequence of activities that creates an overall result for a customer, stakeholder, or end user |
| CourseOfAction | An approach or plan for configuring capabilities and resources to achieve a goal |

**Common Specializations:** Core Capability, Differentiating Capability, Supporting Capability (on `Capability`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Business Layer

Business processes, actors, roles, and services that deliver value.

| Element Type | Description |
|-------------|-------------|
| BusinessActor | An organizational entity capable of performing behaviour |
| BusinessRole | The responsibility for performing specific behaviour |
| BusinessCollaboration | An aggregate of two or more business internal active structure elements working together |
| BusinessInterface | A point of access where a business service is made available |
| BusinessProcess | A sequence of business behaviours that achieves a specific result |
| BusinessFunction | A collection of business behaviour based on criteria (e.g., required skills) |
| BusinessInteraction | A unit of collective business behaviour performed by two or more business roles |
| BusinessEvent | A business state change |
| BusinessService | An explicitly defined exposed business behaviour |
| BusinessObject | A concept used within the business domain |
| Contract | A formal or informal specification of an agreement between a provider and a consumer |
| Representation | A perceptible form of the information carried by a business object |
| Product | A coherent collection of services and/or passive structure elements, accompanied by a contract, offered as a whole to customers |

**Common Specializations:** Customer-Facing Process, Back-Office Function (on `BusinessProcess`); External Partner, Internal Stakeholder (on `BusinessActor`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Application Layer

Software applications, components, and services.

| Element Type | Description |
|-------------|-------------|
| ApplicationComponent | An encapsulation of application functionality aligned to implementation structure |
| ApplicationCollaboration | An aggregate of two or more application components working together |
| ApplicationInterface | A point of access where an application service is made available |
| ApplicationFunction | Automated behaviour performed by an application component |
| ApplicationInteraction | A unit of collective application behaviour performed by a collaboration |
| ApplicationProcess | A sequence of application behaviours that achieves a specific result |
| ApplicationEvent | An application state change |
| ApplicationService | An explicitly defined exposed application behaviour |
| DataObject | Data structured for automated processing |

**Common Specializations:** Microservice, API Gateway, Message Broker, Data Pipeline, Legacy System, SaaS Application (on `ApplicationComponent`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Technology Layer

Infrastructure, platforms, and technology services.

| Element Type | Description |
|-------------|-------------|
| Node | A computational or physical resource that hosts, manipulates, or interacts with other resources |
| Device | A physical IT resource upon which system software and artifacts may be stored or deployed |
| SystemSoftware | Software that provides or contributes to an environment for storing, executing, and using software |
| TechnologyCollaboration | An aggregate of two or more technology internal active structure elements working together |
| TechnologyInterface | A point of access where technology services are made available |
| Path | A link between two or more nodes, through which they can exchange data or material |
| CommunicationNetwork | A set of structures that connects nodes for transmission, routing, and reception of data |
| TechnologyFunction | A collection of technology behaviour that can be performed by a node |
| TechnologyProcess | A sequence of technology behaviours that achieves a specific result |
| TechnologyInteraction | A unit of collective technology behaviour performed by a collaboration |
| TechnologyEvent | A technology state change |
| TechnologyService | An explicitly defined piece of technology functionality exposed through interfaces |
| Artifact | A piece of data that is used or produced in a software development process, or by deployment and operation of an IT system |

**Common Specializations:** Cloud Server, Database Server, Load Balancer, Firewall, Container Platform, Kubernetes Cluster (on `Node`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Physical Layer

Physical structures, equipment, and materials.

| Element Type | Description |
|-------------|-------------|
| Equipment | One or more physical machines, tools, or instruments that can create, use, store, move, or transform materials |
| Facility | A physical structure or environment |
| DistributionNetwork | A physical network used to transport materials or energy |
| Material | Tangible physical matter or energy |

**Common Specializations:** Data Centre, Edge Site, Manufacturing Line (on `Facility`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Motivation Layer

Stakeholders, drivers, goals, and requirements that motivate the architecture.

| Element Type | Description |
|-------------|-------------|
| Stakeholder | The role of an individual, team, or organization that represents their interests in the architecture |
| Driver | An external or internal condition that motivates an organization to define its goals and implement changes |
| Assessment | The result of an analysis of the state of affairs with respect to a driver |
| Goal | A high-level statement of intent, direction, or desired end state |
| Outcome | An end result that has been achieved |
| Principle | A qualitative statement of intent that should be met by the architecture |
| Requirement | A statement of need that must be realized by the architecture |
| Constraint | A factor that prevents or obstructs the realization of goals |
| Meaning | The knowledge or expertise present in, or the interpretation given to, a concept |
| Value | The relative worth, utility, or importance of a concept |

**Common Specializations:** Security Requirement, Performance Goal (on `Requirement`); Compliance Constraint (on `Constraint`); Regulatory Driver (on `Driver`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Implementation & Migration Layer

Work packages, deliverables, and plateau states for managing change.

| Element Type | Description |
|-------------|-------------|
| WorkPackage | A series of actions identified and designed to achieve specific results within specified time and resource constraints |
| Deliverable | A precisely-defined outcome of a work package |
| ImplementationEvent | A state change related to implementation or migration |
| Plateau | A relatively stable state of the architecture that exists during a limited period of time |
| Gap | A statement of difference between two plateaux |

**Common Specializations:** Migration Work Package, Decommissioning Work Package (on `WorkPackage`); Steady-State Plateau, Transition Plateau (on `Plateau`). See `archimate-specializations.md` for the full catalog and `create-element`'s `specialization` param for inline creation.

## Composite Layer

Grouping and location elements that can contain elements from any layer.

| Element Type | Description |
|-------------|-------------|
| Grouping | A composition of concepts, used to aggregate or compose them (can contain elements from any layer) |
| Location | A place or position where structure elements can be located or behaviour can be performed |

## Layer Hierarchy

The typical dependency flow between layers is:

```
Strategy → Business → Application → Technology → Physical
                ↑
           Motivation
```

- Business services are realized by application components
- Application components are deployed on technology nodes
- Strategy capabilities map to business processes
- Motivation elements (goals, requirements) constrain all layers

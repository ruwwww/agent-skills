---
name: evidence-grounded-biomedical-validation
description: Validates in-silico computational biology and drug-screening findings against empirical literature, clinical trial databases, and deterministic metrics.
version: 1.0.0
author: Hermes Agent
---

# Evidence-Grounded Biomedical Validation Workflow

## Overview
Computational biology models (Boltz, AlphaFold, AutoDock, RDKit) generate probabilistic hypotheses. This skill enforces a deterministic multi-tiered validation framework before drawing actionable biological conclusions.

## Validation Levels (Tiered Evidence Hierarchy)
1. **Tier 1: Clinical & In-Vivo Grounding (Gold Standard)**
   - Verify human clinical trial status (ClinicalTrials.gov, PubMed, FDA databases).
   - Check real pharmacokinetics (PK/PD), oral bioavailability (F%), human half-life (t1/2), and therapeutic window.
   - Screen for known organ toxicity (hepatotoxicity, cardiotoxicity / hERG inhibition, renal clearance).

2. **Tier 2: In-Vitro & Target Engagement Evidence**
   - Confirm IC50 / Kd values in cell-free assays vs whole-cell macrophage/adipocyte assays.
   - Verify on-target specificity vs off-target kinases or off-target nuclear receptors.

3. **Tier 3: In-Silico Deterministic Quality Filters**
   - Check structural confidence: pLDDT >= 80, low PAE at binding interface.
   - Lipinski Rule of 5 and Veber rules for oral drug-likeness.
   - Explicitly flag any theoretical or unverified computational predictions as "Unvalidated Hypothesis".

## Reporting Standards
- Always structure output with TL;DR at top, compact tables, and layered explanations.
- Never use horizontal rule dividers (`---`) or padded line breaks around dividers.
- Always categorize findings by evidence level (Clinical Phase -> Animal In-Vivo -> Cellular In-Vitro -> In-Silico Prediction).
- Explicitly highlight pitfalls, failed clinical trials, or bioavailability bottlenecks.
- Never present pure docking scores or folding predictions as confirmed efficacy.

## Linked References
- `references/pipeline-decision-guide.md`: Mapping of biological questions to computational phases (Prediction vs Physical/Cellular Perturbation vs Safety).


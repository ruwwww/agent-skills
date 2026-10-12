# Computational Biology Pipeline Decision Guide

## Phase Mapping: When to Use Which Tool

| Biological Question | Modeling Phase | Primary Tools | Typical Outputs / Metrics |
| :--- | :--- | :--- | :--- |
| **"What does the 3D structure look like?"** | Phase 1: Structure Prediction & Complex Modeling | Boltz-1/Boltz-2, AlphaFold 3, ESMFold, Chai-1 | PDB/mmCIF coordinates, pLDDT, PAE matrix, contact map |
| **"Will the ligand stay bound under dynamic heat/water?"** | Phase 2A: Physical Perturbation (Molecular Dynamics) | OpenMM, GROMACS, Free Energy Perturbation ($\Delta G$) | Trajectory stability (RMSD in ns), binding free energy |
| **"Does a point mutation destabilize the protein?"** | Phase 2B: Mutational Perturbation | ThermoMPNN, FoldX, ESM-1v | Predicted $\Delta\Delta G$ (kcal/mol), residue tolerance |
| **"How does the whole cell react if this target is blocked?"** | Phase 3: Cellular & Transcriptomic Perturbation | GEARS, chemCPA, scGPT | Perturbed RNA-seq profile, cytokine/pathway shifts |
| **"Is the molecule safe & orally bioavailable for humans?"** | Phase 4: Safety, ADMET & Clinical Grounding | ADMET-AI, SwissADME, PubMed / ClinicalTrials.gov | Hepatotoxicity risk, hERG, F%, human trial history |

## Empirical Grounding Checklist
1. **Never stop at Phase 1:** A static PDB docking pose is an unverified hypothesis.
2. **Scan for Clinical Failures:** Specifically query failed Phase II/III trials for off-target toxicity (e.g. MCC950 hepatotoxicity).
3. **Check Delivery Feasibility:** D-retro-inverso peptides and biologics cannot use standard oral delivery; note subcutaneous/IV routes.

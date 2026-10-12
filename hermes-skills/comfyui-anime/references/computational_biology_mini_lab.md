# Rosalind-Style Local Computational Biology Mini-Lab

This reference documents the setup, execution, and verification of the independent computational biology mini-lab running locally on `/mnt/data/bio-lab`.

## Architecture & Components

* **Storage Root**: `/mnt/data/bio-lab` (Secondary HDD)
  * `models/` : Model checkpoints and cache (`$BOLTZ_CACHE`).
  * `workspace/` : Working directory for sequence FASTA, prediction outputs, and structural artifacts (`.pdb`, `.cif`).
  * `viewers/` : Local WebGL molecular viewer server (`server.py`).

## Core Tooling & CLI

1. **Biomolecular Complex Structure Prediction (Boltz-1 / Boltz-2)**
   * **License**: MIT
   * **Capabilities**: Predicts 3D structures for Protein, DNA, RNA, and small-molecule ligand complexes (AlphaFold 3 level accuracy).
   * **Run Command**:
     ```bash
     boltz predict <input.yaml_or_fasta> --out_dir /mnt/data/bio-lab/workspace/<run_id> --cache /mnt/data/bio-lab/models/boltz_cache --accelerator gpu --devices 1
     ```

2. **Cheminformatics & Sequence Analysis**
   * **Packages**: `rdkit`, `biopython`, `gemmi`, `modelcif`
   * Installed under active conda environment (`ai`).

3. **In-Browser Molecular Structure Viewer (Rosalind-Style)**
   * **Service**: `py3Dmol` WebGL viewer hosted on port `9188`.
   * **URL**: `http://127.0.0.1:9188/` or `http://192.168.1.23:9188/`
   * **Features**:
     * Auto-discovers `.pdb` and `.cif` structures in `/mnt/data/bio-lab/workspace`.
     * Renders Cartoon, Stick, and Sphere representations.
     * Colors structures by pLDDT confidence gradient (B-factor).
   * **Start/Restart Viewer Server**:
     ```bash
     nohup /home/kuroko/.conda/envs/ai/bin/python /mnt/data/bio-lab/viewers/server.py > /tmp/bio_viewer.log 2>&1 &
     ```

## Workflow Execution Loop

1. **Formulate Target**: Create input specification YAML/FASTA with target sequence and ligand SMILES.
2. **Run Prediction**: Execute `boltz predict` on GPU.
3. **Inspect Evidence**: Review pLDDT/pTM scores and view 3D coordinates via port 9188.
4. **Report Findings**: Summarize binding pocket residues, contact distances, and confidence metrics.

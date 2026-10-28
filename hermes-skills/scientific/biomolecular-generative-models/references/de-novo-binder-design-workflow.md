# De Novo Protein Binder Design & Sequence Optimization Workflow

End-to-end procedural guide for designing de novo protein binders using RFD4-Proteina / RFdiffusion backbone generation followed by ProteinMPNN sequence redesign and structure verification.

---

## 1. Target Preparation & Hotspot Selection

1. **Extract Target Subunit:**
   Isolate the target chain or domain of interest into a clean `.cif` or `.pdb` file (e.g., using Biotite).
2. **Identify Target Hotspots:**
   Select 3–6 key residues on the binding surface:
   - Central hydrophobic anchor (e.g., Phe, Ile, Trp).
   - Salt-bridge / hydrogen-bonding partner (e.g., Lys, Arg, Asp, Glu, Gln).

---

## 2. RFD4-Proteina Condition Specification (`spec.yaml`)

Format the input YAML specification for binder design:
```yaml
target_binder:
  input: /path/to/target_chain.cif
  contig: "65-80, /0, C32-117"  # Binder length (e.g. 65 aa), chain break (/0), target chain + residue range
  conditions:
    C_CRDGRP:                    # Target internal coordinate backbone geometry
      1:
        - select: "sel('C/*/*/[N,CA,C,O]') and not has_nan_coord()"
    C_SEQ:                       # Target sequence is fixed
      true:
        - select: "sel('C')"
    C_HOT:                       # Specific atom-level hotspots to engage
      true:
        - select: "sel('C/*/60/[CG,CD1,CD2,CE1,CE2,CZ]')"
        - select: "sel('C/*/79/[NZ]')"
        - select: "sel('C/*/85/[CG,CD1,CD2,CE1,CE2,CZ]')"
        - select: "sel('C/*/86/[OE1,NE2]')"
```

Run generation:
```bash
DISABLE_CUEQUIVARIANCE=1 rfd4-generate \
  inputs=/path/to/spec.yaml \
  num_replicates=4 \
  out_dir=/path/to/output_dir \
  '~metrics' \
  compile_lengths=null \
  hf_ckpt_path=/path/to/models/rfd4
```

---

## 3. ProteinMPNN Sequence Redesign

RFD4 produces full-backbone coordinates with placeholder/poly-N sequences for the generated chain. Use ProteinMPNN to design high-affinity, soluble sequences.

### Step 3.1: Convert CIF to PDB & Strip NaN Hydrogens
RFD4 output CIFs contain heavy atoms with valid coordinates, but unassigned hydrogen atoms may have `NaN` coordinates. When exporting to PDB:
```python
import biotite.structure.io as strucio
import biotite.structure.io.pdb as pdb
import numpy as np

array = strucio.load_structure("generated.cif")[0]
# Crucial: Filter out NaN coordinates before PDB export
valid = array[~np.isnan(array.coord).any(axis=1)]
pdb_file = pdb.PDBFile()
pdb_file.set_structure(valid)
pdb_file.write("backbone.pdb")
```

### Step 3.2: Parse Chains & Assign Chains to Design
```bash
# 1. Parse multi-chain complexes into JSONL
python helper_scripts/parse_multiple_chains.py \
  --input_path=/path/to/pdbs \
  --output_path=/path/to/parsed_pdbs.jsonl

# 2. Assign chains:
# CRITICAL RULE: --chain_list specifies the chain(s) TO BE DESIGNED, NOT the fixed chains!
python helper_scripts/assign_fixed_chains.py \
  --input_path=/path/to/parsed_pdbs.jsonl \
  --output_path=/path/to/assigned_pdbs.jsonl \
  --chain_list "A"   # Chain A = generated binder chain to design
```

### Step 3.3: Run ProteinMPNN with Soluble Weights
For soluble mini-proteins and binders, always use `--use_soluble_model` to prevent over-sampling hydrophobic residues (e.g. poly-Leu):
```bash
python protein_mpnn_run.py \
  --jsonl_path /path/to/parsed_pdbs.jsonl \
  --chain_id_jsonl /path/to/assigned_pdbs.jsonl \
  --out_folder /path/to/mpnn_out \
  --num_seq_per_target 4 \
  --sampling_temp "0.2" \
  --seed 42 \
  --batch_size 1 \
  --use_soluble_model
```

---

## 4. In Silico Filtering & Quality Gates

Evaluate designed binders against standard biophysical thresholds:
1. **Net Charge & Solubilty:** Target net charge between -5 and +12; GRAVY < 0.0 (hydrophilic surface) to prevent aggregation.
2. **Cysteine Count:** Filter for designs with 0 cysteines (or deliberate even-numbered disulfide pairs) to avoid mispairing in non-reducing environments.
3. **Hotspot Engagement:** Ensure the designed interface makes heavy-atom contacts (< 4.5 Å) with all targeted hotspot residues.
4. **Validation (Boltz-1 / AlphaFold 3):**
   - Complex pLDDT > 80.
   - Interface PAE (iPAE) < 10.0 Å (ideally < 5.0 Å).
   - Rosetta binding score (ddG) < -30 kcal/mol.

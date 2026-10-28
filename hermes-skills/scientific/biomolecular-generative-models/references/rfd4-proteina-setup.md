# RFD4-Proteina (RFdiffusion v4) Setup & Workaround Reference

## Overview
RFD4-Proteina is an all-atom flow-matching foundation model for biomolecular design (proteins, nucleic acids, ligands, and complexes) released by the Institute for Protein Design (Baker Lab) and NVIDIA GenAIR.

- **Repository:** `https://github.com/RosettaCommons/RFD4-Proteina`
- **Hugging Face Hub Model:** `nvidia/RFD4-Proteina` (public repo, ~1.7 GB safetensors + config)

## Fast Installation into an Existing Conda/Venv

### 1. Shallow Clone
```bash
git clone --depth 1 https://github.com/RosettaCommons/RFD4-Proteina.git
cd RFD4-Proteina
```

### 2. Python Constraint Adjustment (for Python 3.11)
RFD4-Proteina defaults to `requires-python = ">=3.12,<3.13"`. When running in a Python 3.11 environment, edit `pyproject.toml`:
```bash
sed -i 's/requires-python = ">=3.12,<3.13"/requires-python = ">=3.11,<3.13"/' pyproject.toml
```

### 3. Non-Destructive Package Installation
```bash
pip install -e . --no-deps
```

### 4. Selective Leaf Dependencies
Install only what is missing without reinstalling core numerics:
```bash
# Physics & molecular scoring
pip install "tmol>=0.2.0,<0.3" --no-deps

# Molecular I/O and annotations (biotraj is required by biotite.structure.io.xtc)
pip install "atomworks>=3.0.4,<4" "biotite>=1.6.0" biotraj --no-deps

# CLI & runtime typing helpers (marshmallow is required by environs)
pip install environs marshmallow jaxtyping beartype rootutils anarcii assertpy --no-deps
```

## Legacy Namespace Resolution (`proteinfoundation`)
RFD4 was refactored from NVIDIA's internal `proteinfoundation` repository to `rfproteina`. If downstream pipelines or legacy scripts import `proteinfoundation`:
- Create a symlink in the project source and site-packages:
  ```bash
  ln -s ./src/rfproteina ./src/proteinfoundation
  ln -s ./src/rfproteina $(python -c "import site; print(site.getsitepackages()[0])")/proteinfoundation
  ```
- Or alias the import in python:
  ```python
  import rfproteina as proteinfoundation
  ```

## Model Weights & Asset Retrieval
Weights are hosted on Hugging Face (`nvidia/RFD4-Proteina`).

### Token Pitfall (Expired OAuth Token)
If `~/.cache/huggingface/token` contains an expired OAuth token, Hugging Face returns `401 Client Error` or `Repository not found` even for public models.
- Fix: export `HF_TOKEN=""` or copy a valid token from `~/.cache/huggingface/stored_tokens` before downloading.

### Direct Download to Local Bundle Directory
To avoid writing 1.7 GB to the root filesystem (`/`), download directly to high-capacity storage (e.g. `/mnt/data/bio-lab/models/rfd4`):
- `config.json` (7.3 KB)
- `model.safetensors` (1.7 GB)

When both files reside in a local directory, point `hf_ckpt_path=/path/to/dir` and `rfd4-generate` will load them locally without checking the Hugging Face Hub.

## Known Runtime Incompatibilities & Code Fixes

### 1. Python 3.11 f-string SyntaxError in `atomworks`
- **Location:** `atomworks/ml/datasets/metadata.py` (around lines 391–393)
- **Symptom:** `SyntaxError: f-string expression part cannot include a backslash`
- **Fix:** Python 3.11 does not permit backslashes in f-string expression braces. Define the unicode box-drawing character outside the f-string:
  ```python
  dash = "\u2500"
  top = "\u250c" + header.ljust(inner_width, dash) + "\u2510"
  bottom = "\u2514" + (dash * inner_width) + "\u2518"
  empty = f"\u2502{' ' * inner_width}\u2502"
  ```

### 2. cuEquivariance Driver/CUDA Mismatch
If cuEquivariance ops are not installed or fail to compile against local CUDA:
```bash
export DISABLE_CUEQUIVARIANCE=1
```

### 3. Sampling Schedule Constraints in `rfd4-generate`
- **Symptom:** `ValueError: recycle schedule expands to 60 steps; expected 5` or `ValueError: nsteps must be at least tail_steps * tail_step_multiplier`
- **Cause:** Default recycle schedule defines 60 steps (`n_recycle_schedule`), and `_schedule_with_tail_multiplier` enforces `nsteps >= tail_steps * tail_step_multiplier` (10 * 2 = 20 minimum).
- **Rule:** For smoke testing or production runs, keep default `generation.args.nsteps=60` and use `compile_lengths=null` with `'~metrics'` to skip warm-up and evaluation overhead.

### 4. Verified Smoke Test Command
```bash
DISABLE_CUEQUIVARIANCE=1 rfd4-generate \
  inputs=binder.yaml \
  num_replicates=1 \
  out_dir=./runs/smoke \
  '~metrics' \
  compile_lengths=null \
  hf_ckpt_path=/mnt/data/bio-lab/models/rfd4
```
Generates designed `.cif` output under `./runs/smoke/inference_samples/binder_0/`.

---
name: biomolecular-generative-models
description: "Use when deploying biomolecular generative design models."
---

# Biomolecular Generative Models

Procedural guide for deploying, integrating, and operating biomolecular generative foundation models (such as RFdiffusion, RFD4-Proteina, Boltz, and OpenFold) locally in existing Python/CUDA environments without destabilizing shared PyTorch baselines.

## Core Rules for Shared AI Environments

When deploying structural generative models into existing environments (e.g., shared Conda or venv with custom PyTorch/CUDA wheels):

1. **Protect the Baseline PyTorch/CUDA Stack:** Never execute unrestricted `pip install -r requirements.txt` or general install extras (such as `.[all-cuda13]`) that risk replacing optimized PyTorch, torchvision, or Triton builds.
2. **Minimal Non-Destructive Installation:**
   - Always install local packages using editable mode without pulling dependencies:
     ```bash
     pip install -e . --no-deps
     ```
   - Inspect existing packages (`pip list`) before adding anything. Skip packages already present (`numpy`, `scipy`, `matplotlib`, `torch`, `lightning`).
   - Only install absolute missing leaf dependencies directly (e.g., `tmol>=0.2.0,<0.3`, `atomworks`, `biotite`, `environs`).
3. **Prefer Source Patching Over Dependency Upgrades:** If runtime issues arise from package version mismatches (e.g., Python minor version constraints in `pyproject.toml`, deprecated PyTorch API kwargs, or renamed module namespaces), patch the model source code or project configuration rather than altering the host environment libraries.

## Supported Model Playbooks

- **RFD4-Proteina / RFdiffusion v4:** See [references/rfd4-proteina-setup.md](references/rfd4-proteina-setup.md) for full setup instructions, asset downloads from Hugging Face (`nvidia/RFD4-Proteina`), and compatibility workarounds.
- **De Novo Binder Design & Sequence Optimization Pipeline:** See [references/de-novo-binder-design-workflow.md](references/de-novo-binder-design-workflow.md) for full end-to-end workflow (target preparation, hotspot conditioning spec, backbone diffusion, NaN coordinate filtering, ProteinMPNN soluble sequence design, and quality gating).

## General Diagnostics & Workarounds

- **Python Version Mismatch in pyproject.toml:**
  If a repository specifies `requires-python = ">=3.12,<3.13"` but the existing environment is Python 3.11, relax the rule in `pyproject.toml`:
  ```bash
  sed -i 's/requires-python = ">=3.12,<3.13"/requires-python = ">=3.11,<3.13"/' pyproject.toml
  ```
- **Optional CUDA Acceleration Operators (e.g., cuEquivariance):**
  If fused kernels or custom C++/CUDA ops fail to compile or link against the local CUDA version, check for fallback flags (e.g., `export DISABLE_CUEQUIVARIANCE=1`) before attempting to rebuild system CUDA toolchains.
- **Upstream Namespace Renaming:**
  When repositories transition namespaces (e.g., `proteinfoundation` to `rfproteina`), provide aliasing via symlinks or inline import re-aliasing (`import rfproteina as proteinfoundation`) instead of reinstalling old versions.

# Priming Model Reproduction & Latent-Space Porting Lessons (2026-10-16)

## Context
Validation of arXiv:2610.20331 (*"Are We Overthinking One-Step Generation? Priming Models"*, GitHub: `JaeyeonKim01/priming`) on CelebA latents ($16 \times 16 \times 32$) using a 47.5M Looped-DiT backbone.

## Core Lessons & Pitfalls

### 1. Never Compute Optimal Transport on Raw Flattened Latents
- In the official Priming framework, Stage 2 (Distributional Post-Training via Sinkhorn OT) operates in the **feature space** of frozen visual backbones (ConvNeXt-V2, MAE, DINOv2, SigLIP) with calibrated bandwidths and vector-Jacobian products (`input_vjp`).
- Attempting to compute Sinkhorn OT directly on flattened latent vectors ($1 \times 8192$) without semantic feature projectors acts like an unconstrained adversarial distortion:
  - Destroys skin translucency into a synthetic, plastic/waxy finish.
  - Causes severe color clipping (black crush in hair, hyper-saturated neon backgrounds).
  - Produces multi-colored blotchy chromatic noise on 1-step sampling.

### 2. Official Feature-Space OT Behavior
- Moving OT to decoded RGB space with frozen DINOv2 (`dinov2_vits14`) preserves natural color calibration and realistic lighting.
- However, 1-step generation ($NFE=1$) inherently suffers from identity drift and edge harshness compared to proper trajectory integration.
- Even with official Priming, a few-step Euler ODE ($NFE=4$) yields vastly superior structural fidelity, realism, and identity consistency over single-step evaluation.

### 3. User Directive: Default to Official Architecture
- Whenever paper reproduction presents architectural choices, always choose the official paper specification rather than inventing ad-hoc latent shortcuts.

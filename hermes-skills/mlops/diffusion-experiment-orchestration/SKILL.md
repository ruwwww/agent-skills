---
name: diffusion-experiment-orchestration
description: Use when screening, stabilizing, or tracking diffusion runs.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [diffusion, generative, flow-matching, training, wandb, screening]
    related_skills: [weights-and-biases, codex-orchestration, model-inference-verification]
---

# Diffusion Experiment Orchestration & Screening Standard

This skill establishes the mandatory standard for training, screening, tracking, and debugging diffusion/flow-matching models (both latent-space and pixel-space architectures).

---

## 1. Mandatory Pre-Training Screening Protocol

Never launch long training runs (e.g. 50k–100k steps) directly. A screening run of **50–100 steps** must precede the main run to verify:

1. **Numerical Stability & Gradient Flow:**
   - Verify that gradient norms remain bounded (apply `grad_clip` 0.5–1.0).
   - Check that loss decreases smoothly without NaN, Inf, or sudden exponential divergence.
2. **Visual Dynamic Range:**
   - Sample 4–6 images at step 50/100 using Euler ODE.
   - Confirm the presence of structural emergence from noise (no dead solid gray, zero-tensor outputs, or black screens).
3. **Live Tracking Readiness:**
   - Ensure experiment tracker (W&B) initializes cleanly and stream metrics/sample media before committing full hardware resources.

---

## 2. Architecture-Specific Stability Rules

### A. Looped Transformers (Weight-Tying / Recurrent Blocks)
- **Compounding Drift:** Passing through shared core blocks multiple times per step causes activations to compound exponentially.
- **Mandatory Protections:**
  - **QK-Norm:** Apply RMSNorm to Query and Key before attention.
  - **Loop-Boundary RMSNorm:** Normalize hidden states between recurrent loop passes ($h_r$).
  - **Bounded adaLN:** Clamp adaptive modulation scale ($[-2.0, 2.0]$) and gate ($[-4.0, 4.0]$).
  - **Normalized Deep Supervision:** Ensure the sum of all exit loss weights equals a fixed constant (e.g. 2.0).

### B. Pixel-Space Diffusion (Zero-VAE)
- **x-Prediction Objective:** Directly predict clean image $\hat{x}_0$ using $v$-weighted velocity loss:
  $$\mathcal{L} = \left\| \frac{\hat{x}_0 - x_t}{\max(1 - t, 0.05)} - v \right\|^2$$
- **Direct Linear OutputHead (No CNN Upsamplers):**
  - Use `AdaLN-LayerNorm + Linear(dim, patch_size * patch_size * channels)` followed by direct `unpatchify` (tensor reshape).
  - *Anti-Pattern:* Never insert miniature CNN upsampler decoders (e.g. 16-channel `Conv2d` blocks) at the DiT output. Under pixel MSE loss, underparameterized CNN decoders collapse into mode-averaged low-pass blur (painterly/airbrushed faces).
- **Multi-Scale Pyramid Readouts:**
  - Decode intermediate resolutions (e.g. $128 \times 128$) via linear readout heads tapped from intermediate trunk blocks, rather than convolutional upsampling pyramids.
- **Zero-Init & No Tanh for Linear Output Heads:**
  - Initialize `final_layer.linear.weight` and `bias` to zero (`nn.init.zeros_`). Never use Xavier initialization on final pixel projection.
  - Do NOT wrap `unpatchify` in `torch.tanh` (saturates boundary gradients and creates patch-seam checkerboards).
  - Use 2D Sin-Cos positional embeddings and 2D RoPE to enforce cross-patch continuity.
- **Multi-Objective Perceptual Supervision (PixelGen & Linum AI):**
  - Pure MSE in pixel space produces blurry/soft textures due to mode-averaging.
  - Augment with local texture loss (LPIPS VGG, weight 0.1), global semantic loss (P-DINO patch cosine layer 11, weight 0.01), and intermediate representation alignment (REPA with 3-layer MLP projector, weight 0.5).
  - **Noise-Gating Rule:** Enable perceptual losses only at low-noise timesteps ($g(t) = \mathbb{I}(t \ge 0.3)$ where $t=1$ clean, $t=0$ noise) to prevent over-constraining early denoising and reducing sample coverage/recall.
- **ModelEMA Warmup Trap:**
  - Flat `decay=0.9999` retains 37% initial random weights even at step 10,000, causing preview samples to look like washed-out static noise. Always use EMA warmup decay `min(decay, (1 + step) / (10 + step))` or check raw model weights for early diagnostics.

### C. Few-Step & One-Step Generation (Priming Two-Stage Framework - arXiv:2610.20331)
- **First-Class Reproducibility Rule:** When reproducing or validating a paper, ALWAYS strictly adhere to the official published architecture and pipeline. Never substitute core architectural components with ad-hoc heuristics (e.g. bypassing feature encoders or flattening raw latents) unless explicitly requested.
- **The Few-Step Truncation Trap:** Standard flow matching models taking large steps ($dt=1.0$ or $dt=0.25$) output the conditional MMSE mean — resulting in ghost-like, blurry images devoid of fine textures.
- **Two-Stage Priming Protocol:**
  - **Stage 1 (Reconstruction Priming):** Pre-train or fine-tune at fixed high corruption ($t_{\text{noise}} = 0.8$) predicting clean data directly ($\hat{x}_1 = x_t + t_{\text{noise}} \cdot v$) via Huber/SmoothL1 loss. This primes the model with single-step restoration inductive bias. Stage 1 alone already yields high-quality, natural, photorealistic samples under few-step sampling (e.g. 4-step Euler ODE) without mode collapse.
  - **Stage 2 (Distributional Post-Training - Semantic Feature OT Mandatory):**
    - Feed pure noise ($t=0$), predict single-step jump, and minimize unbiased feature-wise Sinkhorn Optimal Transport discrepancy against real data:
      $$\mathcal{L}_{\text{dist}} = D_{\text{OT}}(P_{\text{live}}, P_{\text{real}}) - D_{\text{OT}}(P_{\text{live}}, P_{\text{neg}})$$
    - **CRITICAL LATENT-SPACE PITFALL (Raw Latent Flattening vs Semantic Encoders):**
      - NEVER compute Sinkhorn OT directly on flattened raw latent vectors ($z \in \mathbb{R}^{B \times (C \cdot H \cdot W)}$) or raw pixel intensities. Without frozen semantic encoders (e.g. ConvNeXt-V2, ViT-MAE, SigLIP, or DINOv2), optimal transport in raw feature space penalizes point-wise distance without semantic awareness.
      - *Failure Symptom:* Flattened raw-latent OT induces severe mode distortion — resulting in mannequin-like "waxy/plastic" skin, flat pitch-black crushed shadows on hair, neon-saturated backgrounds, and blotchy chromatic rainbow noise in 1-step sampling.
      - *Remedy:* Always decode latents to RGB ($x = \text{VAE.decode}(z)$) and pass through frozen semantic extractors before computing feature-wise transport cost matrix (`costs.append(_laplacian_cost(feat_q, feat_p, sigma))`) using Vector-Jacobian Product (VJP) backward pass. If frozen vision encoders cannot be used, stop at Stage 1 or use perceptual distillation (LPIPS + DINO).
- **Empirical Validation:** 4-step Euler sampling with Stage 1 Priming achieves crisp, photorealistic face fidelity matching 50-step high NFE (12.5x compute speedup).
- **VRAM Guardrails:** Keep pre-cached latents in CPU pinned memory and disable intermediate exit backward graphs during single-step endpoint training to run smoothly under $\le 4$ GB VRAM.

---

## 3. Experiment Tracking & Artifact Standard

1. **Live Weights & Biases (W&B):**
   - Stream `loss`, `lr`, `grad_norm`, and periodic sample grids with strictly monotonic step ordering.
2. **Offline Fallback (`tracker.py`):**
   - Record `metrics.jsonl` and save local PNGs under `figures/` for resilience against network drops.
3. **Clean Weight Export:**
   - Convert checkpoints to clean `.safetensors` format (EMA weights only) for publishing to Hugging Face Model Hub.

---

## 4. References & Linked Guides
- `references/priming_few_step_two_stage_framework.md`: Mathematical formulation, Sinkhorn Optimal Transport discrepancy, and CelebA-HQ benchmark results for the Priming two-stage framework (arXiv:2610.20331).
- `references/pixel_perceptual_supervision_guide.md`: Detailed math and implementation guide for PixelGen (arXiv:2602.02493) and Linum AI multi-objective loss (LPIPS, P-DINO, REPA, Noise Gating) and pure linear patch unpatchify.
- `references/looped_stability_postmortem.md`: Analysis of recurrent activation compounding in Looped-DiT and QK-norm stabilization.
- `templates/tracker.py`: Complete tracker template with dual W&B streaming and JSONL offline logging.

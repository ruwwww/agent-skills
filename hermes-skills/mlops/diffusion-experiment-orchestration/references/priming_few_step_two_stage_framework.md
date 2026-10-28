# Priming Two-Stage Framework for Few-Step & One-Step Generation

Reference guide based on official implementation of *Are We Overthinking One-Step Generation? Priming Models* (Jaeyeon Kim, Woobin Park, et al., arXiv:2610.20331) validated on CelebA-HQ ($16 \times 16 \times 32$ latent space, f16c32 VAE, 47.5M Looped-DiT).

---

## 1. Why Standard Flow Matching / Diffusion Fails in Few Steps

In standard continuous flow matching ($x_t = t \cdot x_1 + (1 - t) \cdot x_0$), models are trained with mean squared velocity error averaged over all $t \in [0, 1]$:
$$\mathcal{L}_{\text{FM}} = \mathbb{E}_{t, x_0, x_1} \left[ \| v_\theta(x_t, t) - (x_1 - x_0) \|^2 \right]$$

When integrating with Euler ODE at high NFE (e.g. 50 steps, $dt = 0.02$), the trajectory negotiates curved probability paths cleanly. However, in few-step regimes:
- **1-Step Jump ($dt = 1.0$):** Taking a single step along the initial velocity tangent at $t=0$ overshoots the curved data manifold. Because the objective was MSE, the model outputs the conditional mean (MMSE estimate) — an extremely soft, ghostly "average face" devoid of high-frequency details.
- **4-Step Jump ($dt = 0.25$):** Reduces truncation error but still exhibits noticeable haziness, washed-out contrast, and simplified boundaries unless distilled.

Traditional solutions (Consistency Distillation, LCM, Rectified Flow Reflow) require complicated multi-step teacher rollouts, student trajectory pairing, and sensitive ODE solver tolerances.

---

## 2. The Priming Two-Stage Formulation

Priming replaces complex ODE distillation with a clean, stable two-stage training scheme:

```
                  Stage 1: Reconstruction Priming
      [Clean x] ──> Corrupt at fixed t=0.8 ──> [Noisy x_t]
                           │
                           ▼
                    Looped-DiT Denoiser
                           │
                           ▼
              Predict clean endpoint x_clean
              Loss: SmoothL1(x_clean_pred, x)

                           │ (Inherit EMA / Online weights)
                           ▼
               Stage 2: Distributional Post-Training
      [Gaussian Noise x_0] ──> Generate 1-Step Jump x_live = x_0 + 1.0 * v(x_0, 0)
      [Negative Noise x'_0] ──> Generate 1-Step Jump x_neg  (detached)
      [Real Data x_real]   ──> Fetch batch from training set
                           │
                           ▼
         Unbiased Sinkhorn Optimal Transport Discrepancy
        L_dist = OT(x_live, x_real) - OT(x_live, x_neg)
```

### Stage 1: Reconstruction Priming
- **Fixed High Corruption:** Train at fixed $t_{\text{noise}} = 0.8$ (corresponding to $t_{\text{flow}} = 0.2$).
- **Objective:** Directly predict the clean endpoint $\hat{x}_1$:
  $$\hat{x}_1 = x_t + t_{\text{noise}} \cdot v_\theta(x_t, t_{\text{flow}})$$
- **Loss:** Adaptive L1 or Huber loss against clean latent/image:
  $$\mathcal{L}_{\text{Stage 1}} = \text{SmoothL1}(\hat{x}_1, x_1, \beta=0.01)$$
- **Why it works:** Pre-training at fixed high noise primes the network weights with the structural inductive bias of direct single-step restoration, avoiding mode collapse during subsequent distributional optimization.

### Stage 2: Distributional Post-Training (Feature-wise Sinkhorn OT)
- **1-Step Generation:** Feed pure Gaussian noise $x_0 \sim \mathcal{N}(0, I)$ at $t=0$.
  $$x_{\text{live}} = x_0 + 1.0 \cdot v_\theta(x_0, 0)$$
- **Negative Population:** Generate independent reference samples $x_{\text{neg}}$ from distinct noise draws (detached from computation graph).
- **Unbiased Distributional Loss:**
  $$\mathcal{L}_{\text{dist}} = D_{\text{OT}}(P_{\text{live}}, P_{\text{real}}) - D_{\text{OT}}(P_{\text{live}}, P_{\text{neg}})$$
- **Laplacian Kernel & Sinkhorn Plan:**
  $$C(q, p) = -\exp\left(-\frac{\|q - p\|_2}{\sigma}\right)$$
  Compute entropic transport plan $P$ via batch feature-wise Sinkhorn iteration (50 iterations, tolerance $10^{-4}$, $\epsilon = 0.01$).
- Only $x_{\text{live}}$ receives gradients.

---

## 3. Empirical Results & Forensic Failure Analysis on CelebA-HQ ($16 \times 16 \times 32$ Latents, Looped-DiT 47.5M)

| Configuration | NFE | Visual Quality | Key Artifacts / Behaviors |
| :--- | :---: | :--- | :--- |
| **Original Baseline (High NFE)** | 50 | Photorealistic | Converged, crisp eyes, fine wrinkles, natural skin pores, specular highlights. |
| **Baseline Unprimed (1-Step)** | 1 | Extremely Blurry | Ghostly MMSE average face; complete loss of high frequencies. |
| **Baseline Unprimed (4-Step)** | 4 | Soft / Hazy | Recognizable, but soft edges, low contrast, airbrushed textures. |
| **Stage 1 Priming (4-Step Euler)** | 4 | **Sharp & Photorealistic** | Natural skin tones, crisp iris, hair strands, teeth, clean depth of field without color shift. Matches 50-step high NFE at **12.5x speedup**. |
| **Stage 1 Priming (1-Step Jump)** | 1 | Coherent Global Structure | Positions eyes, nose, mouth properly, but diffuse edges under pure L1 regression without adversarial/perceptual loss. |
| **Stage 2 with Raw Latent Flattening (1-Step)** | 1 | **Severely Degraded** | Rainbow chromatic noise, mottled blotches, burned crimson patches, melted eyes/mouth. |
| **Stage 2 with Raw Latent Flattening (4-Step)** | 4 | **Uncanny / Corrupted** | Eliminates blotchiness but produces waxy/porcelain mannequin skin, pitch-black crushed hair without strands, and neon-red background clipping. |

---

## 4. The Raw-Latent Optimal Transport Trap (Forensic Analysis)

### Why Raw Latent Flattening Destroys Generation Quality
In the official implementation (`JaeyeonKim01/priming`), Stage 2 computes Sinkhorn Optimal Transport over **97 multi-scale feature outputs** extracted from frozen vision backbones (ConvNeXt-V2-Base and ViT-Large MAE):
$$\mathcal{L}_{\text{matching}} = \sum_{l=1}^L w_l \cdot D_{\text{OT}}\left(\phi_l(\hat{x}), \phi_l(x_{\text{real}})\right)$$
Backpropagation uses Vector-Jacobian Products (VJP) through the frozen networks.

When adapting to latent-space models, flattening raw latent vectors ($z \in \mathbb{R}^{B \times 8192}$) directly into a Laplacian/Euclidean distance matrix creates an adversarial attractor:
1. **Loss of Semantic Geometry:** The $L_2$ metric in VAE latent space does not correspond to perceptual realism. Shifting latent channels arbitrarily changes chromaticity, contrast, and high-frequency harmonics unpredictably.
2. **Channel-Drift & Over-Sharpening:** Without deep spatial pyramid feature matching, Sinkhorn OT pushes latent marginals by over-saturating extreme values. This results in crushed blacks (pure black hair with zero texture), overexposed highlights (bleached porcelain skin), and hyper-saturated red backgrounds.
3. **The Correct Latent Adaptation (Always Choose Official Architecture over Shortcuts):**
   - **First-Class Rule on Paper Reproduction:** Always follow the official paper's design and loss formulation strictly. Never invent convenient shortcuts (such as flattening raw latents or bypassing frozen visual extractors) when replicating published frameworks.
   - Decode generated latents to RGB: $\hat{x}_{\text{RGB}} = \text{VAE.decode}(z_{\text{live}})$.
   - Pass $\hat{x}_{\text{RGB}}$ through a frozen perceptual encoder (e.g. DINOv2 ViT-S/14 or ConvNeXt).
   - Compute Sinkhorn OT or feature matching on the resulting semantic tokens.
   - Alternatively, omit Stage 2 OT and rely on Stage 1 Priming (which already achieves pristine 4-step sampling) followed by progressive perceptual flow distillation.

---

## 5. Implementation Best Practices & Hardware Guardrails

1. **CPU Pinned Memory for Latents:**
   When background processes (e.g. LLM servers, ComfyUI) occupy VRAM, store the full pre-cached latent dataset in host RAM using `.pin_memory()`. Stream batches to GPU via `non_blocking=True` to keep VRAM usage under ~3.5 GB during post-training.
2. **Gradient Accumulation & Batch Size:**
   Sinkhorn OT benefits from batch size $\ge 32$ per step. Use microbatch 16 with accumulation steps 2 to prevent peak allocation spikes during the dual live/negative forward rollout.
3. **Loop Activation Pruning in Looped-DiT:**
   When training single-step endpoints, evaluate only the final loop exit (`num_loops=4, exit_loops=()`) rather than retaining intermediate loop backward graphs.

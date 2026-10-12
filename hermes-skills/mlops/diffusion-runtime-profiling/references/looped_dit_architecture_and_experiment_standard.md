# Looped-DiT Architecture & Experimentation Pipeline Standards

Reference guidelines for configuring, training, tracking, and evaluating Looped-DiT models (arXiv:2609.40305 / OpenSenseNova) on latent diffusion spaces.

---

## 1. Looped-DiT Architecture Specification (~50M Parameter Class)

Looped-DiT achieves the expressive capacity of deep transformers without multiplying physical parameter weights by reusing a core group of transformer blocks $N$ times within each denoising step.

### Parameter Partitioning (`loop_split = (pre, core, post)`)
- **Pre-loop Blocks ($A$):** Run once per denoising step (`pre = 2`). Encodes early spatial and condition features.
- **Looped Core Blocks ($B$):** Run $N$ times iteratively (`core = 4`, default $N = 4$ loops). Reuses identical physical weights across iterations.
- **Post-loop Blocks ($C$):** Run once per denoising step (`post = 2`), followed by output projection head to decode velocity/clean latent.
- **Physical vs Effective Depth:**
  $$\text{Physical Blocks} = \text{pre} + \text{core} + \text{post} = 2 + 4 + 2 = 8 \text{ blocks}$$
  $$\text{Effective Depth} = \text{pre} + (N \times \text{core}) + \text{post} = 2 + (4 \times 4) + 2 = 20 \text{ blocks}$$
- **Dimension & Capacity (~49M - 50M Parameters):**
  - Hidden dimension $D = 512$, heads $H = 8$ (head dim 64).
  - SwiGLU FFN with `mlp_ratio = 6.0` (intermediate dimension 3,072).
  - Physical parameter count: **49.03M parameters**.

### Exclusive Self-Attention (XSA)
In naive looping, repeated attention passes on the same core blocks suffer from self-reinforcing representation collapse. Looped-DiT applies **Exclusive Self-Attention (XSA)** to looped core blocks:
$$\hat{v} = \frac{v}{\|v\|_2}, \quad \text{Attn}_{\text{XSA}} = \text{Attn} - (\text{Attn} \cdot \hat{v})\hat{v}$$
This projects out the token's own value vector from the attention output, forcing the loop to extract fresh cross-token interactions rather than redundant self-content.

### Deep Supervision
During training, intermediate loop states $h_r$ (for $r \in \{1, \dots, N-1\}$) are passed through post-loop blocks $C$ and supervised against the identical flow matching target:
$$\mathcal{L} = w_N \mathcal{L}_{\text{final}} + \sum_{r=1}^{N-1} w_r \mathcal{L}_r$$
Using exponential weighting ($w_r = \text{scale} \times 0.5^{N-r}$) ensures intermediate layers progressively converge toward clean manifold predictions.

---

## 2. Looped-DiT Training Dynamics & Numerical Stability (Empirical Pitfalls)

Empirical training on latent spaces (e.g. CelebA-HQ f16c32 latents at $105\text{k}$ steps) reveals critical failure modes specific to recurrent weight-tying in diffusion transformers:

### A. Failure Mode: Late-Stage Loss Explosion / NaN Divergence
- **Symptom**: Model converges smoothly during initial epochs (e.g., loss steadily declines from $3.75 \to 0.79$ over steps $1 \dots 28\text{k}$), but exhibits loss spikes around step $30\text{k}-35\text{k}$ ($2.5 \to 80 \to 1800$) before catastrophically exploding into $10^6$ loss magnitude and `FloatingPointError` / NaNs around steps $50\text{k}-58\text{k}$.
- **Root Cause (Recurrent Weight Tying & BPTT Gradient Accumulation)**:
  - In a standard DiT, gradients flow feed-forward through each distinct block once.
  - In Looped-DiT, the same 4 core blocks receive backpropagated gradients across all $N$ loops within a single step. Without per-loop normalizers or spectral gating, repeated weight matrix multiplications compound activation and gradient magnitudes exponentially over long multi-epoch runs.
  - **Deep Supervision Amplification**: When intermediate exits $h_1 \dots h_{N-1}$ are simultaneously differentiated back into the shared core without gradient truncation or detach, small numerical drifts in layer activations create an amplified feedback loop into the core block weights.

### B. Proven Stabilization Interventions for Looped-DiT
When training Looped-DiT for deep runs (>50k steps):
1. **Per-Loop Boundary Normalization**: Apply explicit RMSNorm to the latent state $h_r$ after each loop pass $r$ before re-entering core block $B_1$, strictly bounding representation norm drift to $\sim 22\text{--}25$ instead of compounding to billions.
2. **QK-Normalization in Self-Attention**: Always enable QK-Norm (`q_norm`, `k_norm` via RMSNorm) inside the looped attention blocks to prevent attention logits from saturating during repeated passes.
3. **Bounded adaLN Modulation**: Clamp adaLN `scale` to $[-2.0, 2.0]$ and `gate` to $[-4.0, 4.0]$. This mathematically guarantees that residual multipliers $(1 + \text{scale})$ cannot explode exponentially across recurrent passes.
4. **Normalized Deep Supervision**: Rescale all intermediate exit weights and final exit weights so their total sum equals $2.0$ (matching OpenSenseNova), preventing multi-exit gradient amplification.
5. **Aggressive Gradient Norm Clipping**: Constrain `torch.nn.utils.clip_grad_norm_` to $\le 0.5$ (default $1.0$ is insufficient for recurrent BPTT in DiTs).

---

## 3. Standardized Experiment Tracking Protocol (W&B as Primary)

All generative model training runs must conform to the unified tracking contract:

### A. Weights & Biases (W&B) as First-Class Live Tracking
- **Default Platform**: Always initialize `wandb.init(project=..., name=...)` as the primary live dashboard (default entity `fixgmc-personal`).
- **Real-Time Telemetry**: Log scalar loss, learning rate, GPU memory, and loss components per step.
- **Visual Media Timeline**: Save periodic VAE-decoded generation grids directly via `wandb.log({"samples/face_grid": wandb.Image(grid_path)}, step=step)` to enable interactive step slider review in the W&B UI.
- **Monotonic Step Sync Rule**: When using offline post-sync tools (`sync_wandb.py`), group metrics and images into a step-keyed dictionary and commit in strictly ascending numerical order to prevent out-of-order drop warnings.

### B. Local Output Layout (Offline Backup & Artifact Contract)
```text
outputs/<experiment_name>/
├── config.json               # Full hyperparameter & model dictionary
├── train.log                 # Standard output stream
├── metrics.jsonl             # Newline-delimited JSON metrics per log step (offline buffer)
├── checkpoints/              # Checkpoint directory
│   ├── checkpoint_last.pt    # Atomic auto-resume target
│   └── checkpoint_XXXXXX.pt  # Periodic historical milestones
└── figures/                  # Offline visual artifacts
    ├── loss_curve.png        # Auto-plotted loss curve from metrics.jsonl
    └── sample_step_XXXXXX.png# Periodic VAE-decoded generation grids
```

### Logging Rules
1. Every step must append a machine-readable JSON dictionary to `metrics.jsonl` containing `{"step", "epoch", "loss", "lr", "timestamp"}` as an offline buffer.
2. The `ExperimentTracker` (`tracker.py`) streams live to W&B when connected and maintains local files for offline auditing.
3. Checkpoints must always save `checkpoint_last.pt` so training can resume seamlessly without lost progress.
4. Export clean inference checkpoints to `.safetensors` format when publishing to Hugging Face Hub.

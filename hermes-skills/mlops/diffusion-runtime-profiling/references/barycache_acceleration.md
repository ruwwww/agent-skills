# Training-Free DiT Acceleration via BaryCache

## Core Concept (Kiramei et al., arXiv:2608.28670)
BaryCache accelerates Diffusion Transformers (DiTs) without finetuning or heavy per-layer activation buffers by forecasting intermediate feature trajectories using a clipped, decay-adjusted **Barycentric Extrapolator**:
- At anchor steps, full computation runs across all 32 transformer blocks and feature states immediately preceding the final layer are cached.
- At skipped steps, all 32 transformer blocks are completely bypassed (~100% block FLOPs eliminated) and extrapolated features are directly forwarded to the final layer and unpatchify stage.

## The 90% Refinement Sweetspot (`end_percent = 0.9`)
In diffusion processes, early and middle steps dictate global layout, anatomy, and color composition, while the final ~10% of steps synthesize high-frequency details (micro-hatching, sharp lineart, facial marks, hair wisps).
- **100% Caching (`end_percent = 1.0`):** 8.43s (1.83x speedup vs compile baseline, 2.24x vs eager), but introduces minor perceptual softening on fine lines and serrated details.
- **90% Refined (`end_percent = 0.9`):** Ceases caching for the final 10% of steps (e.g. final 3 steps in a 30-step run). Recovers **100% baseline high-frequency sharpness** in **9.67s** (1.60x vs compile baseline, 1.96x vs eager).

## Warm Benchmark Ablation (832x1216 @ 30 steps, RTX 5060 Ti)
Do not conflate compiler speedup with cache speedup:
- Pure Eager (no compile, no cache): **18.92 s**
- TorchCompile baseline: **15.45 s** (1.22x vs eager)
- BaryCache standalone (no compile): **10.59 s** (1.79x standalone vs eager)
- BaryCache + TorchCompile (100%): **8.43 s** (2.24x vs eager, 1.83x vs compile)
- BaryCache + TorchCompile (90% sweetspot): **9.67 s** (1.96x vs eager, 1.60x vs compile)

## Recommended ComfyUI Production Fastpath
Combine service-level optimizations, compiler, and caching:
1. Systemd service args: `--fast --use-ck-attention`
2. `TorchCompileModelAdvanced`: `backend="inductor"`, `mode="default"`, `compile_transformer_blocks_only=True`
3. `ApplyAnimaBaryCache`:
   - `mode_cache="stepwise"`
   - `mode_schedule="eq-space"`
   - `fresh_start=3`, `fresh_interval=2`, `max_history=2`
   - `start_percent=0.0`, `end_percent=0.9`
4. Result: 832x1216 @ 30 steps renders in **< 10 seconds** with zero perceptual degradation.

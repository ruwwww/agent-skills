---
name: diffusion-runtime-profiling
description: "Profile diffusion DiT models, CFG B=1/B=2, and fusions."
version: 1.0.0
---

# Diffusion Model Runtime Profiling & Optimization

## Core Philosophy: "What You Can't Measure, You Can't Optimize"
When profiling, auditing, or optimizing diffusion models (DiT, Cosmos 2, Anima, Diffusion LM, DiffusionGemma):
1. **Never rely solely on CPU wall-clock timestamps or top-level wrappers**: Isolate the core forward pass (`diffusion._forward`) to measure actual GPU kernel execution without framework dispatch overhead.
2. **Benchmark Both Single ($B=1$) and Batched CFG ($B=2$)**:
   - Single forward ($B=1$) tests pure forward latency and baseline FLOPs.
   - Batched CFG ($B=2$) measures compute saturation when positive and negative conditionings run in a single tensor.
   - Always compare Batched CFG vs Sequential CFG ($2 \times B=1$) to determine batching efficiency and memory bandwidth tradeoffs.
   - **Diffusers vs ComfyUI CFG & Batching Discrepancy (Blackwell SM120 Findings)**:
     * *Transformer Level*: Diffusers `AnimaLoopDenoiser` runs sequentially ($2 \times B=1$), while ComfyUI batches into $B=2$. However, on mid-tier Blackwell GPUs (RTX 5060 Ti 128-bit bus, 36 SMs), $B=2$ transformer forward is **2.8% slower** (537.65 ms vs 523.20 ms) because 1MP latents already saturate SM occupancy, and $B=2$ doubles activation traffic and register pressure.
     * *Timing Boundary*: ComfyUI's 12–13s measurement excludes text encoding and VAE decoding synchronization, measuring only the KSampler loop with persistent zero-allocation buffer reuse.
     * *VAE Decode Latency Bottleneck at Multi-Batch*: In `AutoencoderKLQwenImage`, decoding latency at $B=2$ spikes from **565 ms ($B=1$) to 1,139 ms ($B=2$)** (+574 ms). On Turbo/distilled pipelines (4–8 steps, ~2.5–3.0s DiT time), VAE decoding at $B=2$ dominates total latency, causing **2x batch (CFG=1, ~4.1s) to be slower than 1x batch (CFG>1, ~3.6s)**. Optimizing VAE decoding (or fusing in Mirage MPK) is mandatory for multi-batch scaling.

## Measurement Protocol
- **Kernel-level Timing**: Use `torch.cuda.Event(enable_timing=True)` with proper warmup (2–5 iterations) and multiple test iterations (4–10 iterations).
- **Profiling Traces**: Export Chrome trace JSON (`prof.export_chrome_trace(...)`) to inspect CUDA stream activity, kernel overlaps, and idle bubbles via `ui.perfetto.dev`.
- **Operator Categorization**:
  - `GEMM Linear`: Dense matrix multiplications (`aten::mm`, Cutlass TensorOp kernels).
  - `Attention`: SDPA / FlashAttention (`aten::_flash_attention_forward`).
  - `Norm & RoPE`: Fused RMSNorm / LayerNorm + RoPE (`comfy_kitchen::rms_rope_split_half`).
  - `Non-Attention Elementwise`: Gated Residual (`aten::addcmul`) and AdaLN modulation (`norm * (1 + scale) + shift`).

## Compiler & Fused Kernel Verification
- When using `torch.compile` / Inductor (e.g. `--fast --use-ck-attention` or `TorchCompileModelAdvanced` on DiT blocks):
  - Check whether Inductor generates fused Triton kernels (`inductor_fused_other`) for elementwise operations.
  - Verify if AdaLN modulation and gated residual operations are fused into single-kernel launches to eliminate global VRAM roundtrips.

## CUDA Graph (`reduce-overhead`) Troubleshooting & Best Practices
- **Autograd Registration Blocker**: Custom ops (like `comfy_kitchen.rms_rope_split_half`) lacking backward formulas cause AOTAutograd failures. Always execute sampling under `torch.inference_mode()`.
- **Shape Validation Traps**: CUDA Graph capture replays can fail if internal custom op validators require strict high-dimensional layouts (e.g. requiring 6D `freqs_cis` when DiTs supply compact 4D/5D shapes). Ensure input adapter layers add necessary broadcast dimensions before kernel dispatch.
- **Mark Step Begin**: When invoking CUDA Graph captured subgraphs across iterative diffusion sampling steps, call `torch.compiler.cudagraph_mark_step_begin()` at the start of each step.

## GEMM Acceleration Strategies for DiTs & Key Pitfalls
- **Spatially-Sparse Token GEMM**: Deduplicating flat/identical background tokens in middle MLP blocks (e.g. Blocks 10–26) reduces row dimension $M$ (e.g. $7,904 \rightarrow 4,000$), providing up to **1.94× GEMM speedup** with **Cosine Similarity = 1.000000 (Lossless, $\text{QSNR}=\infty\text{ dB}$)**.
  - **Critical Pitfall (Dynamic Dispatch Overhead)**: Never use `torch.unique` or dynamic Python `index_select` inside the iterative diffusion sampling loop. The Python CPU overhead (~2.5 ms/block) severely outweighs the Tensor Core GEMM savings (~0.17 ms/block), slowing down generation (e.g. from 14.9s to 28.7s).
  - **Fixed Spatial Grid Mapping**: Eliminates dispatch overhead (<0.01 ms/block) but causes representation degradation (cosine similarity drops to ~0.47) on arbitrary non-duplicate spatial tokens.
- **Outlier-Preserving Mixed Precision (W4A8 / DiRotQ Style)**: Protect top 2% activation outlier channels in high precision (BF16/FP8 per-token) while processing 98% in low-bit GEMM to maintain **$\sim 44.5\text{ dB}$ activation QSNR** without AdaLN error cascading.
  - **Kernel Overhead Warning**: Standalone Triton W4A8 dequantization without unified C++/CUTLASS Tensor Core fusion introduces significant kernel launch latency compared to native CUTLASS BF16 on modern RTX cards.

## Workflow & Production Isolation Rules
- **Never Modify Core Production Inference Paths Directly**: Keep experimental GEMM/quantization hooks isolated in standalone worktrees. Modifying core dispatchers in production ComfyUI breaks baseline workflows and increases dispatch latensi.
- **Dedicated Service Isolation for Profiling**: When profiling or testing dangerous changes (e.g. CUDAGraph compile `mode="reduce-overhead"`), launch a separate isolated ComfyUI service instance (e.g. on port `9199` via systemd `comfyui-cudagraph.service` pointing to `/mnt/data/comfy-profiling-worktree/comfy-isolated/` with symlinked `models/`) to ensure production port `8188` remains completely untouched.
## Baseline Sweet Spot for Anima / Cosmos 2 DiT:
  - **BF16 Base**: `--fast --use-ck-attention` + `TorchCompileModelAdvanced` (Inductor, `mode="default"`, `fullgraph=False`). Reaches **~14.9s–15.3s / ~2.08 it/s** on 832x1216 @ 30 steps ($B=2$).
  - **Blackwell MXFP8 Fastpath**: `--fast --use-ck-attention` + Native `TorchCompileModel` + `anima-base-v1.0-mxfp8.safetensors` ([Bedovyy/Anima-FP8](https://huggingface.co/Bedovyy/Anima-FP8/tree/main)). Reaches **~11.7s–12.0s / ~2.75 it/s** on RTX 5060 Ti 16GB (~2.55x speedup vs eager baseline) with zero visual quality loss.
  - **ConvRot (Regular Hadamard Rotation) Quantization**:
    - Smooths DiT activation and weight outliers via group-wise RHT ($N_0=256$) without clipping damage.
    - Native ComfyUI + `comfy-kitchen` execution requires zero custom node registration: uses `{prefix}.comfy_quant` metadata to automatically dispatch to `ck.int8_linear(convrot=True)` and `ck.convrot_w4a4_linear`.
    - Layer retention policy: Keep `blocks.0`, `blocks.1`, `blocks.27`, and `adaln_modulation` in BF16; quantize blocks 2–26 (MLP and attention projections). Cuts model size from 3.89 GB to 2.41 GB with 0.99988 cosine similarity.
    - **Empirical 3-Way Benchmark (RTX 5060 Ti 16GB, 832x1216, 30 steps, B=2)**:
      * ConvRot INT8: **~2.70 it/s (~11.1s)** sustained in warmed-up ComfyUI sessions (**~90% semantic fidelity winrate vs MXFP8**; nearly identical to BF16 ground truth, though inherently a slightly semantically lossy algorithm).
      * MXFP8: **2.67 it/s (~11.2s)** (pure hardware microscaling without online activation rotation).
      * BF16: **2.05 it/s (~14.9s)** (lossless reference ground truth).
    - Converter tool: `tools/quantize_anima_convrot.py` in `ruwwww/anima-fastpath-recipe`. Weights on Hugging Face: `ruwwww/Anima-ConvRot`. Detailed guide in `references/convrot_mxfp8_quantization_guide.md`.
  - **ConvRot Model Quantization Workflow**:
    - Convert standard Cosmos/Anima models to INT8 ConvRot via `/mnt/data/finetune-anima/quantize_anima_convrot.py --input <model.safetensors> --output <model-convrot-int8.safetensors> --mode int8 --groupsize 256`.
    - Symlink or move output directly into `/home/kuroko/ComfyUI/models/diffusion_models/`. ComfyUI's native loader detects `comfy_quant` metadata and runs hardware acceleration out of the box.

## BaryCache Acceleration (Fastest Verified DiT Pipeline):
  - Add `ApplyAnimaBaryCache` (from `ComfyUI-Anima-BaryCache` custom node) after `TorchCompileModelAdvanced` or directly to `UNETLoader`.
  - **Ablation Reporting Rule**: Never conflate compiler speedup with cache speedup. Always report clean 4-way ablation: Pure Eager (18.92s) vs Compile Alone (15.45s) vs BaryCache Alone (10.59s) vs Combined (8.43s).
  - **90% Refinement Sweetspot (`end_percent=0.9`)**: Drops 30-step 832x1216 render time down to **~9.67s (1.96x vs eager, 1.60x vs compile)** while recovering 100% baseline-sharp high-frequency lineart, teeth, and textures.
  - See `references/barycache_acceleration.md` for full parameter profiles and benchmark breakdowns.

## Low-Rank Adapter Optimization & Geometry in DiTs:
  - **Orthogonal Optimizers (Muon / Dion3) Inapplicability on LoRA**: Muon and Dion3 enforce polar decomposition / partial isometries on dense 2D matrices ($d \times d$). On skinny LoRA matrices ($2048 \times 8$), separate factor orthogonalization destroys low-rank gauge invariance and induces severe $\sqrt{d/r} = 16\times$ learning rate distortion between up and down projections.
  - **Normalized Low-Rank Adaptation (NoRA-Init, arXiv:2608.31036)**: Directly stabilizes early LoRA dynamics by normalizing down-projection columns ($||d_j||_2 = 1$) at initialization, equalizing the initial preconditioner diagonal ($s^2 D^\top D = I$) with 0 runtime overhead.
  - **$\sigma$-Demoted Training & Gradient Parity (arXiv:2608.04448, Seunghyun Ji / `sorryhyun/anima_lora`)**:
    - *Theoretical derivation*: Decomposes downscaling gradient error into a $\sigma$-dependent term (decays at high noise as spectral theory predicts) and a $\sigma$-independent floor (carried by absolute token count of the target compute graph).
    - *Certified routing windows*: On $1024 \to 768$, gradients remain near-native specifically within the window $\sigma \in [0.65, 0.95]$; on $1024 \to 896$, valid on half-line $\sigma > 0.5$.
    - *Throughput gain*: Routing high-noise steps to lower-resolution sibling latents (`--sigma_lowres`) cuts DiT LoRA wall-clock time by $14.6\%$ (scheduled `combolate`, $\Delta W \approx 0.75$) to $18.3\%$ (unscheduled `combo`) on identical step budgets with near-native weight fidelity.
    - *Architecture optimizations in `anima_lora`*: Fused $QKV$ single GEMM ($[6144 \times 2048]$), Free-Fit bucketing with one Dynamo graph per tier (zero recompilation), and integrated DP-DMD few-step distillation.

## References & Advanced Architectures
- `references/mirage_mpk_dit_compilation.md` — Sovereign DiT task-graph compilation via Mirage MPK: 100% AOT zero-scheduler execution, in-kernel persistent Euler multi-step loop, Cosmos/Anima layer mapping, and QK-norm pitfalls.
- `references/pjit_convrot_sageattn_optimization.md` — Bare-metal DiT optimization recipe (P-JiT case study): ConvRot INT8 group-64 power-of-4 rules, SageAttention varlen integration, ComfyUI --fast half-precision accumulator flags, and 4-bit NF4 text encoder serving on 16GB GPUs.
- `references/speech_and_audio_diffusion_profiling.md` — Speech & audio diffusion profiling (AuK Flux2Edit, BigVGAN), SDPA vs SageAttention short-context rules, steady-state benchmarking, and VAE vocoder isolation.
- `references/barycache_acceleration.md` — Training-free BaryCache integration, stepwise vs blockwise caching, and 90% refinement sweetspot.
- `references/anima_lora_training_guide.md` — Complete training recipe, SageAttention backward blocker analysis, alpha scaling rules, and ComfyUI LoRA conversion.
- `references/modelopt_ptq_anima_guide.md` — NVIDIA Model Optimizer calibrated PTQ (FP8/NVFP4) for Anima DiT, module filter/exclusion semantics, and dual-branch CFG trajectory calibration.
- `references/anima_runtime_profiling_and_gemm_acceleration.md`
- `references/anima_w4a8_w8a8_vae_benchmarks.md` — Anima DiT W4A8 vs W8A8 latency/reconstruction benchmark, and VAE high-res convolution im2col vs Implicit GEMM analysis on RTX 5060 Ti SM120.
- `references/flow_matching_lagrangian_jacobian.md` — Lagrangian formulation of Flow Matching, denoiser Jacobian curvature dynamics, and decoupled auxiliary curvature head designs for diffusion solvers.
- `references/latent_flow_matching_and_guidance_scaling.md` — Latent Flow Matching training with pre-cached latents, DINOv2 semantic cluster conditioning, CFG dynamics, and DiT width scaling.
- `references/looped_dit_architecture_and_experiment_standard.md` — Looped-DiT 50M architecture (XSA, deep supervision, loop_split=(2,4,2) with 20 effective layers), standardized experiment tracking layout, and numerical stabilization rules against BPTT divergence.
## Finetuning & Tagging Pipeline Protocol (Kohya sd-scripts for Anima DiT)
- **Directory Structure Requirement**: Kohya's `train_data_dir` MUST point to the *parent root* directory containing subfolders named `<repeats>_<concept>` (e.g. `data_root/10_hebi_nyodo/`), NOT directly to the image folder itself, otherwise it throws `ERROR: No data found`.
- **Anima-Specific CLI Arguments & Critical Pitfalls**:
  - **Attention Engine Blocker**: NEVER use `--attn_mode="sageattn"` for training! SageAttention is inference-only in `library/attention.py` (lacks autograd backward). Training with it silently zeroes out all Q/K/V attention weight updates (`lora_up = 0`), updating only MLPs and causing catastrophic output corruption (abstract impasto noise). Always use `--attn_mode="torch"` (native PyTorch SDPA).
  - **VAE Specification**: Anima requires Qwen-Image VAE (`--vae="/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors"` with `--qwen_image_vae_2d`). Do NOT use Wan VAE.
  - **Text Encoder**: Use `--qwen3="/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors"` (do not use `--text_encoder` which causes ambiguous option error).
  - **LoRA Scope & Scaling**:
    - For single character/concept LoRA, always pass `--network_train_unet_only` to isolate DiT transformer blocks and prevent Qwen 3 text encoder semantic degeneration.
    - Set `--network_alpha=1.0` with `--network_dim=8` (or `16`) at `learning_rate=1e-4` to `2e-4`. Setting `--network_alpha=16` at `1e-4` over-scales updates ($\alpha/\text{dim}=1.0$) and destabilizes latent generation; if using `--network_alpha=16`, lower learning rate to `1e-5`.
    - Memory optimization: Enable `--cache_latents` and `--optimizer_type="AdamW8bit"` (or `Prodigy` with lr=1.0).
  - **Selective Gradient Checkpointing Sweet Spot (12 Blocks)**:
    - Full checkpointing (28 blocks) wastes 71.5% step time in recomputation and leaves ~10.5 GB VRAM idle.
    - Zero checkpointing triggers CUDA OOM (>15.5 GiB).
    - Optimal placement on RTX 5060 Ti 16GB: `--selective_checkpointing=count --checkpoint_blocks=12` (available in fork `ruwwww/sd-scripts`). Cuts step latency from 2,134 ms to 1,715 ms (~1.24x speedup, saves 327 ms recomputation) with 12.46 GiB VRAM peak (3.34 GiB safe headroom).
  - **LoRA Adapter Weights vs PiSSA / SVD Initialization in DiTs**:
    - PiSSA (SVD initialization) accelerates LLM agentic RL, but is ill-suited for DiT concept LoRAs: mutating principal singular vectors shifts base style priors and breaks modular zero-shot LoRA merging in ComfyUI. Keep standard LoRA init for diffusion character adapters.
  - **Hadamard / Monarch MLP Considerations**:
    - Replaces dense FFN with 3-stage Kronecker Monarch mixes, cutting MLP FLOPs by 40%. Requires full pretraining from scratch; cannot be hot-swapped into pre-trained dense DiT checkpoints.
- **Key Conversion for ComfyUI**:
  - Kohya `sd-scripts` saves keys with `lora_unet_blocks_...` prefix, whereas ComfyUI Cosmos/Anima loader requires `diffusion_model.blocks....`.
  - Always run the official converter before loading in ComfyUI:
    `python networks/convert_anima_lora_to_comfy.py <input.safetensors> <output_comfy.safetensors>`
- **ComfyUI Verification Flow**:
  - First validate in a clean workflow: `UNETLoader -> LoraLoaderModelOnly -> KSampler` (avoid placing `TorchCompileModelAdvanced` or custom attention hooks before `LoraLoader` during initial acceptance test).
- **Dataset Tagging & Trigger Words**:
  - Run WD14 Tagger (ONNX GPU accelerated via `SmilingWolf/wd-swinv2-tagger-v3`).
  - Prepend trigger phrase (e.g. `hebi nyodo, fate`) to caption `.txt` files and remove generic character tags to avoid concept dilution.
  - Tagging runner helper is stored at `/mnt/data/finetune-anima/run_tagging_pipeline.py`.

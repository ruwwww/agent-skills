# AuK SM120 Native Upstream Optimization Notes (2026-09-12)

## Context & User Correction
When optimizing Tencent Hunyuan AuK (AuK-Flash / AuK-Base) for NVIDIA GeForce RTX 5060 Ti (Blackwell SM120), initial automation attempted to import `ComfyUI-AuK.nodes.runtime` and `comfy.model_management` because the weights were downloaded from a community safetensors repo (`drbaph/AuK-comfyui`).
The user explicitly intervened:
> "did i said anything about using ComfyUI as runtime? i hope you didnt told codex to optimize from the ComfyUI runtime"
> "Tolol2 kok malah pakai comfyui runtime sih. Kan sudah kubilang pakai runtime original bawaan AuK"

## Core Engineering Rules
1. **Zero UI Framework Coupling**:
   - Model optimization must operate at bare-metal PyTorch and CUDA/CUTLASS levels.
   - Never import `comfy`, `comfy.model_management`, or custom node wrappers into an optimization, engine, or benchmark codebase.
2. **Upstream Source Hierarchy (`src/auk`)**:
   - Upstream repo: `Tencent-Hunyuan/AuK`
   - Transformer backbone: `from auk.model.flux2_edit import Flux2Edit`
   - Flow Matching ODE: `from auk.model.cfm_edit import CFMEdit`
   - Vocoder / VAE: `from auk.model.vae import load_vae_model` (`BigVGANFlowVAE`)
   - Inference CLI / API: `from auk.infer.infer_auk import AukInfer`
3. **Blackwell SM120 Performance Stack**:
   - **Attention**: PyTorch SDPA is 5–7x faster than block-quantized SageAttention 2.2 for short audio latent sequences ($S \le 500$ frames).
   - **Precision**: Native BF16 Tensor Cores with immediate BF16 downcast in epilogue registers (avoids FP32 staging register pressure).
   - **4-Step Fixed Diffusion Loop**: AuK-Flash uses a fixed 4-step Euler schedule ($t \in [0.0, 0.07608, 0.29289, 0.61732, 1.0]$) with CFG=1 ($B=1$). Static shape bucketing (3s, 5s, 10s) combined with `torch.compile` delivers >24–30x real-time speech synthesis on RTX 5060 Ti.

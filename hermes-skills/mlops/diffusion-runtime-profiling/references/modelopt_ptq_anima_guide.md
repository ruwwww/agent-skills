# Model Optimizer PTQ & Low-Bit Calibration for Anima DiT

## Overview & Architecture Alignment
Anima 2B is an image diffusion model derived from NVIDIA Cosmos-Predict2 / `CosmosTransformer3DModel`:
- **Core DiT**: 28 layers, 16 attention heads, head dim 128, mlp ratio 4.0 (hidden dimension 2048, MLP intermediate 8192). Total parameters ~1.956B.
- **Text Conditioning**: Qwen3-0.6B (`Qwen3Model`, ~596M parameters) + T5 / LLM adapter.
- **Latent VAE**: Qwen-Image 2D VAE (`AutoencoderKLQwenImage`, ~126M parameters).
- **Target Workload**: Batch-1 generation at $832 \times 1216$, CFG scale $\approx 3.5 - 4.0$, flow-matching Euler / ER-SDE sampler (30 steps).

## ModelOpt Diffusers Quantization Convention
In `examples/diffusers/quantization`:
1. **Module Filter Function Semantics**:
   - `filter_func(module_name: str) -> bool`: returns `True` to KEEP module in original precision (DISABLE quantization).
   - Returns `False` to ENABLE quantization.
2. **Module Targeting Strategy for Anima DiT**:
   - **Preserved in Baseline Precision (`return True`)**:
     * Input patch projection (`patch_embed.proj` / `x_embedder`)
     * Output projection (`proj_out` / `final_layer.linear`)
     * Timestep / text embeddings (`time_embed`, `t_embedder`, `norm`)
     * AdaLN modulation linears (`norm1.linear_1/2`, `norm2`, `norm3`, `norm_out` / `adaln_modulation`)
     * Normalizations and non-linear layers.
   - **Quantization Targets (`return False`)**:
     * Self-attention projections: `attn1.to_q`, `attn1.to_k`, `attn1.to_v`, `attn1.to_out.0`
     * Cross-attention projections: `attn2.to_q`, `attn2.to_k`, `attn2.to_v`, `attn2.to_out.0`
     * Feed-forward / MLP projections: `ff.net.0.proj`, `ff.net.2` (or `mlp.linear_1`, `mlp.linear_2`)
3. **Calibrated PTQ over Real Denoising Trajectory**:
   - Calibrating on raw random noise or static image tensors causes catastrophic dynamic-range distortion.
   - Must execute the actual `pipe(prompt, negative_prompt, num_inference_steps=n_steps, guidance_scale=4.0, height=1216, width=832)` pipeline so forward hooks capture activations across the real flow-matching trajectory covering both positive and negative CFG branches.
   - Micro-batching ($B=1$) with bounded memory prevents VRAM OOM on 16 GB GPUs (RTX 5060 Ti).

## Precision Modes: FP8 vs NVFP4
- **FP8 (E4M3)**: Standard 8-bit floating point for linear layers. Good baseline retention, but can exhibit slight contrast/lineart flattening if modulation paths are improperly quantized.
- **NVFP4 (E2M1 / W4A4)**: Supported on Blackwell (SM120) Tensor Cores. Requires local Hessian or MSE scale calibration. Attention computations should remain in BF16/FP8 while dense linear projections execute in NVFP4.

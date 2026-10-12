# ComfyUI & comfy-kitchen DiT Non-Attention Kernel Integration

## Context & Motivation
Diffusion Transformer (DiT) models (such as Cosmos 2, Anima, Wan2.1, MiniMax-H3) spend noticeable wall-clock time in memory-bound non-GEMM and non-attention operators. In eager PyTorch, these operators cause round-trips to VRAM and launch overhead across 20-30+ layers over dozens of denoising steps.

## Key Non-Attention Fused Operators

### 1. Fused AdaLN Modulation (LayerNorm + Scale/Shift)
- **Formula:** `out = LayerNorm(x) * (1 + scale) + shift`
- **Eager Overhead:** Multiple intermediate allocations for normalized `x`, scaled `x`, and broadcast addition.
- **Kernel Implementation:**
  - Single-pass / single-barrier block reduction for mean and variance.
  - In-register modulation before writing out to global memory.
  - Microbenchmark speedup: ~2.25x - 5.27x over eager PyTorch.

### 2. Fused Gated Residual Accumulation
- **Formula:** `x += gate * result` (in-place)
- **Eager Overhead:** Calling `torch.addcmul` allocates or runs separate elementwise passes without fusing memory traffic.
- **Kernel Implementation:**
  - Vectorized load of `x`, `gate`, and `result` directly in SRAM, accumulating in FP32 and storing in-place (`BF16`/`FP16`).
  - Microbenchmark speedup: ~5.9x over standard `torch.addcmul`.

### 3. Fused QK RMSNorm + RoPE
- **Formula:** `q = rope(rms_norm(q)), k = rope(rms_norm(k))`
- **Kernel Implementation:**
  - Implemented in `comfy_kitchen` via `rms_rope_split_half` or `rms_rope`.
  - Avoids saving unrotated RMSNorm activations back to DRAM.

## Upstream Integration & PR Architecture

When proposing custom kernel optimizations to the ComfyUI ecosystem:
1. **Repository Separation:**
   - **`comfy-kitchen`**: High-performance C++/CUDA and Triton kernels, unit tests, and layout classes.
   - **`ComfyUI` Core**: Safe dispatch hooks with strict fallback:
     ```python
     if comfy.quant_ops._CK_AVAILABLE and hasattr(comfy.quant_ops.ck, "adaln"):
         try:
             return comfy.quant_ops.ck.adaln(x_flat, scale_flat, shift_flat).view(...)
         except Exception:
             pass
     return norm_layer(x) * (1 + scale) + shift
     ```
2. **Numerical Parity Requirement:**
   - Always verify that custom fused kernels match PyTorch eager within tight tolerance (`< 1e-4` for FP32/BF16 accumulate).

# MXFP8 Quantization & MoE Megakernels (ThunderKittens / Mixture-of-Kittens)

## 1. Overview
MXFP8 (Microscaling FP8 - OCP standard) implements elementwise E4M3/E5M2 values paired with shared E8M0 block scale factors (32 elements per scale factor).
In MoE architectures (DeepSeek V4, GLM-5.2, Mixture-of-Kittens), routed expert GEMMs are memory-bandwidth and dispatch bound. Pre-quantizing routed expert weights (Gate, Up, Down) to MXFP8 delivers up to **1.23x - 1.30x speedups** on Hopper/Blackwell clusters (EP64).

## 2. Low-Level Kernel Optimization Patterns (from `mxfp8.cuh`)

### A. Dual-Layout Quantization in Single Kernel Pass
- **Requirement:** Forward GEMM requires normal layout $W$, Backward input gradient GEMM requires transposed layout $W^\top$.
- **ThunderKittens Pattern:** Template parameters `RETURN_NORMAL` and `RETURN_TRANSPOSED` allow generating both $W_{\text{fp8}}$ and $W^\top_{\text{fp8}}$ along with their respective E8M0 scales in a single TMA-loaded memory tile pass ($128 \times 128$).

### B. Bitwise Scale Reciprocal Generation
- **Problem:** Float division `1.0f / scale` is costly on GPU ALUs.
- **Bitwise Trick:** Invert E8M0 block scale by directly constructing the IEEE-754 reciprocal in bitwise integer math:
  ```cpp
  // directly build float32 reciprocal without division
  const float scale_inv = __uint_as_float((254u - scale_byte) << 23);
  ```

### C. NVIDIA TCGEN05 Scale Layout Alignment
- Scales must follow the NVIDIA Tensor Core layout contract for Blackwell / TCGEN05 MMA instructions:
  ```cpp
  move<int>::sts(sc_dst_addr + (row % 32) * 16 + (row / 32) * 4, std::bit_cast<int>(scale_word));
  ```

### D. PTX Instruction Mapping
- **E8M0 Scale Computation:** `cvt.rp.satfinite.ue8m0x2.f32` (Round towards positive infinity, saturate to finite).
- **E4M3 Value Quantization:** `cvt.rn.satfinite.e4m3x2.f32` (Round to nearest even).

## 3. Weight Caching & Invalidation Protocol in PyTorch / NeMo
- **Microbatch & Recomputation Re-use:** Keep quantized MXFP8 weights cached across all forward passes and activation checkpointing backward recomputations.
- **Invalidation Trigger:** Hook invalidation strictly to `optimizer.step()` when master BF16 weights are updated.

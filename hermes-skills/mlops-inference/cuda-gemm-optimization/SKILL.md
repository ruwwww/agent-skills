---
name: cuda-gemm-optimization
description: Optimize CUDA GEMM kernels to achieve peak performance (95-100% of cuBLAS)
references:
  - references/cuda-architecture.md
  - references/benchmark-template.cu
  - references/cublas-comparison.md
tags:
  - cuda
  - gemm
  - optimization
  - tensor-core
  - blackwell
  - sm120
---

# CUDA GEMM Optimization and Benchmarking

Optimize CUDA GEMM kernels to achieve peak performance (95-100% of cuBLAS). Critical learnings from RTX 5060 Ti (SM 120) vs RTX 5080:

## Key Architecture Constraints

### RTX 5060 Ti (SM 120 - Blackwell GeForce)
- ❌ **NO F32 Tensor Cores**
- ✅ **F16/BF16 Tensor Cores available** (mma.sync instructions)
- F32 ops via regular FMA only (~1.9 TFLOPS/SM)
- F16 ops via Tensor Cores (~15.7 TFLOPS/SM) - **8.3x faster**
- 80 SMs, 6MB L2 cache, 896 GB/s memory

### RTX 5080 (SM 120 - Blackwell Ada)
- ❓ **F32 Tensor Core support unclear** (likely not in GeForce variant)
- 102 SMs, 24MB L2 cache, 1.2 TB/s memory
- Better memory bandwidth and cache for larger tiles

## Performance Reality

### F32 GEMM (naive)
```
Time: ~839ms for 4096x4096
GFLOP/s: ~164 GFLOPS
% cuBLAS: ~1.0%
```

### F32 GEMM (optimized, FMA only)
```
Time: ~134ms
GFLOP/s: ~1025 GFLOPS
% cuBLAS: ~6.6%
```

**Maximum achievable F32:** ~1,500 GFLOPS (~9.6% cuBLAS) - **NO F32 TENSOR CORE!**

### F16/BF16 GEMM
```
Time: ~0.35s (naive)
GFLOP/s: ~781 GFLOPS (naive) → ~30,000 GFLOPS (optimized)
% cuBLAS: ~2.6% → ~92.5% achievable
```

**F16 is 8.3x faster than F32 on same hardware!**

## To Achieve 97%+ cuBLAS on SM 120

**Use F16/BF16 precision** (NOT F32!):

1. Check GPU architecture first:
   ```bash
   nvcc --gpu-architecture=sm_120 --arch=sm_120 -ptx kernel.cu 2>&1
   ```

2. For SM 120 (Blackwell GeForce):
   - Only `mma.sync` instructions (thread-level), not `wgmma` (warp-level)
   - F16/BF16 tensor ops supported
   - F32 must use regular FMA (no tensor acceleration)

3. For F16/BF16 optimization:
   - Use `mma.sync.aligned.m16n8k16.rf16` or similar
   - Warp organization: 4 warps per block, 128 threads
   - TMA for memory acceleration on SM 120
   - Register pressure <128 registers/thread

## References

See `references/` directory for detailed documentation, templates, and benchmark scripts:
- `references/cuda-architecture.md`
- `references/benchmark-template.cu`
- `references/cublas-comparison.md`
- `references/hybrid-linear-moe-architectures.md` — Notes on hybrid 3:1 KDA-MLA attention and fine-grained MoE (Ling/Kimi) for 16GB VRAM GPUs.
- `references/mxfp8_quantization_and_moe_megakernels.md` — ThunderKittens MXFP8 E4M3/E8M0 block-scaled dual-layout quantization kernel patterns and MoE caching protocols.
- `references/custom-engine-serving-benchmarks.md` — Prefill chunking, persistent server concurrency sweeps (C=1 to C=8), and MTP speculative decoding verification on Blackwell SM120.
- `references/cutlass-cute-sm120-dit-gemm.md` — CUTLASS 3.x / CuTe C++ and Python CuTe DSL patterns, layout algebra, Swizzle, and DiT GEMM baselines on Blackwell SM120.
- `references/ternary-quantization-and-fused-fwht-gemv.md` — 1.58-bit ternary quantization (PQ2_0/PTQ1_0), Walsh-Hadamard rotated basis overhead analysis, and fused FWHT+GEMV kernel design for Blackwell SM120.
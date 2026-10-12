---
name: cuda-gpu-architecture-tensor-core
description: Guide for working with CUDA GPU architectures and tensor core optimizations
category: cuda
created: 2026-08-29
updated: 2026-08-29
---

# CUDA GPU Architecture & Tensor Core Usage

## Overview

This skill guides working with CUDA GEMM kernels and tensor core optimizations. **Critical:** Different GPU architectures have fundamentally different capabilities and instruction sets.

## GPU Architecture Families

### Blackwell Architecture (SM 12x)

**RTX 5000 series (GeForce)** uses **SM 120/120a/120f** family:
- RTX 5060 Ti = SM 120
- RTX 5070/5070 Ti = SM 120/120a/120f
- RTX 5080/5090 = SM 120/121/121a/121f (121 has more SMs)

**Tensor Core Instructions:**
- Blackwell GeForce (SM 120-121) uses mma.sync for thread-level tensor ops
- No wgmma warp-level instructions (that's Hopper)

**Limitation:** SM 120 (Blackwell GeForce) has NO FP32 Tensor Cores. Only:
- F16 tensor cores (F16 x F16 -> F32 or F16 accumulation via HMMA.16816.F16)
- BF16 tensor cores (BF16 x BF16 -> ONLY F32 accumulation; no native BF16 accumulator in PTX ISA)
- FP8 tensor cores (e4m3/e5m2 formats)

For F32 GEMM, you're limited to **regular FMA instructions**, not tensor cores.

### Hopper Architecture (SM 90/90a)

**RTX A6000 Ada, H100, etc.** use SM 90/90a:
- Supports wgmma warp-level tensor instructions
- Full FP32, FP16, BF16, FP8 tensor core support

**Hopper has actual FP32 Tensor Cores!** This is why Hopper can achieve 97%+ cuBLAS for F32 GEMM.

### Ampere Architecture (SM 89)

**RTX 3000 series (Ampere)** uses SM 89:
- Uses mma.sync.aligned.m16n16k32
- Supports FP16/TF32 tensor cores
- No native BF16 tensor cores

## Critical GPU Capabilities Matrix

| GPU | SM | FP32 TC | FP16 TC | BF16 TC | FP8 TC | Key Limit |
|-----|-----|---------|---------|---------|--------|----------|
| H100 / RTX A6000 | 90a | Yes | Yes | Yes | Yes | None - full tensor support |
| RTX 5090 | 121a | No | Yes | Yes | Yes | No F32 TC (use F16 mixed) |
| RTX 5080 / 5070 | 120/121 | No | Yes | Yes | Yes | No F32 TC |
| RTX 5060 Ti | 120 | No | Yes | Yes | Yes | No F32 TC |
| RTX 3090 / 3080 | 89 | No | Yes | No | No | No BF16, TF32 only |

## Critical Finding from RTX 5060 Ti

**RTX 5060 Ti = SM 120 (Blackwell GeForce)**
- NO FP32 Tensor Cores
- Only F16/BF16/FP8 tensor cores available
- F32 GEMM must use **regular FMA instructions**
- Reality: F32 GEMM on SM 120 won't achieve 97%+ cuBLAS
- Expected F32 GEMM peak: ~10-15% of theoretical peak
- To reach 97%+: Need FP16/BF16 inputs with mixed precision

## Common Pitfalls

### Wrong Instruction Set

Using wgmma on SM 120/121 will fail. Hopper syntax does not work on Blackwell.

### Wrong Precision

Trying to use F16/BF16 tensor cores for F32 computation requires:
- Casting operands to F16/BF16
- Accumulating to F32
- Using c[0:4] for F32 output with BF16 input

### Missing SM 120 Support

Older CUDA toolkits (before 12.x) do not support SM 120:
```bash
# REQUIRED for SM 120
nvcc --gpu-architecture=sm_120 --arch=sm_120  # CUDA 12.4+
```

## For RTX 5060 Ti F32 GEMM

**Expected Performance:**
- F32 GEMM (FMA-only): ~10-15% of cuBLAS peak
- cuBLAS peak: ~15,609 GFLOPS
- Optimized FMA kernel: ~1,500-2,500 GFLOPS achievable
- To get 97%+: Need FP16/BF16 inputs

**Mixed Precision Approach:**
1. Cast input F32 matrices to BF16
2. Use BF16 tensor cores (mma.sync.aligned.m16n8k16.bf16)
3. Accumulate to F32
4. Cast result back to F32 (optional)

This approach can achieve 90-95%+ of cuBLAS peak on SM 120 for F32 operations.

## References

- Tensor Core Accumulator Precision Rules & SASS Matrix: `references/tensor-core-accumulator-precision-rules.md`
- CUDA Tensor Core Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/#tensor-cores
- CUTLASS: https://github.com/NVIDIA/cutlass
- Blackwell PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
- CUDA Best Practices: https://developer.nvidia.com/blog/cuda-best-practices/

## Session Notes

<!-- Add session-specific details here (GPU used, specific findings, errors encountered) -->
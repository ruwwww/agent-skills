# RTX 5060 Ti F32 GEMM F32 GEMM Performance

## Session Date
2026-08-29

## GPU Information
- **Device**: NVIDIA GeForce RTX 5060 Ti
- **Compute Capability**: SM 120 (Blackwell GeForce)
- **Tensor Cores**: F16/BF16/FP8 only, NO F32 tensor cores

## Key Findings

### F32 GEMM Performance Ceiling
- **cuBLAS reference**: 15,609.1 GFLOPS (92.5% of peak)
- **Optimized FMA kernel (double_buffered)**: 1,025.3 GFLOPS (6.6% cuBLAS)
- **Best achievable with F32**: ~10-15% of cuBLAS on SM 120

### Root Cause
RTX 5060 Ti (SM 120) lacks **hardware F32 tensor core support**. Tensor cores are limited to:
- F16 × F16 → F32 accumulation
- BF16 × BF16 → F32/BF16 accumulation
- FP8 × FP8 → F32 accumulation

### Why Tensor Core Kernels Failed
1. **Architecture mismatch**: SM 120 uses `mma.sync` not `wgmma`
2. **F32 precision**: SM 120 has no native F32 tensor core operations
3. **Instruction errors**: Attempting Hopper `wgmma` syntax on SM 120 fails compilation
4. **Limited F32 options**: Can only use regular FMA for F32 GEMM

### Alternative Path (Mixed Precision)
To achieve 97%+ cuBLAS for F32 GEMM on SM 120:
1. Cast F32 inputs to BF16
2. Use BF16 tensor cores (`mma.sync.aligned.m16n8k16.bf16`)
3. Accumulate to F32 output
4. Cast final result to F32

Expected performance: 90-95% cuBLAS with this approach.

## Files Created During Session
- `sgemm_5060ti_tensor_core.cu` - Failed wgmma attempt
- `sgemm_sm120_minimal.cu` - Basic SM 120 structure
- `sgemm_sm120_tc*.cu` - Multiple tensor core attempts
- `test_sm120.cu` - PTX syntax testing

## Lessons Learned
1. **ALWAYS verify GPU architecture** before writing tensor core code
2. **SM 120 ≠ SM 90**: Blackwell GeForce lacks Hopper's warp-level tensor ops
3. **F32 tensor cores only on Hopper+**: SM 90/90a required for F32 tensor cores
4. **Mixed precision may be necessary**: For F32 workloads on non-Hopper GPUs

## References
- CUDA Best Practices: https://developer.nvidia.com/blog/cuda-best-practices/
- CUTLASS: https://github.com/NVIDIA/cutlass
- Blackwell PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
# SM120 FP16 Tensor Core GEMM Ladder & The cuBLAS Gap Analysis

## Target Hardware & Environment
- **Device:** NVIDIA GeForce RTX 5060 Ti (Blackwell architecture, sm_120)
- **Compute Configuration:** 36 SMs, 100 KiB SMEM/SM, 65,536 registers/SM, 128-bit GDDR7 bus
- **Toolchain:** CUDA 13.1 (nvcc V13.1.115), Driver 580.126.09
- **Baseline:** `cublasGemmEx` (FP16 input, FP32 accumulator, FP32 output, `CUBLAS_COMPUTE_32F`)

## Measured Optimization Ladder (N=4096, Real Hardware)

| Kernel Version | Latency (ms) | TFLOP/s | % cuBLAS | Register Usage (ptxas) | Architecture Notes |
|----------------|--------------|---------|----------|------------------------|--------------------|
| **cuBLAS (Golden)** | **2.735 ms** | **50.25 TFLOP/s** | **100.0%** | Custom tuned | Dynamic tile shape, TMA, Hilbert L2 walk |
| **v1: Tiled SMEM** | 71.80 ms | 1.91 TFLOP/s | 3.8% | 37 regs, 0 spill | 32x32 thread block, scalar global loads, sync |
| **v2: Vectorized Async** | 23.32 ms | 5.89 TFLOP/s | 11.7% | 39 regs, 0 spill | 128-bit `cp.async.cg` loads, 2-stage double buffering |
| **v3: Warp/Reg Tiled** | 16.21 ms | 8.48 TFLOP/s | 16.9% | 255 regs, 0 spill | 128x128 CTA, 8x8 register tile, XOR SMEM swizzle |
| **v4: WMMA FP16->FP32** | 5.374 ms | 25.57 TFLOP/s | 50.9% | 136 regs, 0 spill | Direct `nvcuda::wmma` m16n16k16 Tensor Core |
| **v5: Pipelined WMMA** | **3.777 ms** | **36.39 TFLOP/s** | **72.4%** | 96 regs, 0 spill | 2-stage SMEM staging, K-stage=32, 32 KiB SMEM |

## The Architectural Gap: Why Custom Hand-Written WMMA Peaks at ~72% and How to Reach ~95%

Achieving >70% with standard WMMA is straightforward, but closing the final 25-28% gap to cuBLAS on Blackwell consumer cards (SM120) requires architectural features beyond simple double-buffering:

### 1. Asymmetric Warp Specialization (TMA Producer vs MMA Consumer)
- **The v5 Limitation:** All threads/warps participate in both memory transfers and Tensor Core computation. Every warp must handle address calculation and barrier synchronization.
- **The cuBLAS / Production Pattern:** Warps are partitioned into asymmetric roles:
  - **1 Loader Warp:** Executes asynchronous TMA (`cp.async.bulk.tensor`) descriptors to stream data directly into SMEM. Allocates minimal registers (~32–56 regs).
  - **4–8 Consumer Warps:** Focus 100% of cycles on Tensor Core MMA operations without participating in data loading loops. Allocates maximum registers (~224 regs).

### 2. L2 Cache Residency & Swizzled Tile Scheduling
- **The v5 Limitation:** Standard linear launch grid (`blockIdx.x`, `blockIdx.y`) moves sequentially across the matrix.
- **On 128-bit GDDR7:** Linear traversal quickly evicts Matrix B sub-tiles from L2 cache before adjacent row tiles can reuse them.
- **The Solution:** Use **Group-Major / Hilbert Curve Walk** (`l2_group_size = 4` or `8`):
  ```cuda
  int group_id = tile_linear / (l2_group_size * num_n_tiles);
  int within_group = tile_linear % (l2_group_size * num_n_tiles);
  int tile_row = group_id * l2_group_size + (within_group % l2_group_size);
  int tile_col = within_group / l2_group_size;
  ```
  This ensures matrix weights remain hot in L2 across multiple neighboring block computations.

### 3. PTX `ldmatrix` and 128-Byte Layout Alignment
- High-level `wmma::load_matrix_sync` emits generic multi-instruction load sequences.
- Production kernels use inline PTX `ldmatrix.sync.aligned.m8n8.x4` paired with XOR-swizzled shared memory (`SW128B`) to feed Tensor Core registers in a single instruction cycle without bank serialization.

### 4. Epilogue Register Fusion & Early Downcast
- Holding FP32 accumulators through memory write-back incurs high register lifetime penalties.
- In-flight epilogue fusion performs bias addition, activation, and downcasting to FP16/BF16 directly in registers immediately before issuing vectorized stores.

# CUTLASS 3.x & CuTe DSL on NVIDIA Blackwell (SM120)

## 1. Toolchain & Compilation on SM120 (Blackwell GeForce RTX 5060 Ti)
- **Compiler**: CUDA 13.1 (`/usr/local/cuda-13.1/bin/nvcc`), Driver 580.x+.
- **Flags**: `-O3 -std=c++17 -arch=sm_120 -I<path_to_cutlass>/include -lcublas`.
- **CuTe Header**: `#include <cute/tensor.hpp>` provides the entire layout algebra, TiledMMA, TiledCopy, and swizzling.

## 2. Python CuTe DSL (`cutlass.cute`)
Available via `import cutlass.cute as cute` (CUTLASS 4.6.2+):
- Backed by MLIR JIT compiler (`cutlass._mlir`).
- Kernel definitions use `@cute.kernel` and JIT execution entry point `@cute.jit`.
- Dynamic and static layout algebra:
  ```python
  import cutlass.cute as cute
  # Layout = (Shape, Stride)
  layout = cute.make_layout((128, 64), stride=(64, 1)) # Row-major
  ```
- Tiled MMA and Copy atoms:
  ```python
  mma_atom = cute.make_mma_atom(...)
  tiled_mma = cute.make_tiled_mma(mma_atom, atom_layout_mnk=(1, 1, 1))
  ```

## 3. Diffusion Transformer (DiT / Flux2Edit / AuK) GEMM Shapes & SM120 Baselines
In DiT architectures (such as Hunyuan AuK 1.5B speech foundation model), dimension parameters are:
- $D = 1536$, Heads = 24 ($D_{head} = 64$)
- FFN Hidden $D_{ff} = 3072$, Gate+Up Inter = $6144$ (SwiGLU)
- Tokens $M \in [512, 1024, 2048]$

Empirical cuBLAS BF16 baseline throughput on RTX 5060 Ti (sm_120):
| Workload | Shape ($M \times N \times K$) | Latency (ms) | TFLOP/s |
|---|---|---|---|
| QKV ($M=512$) | $512 \times 4608 \times 1536$ | 0.147 | 49.2 |
| QKV ($M=1024$) | $1024 \times 4608 \times 1536$ | 0.290 | 50.0 |
| QKV ($M=2048$) | $2048 \times 4608 \times 1536$ | 0.578 | 50.2 |
| Out Proj ($M=1024$) | $1024 \times 1536 \times 1536$ | 0.102 | 47.1 |
| Out Proj ($M=2048$) | $2048 \times 1536 \times 1536$ | 0.201 | 48.1 |
| FFN Up ($M=1024$) | $1024 \times 6144 \times 1536$ | 0.389 | 49.7 |
| FFN Up ($M=2048$) | $2048 \times 6144 \times 1536$ | 0.774 | 49.9 |
| FFN Down ($M=1024$) | $1024 \times 1536 \times 3072$ | 0.199 | 48.5 |
| FFN Down ($M=2048$) | $2048 \times 1536 \times 3072$ | 0.395 | 48.9 |

## 4. Key Kernel Fusions for DiT Acceleration
1. **Fused SwiGLU**:
   - Compute $[M, 1536] \times [1536, 6144] \to [M, 6144]$.
   - Instead of writing $6144$ elements per row to GMEM and doing elementwise $\text{SiLU}(x[:3072]) \odot x[3072:]$, perform activation directly in SMEM epilogue before storing $[M, 3072]$ or chaining to FFN Down.
2. **Fused AdaLN + GEMM Input**:
   - In DiT blocks, input $x$ is normalized and scaled by timestep conditioning: $\hat{x} = \text{LayerNorm}(x) \cdot (1 + \text{scale}) + \text{shift}$.
   - Fusing this affine scale+shift directly into the global memory load pipeline of the QKV GEMM eliminates an intermediate DRAM round-trip.

## 5. Pitfalls & Engineering Rules
- **Runtime Decoupling**: When a task description cites an integration repo (e.g., ComfyUI-AuK) as architectural inspiration for quantization/dimensions, do **NOT** assume ComfyUI is the execution runtime. Keep kernel research and optimization in a standalone C++/CUDA repository with independent verification harnesses and benchmarks.
- **CuTe CopyAtom Divisibility**: In `make_tiled_copy_A` / `make_tiled_copy_B`, using `SM75_U32x4_LDSM_N` requires the thread-tile partition size in N/K to be an exact multiple of the atom's value vector size (8 BF16 elements for `U32x4`). If the tiled partition produces fewer values, nvcc emits `static assertion failed: "TiledCopy uses too few vals for selected CopyAtom"`. Ensure tile layout aligns or fall back to cooperative vectorized shared-to-register copies.

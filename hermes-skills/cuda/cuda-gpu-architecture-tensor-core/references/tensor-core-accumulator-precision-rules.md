# Tensor Core Accumulator Precision Rules & SASS Instruction Reality

## 1. NVIDIA PTX ISA & SASS Instruction Matrix: FP16 vs BF16 Accumulation

When configuring Tensor Core accumulation behavior in PyTorch via:
```python
torch.backends.cuda.matmul.allow_fp16_accumulation = True
```

### PTX `mma.sync` Instruction Matrix
In the NVIDIA PTX ISA specification, matrix multiply-accumulate instructions have the form:
`mma.sync.aligned.m16n8k16.row.col.dtype.atype.btype.ctype`

| Input Precision ($A, B$) | Accumulator Precision ($C, D$) | SASS Instruction | Register Footprint |
| :--- | :--- | :--- | :--- |
| **`fp16`** (Standard) | **`fp32`** | `HMMA.16816.F32` | 4x 32-bit registers (`%f0..%f3`) per thread |
| **`fp16`** (`allow_fp16_accumulation=True`) | **`fp16`** | `HMMA.16816.F16` | **2x packed fp16x2 registers** (`%r0..%r1`) per thread |
| **`bf16`** | **ONLY `fp32`** | `HMMA.16816.F32` | 4x 32-bit registers (`%f0..%f3`) per thread |

### Why BF16 Has No Hardware Accumulator
- **BF16 Mantissa**: Only 7 bits (coarse precision with 8-bit dynamic exponent). Accumulating repeated dot products in a 7-bit adder tree causes severe catastrophic cancellation and numerical divergence.
- **Hardware Constraint**: NVIDIA hardware does not include an `HMMA.BF16` or `.bf16.bf16.bf16.bf16` adder tree in silicon. All BF16 tensor core math accumulates into FP32 registers.
- **PyTorch Implication**: `allow_fp16_accumulation = True` is a complete **NO-OP** when tensors are in `torch.bfloat16`. To benefit from reduced accumulator register pressure (~1.5x–1.8x GEMM speedup), the model trunk must execute in `torch.float16`.

### Blackwell SM120 (`tcgen05`) Reality
In Blackwell architecture (5th Gen Tensor Cores), `tcgen05.mma` descriptors specify accumulator storage in Tensor Memory (TMEM).
- FP32 accumulation allocates 32-bit TMEM entries.
- FP16 accumulation halves the TMEM allocation footprint to 16 bits, doubling effective TMEM capacity and reducing register spill stages.

---

## 2. Roofline Analysis & Amdahl's Trap: Small ($M \le 512$) vs Large ($M \ge 2048$) Regimes

When profiling DiT models (such as P-JiT 2.2B with patch 32x32 at 512x512 resolution):
- Token sequence length $M = (512/32)^2 + 256 = 512$ tokens.
- At $M = 512$, matrix dimensions ($M \times K \times N$) are small enough that cuBLAS GEMM is memory/launch bound, taking only ~15–20% of forward pass time.
- Non-GEMM vector operations (`RMSNorm`, `AdaLN`, `PostNorm`, `tanh gate`, `SwiGLU`, `RoPE`) take >40–50% of GPU time.

### ConvRot INT8 Trade-off at $M \le 512$
- **Single Layer**: BF16 linear 0.48 ms $\rightarrow$ ConvRot INT8 0.21 ms (2.3x speedup).
- **Full Model (22 layers)**: Online regular Hadamard $H_{64}$ vector transformation and dynamic `amax` scaling per row take ~8–10 ms total, balancing out the ~9 ms GEMM savings.
- **Net Latency**: 1.01x speedup (neutral).
- **Net VRAM Benefit**: Static VRAM reduced from 7.46 GB to 5.74 GB (**-23%, 1.72 GB saved**).

### High-Sequence Scaling ($M \ge 2048$)
For patch 16x16 or 1024x1024 generation where $M \ge 2048 - 4096$:
- GEMM volume scales $O(M \cdot K \cdot N)$ while vector transformation scales only $O(M \cdot D)$.
- Tensor Core GEMM dominates >85% of execution time.
- The online Hadamard rotation cost becomes negligible (<2% of time), unlocking the full 2x+ throughput speedup of INT8 Tensor Cores.

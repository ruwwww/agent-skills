# Ternary (1.58-bit) Quantization & Rotated-Basis GEMM/GEMV Optimization

## 1. Ternary Quantization Architecture (Ternary Bonsai / Q2_0 / PQ2_0)

### Encoding and Storage Formats
Ternary weights constrain values strictly to $\{-s, 0, +s\}$, represented as $w_i = s_g \cdot t_i$ where $t_i \in \{-1, 0, +1\}$ with group-wise FP16 scale factors $s_g$ (typically group size $g = 128$).
- **Theoretical Entropy**: $\log_2(3) \approx 1.585$ bits/weight.
- **Amortized Group Scale**: 16-bit float / 128 weights = $0.125$ bits/weight $\rightarrow$ Ideal bound **~1.71 bpw**.
- **Packed Formats**:
  - `PTQ1_0` (1.76 bpw): Dense trit bitpacking (5 trits per 8 bits or similar). Minimal DRAM footprint, advantageous on memory-constrained GPUs (Ada/L4), but higher unpacking ALU overhead.
  - `PQ2_0` (2.16 bpw, ~7.2 GB for 27B): Fixed 2-bit container slots per trit. Faster bitwise unpack in register, optimal on compute-heavy architectures (Blackwell SM120, Hopper, Apple Silicon).

### Rotated Weight Basis (Walsh-Hadamard Transform)
To prevent outlier activation degradation below 4 bits without preserving dense FP16 escape channels:
- Weights are stored in rotated basis: $W_{rot} = W R^T$, where $R = \frac{1}{\sqrt{n}} H_n S$ ($n = 1024$), $H_n$ is a Walsh-Hadamard matrix, and $S = \text{diag}(\pm 1)$.
- Runtime execution: $y = W_{rot} (R x)$.
- The activation vector $x$ must be pre-transformed by sign-flip and Fast Walsh-Hadamard Transform (FWHT) of complexity $\mathcal{O}(n \log n)$ before GEMM/GEMV.

---

## 2. Decode Bottleneck & Hardware Roofline Analysis (RTX 5060 Ti Blackwell)

### Hardware Specs & Roofline Ceiling
- **RTX 5060 Ti 16GB**: 128-bit GDDR7 bus @ 28 Gbps $\rightarrow$ Theoretical peak **~448 GB/s**.
- **Practical Memory Stream Ceiling (~75–80%)**: **~336–360 GB/s**.
- For a 27B model in `PQ2_0` (~7.25 GB):
  $$\text{Maximum Theoretical Decode} = \frac{336\text{ GB/s}}{7.25\text{ GB}} \approx 46.3\text{ tok/s}$$

### Why Un-fused llama.cpp Yields ~25.7 tok/s (Only ~186 GB/s Bus Utilization)
1. **Un-fused Activation FWHT Overhead at $B=1$**:
   - For every projection in 64 transformer blocks (~450 projections per token), FWHT is launched as an isolated CUDA kernel (`fwht_cuda_block` / `fwht_cuda_smem`).
   - Activation vector at $n=1024$ FP16 is tiny: only **2 KB**.
   - Writing 2 KB to VRAM, synchronizing, and reading it back in the subsequent GEMV kernel incurs disproportionate kernel launch latency and DRAM roundtrips.
2. **Generic GEMV Dispatch**:
   - Generic PTQ/MMQ kernels do not leverage Blackwell SM120-specific register/shared-memory sizing, leaving the DRAM bus under-saturated during latency-dominated serial dispatch.

---

## 3. Optimization Playbook: Fused FWHT + PQ2_0 GEMV

### Architecture for Blackwell SM120
Instead of:
$$\text{Activation } x \xrightarrow{\text{Kernel 1}} \text{FWHT in SMEM} \xrightarrow{\text{DRAM Write}} \text{Global Buffer} \xrightarrow{\text{Kernel 2}} \text{PQ2_0 GEMV}$$

Fuse the pipeline into a single kernel `mul_mat_vec_pq2_0_fused_fwht`:
1. **In-SRAM Transform**:
   - Each thread-block loads the 2 KB activation into `__shared__ float s_act[1024]`.
   - Apply sign-flip and fast butterfly FWHT in-place using warp shuffle (`__shfl_xor_sync`) and shared memory barriers across $\log_2(1024) = 10$ butterfly stages.
2. **Direct Weight Streaming**:
   - The transformed activation remains pinned in shared memory/L1.
   - Threads stream ternary weight blocks (`block_pq2_0`) directly from VRAM via vectorized 128-bit loads (`uint4`).
   - Unpack 2-bit trits in registers and perform fused multiply-accumulate against `s_act`.
3. **Benefits**:
   - Eliminates 450+ intermediate DRAM roundtrips per token.
   - Pushes memory bus utilization from ~41.5% closer to the 75–80% roofline (~45+ tok/s pure autoregressive).

---

## 4. Speculative Decoding & Multi-Token Prediction (MTP)

When base memory-bandwidth limit is reached:
- **N-gram Lookahead (`ngram-mod`)**: Zero-VRAM overhead lookahead match; achieves **1.2x – 1.75x speedup** (~30–45 tok/s on 27B).
- **MTP / DSpark Drafter**:
  - Drafting with trained speculative heads enables verifying 3–4 tokens per DRAM weight pass.
  - Requires matching vocabulary tokenizer space (e.g. Qwen3.8 248k vocab).
  - With 75–80% draft acceptance, effective throughput scales to **2.5x–3.0x base decode** (e.g. 100+ tok/s for 27B on RTX 5060 Ti).

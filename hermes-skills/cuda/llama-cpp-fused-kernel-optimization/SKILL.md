---
name: llama-cpp-fused-kernel-optimization
description: Use when optimizing or fusing CUDA kernels in llama.cpp.
---

# Optimizing and Fusing CUDA Kernels in llama.cpp / GGML

Playbook for profiling, identifying memory-bandwidth bottlenecks, and implementing in-SRAM fused kernels in `llama.cpp` (GGML CUDA backend), derived from the Blackwell SM120 Ternary Bonsai 2 27B optimization.

---

## 1. Diagnose Memory Bandwidth & Roofline

Before writing kernels, establish the theoretical and achievable DRAM roofline:
- Compute GDDR bandwidth: $\text{Bus Width (bytes)} \times \text{Data Rate (Gbps)}$. For RTX 5060 Ti: $\frac{128}{8} \times 28 = 448\text{ GB/s}$.
- Practical CUDA streaming ceiling: ~75–80% of theoretical (for 5060 Ti: ~340–360 GB/s).
- Evaluate current throughput: $\text{Model Size (GB)} \times \text{Decode tok/s} = \text{Achieved Stream Bandwidth}$.
- If achieved bandwidth is far below ceiling (e.g. 186 GB/s vs 350 GB/s, ~41%), the bottleneck is NOT arithmetic or memory bus limit; it is kernel launch latency and intermediate DRAM roundtrips.

---

## 2. Identify the Architectural Bottleneck in llama.cpp

Inspect the computation graph and dispatch path:
- Check `ggml/src/ggml-cuda/ggml-cuda.cu` for graph pattern matching (`ggml_can_fuse_subgraph` or custom fusion hooks).
- Look for multi-kernel execution per layer in decode ($B=1$):
  - Example: `Activation x -> Multiply Sign -> Write DRAM -> FWHT -> Write DRAM -> Quantize -> Write DRAM -> GEMV`.
  - For small activation vectors ($N=1024$ or $2048$), writing 2–4 KB per layer to DRAM across 64+ transformer layers incurs ~400–500 separate kernel launches per token, destroying memory bus occupancy.

---

## 3. Design In-SRAM Fused Execution Pipeline

To eliminate launch latency and roundtrips:
1. **Shared Memory Buffer**: Allocate shared memory for the small activation vector inside the thread block.
2. **In-SRAM Transform**: Perform linear/rotation transformations (e.g. Fast Walsh-Hadamard Transform butterfly stages) entirely in shared memory / warp shuffle registers.
3. **In-SRAM Quantization (Preserving Parity)**: Quantize transformed activations directly in shared memory (e.g., to `block_q8_1`) to preserve 100% bit-exact parity with existing quantization codecs without calling intermediate quantizer kernels.
4. **Direct Weight Streaming**: Threads stream quantized/ternary weights (`PQ2_0`, `Q4_0`, etc.) directly from global DRAM and evaluate dot products against the cached shared-memory activations.
5. **Graph Fusion Guard**: Add a pattern matcher in `ggml-cuda.cu` (e.g. 4-node fusion `MUL -> RESHAPE -> TRANSFORM -> GEMV`) strictly gated for single-token decode ($B=1$).

---

## 4. Verification & Benchmarking Workflow

1. **Bit-Exact Parity Check**: Compare outputs against the unfused baseline to ensure no numerical divergence or degradation.
2. **Compilation**: Target native architecture explicitly:
   `cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="120" -DCMAKE_BUILD_TYPE=Release`
3. **Benchmarking**: Run standardized `llama-bench` runs:
   `./build/bin/llama-bench -m model.gguf -ngl 99 -p 128,512 -n 128 -r 3`
4. **Roofline Confirmation**: Check if achieved bandwidth reaches the 75–80% physical ceiling. If so, single-token decode is fully optimized; subsequent gains require speculative decoding (e.g. MTP / DSpark / n-gram lookahead).

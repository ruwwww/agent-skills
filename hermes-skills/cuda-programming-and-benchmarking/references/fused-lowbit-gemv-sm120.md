# Autoregressive LLM Low-Bit Kernel Fusion & Memory Bandwidth Roofline (Blackwell SM120)

## Problem Profile: Batch-1 Autoregressive Decode Bottlenecks
In single-stream autoregressive generation ($B=1$), transformer inference is strictly memory-bandwidth bound rather than compute bound. Every token generated requires reading the entire model weight tensor from GPU VRAM to compute activations:
$$\text{Ideal Token Latency} = \frac{\text{Model Weights Size (GB)}}{\text{Effective DRAM Bandwidth (GB/s)}}$$

On consumer GPUs like NVIDIA GeForce RTX 5060 Ti (128-bit bus GDDR7, ~448 GB/s theoretical peak, ~340-360 GB/s achievable ceiling):
- A 27B model quantized to ternary/2-bit ($~6.7$ GiB / $7.2$ GB) has a theoretical roofline limit of:
  $$\text{Throughput}_{\text{max}} = \frac{340\text{ to }360\text{ GB/s}}{7.25\text{ GB}} \approx 47 - 50\text{ tok/s}$$

## The Un-fused Transformation Trap (e.g. Walsh-Hadamard in llama.cpp)
Advanced sub-2-bit / ternary quantization schemes (such as Ternary Bonsai or QuIP#) utilize an orthogonal rotation basis:
$$R = \frac{1}{\sqrt{n}} H_n S \quad (n=1024)$$
to eliminate activation outliers prior to low-bit projection.

In naive graph executions:
1. An isolated kernel launch computes the Fast Walsh-Hadamard Transform (FWHT), writing the 1024-element intermediate activation back to global DRAM.
2. An intermediate quantization kernel converts rotated floats to `Q8_1` / `Q8_0` format in DRAM.
3. The GEMV kernel reads activations from DRAM and computes dot products against weights.

**Consequence on 64-layer models**:
- Generates ~450+ separate kernel launches per generated token.
- Adds massive launch latency and round-trip memory bandwidth overhead for tiny 2 KB activation buffers.
- Caps effective memory bandwidth utilization at ~40% (e.g., 25.7 tok/s instead of 48+ tok/s).

## Solution Pattern: In-SRAM Fused Transform + Quantization + GEMV

### 1. In-Shared Memory Transformation
Load the activation vector ($x \in \mathbb{R}^{1024}$, 2 KB in FP16 or 4 KB in FP32) and the sign vector into CUDA Shared Memory:
- Execute the fast Walsh-Hadamard butterfly in-place inside registers and shared memory ($\log_2(1024) = 10$ butterfly steps).
- No global memory writes for intermediate rotated states.

### 2. In-Shared Memory Quantization
Quantize the rotated activations into runtime blocks (e.g., `block_q8_1` with $d$ scale and $s$ sum) directly inside shared memory.

### 3. Streaming GEMV
Each thread or warp directly streams `block_pq2_0` (or target ternary/low-bit format) weights from DRAM:
- Unpack ternary codes $\{-1, 0, +1\}$ directly in registers.
- Accumulate dot products against the pre-quantized activations in shared memory.
- Write only the final scalar/vector projection output to global DRAM.

### 4. Guarded Graph Fusion
In the runtime compute graph (e.g. `ggml-cuda.cu`), detect the sequence pattern:
`MUL (signs) -> RESHAPE -> FWHT -> GEMV (PQ2_0)`
and replace the sub-graph execution with a single fused kernel call on batch size 1.

## Verification & Parity Standards
- **Numerical Parity**: Maintain exact intermediate quantization semantics (e.g. Q8_1 quantization rules) to prevent logit drift, perplexity degradation, or hallucination.
- **Hardware Specialization**: Compile targeting native architecture (`-DCMAKE_CUDA_ARCHITECTURES="120"` for Blackwell SM120) to utilize native register counts and avoid generic PTX JIT overhead.
- **Bandwidth Verification**: Verify that $(\text{Model Size in GB} \times \text{Measured tok/s})$ reaches $75\%-80\%$ of physical GPU GDDR/HBM bandwidth.

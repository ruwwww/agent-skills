---
name: diffusion-kernel-compilation
description: "Use when compiling diffusion DiT models to mega-kernels."
version: 1.0.0
---

# Diffusion Kernel Compilation & Persistent Mega-Kernels

This skill governs the compilation, graph lowering, and persistent execution of Diffusion Transformers (DiT, Flow Matching, U-ViT) into fused task-based kernels (such as Mirage MPK or custom CUDA runtimes).

## Core Principles

1. **AOT Task-Graph Advantage for Diffusion**:
   - Unlike autoregressive LLMs with variable prompt and KV-cache lengths, diffusion sampling operates on **strictly fixed spatial token resolutions and context lengths** across all sampling steps.
   - 100% of the graph should be compiled Ahead-Of-Time (AOT). Eliminate dynamic scheduler warps and allocate all physical SMs as compute workers.

2. **In-Kernel Multi-Step ODE Loop**:
   - Do not exit to host CPU / CUDA stream between sampling steps.
   - Embed the ODE/SDE solver (e.g., Euler, Heun, Flow Matching) as a terminal vector update task in GPU memory.
   - Have the terminal event directly trigger step 0 of the next iteration inside GPU SRAM/VRAM until the step count reaches target (e.g., 25 steps) in a single persistent kernel launch.

3. **Paged Shared-Memory & Cross-Task Pipelining**:
   - Fuse AdaLN modulation and RMSNorm into SRAM pages to eliminate DRAM round-trips.
   - Overlap Tensor Core GEMM computation of the current layer with asynchronous global-to-shared memory pre-loading (`cp.async` / TMA) of weights for the subsequent layer.

4. **Integration of Domain Kernels**:
   - Domain-specific optimizations (ConvRot INT8 GEMM, SageAttention, FP16 HMMA) can be wrapped as uniform device functions (`__device__`) and registered into the task runtime without re-synthesizing from scratch.

5. **Full-Optimization Scope Directive**:
   - When modeling or benchmarking speedup, always evaluate the complete end-to-end optimization horizon (host launch elimination + SRAM staging + cross-task pipelining + loop persistence). Never report narrow launch-only reductions without computing the full hardware speedup potential.

# Hybrid Linear Attention & MoE Architectures (Ling / KDA / MLA)

## Overview

Recent frontier architectures (such as Ling-3.0-tiny / Kimi K3) employ hybrid attention and extreme MoE sparsity to achieve high throughput and sub-10GB VRAM footprints suitable for consumer GPUs (e.g. 16GB VRAM on Blackwell SM120 / RTX 5060 Ti).

### 1. Hybrid 3:1 KDA-MLA Pattern
- **KDA (Kimi Delta Attention):** Recurrent linear attention (3 out of every 4 layers).
  - Preserves a fixed recurrent hidden state matrix $S \in \mathbb{R}^{d_k \times d_v}$ per head.
  - Constant memory across arbitrary sequence lengths; does not expand the standard KV cache during decoding.
  - Chunked parallel scan used during prefill; fused elementwise recurrence used during decode.
- **MLA (Multi-Head Latent Attention):** Standard softmax attention with low-rank latent KV compression (1 out of every 4 layers).
  - Low-rank projection $c_{KV}$ significantly reduces the physical KV cache size per token compared to full MHA/GQA.
  - Decoupled RoPE applied to positional components.

### 2. Fine-Grained Sparse MoE
- Extreme sparsity (e.g., 1/32 to 1/16 activation ratios; 128 to 256 routed experts with top-8 selection).
- Auxiliary-loss-free routing with Sigmoid gating and 1 shared expert.
- GEMM kernels must optimize for small active parameter chunks ($1.3\text{B}$ active per token out of $7.9\text{B}$ total).

### 3. VRAM Budgeting & Quantization for 16GB GPUs
- **Weights:** FP8 ($~8.0\text{ GiB}$) or INT4/Trellis ($~4.5\text{–}5.0\text{ GiB}$).
- **KV Cache:** Quantized INT8 or INT4 group-32 with MLA latent caching ($~1.0\text{–}2.0\text{ GiB}$ for $32\text{k–}64\text{k}$ context).
- Enables simultaneous local execution with heavy diffusion backbones (ComfyUI / Flux) on single consumer GPUs.

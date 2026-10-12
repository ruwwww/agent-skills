# Non-Attention DiT & Diffusion Accelerations

Condensed technical reference for modern DiT non-attention optimizations (e.g., LMSYS MiniMax-H3 / SGLang Diffusion / Cosmos 2 / Anima).

## 1. Fused Non-GEMM Kernels
* **AdaLN Modulation (Indexed Scale-Shift)**: Replaces eager `(norm(x) * (1 + scale) + shift)` and intermediate allocations with a fused CUDA/Triton kernel reading indexed modulation weights in a single pass directly in SRAM.
* **AdaLN Gated Residual**: Combines gating scale and residual addition into the activation buffer (`x += gate * out`) in-place without generating separate intermediate tensors.
* **SwiGLU Activation**: Operates in-place on the concatenated `gate_up` projection buffer before the down-projection.
* **Fused QK RMSNorm + 3D RoPE**: Evaluates query/key RMSNorm and applies Rotary Positional Embeddings in a single fused kernel (e.g. `rms_rope_split_half`), avoiding redundant DRAM roundtrips.

## 2. Step Reuse & Denoising Caching
* **Cache-DiT / DBCache**: Evaluates boundary blocks (e.g., first and last layers) and calculates the normalized residual difference between steps. If the difference is below a defined threshold (`RDT`), intermediate blocks reuse previously cached activations.
* **Stride Caching**: Skips transformer evaluation up to a maximum consecutive cached limit (e.g. 1–3 steps) after initial warmup steps.
* **SSIM vs Latency Tradeoff**: Cache-DiT alone provides up to ~3x speedup at high SSIM (0.90–0.97).

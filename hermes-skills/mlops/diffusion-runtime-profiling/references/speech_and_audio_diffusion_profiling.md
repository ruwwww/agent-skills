# Speech & Audio Diffusion Model Runtime Profiling & Optimization Guide

This reference documents verified patterns, pitfalls, and hardware benchmarks when optimizing foundational speech/audio diffusion models (e.g. AuK Flux2Edit, BigVGAN VAE, AudioCraft, Stable Audio) on modern GPUs (e.g. Blackwell SM120, RTX 40/50 series).

## 1. Upstream Native Runtime vs Framework Decoupling (Critical Rule)
- **Zero UI Framework Coupling**:
  - Never optimize, benchmark, or write custom kernels using high-level UI framework wrappers (e.g. `comfy`, `comfy.model_management`, `ComfyUI-AuK` nodes) as convenience shortcuts.
  - UI runtimes inject arbitrary memory management, tensor conversion layers, and CPU dispatch overhead that skew profiling and prevent clean compilation.
  - Always optimize against the bare-metal upstream model architecture directly:
    - Backbone: `from auk.model.flux2_edit import Flux2Edit`
    - Flow Matching ODE: `from auk.model.cfm_edit import CFMEdit`
    - Vocoder: `from auk.model.vae import load_vae_model` (`BigVGANFlowVAE`)
    - Custom kernels: Package standalone C++/CuTe Tensor Core ops into native PyTorch extensions (`torch.ops.*`).

## 2. Benchmarking & Profiling Protocol
- **Strict Steady-State Measurement**: Never benchmark or report inference latency from the first run. Always perform 2–3 warmup iterations to ensure:
  - Weight tensors are resident in VRAM (cold disk I/O from `.safetensors` can add 5–10s if measured inside timers).
  - JIT compilation (`torch.compile` / Inductor / Triton) has settled.
  - CUDA memory caching allocator has warmed up.
- **Mandatory `torch.inference_mode()`**:
  - Speech diffusion models (especially 1D Conv vocoders like BigVGAN / HiFi-GAN) process tens of thousands of audio sample points per second (e.g. 120,000 samples for 5s @ 24 kHz).
  - Omitting `inference_mode()` forces PyTorch to maintain an autograd DAG across every upsampling residual block, inflating VRAM by >10 GB and triggering allocator thrashing / OOM.
- **Isolate Pipeline Components**:
  - Always separate Text Conditioning (e.g. Qwen2.5-Omni encoder, runs once per prompt) from Iterative Diffusion Sampling and VAE Vocoder Decoding.

## 3. Attention Engine Selection for Audio
- **Sequence Length Regimes**:
  - **Short Sequences ($S \le 500$, standard audio clips 3–10s)**: Native PyTorch SDPA is **5.4× – 6.8× faster** than SageAttention 2.2.0 (e.g. 0.020 ms vs 0.134 ms per attention call). SageAttention's per-block INT8/FP8 quantization setup overhead dominates when context length is short.
  - **Long Sequences ($S > 2048$)**: SageAttention becomes advantageous as $O(S^2)$ attention memory bandwidth begins to dominate.

## 4. Quantization vs Precision Tradeoffs on Small Batch / Sequence ($M \le 384$)
- At batch size 1 ($B=1$) with small audio frame token counts ($M \approx 250 - 378$):
  - Generic INT8 weight-only dequantization (TorchAO / bitsandbytes) introduces unpack and conversion overhead that is **1.5× – 2.0× slower** than native BF16 tensor core GEMMs.
  - Native BF16 with direct BF16 register epilogues achieves optimal throughput (~36–50 TFLOP/s on RTX 5060 Ti) while halving output staging memory traffic compared to FP32 staging.
  - Sub-8-bit formats (NVFP4 / W4A4 / ConvRot) require fused C++/CuTe Tensor Core epilogues to overcome kernel launch latency.

## 5. Sampling Loop Compilation & Hardware Benchmarks (RTX 5060 Ti SM120)
For fixed-step distilled diffusion architectures (e.g. AuK-Flash 4 Euler steps, CFG=1):
- Pad audio latent durations into discrete buckets (e.g. 3s / 150 frames, 5s / 250 frames, 10s / 500 frames).
- Wrapping native `Flux2Edit` in `torch.compile` yields **1.5x–2.6x speedup** over eager PyTorch sampling.
- Empirical steady-state benchmarks measured on NVIDIA GeForce RTX 5060 Ti 16GB (Blackwell SM120, CUDA 13.1):

| Audio Dur | Eager Sampling (4-step) | Compiled Sampling (4-step) | Sampling Speedup | VAE Decode (BigVGAN) | Total Time | Speedup vs Real-Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **3.0s** | 156.26 ms (39.0 ms/step) | **60.91 ms** (15.2 ms/step) | **2.57x** | 62.53 ms | **123.43 ms** | **24.31x RT** |
| **5.0s** | 161.95 ms (40.5 ms/step) | **75.23 ms** (18.8 ms/step) | **2.15x** | 98.74 ms | **173.97 ms** | **28.74x RT** |
| **10.0s** | 163.20 ms (40.8 ms/step) | **107.51 ms** (26.8 ms/step) | **1.52x** | 221.43 ms | **328.94 ms** | **30.40x RT** |

## 6. Streaming Architecture & Time-To-First-Audio (TTFA)
- **Causal Vocoder Decode Tradeoff (Contiguous vs Chunked)**:
  - BigVGAN / HiFi-GAN 1D transposed convolutions with multi-receptive field fusion (AMP blocks) run significantly faster on a single contiguous sequence than on multiple small chunk batches (batch-decoding three 1s chunks introduces conv padding and launch overhead).
  - *Optimal Streaming Strategy*: Perform 4-step sampling via CUDA graph, run a single contiguous GPU VAE decode (which takes only ~60–220ms for 3–10s audio), and immediately slice the resulting 24kHz signed 16-bit PCM waveform into streaming packets on host. This yields sub-**1.0ms TTFA** after prewarmed slice dispatch without boundary discontinuity clicks.
- **Instruction / Persona Conditioning Cache**:
  - Speech foundation models paired with massive audio-language encoders (e.g. Qwen2.5-Omni 3B) incur heavy 1-time prompt encoding latency (~18s in eager PyTorch).
  - Maintain a dual-tier (RAM + disk) LRU cache keyed by SHA-256 hash of `(model_name, instruction_text)`. Cache hits bypass the LLM encoder completely, achieving sub-**0.05ms** conditioning lookups for recurring voice personas.

# Native Model Runtime and Inference Benchmarking

Playbook for implementing, optimizing, and benchmarking neural foundation models directly on bare-metal hardware.

---

## 1. Upstream Native Runtime vs UI Wrappers

When given tasks to optimize, accelerate, or benchmark a foundation model (e.g. AuK, DiT models, VAEs, LLMs):
- **NEVER hook into or optimize from UI wrapper code** (such as ComfyUI custom nodes, WebUI harnesses, or gradio adapters) unless the user explicitly asks for a ComfyUI node.
- Always clone or inspect the official upstream repository architecture (`src/*`, native PyTorch `nn.Module` classes, e.g. `from auk.model.flux2_edit import Flux2Edit`).
- Implement custom kernels (CUTLASS, CuTe, Triton, C++ extensions) directly against the native tensor shapes and contracts of the official upstream architecture.
- Keep the standalone optimization repository free of any ComfyUI/wrapper dependencies.

---

## 2. Sequence-Length Aware Attention Selection

Do not blindly swap PyTorch SDPA with quantized attention backends:
- **PyTorch SDPA (`F.scaled_dot_product_attention`)**:
  - Extremely lightweight dispatch and highly tuned CuDNN/FlashAttention kernels.
  - On short sequence lengths ($S \le 500$, typical for short audio frames like $3s - 10s$ TTS), SDPA is **5.4x – 6.8x faster** than quantized attention libraries (e.g. SageAttention 2.x).
  - Reason: INT8/FP8 per-block quantization overhead, min-max scanning, and launch setup dominate the execution time on small sequences.
- **Quantized Attention (SageAttention, etc.)**:
  - Only introduces a net win when sequence length $S > 2048$, where $O(S^2)$ attention computation dwarfs the quantization and kernel launch overhead.

---

## 3. Epilogue Precision & Register Pressure in CuTe / CUTLASS

In modern NVIDIA Tensor Cores (Ampere `sm_80`, Hopper `sm_90`, Blackwell `sm_120`):
- Hardware MMA instructions perform FP32 accumulation under the hood for BF16/FP16 inputs (`SM80_16x8x16_F32BF16BF16F32_TN`).
- **Bottleneck**: Storing full FP32 accumulators into intermediate shared memory or global memory creates high register pressure (exceeding 128 regs/thread) and doubles memory traffic.
- **Rule**: Downcast early to BF16 within the register epilogue immediately prior to storing. On SM120, BF16 register epilogue yields a **7.3% – 13.4% speedup** over FP32 staging.

---

## 4. Disentangled Steady-State Profiling Rules

Never present benchmark numbers that conflate inference latency with initialization overhead:
1. **Cold Disk I/O**: Preload model weights and safetensors into device memory before starting performance timers.
2. **Missing `torch.inference_mode()`**: Running inference without `torch.inference_mode()` forces PyTorch to construct autograd DAG structures, causing VRAM ballooning (e.g., 699MB inflating to 14.8GB on 120k audio samples) and triggering memory allocation throttling.
3. **Warmup**: Always execute 3–5 warmup iterations so Triton / Inductor / CUDA kernel caches are fully populated.
4. **Hardware Timers**: Use `torch.cuda.Event(enable_timing=True)` with `torch.cuda.synchronize()` rather than host-side Python `time.time()`.
5. **Disentangle Python Reference vs. Compiled Native Inference**: Never report interpreted Python/eager simulation passes as the benchmark performance of a native C++/CUDA inference runtime. Always benchmark the compiled executable directly on hardware.

---

## 5. End-to-End Model Implementation Verification Standards

When implementing or porting model architectures into custom C++/CUDA runtimes (such as NInfer):
1. **Full Implementation vs Partial Stubs**:
   - Implement the complete pipeline end-to-end (conversion, tensor bindings, runtime schedule, and numerical parity) before declaring completion.
   - Do not report "success" while inference fails, attention geometries are unspecialized, or generation produces incoherent gibberish.
2. **Qualitative Output Coherence Check**:
   - Numerical passing of unit tests is necessary but insufficient. Always run an actual generation check on representative natural-language prompts.
   - Verify that output text is fluent, intelligible, and on-topic.
3. **Common Architectural Traps in C++/CUDA LLM Engines**:
   - **RMSNorm Gain Convention**:
     - Qwen engines typically use unit-offset gain: $\text{RMSNorm}(x) \times (1 + w)$.
     - Standard LLaMA / Nanbeige / Mistral architectures use standard gain: $\text{RMSNorm}(x) \times w$.
     - Mixing this convention causes activation values to explode exponentially across layers, producing instant gibberish.
   - **Looped Transformer DRAM Bandwidth Bound**:
     - In Looped Transformers (e.g., Nanbeige with $N_{\text{loops}} = 2$), physical layer weights are read from DRAM $N$ times per generated token.
     - Total DRAM bandwidth traffic per token is $\approx \text{Layer Weights} \times N + \text{LM Head}$.
     - Single-stream decode speed is strictly bound by $\frac{\text{DRAM Bandwidth}}{\text{Bytes per Token}}$. On an RTX 5060 Ti (~380 GB/s sustained), a 3.5 GB W8 model reading ~7.0 GB/tok is hardware-capped at ~54 tok/s. Exceeding this requires 4-bit weights (NVFP4/Q4) to halve DRAM traffic.
   - **Attention Head Dimension ($D=128$ vs $D=256$)**:
     - Many modern engines hardcode $D=256$ for Qwen. Non-standard architectures ($D=128$ or $D=64$) require explicit kernel template specialization across prompt attention, paged KV append, and small-T decode kernels.

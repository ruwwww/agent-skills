# SM120 (Blackwell) CuTe GEMM & Diffusion Optimization Playbook

## 1. Hardware & Tensor Core Realities (SM120)
- **BF16 Tensor Core Accumulation**: On modern architectures (SM80 through SM120), BF16 Tensor Cores compute accumulations in FP32 natively in hardware without throughput penalty.
- **Register Pressure & Spilling**: Keeping FP32 accumulators across epilogues inflates register allocation (exceeding 104–128 regs/thread) and limits occupancy. The performance win comes from downcasting to BF16 early in register space before shared or global memory stores.
- **Shared Memory Layouts & Swizzling**: Use CuTe `Swizzle<3, 3, 3>` with `SM75_U32x4_LDSM_N` to eliminate bank conflicts on 128-bit memory instructions.
- **SM120 Low-Bit Support**: Blackwell introduces hardware FP4 (NVFP4) and FP8 Tensor Cores. For memory-bandwidth bound models at batch size 1, W4A4/NVFP4 combined with ConvRot (Randomized Hadamard transformation) reduces parameter memory traffic by ~4x without activation outlier blowup.

## 2. Kernel Fusion Patterns for Diffusion Transformers (e.g. Flux2Edit / AuK)
- **Fused SwiGLU**:
  - Load activation $A$ along with dual weight matrices $W_{gate}$ and $W_{value}$.
  - Accumulate gate branch in FP32 shared memory; accumulate value branch in registers.
  - Apply in-register $\text{SiLU}(\text{gate}) \odot \text{value}$ in the epilogue to eliminate intermediate global memory roundtrips.
- **Fused AdaLN + QKV**:
  - Apply affine modulation in-flight during global-to-shared memory staging:
    $$\text{shared\_A}[m, k] = \text{BF16}((1 + \text{scale}[m, k]) \cdot x[m, k] + \text{shift}[m, k])$$
  - Directly feed the modulated shared activation tile into the QKV projection MMA pipeline without allocating intermediate modulated tensors.

## 3. Fixed-Step DiT Speedup Hierarchy (e.g. 4-step Distilled)
When batch size is 1 ($B=1$) and step count is fixed:
1. **CUDA Graphs**:
   - For models with 30 layers across 4 steps, CPU-to-GPU launch overhead (~800 kernel launches) can dominate total latency.
   - Bucket input sequences into static dimension tiles (e.g. 5s audio = 250 frames).
   - Capture the full sampling loop with `torch.cuda.CUDAGraph()` or `torch.compile(mode="max-autotune")` with Inductor CUDA graphs.
2. **Attention Backend & Sequence Length Threshold**:
   - **Short sequences ($S \le 500$)**: Use native PyTorch SDPA (cuDNN/FlashAttention backend). At $S=250-378$, SDPA is 5.4x–6.8x *faster* than SageAttention 2.2.0 because per-block quantization and launch overhead dominate.
   - **Long sequences ($S > 2048$)**: Switch to SageAttention for quadratic memory/throughput savings.
3. **Quantization on Small-M Batches**:
   - Standard INT8 weight-only / dynamic INT8 (TorchAO, bitsandbytes) is 1.5x–3.6x *slower* than native BF16 on small $M$ ($M=250-378$) due to on-the-fly dequant unpacking overhead.
   - True low-bit speedups at small $M$ require custom fused kernels (e.g. CUTLASS W4A4 / NVFP4) rather than generic unpack wrappers.
4. **VRAM Safety & VAE Decoding**:
   - Large vocoders / flow VAEs (e.g. BigVGAN with SnakeBeta activations) accumulate massive autograd computation graphs if run without explicit context guards (>14 GB peak VRAM). Always wrap inference in `with torch.inference_mode():` (drops peak to <700 MB).
   - Use sequential model lifecycle on 16GB GPUs: load text encoder $\to$ encode $\to$ unload/empty_cache $\to$ load DiT $\to$ sample $\to$ unload/empty_cache $\to$ load VAE $\to$ decode.
5. **Runtime Decoupling Rule**:
   - Do not conflate checkpoint formats (e.g. ComfyUI weights/nodes) with execution runtime. When asked to optimize or benchmark bare-metal models, implement clean standalone PyTorch/CUDA C++ pipelines unless ComfyUI runtime is explicitly requested.
6. **Disentangled Ablation Methodology**:
   - Disentangle standalone optimizations (SageAttention alone, torch.compile alone, CUDA Graphs alone, fused kernels alone) before reporting combined performance.
   - Always report honest, unexaggerated metrics against baseline cuBLAS.

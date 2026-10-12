---
name: cuda-programming-and-benchmarking
description: CUDA kernel benchmarking, performance verification, and optimization ladder reproduction
category: software-development
---

# CUDA Programming & Performance Verification
**Class-level skill for reproducing, benchmarking, and verifying CUDA kernel performance claims**

## When to Use
- **Reproducing CUDA kernel performance claims** from external sources (blogs, papers, articles)
- **Benchmarking CUDA kernels** against reference implementations (cuBLAS, cuDNN, etc.)
- **Verifying GPU performance** on target hardware matches claimed specifications
- **Debugging CUDA kernel performance** issues (memory bandwidth, occupancy, bank conflicts)
- **Creating systematic CUDA optimization ladders** (naive → optimized kernels)

## Workflow

### Step 1: Clone Source Code (if applicable)
```bash
# For repositories like maxxfuu/optimized-GEMM
git clone <repo-url>
cd <repo>
```

### Step 2: Check Hardware Compatibility
```bash
# Confirm compute capability matches target kernel
/usr/local/cuda/bin/nvcc --version
/usr/local/cuda/bin/nvcc -arch=sm_120 --version  # Match your GPU
```

### Step 3: Compile Individual Kernels
```bash
# Each kernel should be compiled and run separately
/usr/local/cuda/bin/nvcc -O3 -arch=sm_XXX -o kernel_name kernel.cu
./kernel_name
```

**Important:** Run kernels **sequentially, not in parallel** to prevent:
- Memory fragmentation
- GPU process exhaustion (OOM)
- Timing interference from multiple concurrent kernels

### Step 4: Measure Performance
Track these metrics for each kernel:
- **Execution time (ms)**
- **GFLOP/s** = (Total FLOPs) / (Time in seconds)
- **Percentage of cuBLAS** = (Kernel GFLOP/s) / (cuBLAS GFLOP/s) × 100

### Step 5: Create Benchmark Harness (Optional)
```bash
# Compile all kernels into one binary
/usr/local/cuda/bin/nvcc -O3 -arch=sm_120 \
  -o bench benchmark_all.cu \
  bench_kernels.cu
./bench
```

## GPU Memory Management Best Practices

### Prevent OOM (Out-of-Memory)
- **Free device memory immediately after each kernel:**
  ```cuda
  cudaMalloc(&A, M * K * sizeof(float));
  cudaMalloc(&B, K * N * sizeof(float));
  cudaMalloc(&C, M * N * sizeof(float));
  // ... run kernel ...
  cudaFree(A);  // Free immediately
  cudaFree(B);
  cudaFree(C);
  ```
- **Reset device after each benchmark:**
  ```bash
  cudaDeviceReset
  ```

- **Use small test matrices for debugging:**
  - Start with `M=N=K=1024`
  - Scale up to `M=N=K=2048`, `4096`, etc.

### Monitor Memory Usage
```bash
# Check GPU memory before/after
nvidia-smi
```

### Kill GPU Processes Safely
```bash
# If stuck, kill CUDA processes
pkill -9 nvcc
pkill -f cuda
```

## Benchmarking Guidelines

### Matrix Sizes
- **4096 × 4096** = standard test size (137.4 GFLOPs for M=N=K=4096)
- Ensure sizes are **multiples of tile dimensions** to avoid bounds issues
- Typical tile sizes: 32, 64, 128

### Comparison Baselines
- **cuBLAS** (default `cublasSgemm`): ~69% of FP32 peak on RTX 50-series
- **Theoretical FP32 Peak:** 
  - RTX 5060: ~56 TFLOPS
  - RTX 5080: ~90+ TFLOPS
  - RTX 5090: ~113 TFLOPS

### Common Pitfalls
1. ❌ Don't rely on `time` command - use kernel-internal timing
2. ❌ Don't run kernels in parallel without `cudaDeviceSynchronize()`
3. ❌ Don't reuse `cudaStream_t` across kernel launches without proper synchronization
4. ❌ Don't forget `cudaFree()` - memory leaks cause OOM
5. ❌ Don't assume vectorized access = faster (float4 loads have overhead)
6. ⚠️ Bank conflicts may show in profiler but not always impact performance
7. ⚠️ Register pressure limits tile sizes (max ~128 registers/thread on most cards)
8. ⚠️ Tensor Core Accumulation: In modern hardware (SM80–SM120), BF16 Tensor Cores accumulate in FP32 by hardware design; the key bottleneck is register staging—downcast early back to BF16 in the epilogue to avoid register spilling.
9. ⚠️ Fixed-step Diffusion CPU Launch Overhead: Small-batch or fixed-step models (e.g. 4-step distilled DiT with B=1) suffer severe launch overhead (>700 launches); use static shape bucketing with CUDA Graphs (`torch.cuda.CUDAGraph` or inductor cudagraphs) to collapse launches into a single hardware replay.
10. ⚠️ Upstream Native Runtime vs UI Wrappers: When optimizing model backbones (e.g. DiT, TTS, LLMs), implement and benchmark against the official upstream repository architecture (native PyTorch/C++ modules like `src/auk`). Never build or optimize bare-metal pipelines from UI wrapper runtimes (e.g. ComfyUI custom nodes) unless explicitly requested.
11. ⚠️ Attention Backend Selection by Sequence Length: Quantized attention (e.g. SageAttention INT8/FP8) has per-block quantization and launch overhead that causes it to run 5–7x slower than PyTorch native SDPA on short sequences ($S \le 500$); only apply SageAttention on long-context sequences ($S > 2048$).
12. ⚠️ Disentangled Warm Steady-State Profiling: Always measure after warmup passes using CUDA events. Never conflate inference latency with cold disk I/O, initial JIT compilations, or autograd DAG construction (always wrap inference loops in `torch.inference_mode()`).
13. ⚠️ Disentangled Simulation vs Native Benchmarks: Never report interpreted Python/eager reference passes as benchmark numbers for a native C++/CUDA runtime. Implement full end-to-end models, verify text coherence on real prompts, and benchmark the compiled native executable directly.
14. ⚠️ RMSNorm Unit-Offset Trap: Distinguish unit-offset RMSNorm ($x \cdot (1 + w)$) from standard RMSNorm ($x \cdot w$); mismatch causes exponential activation explosion and garbled output.
15. ⚠️ Gymnasium Contract for CUDA Spaces: `gymnasium.spaces.Text` defaults to alphanumeric characters. CUDA code and compiler logs require `charset=string.printable` and `min_length=0` to prevent `check_env` assertion failures.
16. ⚠️ Ephemeral Kernel-Only Compilation: To verify agent-generated kernels without a host harness, compile with `-c` (`nvcc -c -arch=sm_120 -Xptxas -v`) to check syntax, register count, and shared memory without link errors.
17. ⚠️ RL Framework Selection & Fast Rollout Backends: Do not implement custom policy gradient loops or manual rollout workers from scratch when building CUDA kernel optimization agents. Use battle-tested RL libraries (Hugging Face `trl.GRPOTrainer`) paired with native vLLM fast rollout backends (`use_vllm=True`, `vllm_mode="server"`). Strictly cap `vllm_gpu_memory_utilization` ($\le 0.35$ on 16 GB GPUs) to guarantee $>8$ GB VRAM headroom for NVCC compilation, PyTorch reference tensors, and isolated kernel execution without OOM.
18. ⚠️ veRL + Uni-Agent Multi-Turn Sandbox Scalability: When transitioning from single-turn prompt-completion to multi-turn agentic RL (iterative compile $\to$ diagnose $\to$ edit $\to$ benchmark $\to$ submit), decouple the execution stages. Parallelize NVCC compilation across CPU cores with `concurrent.futures.ProcessPoolExecutor`, cache identical kernel binaries using content-addressed SHA256 hashes, and enforce an OS-level file mutex lock (`filelock`) during GPU benchmark passes so timing remains deterministic and concurrent rollouts never corrupt device memory.
19. ⚠️ Autoregressive Decode Bandwidth Trap (Rotated Low-Bit Kernels): In single-token autoregressive decode ($B=1$), isolated activation transforms (e.g. Walsh-Hadamard rotations in ternary/sub-2-bit LLMs like Bonsai) create ~450+ kernel launches/token and small-buffer DRAM roundtrips that choke bus utilization to ~40%. Fuse the Hadamard butterfly and activation quantization (e.g. Q8_1) directly into Shared Memory within the GEMV kernel, streaming weights straight to register dot products. On 128-bit GDDR7 (RTX 5060 Ti), this doubles decode throughput (e.g. 25.7 $\to$ 48.5 tok/s for 27B) and pushes effective streaming bandwidth to the physical ~78% hardware roofline. See `references/fused-lowbit-gemv-sm120.md`.
20. ⚠️ Programmatic Dependent Launch (PDL) & Memory Prefetch: In low-latency single-stream decode ($B=1$), tiny producer-consumer pairs (e.g. RMSNorm/Quantize $\to$ Projection GEMM) waste ~2ms/round to launch serialization. Use CUDA 12.3+/13 PDL (`cudaLaunchAttributeProgrammaticStreamSerialization`) so consumers launch early and prefetch static weights from DRAM into registers. Enforce the **single-wave producer rule** (producer grid $\le$ device SM count) to prevent hardware deadlocks, and **strip `__restrict__` from consumer activation pointers** to prevent NVCC from hoisting `ld.global.nc` above `cudaGridDependencySynchronize()`. See `references/low-latency-ml-runtime-and-pdl.md`.
21. ⚠️ Modern Kernel Architecture (Warp Specialization & TMA Pipelining): In modern architectures (SM90–SM120), high-performance kernels avoid uniform SIMT execution. Partition warps into asymmetric roles (TMA loader, scheduler, MMA, epilogue consumer) with differentiated register budgets (e.g., 56 regs for loaders vs 224 for consumers) to avoid register spilling. Replace synchronous CTA barriers with hardware `mbarrier` multi-stage pipelines, apply XOR swizzling (`SW128B`/`SW64B`) to eliminate shared-memory bank conflicts, and use persistent grid scheduling with group-major tile walks to maximize L2 cache hit rates. See `references/tirx-and-modern-kernel-architecture.md`.

## Verification Checklist

For each kernel, verify:
- [ ] Compiles with `-arch=sm_XXX` matching your GPU
- [ ] Runs without errors (exit code 0)
- [ ] Produces correct results (compare with cuBLAS or reference)
- [ ] No memory leaks (check with `cuda-memcheck`)
- [ ] Performance makes sense (each step should improve over previous)
- [ ] GFLOP/s aligns with expected optimization gains

## References
- `references/sm120-fp16-gemm-ladder-and-cublas-gap.md` - SM120 FP16 Tensor Core GEMM optimization ladder (v1-v5), real Blackwell RTX 5060 Ti benchmark metrics, and cuBLAS gap analysis
- `references/tirx-and-modern-kernel-architecture.md` - Modern GPU kernel architecture patterns (asymmetric warp specialization, TMA mbarrier pipelines, SMEM swizzling, and persistent tile scheduling)
- `references/low-latency-ml-runtime-and-pdl.md` - Low-latency ML runtime engineering, Programmatic Dependent Launch (PDL/PSS), coarse-to-fine MTP screening, and SASS primitives
- `references/fused-lowbit-gemv-sm120.md` - Autoregressive LLM low-bit kernel fusion (FWHT + in-SRAM quantization + GEMV) & memory bandwidth roofline on Blackwell SM120
- `references/cuda-rl-gym-and-kernel-sandboxing.md` - RL environment design, Gymnasium space contracts, GRPO single-GPU sizing, and sandboxed kernel execution
- `references/native-model-runtime-and-inference-benchmarking.md` - Upstream native runtime isolation, SDPA vs quantized attention rules, and warm steady-state profiling
- `references/sm120-cute-diffusion-optimizations.md` - SM120 (Blackwell) CuTe GEMM, fused SwiGLU/AdaLN, and CUDA Graphs diffusion optimization playbook
- `references/comfyui-graph-profiling.md` - ComfyUI graph capture, runtime profiling, and Batched CFG performance analysis
- `references/comfy-kitchen-dit-optimizations.md` - ComfyUI and comfy-kitchen DiT non-attention kernel integration & benchmark guide
- `references/diffusion-non-attention-optimizations.md` - Non-attention DiT optimizations (fused kernels & step caching)
- `references/cuda-workflow.md` - General CUDA benchmarking and validation workflows
- `maxxfuu/optimized-GEMM` - CUDA matmul optimization ladder
- `siboehm.com/articles/22/CUDA-MMM` - CUDA kernel optimization worklog
- `cuda.csdn.net` - CUDA programming examples
- `docs.nvidia.com/cuda/cuda-runtime-api` - CUDA API reference

## See Also
- **performance-optimization**: For general app performance tuning
- **devops/observability-and-instrumentation**: For profiling tools
- **debugging-and-error-recovery**: For CUDA error diagnosis

---

*Last updated: August 2026*
*Tested on: NVIDIA RTX 50-series GPUs (sm_120)*
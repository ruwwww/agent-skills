# CUDA Kernel Performance Verification Workflow
**How to reproduce and benchmark CUDA kernel performance claims on target GPU**

## Session Summary (August 29, 2026)

**Goal:** Reproduce CUDA GEMM optimization ladder from maxxfuu/optimized-GEMM to verify performance claims on RTX 5060 Ti.

**Approach Used:**
1. Clone source repository directly from GitHub
2. Compile kernels sequentially with `nvcc -O3 -arch=sm_120`
3. Run each kernel individually with `time` command
4. Calculate GFLOP/s and percentage vs cuBLAS
5. Document results with timing, GFLOP/s, and optimization insights

**Source:** https://github.com/maxxfuu/optimized-GEMM
**Test Matrix:** M=N=K=4096 (137.4 GFLOPs total)
**GPU:** RTX 5060 Ti (sm_120, 16GB GDDR7, ~56 TFLOPS FP32)

## Step-by-Step Workflow

### 1. Get CUDA Toolchain

```bash
# Check CUDA installation
which nvcc
/usr/local/cuda/bin/nvcc --version

# If nvcc not in PATH:
export PATH=$PATH:/usr/local/cuda-13.1/bin
```

### 2. Clone Repository

```bash
git clone https://github.com/maxxfuu/optimized-GEMM.git
cd optimized-GEMM
```

### 3. Compile Single Kernel

```bash
/usr/local/cuda-13.1/bin/nvcc -O3 -arch=sm_120 -o <kernel_name> <kernel.cu>
# Example:
/usr/local/cuda-13.1/bin/nvcc -O3 -arch=sm_120 -o sgemm_naive sgemm_naive.cu
```

**Compile multiple kernels in batch:**
```bash
nvcc -O3 -arch=sm_120 \
  -o sgemm_naive sgemm_naive.cu \
  -o sgemm_coalesced_2d sgemm_coalesced_2d.cu \
  -o sgemm_coalesced_1d sgemm_coalesced_1d.cu
```

### 4. Run and Benchmark

```bash
# Single kernel
time ./sgemm_naive 2>&1

# Capture timing (e.g., real 0m0.839s → 839 ms)
```

### 5. Calculate Performance

```python
# For M=N=K=4096:
total_flops = 2 * M * N * K  # = 137.4 GFLOPs

# GFLOP/s:
gflops = total_flops / elapsed_time_seconds

# Percentage of cuBLAS:
# cuBLAS on RTX 5060 Ti: ~15609 GFLOPS (92.5% of 16 TFLOPS peak)
pct_cublas = gflops / cublas_perf * 100
```

**Example calculation:**
```
Time: 0.839s
Total FLOPs: 137.4 GFLOPs
GFLOP/s: 137.4 / 0.839 = 163.8 GFLOPS
% cuBLAS: 163.8 / 15609 * 100 = 1.05%
```

### 6. Compare Against cuBLAS Reference

```bash
# Compile cuBLAS reference
/usr/local/cuda-13.1/bin/nvcc -O3 -arch=sm_120 -o cublas_ref \
  sgemm_autotuned.cu -lcublas

# Run cuBLAS benchmark (takes longer, ~10s)
time ./cublas_ref 2>&1
```

**Output example:**
```
cuBLAS M=N=K=4096, sweeping warp-tile configs
median of 5 trials x 3 reps, 200 ms warm-up each
128x128x8 W64x64 I4 T8x4 128t   9.52 ms    14435.5 GFLOP/s  92.5%
...
cuBLAS                            8.81 ms    15609.1 GFLOP/s  100%
```

### 7. Repeat for All Kernels

```bash
for kernel in \
  sgemm_naive \
  sgemm_coalesced_2d \
  sgemm_coalesced_1d \
  sgemm_smem_tiling \
  sgemm_register_tiling_1d \
  sgemm_register_tiling_2d \
  sgemm_vectorized \
  sgemm_warp_tiling \
  sgemm_padded_smem \
  sgemm_double_buffered \
  sgemm_final; do
  
  # Compile
  nvcc -O3 -arch=sm_120 -o "$kernel" "$kernel.cu"
  
  # Run
  time "$kernel" 2>&1
  
  # Cleanup
  rm -f "$kernel"
done
```

## Best Practices (From Session)

### ✅ DO

1. **Compile sequentially** — compile and run kernels one at a time
2. **Free memory after each kernel** — use `cudaFree()` in kernel code or run sequentially
3. **Use `time` command** — not kernel-internal timing for comparison
4. **Match `-arch` to your GPU** — `sm_120` for RTX 50-series
5. **Run cuBLAS reference** — compare all kernels against actual cuBLAS performance
6. **Document each kernel** — record time, GFLOP/s, % cuBLAS, and key insight
7. **Check GPU memory** — `nvidia-smi` before/after to catch leaks

### ❌ DON'T

1. **Don't run kernels in parallel** — causes OOM and timing interference
2. **Don't use numba CUDA** — compilation issues, slower than nvcc
3. **Don't use Python wrappers** — overhead hides real performance
4. **Don't assume NumPy CUDA is same as native CUDA** — different memory layout
5. **Don't compare with theoretical peak** — cuBLAS is the real target

## Common Pitfalls (From Session)

### 1. OOM Errors

**Symptom:** CUDA kernel crashes or hangs

**Cause:** Memory leak from missing `cudaFree()` or too many concurrent kernels

**Fix:**
```bash
# Run kernels sequentially
./kernel1
./kernel2  # kernel1 already freed memory
./kernel3
```

### 2. Compilation Errors

**Symptom:** `nvcc` returns non-zero exit code

**Cause:**
- Wrong `-arch` (e.g., `-arch=sm_80` on RTX 50-series which is `sm_120`)
- Template syntax issues
- Missing dependencies

**Fix:**
```bash
# Check compute capability
/usr/local/cuda/bin/nvcc -query
# For RTX 50-series, use sm_120
/usr/local/cuda/bin/nvcc -arch=sm_120 ...
```

### 3. Timing Confusion

**Symptom:** Times vary between runs

**Cause:** System load, GPU clock throttling

**Fix:**
```bash
# Use time command for wall-clock time
# Run multiple times and average
time ./kernel 2>&1
time ./kernel 2>&1
time ./kernel 2>&1
# Average the times
```

### 4. GPU Process Not Found

**Symptom:** `permission denied` or `command not found`

**Cause:** CUDA binaries not in PATH

**Fix:**
```bash
export PATH=$PATH:/usr/local/cuda-13.1/bin
```

### 5. Benchmark Output Missing

**Symptom:** Kernel runs but no output

**Cause:** Kernel exits without printing (by design)

**Fix:** Use `time` command which captures wall-clock time regardless of output

## Performance Comparison Guide

### Original (RTX 5080) vs This Session (RTX 5060 Ti)

| Factor | RTX 5080 | RTX 5060 Ti | Impact |
|--------|----------|-------------|--------|
| SM Count | More | Fewer | Lower peak occupancy |
| L2 Cache | 24 MB | 6 MB | Less tile reuse |
| Memory BW | 1.2 TB/s | 896 GB/s | ~34% slower memory-bound |
| FP32 Peak | ~90 TFLOPS | ~56 TFLOPS | ~38% slower compute |

**Result:** All performance percentages are lower on 5060 Ti but optimization ladder is preserved.

## Alternative Approaches

### 1. Python NumPy Benchmark (CPU)

```python
import numpy as np
A = np.random.randn(M, K).astype(np.float32)
B = np.random.randn(K, N).astype(np.float32)
start = time.time()
C = A @ B
end = time.time()
# NumPy on CPU achieves ~697 GFLOPS (~1.8% cuBLAS)
```

**Advantages:** No CUDA setup, quick baseline
**Disadvantages:** ~40-100x slower than CUDA

### 2. Numba CUDA (CPU Compilation)

```python
from numba import cuda, jit
@jit(nopython=True, parallel=True)
def kernel(A, B, C):
    # CUDA code here
    pass
```

**Issues:** Compilation overhead, numba version issues, device target selection

### 3. Direct CUDA Source (Recommended)

```bash
# Raw CUDA files with nvcc compiler
# Pros: Native performance, no overhead, accurate
# Cons: Need CUDA toolchain, compilation time per kernel
```

## Verification Checklist

For each kernel, verify:

- [ ] Compiles without errors
- [ ] Runs without errors (exit code 0)
- [ ] Time measurement is recorded
- [ ] GFLOP/s calculated correctly
- [ ] % cuBLAS compared against reference
- [ ] Memory freed properly
- [ ] Optimization insight documented

## References

- **Original article:** https://maxxfuu.com/writings/article4/
- **Source code:** https://github.com/maxxfuu/optimized-GEMM
- **CUDA Programming Guide:** https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- **cuBLAS:** https://docs.nvidia.com/cuda/cublas/index.html
- **Simons' CUDA optimization:** https://siboehm.com/articles/22/CUDA-MMM
- **Robert Zhang's CUDA optimization:** https://robertzhang.me/blog/cuda-mmm
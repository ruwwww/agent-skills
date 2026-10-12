# CUDA Memory Management & OOM Prevention
**Best practices for managing CUDA device memory to avoid Out-of-Memory errors**

## Common OOM Scenarios

### 1. Memory Leaks from Reuse
```cuda
// WRONG - Memory leak!
float *A;
cudaMalloc(&A, M * K * sizeof(float));
// ... use A ...
// Forgot to free!

// CORRECT - Always free
cudaMalloc(&A, M * K * sizeof(float));
// ... use A ...
cudaFree(A);
```

### 2. Accumulating Allocations
```cuda
// WRONG - OOM when running many kernels
for (int i = 0; i < 1000; i++) {
    float *A;
    cudaMalloc(&A, M * K * sizeof(float));
    // Run kernel
    // Forgot to free each iteration!
}

// CORRECT - Free after each kernel
for (int i = 0; i < 1000; i++) {
    float *A;
    cudaMalloc(&A, M * K * sizeof(float));
    // Run kernel
    cudaFree(A);
}
```

### 3. Matrix Size Exceeds GPU Memory
```cuda
// WRONG - OOM for 4096x4096x4096 float
float *A;
cudaMalloc(&A, 4096 * 4096 * 4096 * sizeof(float));
// 4096^3 floats = 137 billion floats = 550 GB (!)

// CORRECT - Use row-major layout
float *A;
cudaMalloc(&A, M * K * sizeof(float));  // 67 MB for 4096x4096
```

### 4. Device vs Host Memory Confusion
```cuda
// WRONG - Trying to use host pointers on device
float *A = new float[4096 * 4096];  // Host memory
// Pass A to CUDA kernel - undefined behavior!

// CORRECT - Allocate on device
float *d_A;
cudaMalloc(&d_A, M * K * sizeof(float));
// Use d_A in kernel
```

## Best Practices Checklist

### Always
- [ ] Call `cudaFree()` for every `cudaMalloc()`
- [ ] Check `cudaError_t` after every CUDA API call
- [ ] Free in reverse order of allocation (LIFO)
- [ ] Call `cudaDeviceSynchronize()` before freeing if needed
- [ ] Call `cudaDeviceReset()` at end of program

### Memory Management Pattern
```cuda
// Allocate
float *d_A, *d_B, *d_C;
cudaMalloc(&d_A, M * K * sizeof(float));
cudaMalloc(&d_B, K * N * sizeof(float));
cudaMalloc(&d_C, M * N * sizeof(float));

// ... run kernel ...

// Free (reverse order)
cudaFree(d_C);
cudaFree(d_B);
cudaFree(d_A);

// Sync and reset
cudaDeviceSynchronize();
cudaDeviceReset();
```

### For Sequential Kernel Testing
```bash
#!/bin/bash
# Run each kernel sequentially
for kernel in kernel1 kernel2 kernel3; do
    echo "=== Testing $kernel ==="
    ./sgemm_naive 2>&1
    # Kernel runs, frees memory internally
    # Next kernel runs on clean GPU
done
```

### Memory Monitoring
```bash
# Check GPU memory usage before/after
nvidia-smi
nvidia-smi -q -d memory

# Check for CUDA errors
cuda-memcheck ./kernel_name

# Monitor GPU process count
nvidia-smi | grep processes
```

### Safe Kernel Execution
```bash
# Run with timeout to prevent hanging
timeout 60 ./sgemm_naive 2>&1

# Kill CUDA processes if stuck
pkill -9 nvcc
pkill -f cuda
nvidia-smi -c 0  # Keep GPU in U0 mode

# Reset GPU
sudo nvidia-smi -d -i 0 --gpu-memtype-split=user
```

## Memory Requirements Matrix

For M=N=K=4096 float32 matrices:
```
Matrix A (4096×4096): 67.1 MB
Matrix B (4096×4096): 67.1 MB
Matrix C (4096×4096): 67.1 MB
Total Host Memory:     201.3 MB
Total Device Memory:   201.3 MB
```

For M=N=K=8192 float32 matrices:
```
Matrix A (8192×8192): 268.4 MB
Matrix B (8192×8192): 268.4 MB
Matrix C (8192×8192): 268.4 MB
Total Host Memory:     805.2 MB
Total Device Memory:   805.2 MB
```

## Error Handling Pattern
```cuda
// Allocate
cudaError_t err = cudaMalloc(&d_A, M * K * sizeof(float));
if (err != cudaSuccess) {
    printf("cudaMalloc failed: %s\n", cudaGetErrorString(err));
    return -1;
}

// Run kernel
err = sgemm_kernel<<<grid, block>>>(...);
if (err != cudaSuccess) {
    printf("Kernel launch failed: %s\n", cudaGetErrorString(err));
    cudaFree(d_A);
    return -1;
}

// Sync
err = cudaDeviceSynchronize();
if (err != cudaSuccess) {
    printf("cudaDeviceSynchronize failed: %s\n", cudaGetErrorString(err));
    cudaFree(d_A);
    return -1;
}

// Free
cudaFree(d_A);
```

## GPU Memory Limits (RTX 5060 Ti)
- **Total Device Memory:** 16 GB
- **Max Memory per Context:** ~14 GB (after system reserves)
- **Recommended Limit:** < 10 GB for safety margin

For 4096×4096 GEMM: 201.3 MB per kernel → **Safe!**
For 10000×10000 GEMM: ~1.6 GB per kernel → **Safe!**
For 100000×100000 GEMM: ~160 GB per kernel → **OOM!**

## References
- NVIDIA CUDA Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- cuda-memcheck tool: https://docs.nvidia.com/cuda/cuda-memcheck/index.html
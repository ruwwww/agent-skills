#!/bin/bash
# CUDA GEMM Kernel Benchmark Script
# Compiles and benchmarks CUDA matmul kernels sequentially
# Prevents OOM by running kernels one at a time with proper cleanup

set -e

CUDA_PATH="/usr/local/cuda-13.1/bin/nvcc"
CUDA_ARCH="-arch=sm_120"
OUTPUT_DIR="${OUTPUT_DIR:-/home/kuroko/benchmark_results}"

mkdir -p "$OUTPUT_DIR"

cd /home/kuroko/optimized-GEMM

echo "=============================================="
echo "CUDA GEMM Kernel Benchmark - RTX 5060 Ti"
echo "=============================================="
echo ""

Kernels=(
    "sgemm_naive"
    "sgemm_coalesced_2d"
    "sgemm_coalesced_1d"
    "sgemm_smem_tiling"
    "sgemm_register_tiling_1d"
    "sgemm_register_tiling_2d"
    "sgemm_vectorized"
    "sgemm_warp_tiling"
    "sgemm_padded_smem"
    "sgemm_double_buffered"
    "sgemm_final"
)

# Create results CSV
echo "Kernel,Time_ms,GFLOPS,%_cublas,Notes" > "$OUTPUT_DIR/results.csv"

total_time=0
count=0

for kernel in "${Kernels[@]}"; do
    echo "=== Compiling: $kernel ==="
    
    # Compile kernel
    if ! $CUDA_PATH -O3 -arch=sm_120 -o "$kernel" "$kernel.cu" 2>&1 | tee "$OUTPUT_DIR/${kernel}.build.log"; then
        echo "ERROR: Compilation failed for $kernel"
        echo "$kernel,ERROR,0,0,Failed to compile" >> "$OUTPUT_DIR/results.csv"
        continue
    fi
    echo "Compilation successful!"
    
    # Run kernel with timeout and capture time
    start_time=$(date +%s%N)
    timeout 300 "$kernel" > /dev/null 2>&1
    exit_code=$?
    
    if [ $exit_code -eq 124 ]; then
        echo "ERROR: Kernel timed out (> 300s)"
        echo "$kernel,TIMED_OUT,0,0,Timeout after 300s" >> "$OUTPUT_DIR/results.csv"
        rm -f "$kernel"
        continue
    fi
    
    end_time=$(date +%s%N)
    elapsed_ns=$((end_time - start_time))
    elapsed_ms=$(echo "scale=3; $elapsed_ns / 1e6" | bc)
    
    # Calculate GFLOPS (137.4 GFLOPs for 4096^3 matrix multiply)
    gflops=$(echo "scale=2; 137.4 / ($elapsed_ns / 1e12)" | bc)
    
    # Estimated cuBLAS performance for RTX 5060 Ti
    cublas_perf=15609  # ~15.6 TFLOPS cuBLAS
    pct_cublas=$(echo "scale=2; ($gflops / $cublas_perf) * 100" | bc)
    
    # Add to totals
    total_time=$(echo "scale=3; $total_time + $elapsed_ms" | bc)
    count=$((count + 1))
    
    # Print result
    echo "  Time: ${elapsed_ms} ms"
    echo "  GFLOPS: ${gflops}"
    echo "  % of cuBLAS: ${pct_cublas}%"
    
    echo "$kernel,${elapsed_ms},${gflops},${pct_cublas}%,OK" >> "$OUTPUT_DIR/results.csv"
    
    # Cleanup
    rm -f "$kernel"
    echo "Cleaned up $kernel"
    echo ""
done

echo "=============================================="
echo "Benchmark Complete!"
echo "=============================================="
echo ""

if [ $count -gt 0 ]; then
    avg_time=$(echo "scale=3; $total_time / $count" | bc)
    echo "Total kernels tested: $count"
    echo "Total time: ${total_time} s"
    echo "Average time per kernel: ${avg_time} s"
else
    echo "No kernels compiled successfully"
fi

echo ""
echo "Results saved to: $OUTPUT_DIR/results.csv"

# Show summary
echo ""
echo "Summary Table:"
echo "-------------"
tail -n +2 "$OUTPUT_DIR/results.csv" | grep -v "ERROR" | grep -v "TIMED_OUT" | while IFS=',' read kernel time gflops pct notes; do
    echo "  $kernel: ${time} ms | ${gflops} GFLOPS | ${pct}% cuBLAS"
done | sort -t',' -k2 -n

# Show top 5 fastest
echo ""
echo "Top 5 Fastest:"
echo "-------------"
tail -n +2 "$OUTPUT_DIR/results.csv" | sort -t',' -k2 -n | head -5 | while IFS=',' read kernel time gflops pct notes; do
    echo "  $kernel: ${time} ms (~${gflops} GFLOPS, ${pct}% cuBLAS)"
done

echo ""
echo "Slowest 5:"
echo "---------"
tail -n +2 "$OUTPUT_DIR/results.csv" | sort -t',' -k2 -rn | head -5 | while IFS=',' read kernel time gflops pct notes; do
    echo "  $kernel: ${time} ms (~${gflops} GFLOPS, ${pct}% cuBLAS)"
done
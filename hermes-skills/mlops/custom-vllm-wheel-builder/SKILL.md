---
name: custom-vllm-wheel-builder
description: "Use when building custom vLLM wheels for target GPU archs."
version: 1.0.0
dependencies: [torch, cmake, ninja]
platforms: [linux]
metadata:
  hermes:
    tags: [vLLM, CUDA, Wheel Build, A100, Ampere, SM80, GLIBC, Packaging]
---

# Custom vLLM Wheel Compilation & Architecture Targeting

## When to Use
Use when deploying vLLM on institutional or enterprise HPC servers (like DGX A100 SXM4) where:
1. Public PyPI wheels lock to a newer CUDA runtime (e.g. CUDA 13 `libcudart.so.13`) incompatible with host drivers (CUDA 12.8 / Driver 570.x).
2. Host users lack root/sudo or compilers (`nvcc`, `gcc`, `cmake`).
3. You need to compile from source in a cloud runner (GitHub Actions / vast.ai / RunPod) for a target architecture.

## Architecture Targeting: Ampere SM 8.0 (A100)
By default, building vLLM compiles CUDA kernels for all architectures (`sm_75`, `sm_80`, `sm_89`, `sm_90`, `sm_100`, `sm_120`), taking >1.5 hours.
Targeting a single compute capability slashes build time to ~15-20 minutes:
```bash
export TORCH_CUDA_ARCH_LIST="8.0"
export VLLM_CUDA_ARCH_LIST="8.0"
export CMAKE_BUILD_TYPE=Release
export MAX_JOBS=4
```

## GLIBC Compatibility Rule
- Check host GLIBC: `ldd --version | head -n1`.
- If building on a workstation (Ubuntu 24.04 with GLIBC 2.39) for deployment to an older cluster (Ubuntu 22.04 LTS with GLIBC 2.35), native compilation links against `GLIBC_2.38` symbols and will fail to load on the cluster.
- Always compile inside an Ubuntu 22.04 container (`nvidia/cuda:12.4.1-devel-ubuntu22.04`) or an `ubuntu-22.04` GitHub Actions runner.

## CMake FetchContent & Sub-dependency Pitfalls
vLLM's build system downloads submodules via CMake FetchContent:
- `CUTLASS`: Set `export VLLM_CUTLASS_SRC_DIR="/path/to/cutlass"` to use local sources instead of fetching over git.
- `triton_kernels`: Set `export TRITON_KERNELS_SRC_DIR="/path/to/triton_kernels"` pointing to the Python package directory.
- `vllm-flash-attn`: Set `export VLLM_FLASH_ATTN_SRC_DIR="/path/to/vllm_flash_attn"`.

## Verification in a Clean Environment
Always test the generated `.whl` in a clean Python virtualenv before publishing:
```bash
python -c "
import vllm
from vllm.model_executor.models import ModelRegistry

print('vLLM version:', vllm.__version__)
archs = ModelRegistry.get_supported_archs()
assert 'Gemma4ForConditionalGeneration' in archs
print('SUCCESS: Target architecture verified in wheel.')
"
```

## Benchmarking: Pure Token Generation (Decode Rate)
When evaluating throughput on served models:
1. Isolate TTFT (Time to First Token / Prefill Phase) from token decode time using streaming SSE responses (`stream=True`).
2. Calculate pure token generation decode rate:
   $$\text{Pure TG (tok/s)} = \frac{\text{Generated Tokens}}{\text{Stream End Time} - \text{First Token Time}}$$
3. Never report combined/blended throughput that mixes prefill token processing with token generation rate.

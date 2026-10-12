---
name: custom-cuda-wheel-builds
description: "Compile CUDA wheels for remote clusters and older GLIBC."
version: 1.0.0
license: MIT
---

# Custom CUDA Wheel Compilation for Remote Clusters

## Overview

Use this skill when deploying LLM inference/training frameworks (such as vLLM, FlashAttention, SageAttention, or custom CUDA kernels) to remote cluster environments (e.g. DGX A100/H100) where:
1. Target host has an older GLIBC (e.g. Ubuntu 22.04 / GLIBC 2.35) while the local workstation has a newer GLIBC (e.g. Ubuntu 24.04 / GLIBC 2.39). Native compilation on the workstation links higher GLIBC symbols (`GLIBC_2.38+`) that will cause immediate dynamic linker failures on the target.
2. Target host lacks `sudo` or compilers (`gcc`, `g++`, `nvcc`).
3. Upstream PyPI wheels either lack newly merged model architectures (e.g. unreleased multi-modal heads or model classes) or lock to an incompatible CUDA runtime version.

## Containerized Build Protocol

To ensure 100% binary compatibility with the target machine without requiring host root modifications or risky volume mounts:

```bash
# 1. Start a persistent background container matching the target OS and CUDA version
docker run -d --name cuda_wheel_builder nvidia/cuda:12.4.1-devel-ubuntu22.04 sleep infinity

# 2. Stage build scripts into the container via docker cp
docker cp build_script.sh cuda_wheel_builder:/workspace/build_script.sh
docker exec cuda_wheel_builder chmod +x /workspace/build_script.sh

# 3. Execute build inside container
docker exec cuda_wheel_builder /workspace/build_script.sh

# 4. Extract generated wheel back to host
docker cp cuda_wheel_builder:/workspace/dist/*.whl ./dist/
docker rm -f cuda_wheel_builder
```

## Compilation Flags & Optimization

Compiling all CUDA architectures (Turing, Ampere, Ada, Hopper) takes hours and can exhaust RAM. Always restrict compilation to the exact target GPU:

```bash
# Restrict CUDA kernels to target architecture only:
# - A100: "8.0"
# - RTX 3090: "8.6"
# - RTX 4090 / Ada 6000: "8.9"
# - H100: "9.0"
export TORCH_CUDA_ARCH_LIST="8.0"
export VLLM_CUDA_ARCH_LIST="8.0"
export CMAKE_BUILD_TYPE=Release

# Cap parallel jobs (especially on dev hosts with <= 16GB RAM) to avoid compiler OOM
export MAX_JOBS=3
python setup.py bdist_wheel
```

## Common Pitfalls & Workarounds

### Git Clone RPC / Packfile Disconnects vs PyPI sdist
Large AI framework repositories (e.g. vLLM, transformers) frequently fail to clone over HTTPS inside containers with:
`error: RPC failed; curl 92 HTTP/2 stream 0 was not closed cleanly: CANCEL (err 8)` or
`curl 18 transfer closed with outstanding read data remaining` / `unexpected disconnect while reading sideband packet`

Even with `git config --global http.version HTTP/1.1` and `http.postBuffer`, network dropouts on large packfiles remain common.

**Superior Solution (PyPI sdist)**:
Download the official source distribution (`sdist`) from the PyPI Fastly CDN instead of cloning git history:
```bash
curl -L -o /tmp/vllm-sdist.tar.gz https://files.pythonhosted.org/packages/.../vllm-<version>.tar.gz
tar -xzf /tmp/vllm-sdist.tar.gz
```
The sdist is ~40MB (vs >1GB for full git clones), downloads in seconds, and includes all necessary C++, CUDA, Rust sources and CMakeLists.

### Hybrid Build Toolchains (Rust / Cargo)
Modern AI serving packages (such as vLLM) utilize Rust for parser modules via `setuptools-rust`. Ensure both C++ and Rust toolchains are provisioned in the builder container:
```bash
apt-get install -y cargo rustc build-essential cmake ninja-build ccache
```

### Proactive Local Container Building
When a GLIBC mismatch exists between local workstation and remote cluster, check `docker --version`. If Docker is running locally, proceed with local containerized compilation immediately rather than requiring cloud instance rentals (vast.ai/RunPod) or external CI runners.

### Post-Build Pre-Deployment Architecture Verification
Never deploy an unverified wheel to a remote server. Test-install in a fresh virtualenv inside the build container:

```python
import framework_module
from framework_module.model_executor.models import ModelRegistry

archs = ModelRegistry.get_supported_archs()
assert "TargetModelArchitecture" in archs, "Target architecture is missing from registry!"
print("Architecture confirmed.")
```

### Remote Node Deployment & Benchmark Isolation
On the target cluster (e.g. institutional DGX), install via fast virtualenv tools:
```bash
/path/to/uv pip install "/path/to/wheel.whl" --python /path/to/venv/bin/python
```

When evaluating throughput on the cluster, isolate **pure Token Generation (TG tok/s)** from Time-to-First-Token (TTFT / prefill latency) using streaming tokens, ensuring prompt processing time does not skew decode throughput metrics.

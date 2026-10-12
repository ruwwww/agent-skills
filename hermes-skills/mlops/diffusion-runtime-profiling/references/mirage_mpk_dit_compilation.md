# Mirage MPK Task-Based Compilation for Diffusion Transformers (DiT)

## Architectural Principle: LLM vs. DiT Task Graph Compilation
Mirage Persistent Kernel (MPK, OSDI 2026) was originally developed for LLM decoding, but DiT inference is an even better fit:
1. **Zero-Scheduler AOT Compilation**:
   - LLMs suffer from variable KV-cache lengths and dynamic request scheduling, requiring scheduler warps on dedicated SMs and Just-In-Time (JIT) task dispatch.
   - DiTs operate on **100% static shapes** across all diffusion steps ($S = (H/p) \times (W/p)$ spatial tokens + fixed text context tokens).
   - All tasks are classified as Ahead-Of-Time (AOT). All physical SMs (e.g. 36 SMs on RTX 5060 Ti) are allocated to compute workers (`num_local_schedulers = 0`, `num_schedulers = 0`), eliminating scheduler-worker round-trip latency.
2. **In-Kernel Multi-Step Sampling Loop (Single Persistent Launch)**:
   - Traditional PyTorch/CUDA Graph sampling executes $N$ host-driven model iterations with inter-step stream synchronization.
   - In MPK, an **Euler ODE step update task** ($x_{t+\Delta t} = x_t + \Delta t \cdot v_\theta$) is registered as the terminal node of the task graph in device memory.
   - If `step < max_steps`, the terminal event directly triggers `TASK_BEGIN_TASK_GRAPH` for the next step, executing all 25–50 sampling steps in **one single persistent kernel launch** (`mpk()`) with zero host CPU re-entry.
3. **Cross-Task Software Pipelining Across Blocks**:
   - Decomposes each task into pre-loading (`cp.async` / TMA global-to-shared copy) and compute (Tensor Core MMA).
   - Overlaps Tensor Core compute of block $N$ with asynchronous weight pre-loading for block $N+1$ using Paged Shared-Memory, preventing pipeline flushes between layers.

## Anima DiT (`CosmosTransformer3DModel`) Architecture Mapping
Anima DiT in Diffusers >= 0.39.0 (`transformer_cosmos.py`) consists of 28 transformer blocks:
```
transformer_blocks.{i}.norm1 (AdaLayerNormZero) -> [linear_1: (256, 2048), linear_2: (6144, 256)]
  outputs: shift_msa, scale_msa, gate_msa (2048 each)
transformer_blocks.{i}.attn1 (Self-Attention) -> to_q, to_k, to_v, to_out.0: (2048, 2048)
  qk_norm: norm_q, norm_k: (128)
transformer_blocks.{i}.norm2 (AdaLayerNormZero) -> [linear_1: (256, 2048), linear_2: (6144, 256)]
  outputs: shift_cross, scale_cross, gate_cross (2048 each)
transformer_blocks.{i}.attn2 (Cross-Attention) -> to_q: (2048, 2048), to_k, to_v: (2048, 1024), to_out.0: (2048, 2048)
  qk_norm: norm_q, norm_k: (128)
transformer_blocks.{i}.norm3 (AdaLayerNormZero) -> [linear_1: (256, 2048), linear_2: (6144, 256)]
  outputs: shift_mlp, scale_mlp, gate_mlp (2048 each)
transformer_blocks.{i}.ff (FeedForward) -> net.0.proj: (8192, 2048), GeLU, net.2: (2048, 8192)
```

### Critical Correctness Pitfall: Attention QK-Norm
- In Diffusers `CosmosTransformerBlock`, RMSNorm on Q and K is performed *inside* the attention block using `norm_q` and `norm_k` weights.
- When mapping to MPK's `attention_layer`, pass the attached `norm_q` and `norm_k` weights directly into the kernel ABI.
- **Do NOT insert standalone `rmsnorm_layer` calls on Q and K before calling `attention_layer`**, as that causes catastrophic double-normalization.

## Verified Fastpath Benchmark Baseline (RTX 5060 Ti 16GB, SM120)
For rapid verification of Anima models under 1MP @ 30 steps CFG 4.5:
- **Stack**: `anima-base-v1.0-convrot-int8.safetensors` + `TorchCompileModelAdvanced` (Inductor, `compile_transformer_blocks_only=True`) + `ApplyAnimaBaryCache` (stepwise, eq-space, `fresh_start=3`, `fresh_interval=2`, `end_percent=0.9`).
- **Portrait 832x1216 (1.01 MP)**: **8.24s (~3.64 it/s)**.
- **Square 1024x1024 (1.05 MP)**: **8.52s (~3.52 it/s)**.
- Both comfortably beat the $\le 15$s operational latency ceiling with zero visual lineart softening.

## Sovereign Standalone Implementation & Native Mirage Build
- **Mirage MPK C++/Rust Compilation Recipe**:
  - Build Rust sub-crates: `cargo build --release --manifest-path src/search/abstract_expr/abstract_subexpr/Cargo.toml` and `formal_verifier_equiv/Cargo.toml` -> copy `.so` files to `python/mirage/lib/`.
  - Fix CMake JSON serialization: Patch `src/search/search_context.cc` with `to_json`/`from_json` for `SearchLevel` and non-null pair fallback for GUID lookup.
  - Submodules: Place CUTLASS in `deps/cutlass` and `nlohmann/json` in `deps/json`.
  - Compile extension: `python setup.py build_ext --inplace && pip install -e .`.
- **AnimaBuilder Registration**:
  - Implemented in `python/mirage/mpk/models/anima/builder.py` under branch `feature/anima-dit` (synced to fork `ruwwww/mirage`).
  - Registered as `anima`, `Anima`, `CosmosTransformer3DModel`.
  - Validated with 6 unit tests in `tests/test_anima_builder.py`.
- **Pure Standalone (Zero ComfyUI) Benchmark Results**:
  - Standalone PyTorch BF16 + Inductor: 24.04s.
  - Standalone ConvRot INT8 (250 linear layers via `torch.ops.comfy_kitchen.int8_linear`): 16.34s (sequential CFG) / 12.19s potential (batched $B=2$).
  - **ConvRot Boundary Policy**: Keep Block 0, 1, 27, embeddings, norms, and AdaLN in BF16; quantize only intermediate blocks 2–26 (10 layers each).
  - **VAE Precision**: Keep Cosmos/QwenImage VAE in BF16/FP32 to prevent FP16 numerical underflow (black screen).
- **CFG Execution Latency Trap**:
  - Diffusers `AnimaModularPipeline` defaults to sequential iteration over conditionings ($2 \times B=1$ passes per step = 60 forward passes), inflating launch overhead.
  - Concatenating conditionings into batched $B=2$ cuts passes to 30, matching ComfyUI's 12–13s latency on SM120.

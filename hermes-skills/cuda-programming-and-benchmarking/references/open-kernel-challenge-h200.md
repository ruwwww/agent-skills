# Open Kernel Challenge (H200 SXM & SGLang Serving) Reference

## 1. Challenge Architecture & Evaluation Harness
- **Target Hardware:** Single NVIDIA H200 SXM (SM90a, 141 GB HBM3e @ 4.8 TB/s, 132 SMs).
- **Serving Baseline:** SGLang commit `a55ab7d5ae1bba59ac351e55026fe7f7644ecc5f` (Muse Spark Open day-0 support).
- **Timing & Harness:**
  - Evaluated strictly under **CUDA Graph replay** (`torch.cuda.make_graphed_callables` or native graph capture).
  - Every timed replay begins with a **cold L2 cache** (judge flushes L2 by streaming a large buffer before timing).
  - Fixed graph launch cost (~4 µs) is subtracted by the judge from both reference and candidate.
  - Scores are computed from paired speedup ratios across scored shapes with geometric mean over loads.
- **Untimed Setup:**
  - `prepare(weights)` runs once untimed (up to 300 seconds).
  - Use this for static workspace allocations, weight repacking, layout transpositions, and constant fusion.

## 2. Authentication & CLI Operational Rules
- CLI: `okc` installed via `curl -fsSL https://openkernelchallenge.dev/install.sh | sh` (default binary: `~/.okc/bin/okc`).
- **Human-in-the-loop rule:** Agents must NOT accept challenge terms automatically. A human user must execute `okc login` interactively in a TTY to review terms and complete GitHub device authorization (`POST /api/v1/auth/device/start`).
- **Headless Sandbox Auth:** Pass token via `export OKC_TOKEN="$(okc api token)"`.
- **Offline Codebase Inspection:** Run `okc serve init <dir>` to clone the pinned SGLang codebase (`a55ab7d5ae1b`) for exact local inspection of kernel dispatches, headers (`moe_wna16_marlin.cuh`), and unit tests.
- **Non-blocking CLI Execution Rule:** Always submit runs with `--no-wait --json` (e.g. `okc check submission.py --no-wait --json` or `okc submit submission.py --no-wait --json`). Remote execution takes 3–5 minutes; blocking foreground commands will hit harness timeouts. Poll progress via `okc status <job_id> --json` or `okc jobs`.
- **Workflow Commands:**
  - `okc init <problem> [dir]`: Scaffolds `submission.py`, `baseline.py`, `reference.py`, `checks.py`, `TASK.md`, `AGENTS.md`.
  - `okc check submission.py --no-wait`: Runs functional correctness and timing against SGLang off the leaderboard without consuming scored attempts.
  - `okc submit submission.py --no-wait`: Submits for official leaderboard scoring.

## 3. Kernel Problem Analysis & Optimization Vectors

### A. Dense Projections (`muse_bf16_proj`)
- **Shapes:** $M \in \{1, 8, 16, 32, 128, 256\}$, $K \in \{1024, 4096, 8192\}$, $N \in \{1024, 2304, 4096, 8192\}$.
- **Baseline Pitfall:** SGLang dispatches to `_bf16_gemm_dispatch_impl` (cuBLAS GEMM). For decode steps ($M \le 32$), cuBLAS exhibits poor SM utilization and launch overhead on 132 SMs.
- **Optimization Strategy:**
  - **Split-K GEMV:** For $M \in \{1, 8, 16\}$, partition the $K$-dimension across multiple threadblocks with 128-bit vectorized loads (`ld.global.v4.b32` / `float4`).
  - **Router FP32 Hi/Lo Fusion:** Router FP32 weights can run as a BF16 hi + lo split. Instead of launching two sequential `torch.mm` passes, fuse the dual accumulation directly into a single register/accumulator pass.

### B. Routed NVFP4 MoE (`muse_moe_w4a16`)
- **Shapes:** 256 total experts, 32 local per GPU under EP8, Top-8 routing, hidden width 4096, intermediate width 4096.
- **Baseline Pitfall:** SGLang runs Marlin MoE (`moe_align_block_size` + `moe_wna16_marlin_gemm`). Marlin requires sorting and padding tokens to block sizes of 8, 16, 32, or 64. At decode batch sizes ($M \le 32$), each GPU handles only ~1–4 active tokens across 32 experts. The block padding and sorting introduces massive wasted compute and DRAM traffic.
- **Optimization Strategy:**
  - Replace Marlin block GEMM with unpadded grouped GEMM or direct W4A16 GEMV kernel designed for tiny $M$.
  - Pre-allocate all activation scratch buffers in `prepare()`. SGLang dynamically allocates `cache1`, `cache2`, `cache3`, `cache13` on every call.
  - Fuse `silu_and_mul` and `fused_post_expert_norm_weighted_sum` directly into GEMM epilogues where possible.

### C. Gated Attention Decode (`muse_attention_decode`)
- **Shapes:** Batch $B \in \{1, 16, 32\}$, $L \in \{1, 8\}$, 16 query heads, 2 KV heads (TP8), head dimension 64, FP8 E4M3 cache, context ~80K tokens.
- **Baseline Pitfall:** Dispatches 4 sequential operations: Triton QKNorm+RoPE $\to$ KV-cache store $\to$ FlashAttention-3 $\to$ CUDA RMSNorm+sigmoid gate.
- **Optimization Strategy:**
  - **FlashDecoding:** FA3 is optimized for prefill/parallel query chunks; for single-query decode ($L=1$) over 80K paged tokens, FlashDecoding (splitting the KV sequence across SMs with online reduction) significantly reduces latency.
  - **Producer Fusion:** Fuse QK-Norm + RoPE + FP8 casting + KV-cache write into a single pass to eliminate intermediate global memory writes.

### D. Prefill Decoder Layer (`muse_prefill_layer`)
- **Shapes:** Batch $B \in \{1, 4\}$, context 0 to 80,000 tokens, query length $L \in \{753, 16384\}$ (first turn agentic chunks). Scored case weights heavily favor $L=16384$ sliding window (weight 138).
- **H200 Hardware Execution Profile:**
  - **Marlin MoE (`w13` & `w2`):** Consumes **63.5%–64.5% (~11.6 ms)** of total GPU execution time on 16K prefill chunks.
  - **Dense Projections (`qkv_gate`, `pooler`, `unpooler`, `o`):** Consumes **~22% (~4.0 ms)**.
  - **Attention (`flash_attn_with_kvcache`):** Consumes **~5%–28% (~0.9 ms – 1.6 ms)**.
  - **Norms & Fused Residuals:** Consumes **~4%–5% (~0.8 ms)**.
- **Hopper Tile Efficiency Rule:**
  - Setting `block_size_m < 64` (e.g. 16 or 32) degrades arithmetic intensity on H200 tensor cores. Although $M=753$ has fewer tokens per local expert, Marlin with `block_size_m=16` takes 1048 µs vs 620 µs with `block_size_m=64` (a 0.76x slowdown). Keep `block_size_m=64` for all prefill shapes.
- **Zero-Allocation Static Pre-Allocation:**
  - Pre-allocate maximum sized intermediate buffers in `prepare()`:
    - `cache13` ($M_{\text{max}} \times 8 \times 8192 \times 2 = 2.14 \text{ GB}$)
    - `cache2` ($M_{\text{max}} \times 8 \times 4096 \times 2 = 1.07 \text{ GB}$)
    - Alignment buffers for `sgl_moe_align_block_size` (`sorted_ids`, `expert_ids`, `n_padded`, `cumsum_buffer`).
  - Eliminates dynamic PyTorch caching allocator overhead and prevents graph replay instability.
- **Multi-Stream Producer-Consumer Overlap:**
  - `pre_expert_norm(expert_input)` depends only on pooler output, not routing IDs or weights.
  - Launch `expert_input = torch.mm(ffn_input, pooler_t)` followed immediately by `pre_expert_norm(expert_input)` on `main_stream`.
  - Concurrently compute split router GEMMs and top-k routing on `side_stream`.
  - Synchronize `main_stream.wait_stream(side_stream)` after `pre_expert_norm` finishes, completely overlapping the pre-expert RMSNorm pass under router execution.

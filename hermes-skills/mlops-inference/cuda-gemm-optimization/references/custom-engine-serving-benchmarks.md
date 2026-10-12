# Custom Engine Serving, Benchmarking & Speculative Decoding

Guidelines and empirical insights for benchmarking and verifying custom C++/CUDA LLM inference engines (such as NInfer) on NVIDIA Blackwell architectures (SM120, RTX 5060 Ti / RTX 5090).

## 1. Prefill Throughput & Prompt Length Amortization

- **The Short-Prompt Artifact**:
  - Measuring prefill on short prompts (e.g. 10–50 tokens) yields misleadingly low throughput (e.g. ~250–350 tok/s).
  - At small token counts, latency is dominated by CUDA kernel launch overhead, arena memory reservations, and non-saturated matrix shapes.
- **Realistic Long-Prompt Benchmarking**:
  - True prefill throughput must be measured with representative long prompts ($\ge 1,500\text{--}2,000$ tokens) and configured chunked prefill (e.g. `--prefill-chunk 4096`).
  - On RTX 5060 Ti (40 SMs, SM120a), full-attention / GDN hybrid 9B backbones reach **2,500–2,650 tok/s** once Tensor Cores are fully saturated.

## 2. Serving Concurrency Sweeps (C=1 to C=8)

- **Persistent Server Architecture**:
  - Reloading weights from NVMe to GPU takes 30–60 seconds per process launch for 6–18 GB models.
  - **Never** restart the server process for each concurrency level ($C=1, 2, 4, 8$) during benchmark campaigns; doing so causes timeouts and measurement drift.
  - Launch a single persistent server instance with `--max-concurrency 8` and adequate `--kv-capacity` (e.g. 32k tokens) and `--kv-dtype int8`.
  - Dispatch successive request waves ($C=1 \to C=2 \to C=4 \to C=8$) via parallel client worker pools (`ThreadPoolExecutor`) against the same warm server.
- **Empirical Scaling on RTX 5060 Ti (Ornith 1.5 9B / Qwen 3.5 9B)**:
  - $C=1$: ~88 tok/s aggregate decode (1.00×)
  - $C=2$: ~108 tok/s aggregate decode (1.22×)
  - $C=4$: ~127 tok/s aggregate decode (1.44×)
  - $C=8$: ~218 tok/s aggregate decode (**2.46× scaling**)
  - Total latency for 8 parallel 2k-prompt + 256-gen requests: < 9.5 seconds.

## 3. Speculative Decoding (Multi-Token Prediction - MTP)

- **Mechanics**:
  - MTP appends lightweight draft heads/layers trained to predict future tokens $k+1, k+2, \dots$ concurrently.
  - The base model validates the full draft tree in a single forward pass, amortizing memory bandwidth costs across accepted tokens.
- **Verification Metrics**:
  - Draft Window: Typically 3 to 5 tokens.
  - Acceptance Rate: Typically 40%–80% depending on prompt entropy and thinking mode.
  - Acceptance Length: Target $> 2.0\text{ tok/round}$ to achieve significant decode acceleration (~20%–50% throughput gain over greedy decode).

## 4. Storage-Constrained Model Ingestion

- **On-the-Fly Dequantization**:
  - In environments with constrained disk space (< 20 GB free), downloading uncompressed raw BF16 checkpoints (~18–20 GB) risks exhausting disk capacity when writing the packaged artifact (.ninfer ~6.1 GB).
  - Download compressed checkpoints (e.g. NVFP4 / FP8 mixed safetensors ~8.8 GB).
  - Implement a streaming shard reader (`source.py`) that reads NVFP4 (U8) and FP8 (E4M3) on-the-fly, unpacks them to logical BF16, and feeds them directly into the engine's target quantization pipeline (e.g. Q4/Q5/Q6/W8 groupwise-int).
  - Preserve any native unquantized layers (such as MTP transformer layers, which are often left in BF16 in published NVFP4 checkpoints).

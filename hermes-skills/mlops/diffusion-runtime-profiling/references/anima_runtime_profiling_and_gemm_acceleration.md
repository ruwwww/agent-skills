# Anima / Cosmos 2 DiT Runtime Profiling & GEMM Acceleration Reference

## 1. Fastpath Architecture & Execution Stack
For Anima (Cosmos 2 DiT architecture, ~2.37B params, 32 Blocks) on modern RTX GPUs (e.g. RTX 5060 Ti 16GB) at full $832 \times 1216$ resolution (3,952 patch tokens):
* **Startup Flags**: `python main.py --fast --use-ck-attention`
* **Compilation Node**: Native ComfyUI compile node (`TorchCompileModel` in `comfy_extras/nodes_torch_compile.py`, backend `inductor`, dynamic `False` automatically enforced) or `TorchCompileModelAdvanced` with `mode='max-autotune-no-cudagraphs'` or `'default'`, `dynamic=False`.
* **Throughput & Speed**:
  - **BF16 Base Checkpoint (`anima-base-v1.0.safetensors`)**: ~1.95 – 2.08 it/s on Batched CFG ($B=2$), completing 30 steps in ~14.9 – 15.3s.
  - **Blackwell MXFP8 Checkpoint (`anima-base-v1.0-mxfp8.safetensors` from `Bedovyy/Anima-FP8`)**: **~2.75 it/s**, completing 30 steps in **~11.7 – 12.0s** (~2.55x speedup vs eager BF16 baseline) with ~5.2 GiB VRAM peak on RTX 5060 Ti.
* **MXFP8 Quantization Structure (`comfy-dit-quantizer`)**:
  - `keep` (FP16/BF16 full precision): `blocks.0.`, `blocks.1.`, `blocks.27.`, and all `adaln_modulation` layers to preserve initial layout and high-frequency edge detail.
  - `mxfp8` (Microscaling FP8): `q_proj`, `k_proj`, `v_proj`, `output_proj`, and `.mlp` layers directly mapped to 5th-gen Tensor Cores.

## 2. Kernel & Operator Breakdown (Batched CFG B=2)
* **GEMM Linear Layers (68.5% – 75.5% GPU time, ~598 ms)**: QKV projections, attention out-proj, and MLP up/down projections via CUTLASS BF16 TensorOp.
* **Inductor Fused Elementwise (15.3% – 16.8% GPU time, ~133 ms)**: PyTorch Inductor fuses AdaLN modulation, gated residuals (`addcmul`), and GELU/SiLU activations into ~704 specialized Triton pointwise/reduction kernels.
* **SageAttention / CK-Attention (4.9% – 12.0% GPU time, ~38 – 60 ms)**: INT8/FP8 quantized attention from `comfy_kitchen`.
* **Fused RMSNorm + 3D RoPE (2.4% – 2.7% GPU time, ~21 ms)**: Vectorized CUDA/Triton spatial-temporal rotary embedding (`comfy_kitchen::rms_rope_split_half`).

### Video DiT vs Image DiT Bottleneck Divergence (VC-Attention / Low-Bit Attention Applicability)
* **Image DiT (Anima, SD3, FLUX at ~1MP / 3.9k tokens)**: Attention comprises only **<10–12%** of GPU runtime. GEMM (FFN / Linear Projections) is the dominating bottleneck ($\sim 70\%$). Low-bit attention optimizations (like SageAttention2 or VC-Attention / ExpCast-FP8) yield negligible end-to-end acceleration (<1–2%) and introduce unnecessary quantization noise or token-clustering overhead. Prioritize GEMM quantization (NVFP4 / W4A4 / W4A8) and TorchCompile for Image DiT.
* **Video DiT (MiniMax-H3, CogVideoX, Wan2.1 with $N \ge 30\text{k}-100\text{k}$ tokens)**: Due to $\mathcal{O}(N^2)$ quadratic complexity, Attention dominates **~65%–75%** of each denoising step. Here, advanced low-bit attention (e.g. VC-Attention with V-Smooth k-means residual quantization and ExpCast-FP8 linear softmax casting) provides massive 1.6×–1.9× kernel speedups on Blackwell/Hopper without retraining. Only adopt VC-Attention into Anima workflows if extended to multi-frame video generation or ultra-high native resolutions ($>4\text{K} \times 4\text{K}$).

## 3. CUDA Graph (`reduce-overhead`) Troubleshooting & Fixes
* **Blocker 1 (Autograd Missing)**: PyTorch AOTAutograd attempts backward trace on custom ops. Must execute under `torch.inference_mode()`.
* **Blocker 2 (Tensor Shape Mismatch in RoPE Validator)**: Raw `comfy_kitchen` validator expects 6D `freqs_cis`. Cosmos passes 4D/5D `[3952, 1, 1, 128]`. Wrap/adapter must add broadcast dimensions before dispatching to custom C++/CUDA kernel.
* **Execution Boundary & In-Place Overwrite Fix**: In multi-step KSampler loops, compiled blocks in DiT throw `RuntimeError: Error: accessing tensor output of CUDAGraphs that has been overwritten by a subsequent run` on residual `addcmul`. Fix this by calling `torch.compiler.cudagraph_mark_step_begin()` inside `comfy_api/torch_helpers/torch_compile.py` wrapper immediately before model executor invocation.

## 4. GEMM Acceleration Strategies for DiT without Degradation
* **Spatially-Sparse Token GEMM**: Deduplicating identical/flat background tokens in middle MLP blocks (Blocks 10–26) reduces row dimension $M$ from $7,904 \rightarrow \sim 4,000$, yielding **1.94× GEMM speedup** with **Cosine Similarity = 1.000000 (Lossless, QSNR = $\infty$)**.
  - **Dynamic Dispatch Overhead Warning**: Do NOT perform `torch.unique` or dynamic `index_select` inside the iterative sampling loop in Python. Python dispatch overhead (~2.5 ms/block) exceeds GEMM savings (~0.17 ms/block), slowing end-to-end generation from 14.9s to 28.7s.
  - **Fixed Grid Limitation**: 2x2 static grid pooling avoids dispatch overhead (<0.01 ms/block) but drops cosine similarity to ~0.47 on non-redundant spatial tokens.
* **Outlier-Preserving Mixed Precision (W4A8 / DiRotQ style)**: Protecting top 2% activation outlier channels preserves **44.55 dB activation QSNR**, avoiding the severe distortion caused by naive FP8/W4A4 quantization.
* **Timestep-Aware Precision Scheduling**: Running accelerated precision during noise-tolerant intermediate steps ($t \in [700, 100]$) while retaining full BF16 on initial layout ($t \in [1000, 700]$) and final micro-detail ($t \in [100, 0]$) steps.

## 5. Published Recipe & Artifacts
* **Fastpath GitHub Repo**: https://github.com/ruwwww/anima-fastpath-recipe (Public recipe with clean `TorchCompileModelAdvanced` + `--fast --use-ck-attention` flags and UI/API workflows).
* **Isolated CUDAGraph Research Service**: Running on port `9199` via systemd `comfyui-cudagraph.service` at `/mnt/data/comfy-profiling-worktree/comfy-isolated/` with symlinked models and custom nodes.
* **Finetuning & Captioning Pipeline**: Setup at `/mnt/data/finetune-anima/` with Kohya `sd-scripts` (`anima_train_network.py`) and GPU-accelerated ONNX WD14 tagger runner (`run_tagging_pipeline.py`).
  - **Dataset Scraping & Preparation**: Scraped via Safebooru/Gelbooru/Cheesechaser APIs into concept directory (e.g. `dataset/10_concept_name`).
  - **Caption Processing**: WD14 auto-tagging (`SmilingWolf/wd-swinv2-tagger-v3`), replacing generic character tags with the dedicated trigger word (e.g. `hebi nyodo, fate, 1girl, ...`).
  - **LoRA Training Parameters**: `networks.lora` (Rank 16, Alpha 16), `AdamW8bit`, `bf16`, `gradient_checkpointing`, native aspect-ratio bucketing (`min_bucket_reso=512, max_bucket_reso=1536`), `cache_latents` on WanVAE. Ensure ComfyUI background services are stopped to free GPU VRAM before launching.

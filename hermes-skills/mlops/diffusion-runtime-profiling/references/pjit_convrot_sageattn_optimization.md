# Bare-Metal DiT Optimization Recipe: ConvRot INT8, SageAttention & Fast Flags (Pyramid-JiT / P-JiT Case Study)

## Context & Motivation
P-JiT (Linum Pyramid-JiT) is a 2.18B parameter pixel-space diffusion transformer operating directly in RGB (x-prediction, no VAE), conditioned on concatenated Qwen3.5-4B full-attention layers (layers 7, 15, 27 -> 7680 features).
When deploying directly from upstream research code on consumer GPUs (e.g. RTX 5060 Ti 16GB), two critical roadblocks occur:
1. **Upstream FP32 Weight Assertion Trap**: Upstream loads weights as FP32 masters (8.72 GB) + unquantized Qwen3.5-4B (8.0 GB) = 16.7 GB, causing immediate out-of-memory.
2. **Dimension Constraints for ConvRot**: Unlike Cosmos/Anima where dimensions are multiples of 256, P-JiT uses $D=2944$, $FFN_{hidden}=5376$, $FFN_{w13}=10752$. Group size 256 fails ($2944 \% 256 = 128 \ne 0$).

## 1. ConvRot INT8 Group Size Mathematical Rule
Regular Hadamard matrices $H_N$ generated via recursive Kronecker product $H_N = H_{N/4} \otimes H_4$ require $N$ to be an integer power of 4 ($4, 16, 64, 256, 1024$).
- Dimension analysis for P-JiT:
  - $D = 2944$: $2944 / 64 = 46$ (clean integer)
  - $FFN_{hidden} = 5376$: $5376 / 64 = 84$ (clean integer)
  - $FFN_{w13} = 10752$: $10752 / 64 = 168$ (clean integer)
- **Rule**: For architectures where $D$ is not divisible by 256, select $N = 64$.
- **Kernel Dispatch**:
  ```python
  from comfy_kitchen import registry, DTYPE_TO_CODE
  quantizer = registry.get_implementation("quantize_int8_convrot_weight", backend="cuda")
  qweight, qscale = quantizer(weight.detach().contiguous(), 64)
  # Forward pass:
  code = DTYPE_TO_CODE[torch.bfloat16]
  out = torch.ops.comfy_kitchen.int8_linear(x, qweight, qscale, bias, code, True, 64)
  ```
- **Performance Benchmark**:
  - Linear $2944 \to 7936$ on RTX 5060 Ti: BF16 0.484 ms $\to$ ConvRot INT8 0.205 ms (**2.36x faster**).
  - Model VRAM reduction: Trunk weights drop by ~1.7 GB (static model VRAM from 7.35 GB $\to$ 5.66 GB).

## 2. SageAttention Varlen Integration
SageAttention (`sageattention`) provides quantized 8-bit attention with plug-and-play varlen interface:
- Signature compatibility with `flash_attn_varlen_func`:
  ```python
  from sageattention import sageattn_varlen
  # Accepts identical packed tensors and cumulative sequence lengths:
  x_packed = sageattn_varlen(
      q=pack(q),
      k=pack(k),
      v=pack(v),
      cu_seqlens_q=cu_seqlens,
      cu_seqlens_k=cu_seqlens,
      max_seqlen_q=int(max_seqlen_cpu),
      max_seqlen_k=int(max_seqlen_cpu),
  )
  ```
- No changes required to sequence packing or prefix masking logic.

## 3. ComfyUI `--fast` Flags for Reduced-Precision Accumulator
In PyTorch 2.5+, enabling lower-precision accumulation and SDP reduction yields significant speedups on modern Tensor Core architectures without quality degradation:
```python
# 1. Allow FP16 accumulation in cuBLAS GEMM (mimicking ComfyUI --fast)
torch.backends.cuda.matmul.allow_fp16_accumulation = True
# 2. Allow reduced precision math in SDPA
torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = True
if hasattr(torch.backends.cuda, "allow_fp16_bf16_reduction_math_sdp"):
    torch.backends.cuda.allow_fp16_bf16_reduction_math_sdp(True)
# 3. Enable cuDNN benchmark autotuning
torch.backends.cudnn.benchmark = True
# 4. Prevent CUDA allocator fragmentation
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
```

## 4. LLM Text Encoder 4-bit NF4 Quantization
To fit large text encoders (e.g. Qwen3.5-4B, 8 GB BF16) alongside the DiT on 16GB GPUs:
- Quantize via `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")`.
- Memory drops to **3.25 GB** VRAM.
- Extract multi-layer hidden states directly from `outputs.hidden_states[layer_idx + 1]` in native `bfloat16`.
- **Caution**: Qwen3.5 hybrid architecture contains fast linear attention (`fla`) layers whose Triton kernels require GPU execution; do not offload to CPU.

## 5. Empirical 4-Way Ablation Benchmark (RTX 5060 Ti 16GB)
Evaluated on Linum P-JiT (2.2B DiT), 512x512 resolution, 25 Euler steps, Seed 42:
| Configuration | Total Time | Per-Step Latency | Throughput | Peak VRAM | Delta / Speedup |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Baseline BF16 (SDPA)** | 13.54s | 541.5 ms/step | 1.85 it/s | 7,459 MB | 1.00x (Baseline) |
| **2. Fast Flags (Half-Acc + SDPA)** | 6.01s | 240.4 ms/step | 4.16 it/s | 7,460 MB | **2.25x speedup** |
| **3. SageAttention (BF16 + Sage)** | 6.52s | 261.0 ms/step | 3.83 it/s | 7,460 MB | **2.08x speedup** |
| **4. ConvRot INT8 + Sage + Fast** | 5.79s | 231.8 ms/step | 4.31 it/s | 5,738 MB | **2.34x speedup, -1.72 GB VRAM (-23%)** |

Key takeaway: Enabling PyTorch half-precision accumulator flags (`allow_fp16_accumulation` & `allow_bf16_reduced_precision_reduction`) gives an immediate >2.2x speedup on Blackwell/Ada GPUs. Combining with ConvRot INT8 ($H_{64}$) further cuts memory footprint by 1.72 GB while achieving peak 4.31 it/s generation speed.

---
name: comfy-kitchen-standalone-optimization
description: Use when using comfy-kitchen ops in standalone PyTorch.
category: mlops-inference
created: 2026-10-08
updated: 2026-10-08
---

# Comfy-Kitchen Standalone Optimization

Guide for extracting and using `comfy-kitchen` hardware-accelerated kernels, ConvRot INT8, and ComfyUI `--fast` runtime optimizations directly in pure PyTorch architectures (Diffusion Transformers, LLMs, Vision models) without ComfyUI runtime dependencies or custom node wrappers.

---

## 1. Core Principles

- **Zero UI Dependency**: Use low-level C++/CUDA operators (`torch.ops.comfy_kitchen.*`) and registries directly inside standard `torch.nn.Module`.
- **Hadamard Group Constraints**: ConvRot regular Hadamard transformation requires group size $N$ to be an integer power of 4 ($4, 16, 64, 256$). Check input dimension divisibility:
  $$\text{in\_features} \pmod N = 0$$
  *Example*: P-JiT ($D=2944$, $FFN=5376$, $W_{13}=10752$) is divisible by $64$ ($4^3$), but not $256$ ($4^4$).
- **Selective Retention Policy**:
  - Keep sensitive boundary layers in full/BF16 precision: embeddings, first and last blocks, AdaLN modulation routers, and final output heads.
  - Quantize heavy intermediate matrix multiplications: Attention $Q, K, V, O$ and MLP feed-forward projections ($W_{13}, W_2$).

---

## 2. ConvRot INT8 Implementation

### Quantizing Weights
```python
import torch
import comfy_kitchen

def quantize_weight_convrot(weight: torch.Tensor, group_size: int = 64):
    """
    Quantizes a floating-point [out_features, in_features] weight matrix.
    Uses 'eager' on CPU (for offline conversion) or 'cuda' for GPU tensors.
    """
    backend = "cuda" if weight.is_cuda else "eager"
    quantizer = comfy_kitchen.registry.get_implementation(
        "quantize_int8_convrot_weight", backend=backend
    )
    qweight, qscale = quantizer(weight.detach().contiguous(), group_size)
    return qweight.contiguous(), qscale.to(dtype=torch.float32).contiguous()
```

### Drop-In `ConvRotLinear` Module
```python
import torch
import torch.nn as nn
import comfy_kitchen

class ConvRotLinear(nn.Module):
    def __init__(self, qweight: torch.Tensor, qscale: torch.Tensor, bias: torch.Tensor = None, group_size: int = 64):
        super().__init__()
        self.register_buffer("qweight", qweight.detach().contiguous())
        self.register_buffer("qscale", qscale.detach().to(dtype=torch.float32).contiguous())
        self.register_buffer("bias", None if bias is None else bias.detach().contiguous())
        self.group_size = group_size
        self.dtype_code = comfy_kitchen.DTYPE_TO_CODE[torch.bfloat16] # 2

    @classmethod
    def from_linear(cls, linear: nn.Linear, group_size: int = 64):
        qweight, qscale = quantize_weight_convrot(linear.weight, group_size)
        bias = None if linear.bias is None else linear.bias.detach().clone()
        return cls(qweight=qweight, qscale=qscale, bias=bias, group_size=group_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # torch.ops.comfy_kitchen.int8_linear handles online activation rotation and INT8 GEMM
        return torch.ops.comfy_kitchen.int8_linear(
            x.contiguous(),
            self.qweight,
            self.qscale,
            self.bias,
            self.dtype_code,
            True,           # convrot enable
            self.group_size # regular Hadamard size
        )
```

### Dynamic Model Quantization Helper
```python
def quantize_model_convrot(model: nn.Module, target_layers=("q", "k", "v", "o", "w13", "w2"), group_size=64):
    for name, module in model.named_modules():
        for attr in dir(module):
            child = getattr(module, attr, None)
            if isinstance(child, nn.Linear) and attr in target_layers:
                if child.in_features % group_size == 0:
                    setattr(module, attr, ConvRotLinear.from_linear(child, group_size=group_size))
    return model
```

---

## 3. Half-Precision Accumulator & ComfyUI `--fast` Flags

Enabling reduced precision accumulation cuts Tensor Core latency by >2x on NVIDIA Ada / Blackwell (SM89 / SM120):

```python
def enable_fast_flags():
    # 1. Enable FP16/BF16 accumulation in cuBLAS matmul
    torch.backends.cuda.matmul.allow_fp16_accumulation = True
    torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = True

    # 2. Enable half-precision reduction in FlashAttention / SDPA math
    if hasattr(torch.backends.cuda, "allow_fp16_bf16_reduction_math_sdp"):
        torch.backends.cuda.allow_fp16_bf16_reduction_math_sdp(True)

    # 3. cuDNN benchmark for kernel autotuning
    torch.backends.cudnn.benchmark = True

    # 4. Memory fragmentation protection
    import os
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
```

---

## 4. SageAttention Standalone Dispatch

For models with sequence length $> 256$ tokens or dense attention grids, use `sageattention`:

```python
from sageattention import sageattn, sageattn_varlen

# Unpadded layout: [B, H, L, D]
def dispatch_sage_attn(q, k, v):
    return sageattn(q, k, v, tensor_layout="HND")

# Masked/Packed Varlen layout:
def dispatch_sage_varlen(q_packed, k_packed, v_packed, cu_seqlens, max_seqlen):
    return sageattn_varlen(
        q=q_packed,
        k=k_packed,
        v=v_packed,
        cu_seqlens_q=cu_seqlens,
        cu_seqlens_k=cu_seqlens,
        max_seqlen_q=max_seqlen,
        max_seqlen_k=max_seqlen
    )
```

---

## 5. Torch.Compile for Diffusion Samplers

When running Euler/Heun/RK4 iterative diffusion loops with static batch and resolution:
```python
# dynamic=False allows static CUDA graphs and kernel fusion
model = torch.compile(model, mode="reduce-overhead", dynamic=False)
```
Ensure you warm up with 1 dummy step before timing.

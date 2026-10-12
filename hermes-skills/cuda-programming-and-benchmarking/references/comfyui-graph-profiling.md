# Profiling & Runtime Graph Extraction Guide for ComfyUI & Diffusion Transformers

## Overview
ComfyUI's dynamic architecture (`ModelPatcher`, `WrapperExecutor`, dynamic dispatch) obscures exact computational paths and adds execution indirection. This reference defines how to deterministically capture computational graphs, isolate execution kernels, and benchmark Batched CFG vs Single Forward paths.

## Key Measurement Rules
1. **Measurement First ("What you can't measure, you can't optimize")**:
   - Never speculate on kernel speedup or dispatch overhead without CUDA event timing.
   - Use `torch.cuda.Event(enable_timing=True)` for microsecond-precision hardware timestamps.
   - Separate CPU dispatch time from GPU active kernel time.
2. **No STEM / Layperson Analogies**:
   - Present technical findings directly with raw FLOPs, bandwidth, latency tables, and exact tensor shapes.

## Capturing Runtime Computational Graphs
### 1. Symbolic FX Graph Capture
Capture pure tensor transformations without wrapper code:
```python
import torch
from torch.fx.experimental.proxy_tensor import make_fx

def capture_fx_graph(model, sample_args, sample_kwargs):
    with torch.no_grad():
        fx_graph = make_fx(model)(*sample_args, **sample_kwargs)
    return fx_graph
```

### 2. TorchDynamo Export / AOTAutograd
To inspect compiler IR, fused Triton kernels, and Inductor graph breaks:
```bash
export TORCH_COMPILE_DEBUG=1
export TORCH_LOGS="+inductor,+aot"
```

## Profiling Batched CFG vs Single Forward
ComfyUI evaluates Classifier-Free Guidance (CFG) by concatenating positive and negative conditioning along the batch dimension ($B=2$):
- **$B=1$ (Single / Uncond)**: Baseline single forward pass.
- **$B=2$ (Batched CFG)**: Evaluates cond and uncond simultaneously in a single tensor.
  - On compute-bound models (large spatial token dimensions, e.g. 3,952 tokens in $832 \times 1216$), GEMM operations reach ~99% Tensor Core compute ceiling on cards like RTX 5060 Ti.
  - Consequently, doubling batch size scales latency almost linearly (~2x time of B=1), yielding ~1.07 CFG steps/s.
- **Sequential CFG ($2 \times B=1$)**: Two separate $B=1$ forward passes.

## Trace Generation & Visual Inspection
Export Chrome trace for visualization on [ui.perfetto.dev](https://ui.perfetto.dev/):
```python
with torch.profiler.profile(
    activities=[
        torch.profiler.ProfilerActivity.CPU,
        torch.profiler.ProfilerActivity.CUDA,
    ],
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
) as prof:
    out = model_forward_fn(*inputs)
    torch.cuda.synchronize()

prof.export_chrome_trace("profile_trace.json")
```

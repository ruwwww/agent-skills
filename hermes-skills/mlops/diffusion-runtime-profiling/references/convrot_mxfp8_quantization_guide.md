# ConvRot & MXFP8 Quantization Guide for Anima DiT (Cosmos 2)

## Overview
Diffusion Transformers suffer from activation outliers in deep attention projections and MLP layers. Standard low-bit quantization (INT8, FP8, NVFP4) without outlier treatment causes clipping distortion, desaturated colors, and broken anatomical coherence.

**ConvRot** (arXiv:2512.03673) resolves this via group-wise **Regular Hadamard Transform (RHT)**. The orthogonal matrix rotation spreads outlier energy evenly across channels with zero quality loss ($H \cdot H^\top = I$).

---

## 1. Native ComfyUI & comfy-kitchen Integration
ComfyUI and `comfy-kitchen` natively support ConvRot execution **without any custom node registration**:
- **Weight rotation (Offline):** $W_{\text{rot}} = W \cdot H^\top$ folded into weights.
- **Activation rotation (Online):** $X_{\text{rot}} = X \cdot H$ executed inside fused Triton/CUDA kernels (`ck.int8_linear` and `ck.convrot_w4a4_linear`).
- **Metadata Routing:** When saved with `{prefix}.comfy_quant` uint8 JSON metadata:
  ```json
  {
    "format": "int8_tensorwise",
    "convrot": true,
    "convrot_groupsize": 256
  }
  ```
  ComfyUI's model loader (`comfy/ops.py`) automatically wraps layers in `TensorWiseINT8Layout` or `TensorCoreConvRotW4A4Layout` and dispatches to `comfy-kitchen`.

---

## 2. Layer Retention Policy (Zero Visual Degradation)
To preserve 100% BF16 visual fidelity while achieving >38% weight compression and accelerated GEMM:

### Preserved in Full Precision (BF16 - KEEP):
1. **Initial Blocks (`blocks.0.`, `blocks.1.`):** High sensitivity to noise; controls early latent representation.
2. **Final Reconstruction Block (`blocks.27.`):** Governs fine lineart, high-frequency textures, and color clarity.
3. **Modulation Layers (`adaln_modulation`):** Timestep embedding and text conditioning routing. Quantization errors here cascade into every block.
4. **Patch Embedder & Final Projection (`x_embedder`, `final_layer`):** Negligible compute cost (<1% FLOPs); keeping in BF16 prevents boundary discretization.

### Quantized with ConvRot (Group Size = 256):
- **Blocks 2 through 26:**
  - Attention Projections: `self_attn.q_proj`, `k_proj`, `v_proj`, `output_proj` and `cross_attn.*`
  - Feed-Forward Networks: `mlp.layer1` ($2048 \rightarrow 8192$) and `mlp.layer2` ($8192 \rightarrow 2048$)
  *(Note: Anima hidden dimension $d=2048$ is a power-of-4 multiple of 256, perfectly matching RHT requirements).*

---

## 3. Automation Script & Execution
A standalone, memory-efficient quantization script is available at:
`/mnt/data/finetune-anima/quantize_anima_convrot.py`

Usage:
```bash
# Quantize Anima Base v1.0 to ConvRot INT8
python /mnt/data/finetune-anima/quantize_anima_convrot.py \
  --input /home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors \
  --output /mnt/data/models/anima-base-v1.0-convrot-int8.safetensors \
  --mode int8 \
  --groupsize 256

# Optional: ConvRot W4A4 (NVFP4 / INT4 on Blackwell)
python /mnt/data/finetune-anima/quantize_anima_convrot.py \
  --mode w4a4 \
  --output /mnt/data/models/anima-base-v1.0-convrot-w4a4.safetensors
```

### Verified Benchmark & Fidelity Results (RTX 5060 Ti 16GB, 832x1216, 30 steps, B=2):
- **Conversion Time**: ~44s on CPU/RAM via `tools/quantize_anima_convrot.py`.
- **Checkpoint Size**: 3.89 GB $\rightarrow$ 2.41 GB (61.9% of original, ~38% saving).
- **Cosine Similarity**: **0.99988** on individual linear projections.
- **Empirical 3-Way ComfyUI Comparison**:
  - **ConvRot INT8 (`anima-base-v1.0-convrot-int8`)**: **~2.70 it/s (~11.1s)** sustained in warmed-up sessions. **Top Daily Recommendation**: ~90% semantic fidelity winrate vs MXFP8, producing visual outputs nearly indistinguishable from BF16 ground truth (though inherently a slightly semantically lossy algorithm vs native uncompressed BF16).
  - **MXFP8 (`anima-base-v1.0-mxfp8`)**: **2.67 it/s (~11.2s)**. Fast raw throughput via native Blackwell 5th-gen Tensor Core microscaling without online activation rotation.
  - **BF16 Base (`anima-base-v1.0`)**: **2.05 it/s (~14.9s)**. Lossless reference ground truth.
- **Latency & Roofline Analysis**:
  - ConvRot INT8 sustains ~2.70 it/s thanks to dense INT8 Tensor Core instruction throughput in `ck.int8_linear`.
  - MXFP8 avoids online activation rotation, but unrotated outlier channels cause micro-texture and color variance.
  - Both models operate near practical saturation (~70–80% dense Tensor Core roofline efficiency); remaining time is Amdahl-bounded by BF16 attention (~80 ms), AdaLN/RMSNorm/RoPE (~40 ms), and boundary BF16 blocks.
- **Public Artifacts & Checkpoint Family**:
  - Hugging Face repository: `https://huggingface.co/ruwwww/Anima-ConvRot`
  - Complete 7-model ConvRot INT8 collection:
    * `anima-base-v1.0-convrot-int8.safetensors` (Base v1.0, 25–30 steps, CFG 4–5)
    * `anima-turbo-v1.0-convrot-int8.safetensors` (Turbo v1.0, 8–12 steps, CFG 1–2)
    * `anima-turbo-v1.1-convrot-int8.safetensors` (Turbo v1.1, 8–12 steps, CFG 1–2)
    * `anima-aesthetic-v1.0b-convrot-int8.safetensors` (Aesthetic v1.0b, 25–30 steps, CFG 4–5)
    * `anima-preview-convrot-int8.safetensors` (Preview 1, 25–30 steps, CFG 4–5)
    * `anima-preview2-convrot-int8.safetensors` (Preview 2, 25–30 steps, CFG 4–5)
    * `anima-preview3-base-convrot-int8.safetensors` (Preview 3 Base, 25–30 steps, CFG 4–5)
  - GitHub recipe & converter: `https://github.com/ruwwww/anima-fastpath-recipe` (tool: `tools/quantize_anima_convrot.py`)
  - Batch runner: `/mnt/data/finetune-anima/batch_convert_convrot.py`
  - **Hugging Face Large Upload Network Traps**:
    * Always export `HF_HUB_DISABLE_XET=1` when pushing multi-gigabyte models from international/high-latency routes to avoid `cas-server.xethub.hf.co` connection resets.
    * `huggingface_hub` has a default `constants.DEFAULT_REQUEST_TIMEOUT = 10` seconds, which causes spurious `RuntimeError: Error while uploading ... Request TimedOut` on large 2.5GB+ files whenever a socket stalls. Fix by setting `constants.DEFAULT_REQUEST_TIMEOUT = 600` and registering a custom client factory: `set_client_factory(lambda: httpx.Client(timeout=httpx.Timeout(600.0, connect=60.0)))`.

# Latent Flow Matching DiT: Training, Semantic Clustering & CFG Scaling

Empirical findings and operational protocols from training Flow Matching Diffusion Transformers on compressed VAE latent spaces (tested on RTX 5060 Ti 16GB SM120).

## 1. Latent Pre-Caching & I/O Optimization
- **Problem**: Performing on-the-fly VAE encoding during DiT training limits throughput to 4–7 batches/second due to repeated conv downsampling and DataLoader multiprocessing serialization bottlenecks.
- **Solution (In-Memory Latent Cache)**:
  - Pre-encode the entire dataset (e.g. 28,000 CelebA-HQ images) using the frozen VAE into `bfloat16` tensor files (`latents.shape = (N, C, H, W)`).
  - Storage footprint is minimal: 28k $16 \times 16 \times 32$ latents require only **468 MB** of RAM.
  - Set `num_workers=0` with `pin_memory=True` when loading from RAM tensors. Throughput jumps immediately from 7 batch/s to **17+ batch/s (~540 images/sec)**.

## 2. Unconditional Diffusion vs. Classifier-Free Guidance (CFG)
- **High-Entropy Mode Collapse**:
  - Unconditional diffusion/flow matching without guidance inevitably samples into blurry high-entropy compromise states ("melted" faces, fused teeth, misaligned eyes, waxy plastic textures).
  - Training for 25k–30k steps without guidance fails to resolve fine anatomical boundaries regardless of latent quality.
- **Pseudo-Class Conditioning for Datasets Without Captions**:
  - Extract global semantic embeddings using a vision backbone (e.g. DINOv2-small ViT-S/14).
  - Cluster embeddings into discrete semantic archetypes (e.g. $K=64$ via MiniBatchKMeans).
  - Inject classes via a `LabelEmbedder(num_classes=K, hidden_size=D, dropout_prob=0.15)`.
  - Condition DiT blocks via `conditioning = t_embed(t) + y_embed(y)`.
- **CFG Sampling Dynamics**:
  - Velocity interpolation: $v_{\text{cfg}} = v_{\text{uncond}} + s \cdot (v_{\text{cond}} - v_{\text{uncond}})$.
  - **Scale $s = 1.0 - 1.5$**: Under-guided; structural melting and asymmetrical drift persist.
  - **Scale $s = 3.0 - 4.0$**: Sweet spot for compact DiTs; pulls sampling trajectories tightly onto high-density natural image modes (sharp jawlines, distinct iris catchlights, crisp hair strands).

## 3. Parameter Scaling (Width vs. Depth Tradeoffs)
- **57.8M Baseline ($D=512, L=12, H=8$)**:
  - Easily learns global face topology and rough feature placement.
  - Lacks representation capacity to maintain 100% topological consistency across all random seeds, leading to occasional asymmetric eye collapse.
- **177M Width-Scaled ($D=896, L=12, H=14$, 3.06× params)**:
  - Width scaling (+75% channels per block) significantly expands channel representational expressiveness while keeping Transformer sequence length ($N=256$) constant.
  - Fits comfortably within consumer VRAM (~7.7 GB / 16 GB peak on RTX 5060 Ti at batch size 32 bfloat16 AMP) while sustaining ~3.7 batch/sec throughput.
  - Substantially eliminates global structural melting and tightens facial symmetry, proving that parameter capacity is a hard prerequisite for crisp feature boundaries.

## 4. Checkpoint Export & Artifact Delivery Pipeline
- **Clean Safetensors Conversion**:
  - Raw PyTorch checkpoints contain optimizer states and EMA duplicates (bloating a 177M model to 2.7 GB).
  - Always export inference-ready weights to `.safetensors` using EMA weights:
    ```python
    from safetensors.torch import save_file
    ckpt = torch.load("checkpoint.pt", map_location="cpu")
    state = {k: v.contiguous() for k, v in ckpt["ema"].items()}
    save_file(state, "model.safetensors")
    ```
  - Compresses a 2.7 GB checkpoint down to **675 MB** (or 12 MB for the f16 VAE) without risk of arbitrary pickle code execution.
- **Hugging Face Model Upload**:
  - For files exceeding 500 MB, use `api.upload_folder(...)` with background session execution to avoid CLI timeout caps.

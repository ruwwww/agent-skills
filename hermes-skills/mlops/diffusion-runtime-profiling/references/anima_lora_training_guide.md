# Anima DiT LoRA Training & Validation Guide (Kohya sd-scripts)

## Overview & Architecture
Anima Base v1.0 is a 2B Diffusion Transformer (DiT) based on Cosmos 2 / MiniTrainDIT with Rectified Flow velocity matching.
- DiT: 28 transformer blocks, 16 attention heads, model width 2048, cross-attention width 1024.
- Text Encoder: Qwen3-0.6B Base (`/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors`).
- VAE: Qwen-Image 2D VAE (`/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors`, 16 latent channels, 8x spatial downscale).

## Critical Training Pitfalls & Proven Fixes

### 1. The SageAttention Backward Pass Trap
- **Symptom**: Trained LoRA produces abstract oil painting / blurred impasto textures when loaded in ComfyUI, even at low strengths (e.g. 0.3).
- **Root Cause**: In `sd-scripts`, `library/attention.py` implements SageAttention for **inference only**. During training, SageAttention lacks autograd backward formulas, silently producing zero gradients for all $Q$, $K$, and $V$ attention projections. Only MLPs and output projections receive updates, causing complete decoupling of prompt tokens from image features.
- **Rule**: ALWAYS use `--attn_mode="torch"` for training. SageAttention can only be used during inference.

### 2. VAE Selection
- Anima requires Qwen-Image VAE (`--vae` pointing to `qwen_image_vae.safetensors`) with the `--qwen_image_vae_2d` flag.
- Never use Wan2.1 VAE or generic SD VAEs.

### 3. Alpha & Learning Rate Scaling
- Kohya calculates scaling as: $\text{scale} = \alpha / \text{dim}$.
- Using $\alpha = 16$ with $\text{dim} = 16$ at $\text{LR} = 1\times 10^{-4}$ causes aggressive over-adaptation ($\text{scale} = 1.0$), pushing delta weight norms past 3.3.
- **Recommended**:
  - `network_dim=8`, `network_alpha=1.0` (scale = 0.125), `learning_rate=1e-4` to `2e-4`.
  - If using `network_alpha=16`, reduce `learning_rate` to `1e-5`.

### 4. Text Encoder Scope
- Training Qwen 3 text encoder concurrently without a separate micro-LR or proper mapping destroys text representations.
- Pass `--network_train_unet_only` for character LoRA to isolate learning to the DiT blocks.

### 5. Checkpoint Key Conversion for ComfyUI
- Kohya outputs: `lora_unet_blocks_<N>_<module>...`
- ComfyUI Cosmos/Anima loader expects: `diffusion_model.blocks.<N>.<module>...`
- Convert using:
  ```bash
  python /mnt/data/finetune-anima/sd-scripts/networks/convert_anima_lora_to_comfy.py \
    <input_lora.safetensors> <output_comfy.safetensors>
  ```

### 6. Clean ComfyUI Acceptance Pipeline
- When validating new LoRA weights, bypass `TorchCompileModelAdvanced` or custom attention hooks:
  ```
  UNETLoader (anima-base-v1.0.safetensors)
      -> LoraLoaderModelOnly (converted LoRA, strength 0.4 - 0.8)
      -> KSampler (er_sde, simple, 30 steps, cfg 4.0)
      -> VAEDecode (qwen_image_vae.safetensors)
  ```

## Reference Script (`train_lora_v2.sh`)
```bash
python anima_train_network.py \
  --pretrained_model_name_or_path="/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors" \
  --train_data_dir="/mnt/data/finetune-anima/data_root" \
  --output_dir="/mnt/data/finetune-anima/output_lora" \
  --output_name="anima_char_lora" \
  --network_module="networks.lora_anima" \
  --network_dim=8 \
  --network_alpha=1.0 \
  --network_train_unet_only \
  --learning_rate=2e-4 \
  --lr_scheduler="cosine" \
  --lr_warmup_steps=10 \
  --max_train_epochs=10 \
  --save_every_n_epochs=2 \
  --mixed_precision="bf16" \
  --save_precision="bf16" \
  --seed=42 \
  --resolution="832,1216" \
  --enable_bucket \
  --min_bucket_reso=512 \
  --max_bucket_reso=1536 \
  --cache_latents \
  --gradient_checkpointing \
  --optimizer_type="AdamW8bit" \
  --caption_extension=".txt" \
  --keep_tokens=2 \
  --vae="/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors" \
  --qwen_image_vae_2d \
  --qwen3="/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors" \
  --attn_mode="torch"
```

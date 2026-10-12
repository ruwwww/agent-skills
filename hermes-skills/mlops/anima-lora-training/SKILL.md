---
name: anima-lora-training
description: "Use when training LoRA for Anima DiT. Pipeline and recipes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [anima, dit, lora, finetune, kohya, sd-scripts, diffusion, anime]
---

# Anima DiT LoRA Training Playbook

Comprehensive end-to-end guide for training high-fidelity character and style LoRAs on the Anima Cosmos 2 DiT architecture using `sd-scripts` (Kohya).

## 1. Environment & Model Assets

- **Python Binary:** `/home/kuroko/.conda/envs/ai/bin/python`
- **sd-scripts Path:** `/mnt/data/finetune-anima/sd-scripts/`
- **Diffusion DiT:** `/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors`
- **Text Encoder:** `/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors` (Qwen3-0.6B Base)
- **VAE:** `/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors` (Qwen-Image VAE)

## 2. Critical Training Invariants & Rules

1. **Attention Mode:**
   - Always set `--attn_mode="torch"` (native PyTorch SDPA).
   - **DO NOT USE `--attn_mode="sageattn"`**: SageAttention does not have an autograd backward implementation in sd-scripts; training with it results in bitwise-zero weights for all Q/K/V projections and causes severe noise/impasto artifacts.
2. **Target Modules & Style Bleeding Prevention:**
   - For character LoRAs, use `--network_train_unet_only`.
   - To prevent the LoRA from overwriting the clean anime rendering aesthetic of Anima with the dataset artist's heavy style (overcooking), exclude MLP layers:
     `--network_args "exclude_patterns=['.*mlp.*']"`
   - Cross-attention projections bind character tokens to visual latents. Keeping MLPs frozen preserves the base model's native aesthetic.
3. **Rank, Alpha, and Learning Rate Scaling:**
   - Standard configuration: `--network_dim=8` or `16`, `--network_alpha=1.0`.
   - Learning rate: `3e-5` to `5e-5` with `AdamW8bit` for small datasets (10–30 images).
   - Never pair `network_alpha=16` with high learning rates like `2e-4`, as the adapter scale causes severe over-adaptation.
4. **VAE Configuration:**
   - Always include `--qwen_image_vae_2d` when using the official Qwen-Image VAE.
5. **VRAM Freeing:**
   - Free GPU memory before training: `systemctl --user stop comfyui.service comfyui-cudagraph.service`.

## 3. Dataset Preparation & Augmentation Rules

1. **Folder Hierarchy:**
   ```
   data_root/
     └── 10_<concept_name>/
           ├── img01.jpg
           ├── img01.txt
           └── ...
   ```
2. **Tagging & Shuffling Protocol:**
   - Prepend `<trigger_word>, <series_name>` to the very beginning of each `.txt` caption.
   - Set `--keep_tokens=1` so the trigger word is never randomized in position.
   - Enable `--shuffle_caption` for Danbooru/tag-based datasets to prevent positional overfitting. (Do not enable for prose/natural language).
   - Tag all background elements, artist quirks (e.g. `monochrome`, `lineart`, `sketch`), clothing details, and generic attributes so the trigger word only absorbs the unique character identity.
   - **Asymmetry Check:** Only enable `--flip_aug` if the character design is completely symmetrical. Disable if they have single-sided accessories, asymmetrical hairstyles (e.g. hair over one eye), or localized marks/tattoos.

## 4. Optimizer Alternatives: AdamW8bit vs Prodigy

- **Standard Stable Recipe (Empirically Verified):**
  - Optimizer: `AdamW8bit`
  - Learning Rate: `3e-5` to `5e-5` (constant or cosine)
  - `network_dim=8` or `16`, `network_alpha=1.0`
  - Exclude MLPs: `--network_args "exclude_patterns=['.*mlp.*']"`
- **Adaptive D-Adaptation Recipe (Civitai Community):**
  - Optimizer: `Prodigy` (with `--learning_rate=1.0`, `--lr_scheduler="cosine"`, `--weight_decay=0.1`)
  - With Prodigy, setting `network_alpha == network_dim` (e.g. 8/8 or 16/16) scales properly as Prodigy handles the adaptive coefficient dynamically.

## 5. Checkpoint Selection & Testing Protocol

- Track `loss/epoch_average` (e.g. via TensorBoard or log files) until it reaches the **Loss Floor** (plateaus and oscillates within a narrow band).
- Test the lowest-loss epoch alongside earlier checkpoints (where loss briefly dipped). Earlier epochs often generalize better without prompt bleed or stiff poses.
- Test with 5–10 diverse prompts (varying outfits and settings) using a fixed seed, without ADetailer/FaceDetailer, to judge raw anatomical consistency and prompt flexibility.

## 6. Decoupled Architecture, Entanglement & Trigger Selection Guide

### A. The Core Principle of Captioning & Entanglement
> **"What is written in the caption is DECOUPLED (separated) from the trigger token. What is HIDDEN/OMITTED from the caption BINDS PERMANENTLY to the trigger token."**

1. **Preventing Concept Dissolution (The "Random Human" Pitfall):**
   - If you tag every single signature attribute of a character in the dataset captions (e.g. `turquoise_skin`, `blue_skin`, `pointy_ears`, `orange_hair`, `blue_eyes`), cross-attention gradients get absorbed by those individual tag embeddings.
   - The primary trigger (e.g. `mira_nova`) is stripped of its identity and becomes an empty container. Prompting `mira_nova` alone will fall back to the base model's default prior (a generic pale human girl).
   - **Fix:** Omit core anatomical/alien/fantasy identifiers (`colored_skin`, `pointy_ears`, signature eye/hair colors) from captions across the entire dataset. The model is forced to attribute those features solely to the primary trigger token.

2. **Attire Decoupling (Preventing Outfit Sticking / Armor Bleed):**
   - When a character frequently wears a signature outfit (e.g. Inque's liquid bodysuit, Mira Nova's Pulsar-400 armor, Aya's Green Lantern chestplate):
     - Curate signature armor/attire images into a dedicated subset/folder.
     - Tag the outfit with explicit, modular tokens (e.g. `pulsar_suit`, `space_ranger_suit`, `white_armor`, `chestplate`, `pauldrons`).
     - **Critically:** Completely remove all armor/suit tags from casual, swimsuit, or nude images.
     - This ensures the model learns that the armor is a removable layer, enabling 100% clean clothing swaps and nude renders without armor collars or pauldrons leaking onto bare shoulders.

3. **Compound Binding (`keep_tokens = 2`):**
   - If using `keep_tokens = 1`, shuffling (`shuffle_caption = true`) will throw attire tokens far back into the token sequence (e.g. position 12+), heavily diluting their activation strength.
   - Use `keep_tokens = 2` and structure captions as:
     - Armor subset: `char_name, char_armor, ...` (e.g. `mira_nova, pulsar_suit, ...`)
     - Casual/nude subset: `char_name, solo, ...` (or `char_name, char_casual, ...`)
   - Avoid long hyphenated phrases that fragment into many subwords in the Qwen tokenizer (e.g. `pulsar-400_enviro-suit` splits into 11 subwords; use clean concise tokens like `pulsar_suit` which splits into only 2).

4. **Artist Style Interference vs Exotic Features:**
   - Dominant anime artist tags (e.g. `@kurotsuki machi`) strongly bias generation toward fair/porcelain human skin.
   - When generating characters with exotic traits (cyan/blue skin, green skin, mechanical joints):
     - Ban human skin in the negative prompt: `human skin, peach skin, fair skin`.
     - Or explicitly re-anchor the feature in the positive prompt alongside the artist: `char_name, blue skin, @kurotsuki machi, ...`.

## 7. Unified End-to-End Autonomous Bash Pipeline

Untuk eksekusi yang fully autonomous dan AI agent-friendly, gunakan unified script:
`/mnt/data/finetune-anima/run_anima_lora_pipeline.sh`

Script ini menggabungkan seluruh tahapan dalam satu eksekusi:
1. **Auto-Tagging:** Menjalankan WD14 ONNX tagger otomatis jika file `.txt` belum ada.
2. **Curation & Sparse Tagging:** Memfilter gambar multi-karakter dan menyerap atribut visual spesifik ke dalam trigger word.
3. **VRAM Safety:** Menghentikan ComfyUI sebelum training, menggunakan trap cleanup agar ComfyUI otomatis di-restart saat script selesai/gagal.
4. **Prodigy + Selective Checkpointing:** 5 epochs, Prodigy lr=1.0, count=12 selective blocks (1.9s/step, ~12.4GB VRAM).
5. **Auto-Convert:** Mengonversi checkpoint safetensors ke format ComfyUI Cosmos DiT (`/home/kuroko/ComfyUI/models/loras/`).
6. **Auto-Generate Verification:** Menunggu port 8188 ComfyUI siap, lalu men-generate sampel verifikasi dengan sampler `er_sde`, **30 steps**, CFG 4.0, strength 1.0 (dengan style prefix `@ratatatat74`).

### CLI Command Example:
```bash
/mnt/data/finetune-anima/run_anima_lora_pipeline.sh \
  --concept belobetty \
  --trigger "belo betty, one piece" \
  --epochs 5 \
  --steps 30 \
  --style "@ratatatat74"
```

### Options:
- `-c, --concept <name>`: Nama konsep (misal `belobetty`, `burstinatrix`).
- `-t, --trigger "<trigger>"`: Trigger tokens (misal `"belo betty, one piece"`).
- `-s, --staging <dir>`: Folder staging (default `/mnt/data/finetune-anima/staging_images/<concept>`).
- `-e, --epochs <N>`: Jumlah epoch (default 5).
- `-r, --repeats <N>`: Repeats per epoch (default 4).
- `--steps <N>`: Langkah sampling ComfyUI (default 30).
- `--style "<style>"`: Style modifier prompt (default `@ratatatat74`).
- `--test-prompt "<prompt>"`: Custom prompt untuk verifikasi.
- `--skip-tag`: Lewati WD14 auto-tagging.
- `--skip-train`: Lewati training (hanya run curation/conversion/render).
- `--skip-gen`: Lewati render ComfyUI.


## 8. Fastpath Recipe & Persistent Runtime Daemon (Phase 2)

A hardware-optimized, persistent in-VRAM architecture for **RTX 5060 Ti 16GB**. The base DiT (28 blocks), text encoder, and VAE remain resident in VRAM across training jobs. Subsequent jobs achieve **zero-second model reload** and **zero JIT recompilation** via in-place LoRA weight re-initialization.

### A. Persistent Daemon Commands
Database: `/mnt/data/finetune-anima/runtime_daemon.sqlite3`

```bash
# Start background worker daemon (if not already running)
PYTHONPATH="/mnt/data/finetune-anima/sd-scripts:/mnt/data/finetune-anima/anima-lora-fastpath-recipe" \
/home/kuroko/.conda/envs/ai/bin/python -m runtime \
  --database=/mnt/data/finetune-anima/runtime_daemon.sqlite3 \
  run \
  --trainer=/mnt/data/finetune-anima/sd-scripts/anima_train_network.py \
  --workdir=/mnt/data/finetune-anima/sd-scripts \
  --engine-cache-root=/mnt/data/finetune-anima/engine_cache \
  --warm \
  --poll-seconds=1.0

# Submit a job JSON
PYTHONPATH="/mnt/data/finetune-anima/anima-lora-fastpath-recipe" \
/home/kuroko/.conda/envs/ai/bin/python -m runtime \
  --database=/mnt/data/finetune-anima/runtime_daemon.sqlite3 \
  submit job.json --preflight

# Check queue status
python -m runtime --database=/mnt/data/finetune-anima/runtime_daemon.sqlite3 list
python -m runtime --database=/mnt/data/finetune-anima/runtime_daemon.sqlite3 status <job_id>
```

### B. Job JSON Template
```json
{
  "schema_version": 1,
  "job_id": "<concept_name>",
  "priority": 10,
  "engine_policy": "allow_build",
  "trainer_argv": [
    "--pretrained_model_name_or_path=/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors",
    "--train_data_dir=/mnt/data/finetune-anima/data_root_<concept_name>/10_<concept_name>",
    "--output_dir=/mnt/data/finetune-anima/output_lora/<concept_name>",
    "--output_name=<concept_name>_lora",
    "--network_module=networks.lora_anima",
    "--network_dim=16",
    "--network_alpha=16.0",
    "--network_train_unet_only",
    "--selective_checkpointing=count",
    "--checkpoint_blocks=1",
    "--compile",
    "--compile_mode=default",
    "--compile_cache_size_limit=32",
    "--fused_lora",
    "--fused_mlp",
    "--fused_mlp_storage=fp8",
    "--fused_mlp_fp8_backend=triton",
    "--fused_mlp_fp8_direct_backward",
    "--attn_mode=torch",
    "--optimizer_type=Prodigy",
    "--learning_rate=1.0",
    "--lr_scheduler=cosine",
    "--lr_warmup_steps=10",
    "--optimizer_args", "weight_decay=0.1", "decouple=True", "use_bias_correction=True", "d_coef=1.0",
    "--max_train_epochs=5",
    "--save_every_n_epochs=1",
    "--mixed_precision=bf16",
    "--save_precision=bf16",
    "--seed=2026",
    "--cache_latents",
    "--cache_latents_to_disk",
    "--vae=/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors",
    "--qwen_image_vae_2d",
    "--qwen3=/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors",
    "--resolution=832,1216",
    "--enable_bucket",
    "--min_bucket_reso=512",
    "--max_bucket_reso=1536",
    "--bucket_reso_steps=32",
    "--caption_extension=.txt",
    "--caption_tag_dropout_rate=0.05",
    "--caption_dropout_rate=0.1",
    "--shuffle_caption",
    "--keep_tokens=1",
    "--persistent_session"
  ],
  "metadata": {
    "engine_config": {
      "trainer": "anima",
      "model": "/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors",
      "network_dim": 16,
      "mixed_precision": "bf16",
      "compile": true,
      "compile_mode": "default",
      "fused_lora": true,
      "fused_mlp": true,
      "fused_mlp_storage": "fp8",
      "fused_mlp_fp8_backend": "triton",
      "fused_mlp_fp8_direct_backward": true,
      "checkpoint_blocks": 1
    }
  }
}
```

## 5. Conversion to ComfyUI Native Format

Before loading into ComfyUI's standard `LoraLoader` or `LoraLoaderModelOnly`, convert the safetensors file:

```bash
/home/kuroko/.conda/envs/ai/bin/python /mnt/data/finetune-anima/sd-scripts/networks/convert_anima_lora_to_comfy.py \
  /mnt/data/finetune-anima/output_lora/my_anima_lora.safetensors \
  /home/kuroko/ComfyUI/models/loras/my_anima_lora_comfy.safetensors
```

## 6. ComfyUI Testing

- Start ComfyUI: `systemctl --user start comfyui.service`.
- Connect: `UNETLoader -> LoraLoaderModelOnly(strength=0.6) -> KSampler(steps=30, cfg=4.0, sampler_name='er_sde', scheduler='simple') -> VAEDecode -> SaveImage`.

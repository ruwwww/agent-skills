# LoRA Training Curation, Epoch Overfitting & Prompt Delivery (2026-09-22)

## 1. Direct Prompt Delivery vs Auto-Generation Friction
- **User Signal**: "training is done, no need to run generation. just give me the prompt to run myself" -> "give me the prompt damn it"
- **Rule**: When the user asks for prompts, deliver the text block, parameter settings (sampler, steps, cfg), and negative prompt directly in the reply. Never trigger automated generation scripts or ComfyUI `/prompt` queue calls unless explicitly instructed to generate.

## 2. LoRA Checkpoint Dropdown Visibility & Intermediate Conversions
- **User Signal**: "kok gada di comfyui!?"
- **Problem**: When a LoRA finishes training, the trainer writes intermediate checkpoints (`-000001` through `-000010`) in raw sd-scripts format under `/mnt/data/finetune-anima/output_lora/`. If only the final checkpoint is converted, earlier candidate epochs do not appear in ComfyUI's `LoraLoader` dropdown.
- **Workflow**: Immediately batch-convert candidate epochs (Epochs 5 through 9) using `convert_anima_lora_to_comfy.py` into `/home/kuroko/ComfyUI/models/loras/` with proper permissions (`chmod 664`) so they are instantly accessible upon browser refresh.

## 3. Empirical Overfitting Dynamics (Epoch 10 vs Epoch 5)
- **Large Curated Datasets (50+ images, e.g. SMT Asherah)**:
  - 5,000 steps (10 repeats x 10 epochs).
  - Can sustain full 10 epochs without burning; high anatomical and tattoo fidelity.
- **Medium/Small Datasets (20–40 images, e.g. Mata Hari, Hirara, Kekko Kamen)**:
  - Often experience severe overfitting at Epoch 10 (stiff poses, artifacting, inability to compose novel scenes).
  - **Optimal sweet spot is Epoch 5** (e.g. ~1,250 steps for Mata Hari, ~3,600 steps for Hirara).
  - Always evaluate Epoch 5 first before assuming the final epoch is superior.

## 4. Cryptid / Collision-Free Trigger Naming
- If a character or franchise already exists in Danbooru / base model training data, canonical names trigger semantic prior bleeding (e.g. `kekko_kamen` colliding with pretraining priors).
- Use synthetic / cryptid trigger words (e.g. `kekkocrypt`, `sashakara`, `atlantmera`) at token 0 (`--keep_tokens=1`).
- For modular features (e.g. unmasking), isolate them in a subfolder and tag with an explicit key tag (`unmasking`) so the concept can be toggled on/off modularly during inference.
- For excluded features (e.g. cropped weapons/knives), completely remove all related tags from captions.

## 5. Hugging Face Curated Registry (`ruwwww/diffusion_loras`)
- Structure:
  `diffusion_loras/anima/<character_name>/<character_name>_<curated_epoch>.safetensors`
- Never upload all 10 raw epochs to the public hub. Only upload the tested, sweet-spot epoch per character (typically Epoch 5 for 20–40 image datasets).
- Include individual `README.md` per model with trigger words, character traits, recommended sampler settings (`er_sde`, 30 steps, CFG 4.0), and clean, pure character prompt examples.
- **Do NOT force artificial style anchors**: Do not inject `@ratatatat74` or artist style anchors into model card prompts or registry READMEs unless specifically requested by the user. Keep character prompts pure and modular.

## 6. VRAM Freeing & ComfyUI Service Coexistence
- **Rule**: Never kill or stop `comfyui.service` or `comfyui-cudagraph.service` when starting training.
- Free VRAM via the ComfyUI API endpoint:
  `curl -s -X POST http://127.0.0.1:8188/free -H "Content-Type: application/json" -d '{"unload_models": true, "free_memory": true}'`
- This drops VRAM immediately to ~130–280 MiB idle, allowing the persistent daemon (`anima-runtime`) to run training without OOM while preserving user UI/browser sessions.

## 7. Fast WD14 Tagging via Direct ONNX Runtime
- The CLI wrapper `tag_images_by_wd14_tagger.py` imports diffusers, flax, torch, and performs remote hub checks, taking 25–40s and frequently triggering terminal execution timeouts (180s) on larger folders.
- Instead, use a direct Python snippet loading `onnxruntime.InferenceSession` with `/home/kuroko/wd14_tagger_model/SmilingWolf_wd-swinv2-tagger-v3/model.onnx` and `selected_tags.csv` with `CUDAExecutionProvider`. It tags 25+ images in under 3 seconds without torch/diffusers import latency.

## 8. Canonical Manhwa & Pop-Culture Verification
- Verify character identities before tagging or documenting: e.g. "Mia's Back" refers to the webtoon/manhwa title featuring Cha Mia (차미아), not a literal anatomical back study.
- Cross-check canonical character traits (e.g. Cha Mia: straight bangs, single fang `:d`, ear piercings, black choker, sporty track jacket, red eyeliner) rather than generic tags.

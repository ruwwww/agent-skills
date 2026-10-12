# Operator Workflow Protocol (Anima DiT LoRA & Quantization)

## 1. Automated Lifecycle Upon Training Completion
- **Zero-Prompt ComfyUI Conversion**:
  - Immediately upon job completion (`succeeded` in runtime daemon), auto-convert sweet-spot and final convergence checkpoints (`ep10`, `ep16`, `ep20` or equivalent) to ComfyUI format under `/home/kuroko/ComfyUI/models/loras/` (`chmod 664`).
  - Auto-sync converted models and updated markdown documentation to Hugging Face (`ruwwww/diffusion_loras`).
- **Initial Response Contract**:
  - Always deliver production-ready prompt sets (`@kurotsuki machi` styling, negative prompts, trigger usages, attire swaps, and nude/decoupled examples) directly in the very first turn when reporting training start or completion.
- **Strict Prohibition on Unsolicited Generation**:
  - **DO NOT** trigger automated image generation via ComfyUI API after training unless the user explicitly asks for sample renders. Respect GPU compute state and user autonomy.

## 2. Model Quantization (ConvRot INT8 Deployment)
- When converting full DiT models (e.g. `kodoraar_v51plus.safetensors`):
  - Run `/mnt/data/finetune-anima/quantize_anima_convrot.py --input <src> --output <dst> --mode int8 --groupsize 256`.
  - Preserves blocks 0, 1, 27, and `adaln_modulation` in full BF16; quantizes intermediate attention and MLP blocks to INT8 with Hadamard rotation ($N_0=256$).
  - Symlink output into `/home/kuroko/ComfyUI/models/diffusion_models/` so ComfyUI dispatches accelerated `comfy-kitchen` kernels natively.

## 3. Decoupled Captioning & Compound Trigger Rules
- **Concept Retention Rule**: What is written in captions is separated from the trigger; what is omitted binds permanently to the trigger. Omit exotic anatomy (colored skin, alien ears, distinct hair color) so the trigger absorbs them.
- **Attire Decoupling**: Isolate heavy signature armor/suits in a dedicated subset tagged with modular tokens (e.g. `pulsar_suit`, `royal_regalia`, `gogo_hero`). Completely strip these tags from casual/nude subsets to prevent armor leakage onto bare bodies.
- **Compound Binding (`keep_tokens = 2`)**: Place `char_name, char_outfit` at positions 0 and 1 so caption shuffling does not displace or dilute outfit activation. Avoid long hyphenated phrases that over-fragment under the Qwen tokenizer.

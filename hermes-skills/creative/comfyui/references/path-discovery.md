# ComfyUI Path Discovery & Model Inventory

This reference captures patterns discovered during session work with ComfyUI, particularly:
- Auto-detecting ComfyUI installation location  
- Checking model availability for specific workflows
- Troubleshooting custom node import issues

## Installation Location Detection

ComfyUI is commonly installed in several locations. Run these checks to find it:

```bash
# Quick check for common locations:
echo "=== CHECKING COMFYUI PATHS ===" && \
echo "- ~/ComfyUI:" && ls ~/ComfyUI 2>/dev/null && echo "  ✓ Found" || echo "  ✗ Not found" && \
echo "- ~/comfy/ComfyUI:" && ls ~/comfy/ComfyUI 2>/dev/null && echo "  ✓ Found" || echo "  ✗ Not found" && \
echo "- /mnt/data/ComfyUI:" && ls /mnt/data/ComfyUI 2>/dev/null && echo "  ✓ Found" || echo "  ✗ Not found" && \
echo "- /home/$USER/ComfyUI:" && ls /home/$USER/ComfyUI 2>/dev/null && echo "  ✓ Found" || echo "  ✗ Not found"
```

### Auto-Detect ComfyUI for Skill Scripts

To feed into ComfyUI skill scripts (run_workflow.py, etc.):

```bash
# Find the active ComfyUI path
find ~/ ~/.comfy /mnt/data /mnt/Comfy* 2>/dev/null -type d -name "ComfyUI" | head -1
```

Or interactively check:
```bash
# Check each path, first match wins:
for path in ~/ComfyUI /mnt/data/ComfyUI /home/$USER/ComfyUI; do
  if [ -d "$path" ]; then
    echo "Using: $path"
    break
  fi
done
```

## Model Inventory Commands

### Check Checkpoints

```bash
# List all checkpoints
ls -1 ~/ComfyUI/models/checkpoints/*.safetensors 2>/dev/null

# Count checkpoints
echo "Checkpoints: $(ls ~/ComfyUI/models/checkpoints/*.safetensors 2>/dev/null | wc -l)"

# Find checkpoint by partial name
ls ~/ComfyUI/models/checkpoints/ | grep -i "sdxl\|flux\|sdxl"
```

### Check ControlNet Models

```bash
ls -1 ~/ComfyUI/models/controlnet/*.safetensors 2>/dev/null
ls -1 ~/ComfyUI/models/controlnet/*.pt 2>/dev/null
```

If no controlnets found:
```bash
# Download ControlNet (ControlNet V1, SDXL compatible)
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_refonly_clip_skip_0_0_1.safetensors" \
  --relative-path models/controlnet
```

### Check VAE Models

```bash
ls -1 ~/ComfyUI/models/vae/*.safetensors

# For SDXL workflows, check for SDXL-compatible VAE:
ls ~/ComfyUI/models/vae/ | grep -i "vae\|diffusion"
```

### Check Lora Models

```bash
ls -1 ~/ComfyUI/models/loras/*.safetensors 2>/dev/null
```

### Check Text Encoders (for SDXL)

SDXL workflows typically need SDXL text encoders:

```bash
# SDXL CLIP (text encoder 1)
ls ~/ComfyUI/models/clip/ 2>/dev/null | head -3

# Or text encoders directory:
ls -1 ~/ComfyUI/models/checkpoint_text_encoders/ 2>/dev/null
```

If missing:
```bash
# Download SDXL CLIP
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_clip_skip_0_0_1.safetensors" \
  --relative-path models/clip

# Download SDXL text encoder 2
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_refonly_clip_skip_0_0_1.safetensors" \
  --relative-path models/text_encoders
```

## Troubleshooting Import Errors

### "class_type not found" Error

This means a custom node is missing. Run:

```bash
# Check which custom nodes are registered:
ls ~/ComfyUI/custom_nodes/ | grep -v "^custom_nodes\["

# Check for broken symlinks or extra directories:
ls -la ~/ComfyUI/custom_nodes/ | grep "^-" | head -20

# Look for auto-generated directories that cause issues:
ls ~/ComfyUI/custom_nodes/ | grep "^custom_nodes[0-9]"
```

Fix by renaming problematic directories:
```bash
mv ~/ComfyUI/custom_nodes/custom_nodes[N] ~/ComfyUI/custom_nodes/custom_nodes[N].disabled
```

Then restart ComfyUI with:
```bash
python3 main.py --disable-all-custom-nodes
```

## Diffusion Model Check (for SDXL)

SDXL workflows require diffusion models compatible with SDXL. Check:

```bash
# List diffusion models
ls -1 ~/ComfyUI/models/diffusion_models/ 2>/dev/null | wc -l

# Check for SDXL-compatible models
ls ~/ComfyUI/models/diffusion_models/ | grep -i "xl\|SDXL\|sdxl"
```

If needed, download SDXL diffusion model:
```bash
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  --relative-path models/diffusion_models
```

## Server Status Check

```bash
# Try common ports
for port in 8188 8888 9090 10000; do
  if curl -s --connect-timeout 5 http://127.0.0.1:$port/ >/dev/null 2>&1; then
    echo "Server found on port $port"
    break
  fi
done

# Or check with user_options.json if exists:
grep -i "port\|listen" ~/ComfyUI/comfyui_user_config.json 2>/dev/null
```

## Summary for Agents

When a user asks to use ComfyUI:

1. **Detect install location** (~/ComfyUI, /mnt/data/ComfyUI, etc.)
2. **Verify hardware** with `hardware_check.py`
3. **Check server status** - restart if needed  
4. **Verify models** for the target workflow (SDXL needs checkpoints, text encoders, diffusion models)
5. **Fix custom node issues** if import errors occur
6. **Run workflow** with correct `--host` or default `--listen`
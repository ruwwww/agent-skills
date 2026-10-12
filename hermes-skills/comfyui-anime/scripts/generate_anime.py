#!/usr/bin/env python3
"""
ComfyUI Anime SDXL Generator Script
Uses the local ComfyUI instance with waiIllustriousSDXL_v170.safetensors
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request

COMFY_HOST = os.getenv("COMFY_HOST", "http://127.0.0.1:8188")
CHECKPOINT = "waiIllustriousSDXL_v170.safetensors"

DEFAULT_POSITIVE_BOOSTERS = "masterpiece, best quality, very aesthetic, absurdres, newest"
DEFAULT_NEGATIVE = "lowres, worst quality, low quality, bad anatomy, bad hands, missing fingers, extra digits, signature, watermark, username, blurry, jpeg artifacts, artist name, mutated, disfigured, text, ugly, bad proportions, bad eyes, poorly drawn hands"

def build_workflow(prompt: str, negative: str, width: int, height: int, steps: int, cfg: float, seed: int):
    # Combine Danbooru positive tags with Illustrious XL quality boosters
    full_positive = f"{prompt}, {DEFAULT_POSITIVE_BOOSTERS}" if "masterpiece" not in prompt.lower() else prompt
    full_negative = f"{negative}, {DEFAULT_NEGATIVE}" if negative else DEFAULT_NEGATIVE

    if seed == -1:
        seed = random.randint(1, 999999999999)

    return {
        "3": {
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"},
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load SDXL Checkpoint"},
            "inputs": {"ckpt_name": CHECKPOINT}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "Empty Latent"},
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Positive Prompt"},
            "inputs": {
                "text": full_positive,
                "clip": ["4", 1]
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Negative Prompt"},
            "inputs": {
                "text": full_negative,
                "clip": ["4", 1]
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"},
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"},
            "inputs": {"filename_prefix": "hermes_anime", "images": ["8", 0]}
        }
    }, seed

def generate(prompt: str, negative: str = "", width: int = 832, height: int = 1216, steps: int = 25, cfg: float = 6.0, seed: int = -1):
    workflow, used_seed = build_workflow(prompt, negative, width, height, steps, cfg, seed)
    
    # 1. Queue prompt
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_HOST}/prompt", data=payload, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            prompt_id = data.get("prompt_id")
    except Exception as e:
        return {"status": "error", "error": f"Failed to submit prompt to ComfyUI ({COMFY_HOST}): {e}"}

    # 2. Poll history for completion
    start_time = time.time()
    timeout = 180  # 3 minutes max
    while time.time() - start_time < timeout:
        time.sleep(2)
        try:
            h_req = urllib.request.Request(f"{COMFY_HOST}/history/{prompt_id}")
            with urllib.request.urlopen(h_req, timeout=10) as resp:
                hist = json.loads(resp.read().decode())
                if prompt_id in hist:
                    outputs = hist[prompt_id].get("outputs", {})
                    if "9" in outputs:
                        images = outputs["9"].get("images", [])
                        if images:
                            filename = images[0]["filename"]
                            subfolder = images[0].get("subfolder", "")
                            out_dir = "/mnt/data/ComfyUI/output"
                            filepath = os.path.join(out_dir, subfolder, filename) if subfolder else os.path.join(out_dir, filename)
                            return {
                                "status": "success",
                                "prompt_id": prompt_id,
                                "seed": used_seed,
                                "filename": filename,
                                "file_path": filepath,
                                "dimensions": f"{width}x{height}",
                                "url": f"{COMFY_HOST}/view?filename={filename}&type=output"
                            }
        except Exception:
            pass

    return {"status": "error", "error": "Generation timed out"}

def main():
    parser = argparse.ArgumentParser(description="Generate anime artwork using ComfyUI and Illustrious SDXL")
    parser.add_argument("prompt", type=str, help="Danbooru / descriptive anime prompt")
    parser.add_argument("--negative", type=str, default="", help="Negative prompt / tags")
    parser.add_argument("--width", type=int, default=832, help="Image width (default: 832)")
    parser.add_argument("--height", type=int, default=1216, help="Image height (default: 1216)")
    parser.add_argument("--steps", type=int, default=25, help="Sampling steps (default: 25)")
    parser.add_argument("--cfg", type=float, default=6.0, help="CFG Scale (default: 6.0)")
    parser.add_argument("--seed", type=int, default=-1, help="Seed (-1 for random)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")

    args = parser.parse_args()
    res = generate(args.prompt, args.negative, args.width, args.height, args.steps, args.cfg, args.seed)
    
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if res.get("status") == "success":
            print(f"MEDIA:{res['file_path']}")
            print(f"✓ Image Generated Successfully!")
            print(f"📁 Path: {res['file_path']}")
            print(f"🎲 Seed: {res['seed']}")
        else:
            print(f"❌ Error: {res.get('error')}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()

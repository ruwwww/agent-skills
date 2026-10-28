---
name: anima-lora-training
description: "Use when preparing datasets and training LoRA for Anima DiT models (Cosmos 2 DiT). Complete SOP for dataset extraction, WD14 tagging, caption absorption/decoupling, fastpath daemon submission, and ComfyUI conversion."
version: 2.0.0
author: Buzzer Lab / Faruq
license: MIT
platforms: [linux]
metadata:
  tags: [anima, dit, lora, finetune, kohya, sd-scripts, diffusion, anime, label-studio, fastpath]
---

# Anima DiT LoRA Training & Dataset Preparation Playbook

SOP dan panduan lengkap end-to-end untuk AI agent (OpenCode, Codex, Freebuff, Hermes, Claude Code) dalam mempersiapkan dataset dan melatih LoRA pada arsitektur **Anima Cosmos 2 DiT** menggunakan hardware **NVIDIA RTX 5060 Ti 16GB**.

---

## 1. Environment & Path Invariants (WAJIB PAKAI PATH ABSOLUT)

* **Python Environment:** `/home/kuroko/.conda/envs/ai/bin/python`
* **Workspace Root:** `/mnt/data/finetune-anima/`
* **sd-scripts Path:** `/mnt/data/finetune-anima/sd-scripts/`
* **Fastpath Runtime Recipe:** `/mnt/data/finetune-anima/anima-lora-fastpath-recipe`
* **Fastpath SQLite DB:** `/mnt/data/finetune-anima/runtime_daemon.sqlite3`
* **Model Base DiT:** `/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors`
* **Text Encoder:** `/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors` (Qwen3-0.6B Base)
* **VAE:** `/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors` (Qwen-Image VAE, wajib `--qwen_image_vae_2d`)
* **ComfyUI LoRA Output:** `/home/kuroko/ComfyUI/models/loras/`
* **Label Studio DB:** `/mnt/data/label-studio/data/label_studio.sqlite3`
* **Label Studio Media:** `/mnt/data/label-studio/data/media`

---

## 2. Invarian Teknis Kritis (Jangan Dilanggar!)

1. **Attention Mode:**
   * **WAJIB:** `--attn_mode="torch"` (PyTorch SDPA).
   * **DILARANG:** `--attn_mode="sageattn"`. SageAttention tidak mendukung autograd backward di sd-scripts; jika dipakai bobot Q/K/V akan bernilai nol (rusak total).
2. **Environment Variable untuk Daemon / Watcher:**
   * Setiap memanggil `python -m runtime` atau mengecek status job di daemon, **WAJIB MENYERTAKAN:**
     `PYTHONPATH="/mnt/data/finetune-anima/anima-lora-fastpath-recipe"`
   * Jika tidak disertakan, subproses Python akan error silent `No module named runtime` dan watcher akan hang.
3. **Konversi ComfyUI & Permission:**
   * Format safetensors dari sd-scripts **harus dikonversi** ke format native ComfyUI Cosmos DiT menggunakan:
     `/mnt/data/finetune-anima/sd-scripts/networks/convert_anima_lora_to_comfy.py`
   * Berikan permission `chmod 664` pada file `.safetensors` hasil konversi di `/home/kuroko/ComfyUI/models/loras/`.
4. **Kebijakan GPU / Service Background:**
   * Jangan menyalakan kembali service ComfyUI background secara otomatis jika tidak diminta.
   * Model Anima base tetap resident di VRAM via runtime daemon untuk *zero-second reload*.

---

## 3. Workflow Lengkap: 5 Langkah dari Nol ke Model Jadi

### Langkah 1: Ekstraksi Dataset

Jika sumber data berasal dari **Label Studio** (misal Project ID $X$):
Export file gambar langsung dari SQLite Label Studio ke direktori dataset konsep:
`/mnt/data/finetune-anima/data_root_<concept>/<repeats>_<concept>/`

Contoh script Python:
```python
import os, shutil, sqlite3, json

PROJECT_ID = 11  # ganti sesuai project id
OUT_DIR = "/mnt/data/finetune-anima/data_root_lubna/2_lubna"
os.makedirs(OUT_DIR, exist_ok=True)

con = sqlite3.connect("/mnt/data/label-studio/data/label_studio.sqlite3")
cur = con.cursor()
cur.execute("SELECT task.id, task.data FROM task WHERE task.project_id = ? ORDER BY task.id ASC", (PROJECT_ID,))
rows = cur.fetchall()

count = 0
for task_id, data_str in rows:
    data = json.loads(data_str)
    img_rel = data.get("image") or data.get("$undefined$")
    if not img_rel: continue
    if img_rel.startswith("/data/"): img_rel = img_rel[len("/data/"):]
    src_path = os.path.join("/mnt/data/label-studio/data/media", img_rel)
    if not os.path.exists(src_path): continue
    
    ext = os.path.splitext(src_path)[1]
    count += 1
    dst = os.path.join(OUT_DIR, f"img_{count:03d}_task{task_id}{ext}")
    shutil.copy2(src_path, dst)
print(f"Exported {count} images to {OUT_DIR}")
```

---

### Langkah 2: Auto-Tagging dengan WD14 Tagger (ONNX GPU)

Jalankan WD14 SwinV2 Tagger v3 untuk menghasilkan file `.txt` caption untuk tiap gambar:

```bash
/home/kuroko/.conda/envs/ai/bin/python /mnt/data/finetune-anima/sd-scripts/finetune/tag_images_by_wd14_tagger.py \
  /mnt/data/finetune-anima/data_root_<concept>/<repeats>_<concept> \
  --repo_id="SmilingWolf/wd-swinv2-tagger-v3" \
  --batch_size=8 \
  --thresh=0.35 \
  --character_threshold=0.85 \
  --onnx \
  --caption_extension=.txt
```

---

### Langkah 3: Caption Refinement (Prinsip Absorpsi vs Decoupling)

> **Golden Rule:**
> * **Yang DITULIS di caption akan TERPISAH (DECOUPLED) dari trigger token.**
> * **Yang DIHAPUS / DISIMPAN RAHASIA dari caption akan MENYATU PERMANEN (ABSORBED) ke trigger token.**

#### A. Fitur yang WAJIB DIBERSIHKAN (Diserap ke Trigger):
* **Rambut:** Warna rambut (`purple_hair`, `blue_hair`), panjang (`long_hair`), poni/gaya (`hair_over_eyes`, `blunt_bangs`, `ahoge`, `hair_bun`).
* **Mata & Wajah:** Warna mata (`yellow_eyes`, `amber_eyes`), bentuk mata, blushing (`blush`), ekspresi (`smile`, `open_mouth`, `wavy_mouth`, `skin_fang`).
* **Noise Tags:** `1girl`, `solo`, `solo_focus`, `text`, `english_text`, `watermark`, `artist_name`, `username`, `parody`, `anime_coloring`.

#### B. Fitur yang WAJIB DIPERTAHANKAN (Agar Ter-decouple / Bisa Ganti Baju):
* **Pakaian:** `school_uniform`, `black_jacket`, `white_shirt`, `pleated_skirt`, `dress`, `choker`, `shawl`, `pajamas`, dll.
* **Mascot / Karakter Pendamping:** `ghost`, `hitodama`, `spirit` (agar karakter bisa dipanggil sendiri tanpa maskot atau sebaliknya).
* **Setting & Background:** `night`, `library`, `outdoors`, `bookshelf`, `daylight`.

#### C. Struktur Akhir Caption:
* Baris caption dimulai dengan: `<trigger_word>, 1girl, solo, <decoupled_tags...>` (atau `1boy, otoko_no_ko, solo` untuk karakter laki-laki/femboy).
* Pastikan `keep_tokens = 1` agar posisi trigger word tidak teracak saat caption di-shuffle.

---

### Langkah 4: Pembuatan `dataset.toml`

Buat file konfigurasi dataset di folder konsep: `/mnt/data/finetune-anima/data_root_<concept>/dataset.toml`:

```toml
[general]
shuffle_caption = true
keep_tokens = 1
caption_extension = ".txt"

[[datasets]]
resolution = [1024, 1024]
batch_size = 1
enable_bucket = true
min_bucket_reso = 512
max_bucket_reso = 1536
bucket_reso_steps = 32

  [[datasets.subsets]]
  image_dir = "/mnt/data/finetune-anima/data_root_<concept>/<repeats>_<concept>"
  num_repeats = 2
```

---

### Langkah 5: Pembuatan Job JSON & Eksekusi Fastpath Daemon

1. Buat file job JSON di `/mnt/data/finetune-anima/<concept>_<epochs>ep_job.json`:

```json
{
  "schema_version": 1,
  "job_id": "<concept>-<epochs>ep-<steps>s",
  "priority": 10,
  "engine_policy": "allow_build",
  "trainer_argv": [
    "--pretrained_model_name_or_path=/home/kuroko/ComfyUI/models/diffusion_models/anima-base-v1.0.safetensors",
    "--dataset_config=/mnt/data/finetune-anima/data_root_<concept>/dataset.toml",
    "--output_dir=/mnt/data/finetune-anima/output_lora/<concept>_<epochs>ep",
    "--output_name=<concept>_lora",
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
    "--optimizer_args", "weight_decay=0.01", "decouple=True", "use_bias_correction=True", "d_coef=1.0",
    "--max_train_epochs=10",
    "--save_every_n_epochs=2",
    "--save_state",
    "--mixed_precision=bf16",
    "--save_precision=bf16",
    "--seed=2026",
    "--cache_latents",
    "--persistent_data_loader_workers",
    "--max_data_loader_n_workers=4",
    "--vae=/home/kuroko/ComfyUI/models/vae/qwen_image_vae.safetensors",
    "--qwen_image_vae_2d",
    "--qwen3=/mnt/data/models/text_encoders/qwen_3_06b_base.safetensors",
    "--caption_extension=.txt",
    "--caption_tag_dropout_rate=0.3",
    "--caption_dropout_rate=0.05",
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

2. Submit job ke daemon:

```bash
PYTHONPATH="/mnt/data/finetune-anima/anima-lora-fastpath-recipe" \
/home/kuroko/.conda/envs/ai/bin/python -m runtime \
  --database=/mnt/data/finetune-anima/runtime_daemon.sqlite3 \
  submit /mnt/data/finetune-anima/<concept>_<epochs>ep_job.json --preflight
```

---

### Langkah 6: Watcher Script & Konversi ComfyUI

Gunakan script watcher otomatis (misal `/mnt/data/finetune-anima/auto_finish_<concept>.py`):
1. Polling status job dengan `PYTHONPATH="/mnt/data/finetune-anima/anima-lora-fastpath-recipe"`.
2. Saat status bernilai `succeeded`, otomatis jalankan konversi:

```python
import os, glob, re, subprocess

PYTHON = "/home/kuroko/.conda/envs/ai/bin/python"
CONV_SCRIPT = "/mnt/data/finetune-anima/sd-scripts/networks/convert_anima_lora_to_comfy.py"
OUT_DIR = "/mnt/data/finetune-anima/output_lora/<concept>_<epochs>ep"
COMFY_DIR = "/home/kuroko/ComfyUI/models/loras"

ckpts = sorted(glob.glob(os.path.join(OUT_DIR, "*.safetensors")))
ckpts = [c for c in ckpts if not c.endswith("_comfy.safetensors")]

for c in ckpts:
    fname = os.path.basename(c)
    if "00000" in fname or "epoch" in fname:
        m = re.search(r"(?:epoch-?0*|00000)(\d+)", fname)
        ep = int(m.group(1)) if m else "x"
        dest_name = f"<concept>_ep{ep}_comfy.safetensors"
    else:
        dest_name = f"<concept>_final_comfy.safetensors"
    dst = os.path.join(COMFY_DIR, dest_name)
    subprocess.run([PYTHON, CONV_SCRIPT, c, dst], check=True)
    os.chmod(dst, 0o664)
    print(f"Converted: {dest_name}")
```

---

## 4. Prompting SOP untuk Pengujian Inferensi

* **Trigger Token:** 1 token murni (misal: `lubna`)
* **LoRA Weight:** `0.85` – `1.0`
* **Test 1 - Canonical Look:** Gabungkan trigger + decoupled attire + decoupled mascot.
* **Test 2 - Decoupled Attire Test (Ganti Pakaian):** Trigger + pakaian berbeda (misal: `wearing gothic dress` atau `sweater`) tanpa tag pakaian aslinya.
* **Test 3 - Style Modifier Test:** Prefix `@ciloranko` atau `@ratatatat74` untuk melihat apakah gaya eksternal tetap bekerja tanpa merusak karakter.

# Legal LLM Alignment Pitfalls & Production Lessons

Hard-won engineering and data quality lessons from aligning LLMs on statutory court decisions (e.g. Indonesian Criminal Law / Faruq corpus, 22.6k court rulings):

## 1. The Context Budget Truncation Trap (Why Low Loss Misleads)
- **Symptom:** SFT loss drops to ~0.90 with token accuracy >64%, yet the model generates rambling, incoherent run-on sentences or loops boilerplate (`menimbang bahwa ...`).
- **Root Cause:** Court decisions (fact + reasoning + amar) frequently have 8,000–16,000 tokens (median ~12k tokens). If trained with a naive small context window (e.g., 2,048 tokens) with completion-first packing, the target reasoning alone exhausts the 2,048 budget.
- **Consequence:** In 75%+ of training examples, **zero prompt tokens (facts/indictments) fit inside the supervised window**. The model learns only unconditional continuation of repetitive judicial boilerplate without grounding on facts.
- **Amar & EOS Amputation:** The operational verdict (`Amar putusan:`) and `<|im_end|>` / `EOS` token sit at the end of the text. When truncated, the model never sees an EOS token and never learns when to stop.
- **Remedy:**
  1. Section-aware packing: Extract core facts (`dakwaan` + key testimony summaries) and paired reasoning/amar rather than feeding 50-page raw documents.
  2. Maintain a hard constraint: Both prompt prefix AND completion suffix (including amar and EOS) must fit inside the model's sequence budget (typically 4k–8k+ tokens).
  3. Filter data by strict token budget tiers before training.

## 2. Court XML & OCR Noise Profiling
- **Punctuation & Case Normalization:** Supreme Court public directory XMLs often stem from unpunctuated OCR or stripped plain text (99.9% lowercase, no commas/periods).
  - *Pitfall:* Do NOT naively train a chat/instruct model on raw unpunctuated text without standard ChatML formatting (`<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n...`), otherwise inference prompts produce delimiter mismatch and unpunctuated hallucination loops.
- **Noise Tokens:** Detect and filter synthetic placeholders like `_unk_` (present in >50% of raw cases) and `<TRUNCATED>`.
- **Procedural vs Substantive Ratio:** Measure substantive reasoning density. Filter out cases where reasoning is missing or purely procedural (e.g. formal scheduling orders).

## 3. Train/Val/Test Split Isolation & Leakage
- **Exact & Near Duplicates:** Court decisions frequently contain identical companion cases (*perkara splitsing*) where facts and reasoning are word-for-word identical under different case IDs.
- **Requirement:** Deduplicate by normalized text hash and group near-duplicates (e.g., SimHash Hamming distance <= 8) into the SAME partition BEFORE assigning splits. Row-level random splitting causes massive cross-split data leakage.

## 4. EDA Presentation & Notebook Delivery Standards
- **User Preference & Quality Standard:** Deliver **traditional, clean Data Science Jupyter Notebooks (`.ipynb`)** using native `matplotlib`, `seaborn`, `pandas`, and `numpy` inline plots and DataFrame tables with clear analytical narrative.
- **Strict Prohibition on Forced HTML/Slide Wrappers:** Do NOT force HTML slide rendering, raw `IPython.display.HTML` div cards, or embed pre-rendered PNG images via `display(Image(...))` in lieu of real cell-executed plotting. Reviewers and researchers expect standard notebooks where plots are generated natively via `fig, ax = plt.subplots(...)`, `sns.barplot(...)`, `plt.show()` and tables rendered via standard DataFrame outputs.
- **Standalone Plots:** Concurrently save native figures to a dedicated directory (e.g. `eda/plots/*.png`) for inclusion in academic slides, papers, or thesis defenses.
- Do NOT generate throwaway Office artifacts (`.pptx`, `.docx`) unless explicitly requested; prioritize version-controlled code, clean `.ipynb`, and high-resolution standalone figures.

## 5. Synthetic OCR Token Normalization (`_unk_`)
- **Root Cause of `_unk_` in Court Corpora:** Prevalent in >50% of OCR-scanned court XMLs. Arises from OCR conversion failures on currency symbols (`Rp`, `Rp.`, initial digits of fines) and alphanumeric serial strings (vehicle chassis/engine numbers `noka`/`nosin`, indictment registration codes `pdm _unk_`).
- **Mitigation:** Never allow the model to memorize and repeat `_unk_`. Normalize contextually:
  - Fines / financial amounts: `[NOMINAL]` (relying on Indonesian textual amounts such as *"lima puluh juta rupiah"*).
  - Vehicle / evidence serials: `[NOMOR_SERI]`.
  - Case / docket numbers: `[KODE]`.

## 6. Academic Thesis & LaTeX Scaffolding Standards
- When scaffolding academic theses or defense proposals in LaTeX:
  - Maintain a modular chapter structure (`main.tex`, `chapters/bab1.tex`, `chapters/bab2.tex`, `references.bib`).
  - Use canonical academic citations for preference alignment (`rafailov2023direct` for DPO, `schulman2017proximal` for PPO, `ouyang2022training` for RLHF, `hu2021lora` for LoRA) and local statutory law (KUHAP UU 8/1981, KUHP, Yahya Harahap).
  - Package ready-to-compile `.zip` archives compatible with Overleaf (`pdfLaTeX` + `BibTeX` / `natbib`).

## 7. Codebase Hygiene & Single Canonical Pipeline Rule
- **Consolidation over Proliferation:** When graduating from exploratory pilot/smoke runs to production, prune and consolidate deprecated codebases immediately.
- Never leave competing versions (e.g. `v1` vs `v2`, experimental scripts, pilot configs, temporary smoke artifacts) lingering in the repository.
- Consolidate around a single canonical pipeline:
  - Prune temporary smoke checkpoints, obsolete configs, and superseded dataset formats from `artifacts/`.
  - Standardize config naming (e.g. `sft/trl/qwen25_1_5b_lora.yaml` pointing directly to canonical `artifacts/sft_v2/` and saving to `artifacts/faruq_sft_v2_lora/`).
  - Rewrite root `README.md` to present a clean, accessible overview for supervisors/evaluators, stripping out historical experimentation debris and keeping only operational commands and clear non-technical/architectural summaries.
  - Deliver changes strictly via Pull Request merges into `main`, keeping history clean and auditable.

## 8. Training Budget & Compute Dynamics (Curated vs Uncurated Scaling)
- **Why Curation Dramatically Accelerates Training:**
  - Raw, uncurated legal corpora (e.g. 20k+ court records) require 2,500+ optimizer steps and 4–6+ hours of GPU time, but suffer from high noise, OCR corruption, and repetitive boilerplate overfitting.
  - Curating to Tier-1 Gold records (e.g. 1,125 high-quality cases) reduces dataset volume by ~18x while vastly improving signal-to-noise ratio.
  - With effective batch size = 8 (`per_device_batch_size: 1` $\times$ `gradient_accumulation_steps: 8`), 1 epoch over 1,125 samples yields exactly 141 optimizer steps.
  - At ~14–15 seconds per 4096-token step on standard desktop/server GPUs (e.g. RTX 5060 Ti / RTX 4090), 1 epoch completes in only ~33 minutes.
- **5x Budget Scaling Strategy:**
  - To utilize multi-hour compute budgets effectively without diluting data quality, scale **epoch count** (e.g. 5.0 epochs = 705 steps ≈ 2.8–3.0 hours) rather than re-introducing low-quality Tier-3 noise.
  - 3–5 epochs allows the learning rate schedule (e.g. linear/cosine decay from $10^{-4}$ down to 0) to mature across the dataset, enabling the model to learn proper legal reasoning transitions from indictment to verdict and escape repetitive question loops.

## 9. GPU Resource Hygiene with Background Daemons
- **Silent VRAM Contention:** Background local daemons (such as ComfyUI on port 8188 or vLLM instances) frequently reserve 5–6+ GB of VRAM in persistent cache, causing immediate CUDA OOM during 4096-token SFT runs on 16GB GPUs.
- **Non-Destructive Memory Release:** Instead of terminating background server processes, invoke their model-unloading APIs to release VRAM cleanly:
  - ComfyUI: `curl -s -X POST http://127.0.0.1:8188/free -H "Content-Type: application/json" -d '{"unload_models": true, "free_memory": true}'` instantly frees memory back to <300MB without dropping the server session.

## 10. Unified Multi-Model Hub Distribution (Hugging Face Subfolder Pattern)
- **Avoid Repository Sprawl:** Rather than creating a new Hugging Face repo for every experimental checkpoint (e.g. separate repos for `model-1ep`, `model-5ep`, `model-dpo`, `model-ppo`), organize the research under **a single project hub model repository** (e.g. `<user>/<project>-alignment-models`).
- **Standardized Subfolder Structure:**
  ```text
  <project>-alignment-models/
  ├── README.md                      # Comprehensive Model Card with comparison table & GitHub link
  ├── scripts/infer.py               # Standalone generation script loading from subfolders
  └── models/
      ├── sft-v2-5epoch/             # Canonical SFT adapter
      │   ├── adapter_model.safetensors
      │   ├── adapter_config.json
      │   ├── tokenizer.json & tokenizer_config.json
      │   ├── chat_template.jinja
      │   ├── training_recipe.yaml   # Exact reproduction hyperparameters
      │   ├── training_metrics.json  # Step-by-step train/eval metrics
      │   └── README.md              # Subfolder quickstart
      ├── sft-v2-1epoch/             # Baseline comparison adapter
      └── (upcoming dpo / ppo / reward-model checkpoints...)
  ```
- **Native Subfolder Loading in PEFT & Transformers:**
  Both libraries support subfolder resolution directly from the Hub without cloning:
  ```python
  from peft import PeftModel
  from transformers import AutoModelForCausalLM, AutoTokenizer

  repo_id = "user/project-alignment-models"
  subfolder = "models/sft-v2-5epoch"

  tokenizer = AutoTokenizer.from_pretrained(repo_id, subfolder=subfolder)
  base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B", torch_dtype="auto", device_map="auto")
  model = PeftModel.from_pretrained(base, repo_id, subfolder=subfolder)
  ```
- **Hugging Face Hub Staging & Upload:**
  Build the staging tree locally, verify file existence, create the repo with `api.create_repo(repo_id=..., repo_type="model", exist_ok=True, private=False)`, and upload using `api.upload_folder(folder_path=staging_dir, repo_id=repo_id, repo_type="model")`.

## 11. Hardware Economics: Compute vs Memory Bandwidth in Legal SFT & RLHF (PPO vs DPO)
- **Different Compute Profiles:**
  - **SFT & DPO:** Primarily compute-throughput and VRAM-capacity bound (dense GEMM forward/backward passes over batch tokens). GPUs with strong Tensor Cores (e.g. RTX 6000 Ada, A100 SXM4) with 48–80GB VRAM can train 7B–14B models with large batch sizes without aggressive gradient checkpointing.
  - **RLHF (PPO):** Primarily **memory bandwidth bound**. PPO requires autoregressive rollout generation (single-token decode steps) across the Policy (Actor), Critic (Value), Reference, and Reward models.
  - Generative rollouts on consumer GDDR6/GDDR6X (~0.5–1.0 TB/s) become severely bandwidth-starved. GPUs with High Bandwidth Memory (HBM2e/HBM3 >2.0–3.35 TB/s, such as A100 SXM4 or H100) run PPO rollout engines (vLLM) 3x–5x faster, drastically lowering total wall-clock rental costs in cloud environments.
- **The Gradient Checkpointing Cost Trap:**
  - Activation checkpointing saves VRAM by discarding forward activations and recomputing them during backward pass (~30–33% compute penalty).
  - On tight VRAM consumer GPUs (24GB), forced checkpointing + micro-batch 1 can double training time, negating low per-hour GPU rental rates. Prefer VRAM capacity that fits the sequence length without excessive recomputation.

## 12. Transformers 5.16+ Compatibility Trap with TRL Imports
- **Bug Mechanism:** In `transformers` >= 5.16, `_is_package_available` was changed to return a tuple `(bool, version_str)` instead of a boolean scalar when `return_version` is omitted.
- **TRL Failure:** In TRL (<=0.27), functions like `is_vllm_ascend_available()` check `return _is_package_available("vllm_ascend")`. In Python, a non-empty tuple `(False, None)` evaluates as `True` in boolean contexts (`if is_vllm_ascend_available():`), causing immediate import crashes: `ModuleNotFoundError: No module named 'vllm_ascend'`.
- **Remedy:** Ensure `_is_package_available` results are coerced properly before boolean checks:
  ```python
  res = _is_package_available(pkg_name, return_version=return_version)
  return res[0] if isinstance(res, tuple) else bool(res)
  ```

## 13. Judicial Preference Design (Pasal 184 KUHAP Evidentiary Grounding)
- **Directly Consumable DPO/RLHF Format:** Pairs must be structured for immediate ingestion by TRL `DPOTrainer` (`prompt`, `chosen`, `rejected`).
- **Prompt:** ChatML system instruction + `[SURAT DAKWAAN]` + `[FAKTA PERSIDANGAN & ALAT BUKTI]`.
- **Chosen (Ground Truth Judicial Subsumption):**
  - Authentic ratio decidendi from judges analyzing evidentiary elements pursuant to Article 184 KUHAP (keterangan saksi, surat, petunjuk, keterangan terdakwa).
  - Explicit deliberation connecting facts to the statutory requirements of the indictment.
  - Proportional, legally sound dictum (`[AMAR PUTUSAN]`) terminating with `<|im_end|>`.
- **Rejected (Realistic Legal LLM Failure Modes):**
  - *Failure Mode A (Evidentiary / KUHAP Breach):* Declaring guilt without testing statutory elements or relying on a single witness without corroboration (*unus testis nullus testis*).
  - *Failure Mode B (Procedural Looping):* Trapped in formalistic "menimbang bahwa" preambles without ever producing an operative verdict (amar).
  - *Failure Mode C (Disproportionate / Ultra Petita Dictum):* Penal sanctions that drastically deviate from statutory ranges or ignore mitigating/aggravating factors.
  - *Failure Mode D (Fact / Exhibit Hallucination):* Fabricating vehicles, weapons, or amounts not present in the trial facts.

## 14. vLLM Rollout Backend & LoRA Weight Streaming Contract
- When running Online DPO or PPO, the policy adapter is updated by PyTorch optimizer steps while the rollout engine (vLLM) generates rollouts.
- Implement an explicit `LoRAWeightStreamer` contract that synchronizes updated adapter weights dynamically to the vLLM engine between rollout iterations (via vLLM dynamic LoRA request or shared adapter snapshot) to avoid expensive full-model restarts.

## 15. PEFT 0.18 + torchao Quantization Dispatch Trap
- **Symptom:** `ImportError: cannot import name 'LinearActivationQuantizedTensor' from 'torchao.quantization'` when loading LoRA adapters with `is_trainable=True` via `PeftModel.from_pretrained()`.
- **Root Cause:** In PEFT 0.18+, the LoRA tuner invokes `dispatch_torchao` whenever `torchao` is found on `sys.path`. If an in-development or mismatched torchao version is present without `LinearActivationQuantizedTensor`, standard BF16/FP16 training crashes during adapter injection even when quantization is completely unused.
- **Remedy:** Force-disable PEFT's torchao dispatcher before instantiating or training PEFT models:
  ```python
  def disable_incompatible_torchao_dispatch() -> bool:
      try:
          from torchao.quantization import LinearActivationQuantizedTensor
      except (ImportError, AttributeError):
          import peft.tuners.lora.torchao as peft_torchao
          peft_torchao.is_torchao_available = lambda: False
          return True
      return False
  ```

## 16. Judicial Reward Model Architecture & PPO Scoring Contract
- **Reward Modeling Triad:** Supervised Fine-Tuning establishes base legal syntax; the Reward Model quantifies statutory and evidentiary alignment; PPO/DPO optimizes policy against this signal.
- **Sequence Classification vs LoRA (`SEQ_CLS`):**
  - Train reward models using `AutoModelForSequenceClassification` with `num_labels=1` and LoRA `task_type="SEQ_CLS"`.
  - Ensure the classification head (`score.weight`) is properly handled during loading/checkpointing (transformers reports uninitialized weights on base model load; LoRA saves adapter weights alongside the head).
  - Target attention and MLP projections (`[q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]`).
- **Pairwise Bradley-Terry Loss in TRL `RewardTrainer`:**
  - Tokenize prompt + chosen and prompt + rejected as complete sequences.
  - Filter sequences exceeding context window (e.g. 4,096 tokens) to prevent silent CUDA indexing errors or severe truncation of verdicts.
  - Apply padding tokens explicitly (`tokenizer.pad_token = tokenizer.eos_token` if pad is None) with left or right padding aligned to model architecture.
- **Inference & Scoring Engine (`JudicialRewardScorer`):**
  - Extract scalar reward values via last-token logit pooling on sequence outputs: `outputs.logits.squeeze(-1)`.
  - Provide a clean batch evaluation interface: `score_completions(prompts: Sequence[str], completions: Sequence[str]) -> list[float]`.
  - Decouple rollout generation from reward scoring: the PPO trainer (`train_ppo.py`) should support scoring rollouts via a real trained reward model checkpoint while maintaining an explicit fallback scorer (e.g. rule-based heuristic checking amar/section presence) for dry-runs and smoke tests.

## 17. Multi-Model SFT Candidate Scaling & Local Hardware Fit (16GB VRAM)
- **Local Workstation Constraint (RTX 5060 Ti 16GB):**
  - Evaluating model families for thesis defense requires balancing parameter capacity against VRAM ceilings and inference throughput.
  - **Qwen2.5-3B (Base):** The sweet spot for local 16GB VRAM. Weights consume ~6.0 GB in BF16, leaving ~10 GB for LoRA activations, KV cache, and 4k context. Enables clean empirical comparison against 1.5B on statutory subsumption without quantization penalties.
  - **Llama-3.2-1B-Instruct:** Excellent lightweight cross-architecture baseline (~2.5 GB BF16), but note tokenizer efficiency difference on Indonesian text (~1.3x–1.5x more tokens for equivalent statutory prose).
  - **Qwen2.5-7B:** Exceeds native BF16 capacity on 16GB VRAM (~14 GB base weights alone cause OOM during 4k context forward-backward pass). Requires QLoRA (NF4 4-bit quantization, consuming ~4.8 GB base) if run locally.

## 18. SFT Generation Sample Delivery & Generation Token Cap Pitfalls
- **The Generation Truncation Pitfall (`max_new_tokens` Under-budgeting):**
  - **Symptom:** Sampling SFT candidate completions for human/colleague review produces text that appears "cut off" in the middle of witness testimonies or statutory element analysis, rarely reaching `[AMAR PUTUSAN]` (<1% completion rate).
  - **Root Cause:** Full statutory judicial reasoning is lengthy (median ~900–1,200 tokens). Setting a low generation cap (e.g. `max_new_tokens=320`) to accelerate batch sampling artificially halts generation before the model reaches the operative verdict and `<|im_end|>`.
  - **Remedy:**
    1. Set `max_new_tokens >= 1024` for statutory reasoning generation to allow full ratio decidendi + dictum closure.
    2. Add diagnostic metadata columns in evaluation/sample CSV exports: `is_completed` (terminated with `<|im_end|>`), `has_amar_putusan` (contains `[AMAR PUTUSAN]`), and `finish_reason` (`eos_token` vs `length_limit`).
    3. Apply moderate `repetition_penalty = 1.1` to prevent formalistic preambles ("menimbang bahwa") from exhausting the token budget before reaching the verdict.

## 19. Ephemeral Remote Instance Automation (Train-Ablate-Publish Pipeline)
- **Cloud/Spot Instance Lifecycle Constraints:**
  - Remote cloud GPU instances (RunPod, Lambda, Vast.ai) are time-bounded, cost-metered per hour, and prone to preemption or storage disk exhaustion (limited 30–50 GB root volume).
  - Storing multiple experimental checkpoint adapters locally risks "No space left on device" crashes.
- **Immediate Checkpoint Publishing & Local Pruning:**
  - Structure ablation runners to execute an atomic lifecycle per experiment:
    $$\text{Train} \implies \text{Evaluate} \implies \text{Upload Subfolder to HF Hub} \implies \text{Prune Local Disk Adapter}$$
  - Tag W&B runs with the corresponding Hugging Face Hub commit URL.
  - Guarantees zero data loss if an instance is terminated mid-sweep, and keeps local SSD usage strictly bounded.

## 20. Statutory Verdict Termination Dynamics & Repetitive Fee Loops
- **The Infinite Biaya Perkara Loop:**
  - In Indonesian criminal court rulings, the closing clause typically assesses court fees to the defendant (e.g., *"membebankan kepada terdakwa membayar biaya perkara sebesar rp 2 000 dua ribu rupiah"*).
  - When models generate beyond this point without a strong EOS transition, they frequently degenerate into an infinite loop repeating the fee assessment clause (`"... 15 membebankan ... 16 membebankan ..."`).
  - **Remedy in Inference Pipelines:** Implement a deterministic `StoppingCriteria` that halts generation immediately upon matching the regex `biaya perkara[^\n]+rupiah` and appends `<|im_end|>`, guaranteeing clean and complete operative verdicts without runaway token consumption.
- **vLLM Multi-Process / CUDA Graph Freezing on Mismatched Environments:**
  - On workstations with newer CUDA runtimes (e.g., CUDA 13) or concurrent PyTorch background workers, vLLM's internal CUDAGraph piecewise capture can hang indefinitely during worker startup.
  - For batch sample exports and offline candidate generation on a single GPU, batched native PyTorch inference (`AutoModelForCausalLM` with `torch.inference_mode()`, batch size 4–8) provides deterministic, zero-hang generation with predictable memory usage.

## 22. Parameter Capacity Scaling vs Epoch Saturation (The 3B "Doom Loop" Phenomenon)
- **Symptom:** Scaling from 1.5B to 3B model parameters under a 3-epoch budget yields higher token accuracy (~87.5%) and lower validation loss (~0.536), yet qualitative autoregressive generation still suffers from circular reasoning loops (getting stuck elaborating witness testimonies or evidence specifications) and fails to emit `<|im_end|>` to close the verdict.
- **Root Cause (Capacity vs Convergence Depth):**
  - Larger parameter models (3B vs 1.5B) have higher expressive capacity and require more optimizer steps / gradient updates to reliably learn the sharp probability transition from extensive factual reasoning (`[PERTIMBANGAN HUKUM]`) into the operative verdict (`[AMAR PUTUSAN]`) and terminal EOS token (`<|im_end|>`).
  - At 3 epochs (423 optimizer steps with batch size 8), the model's loss landscape has minimized next-token prediction on long factual sequences, but has not yet saturated the decisive transition probability for the terminal verdict.
- **Remedy:**
  1. Scale to **5.0 epochs (705 optimizer steps)** for 3B parameter models on curated legal corpora (~1,125 cases) to allow the cosine/linear learning rate schedule to settle deeper into the target verdict transition distribution.
  2. Maintain strict completion-only loss masking so gradient signal is concentrated 100% on the assistant's legal analysis and terminal dictum rather than being diluted across the user's indictment prompt.

## 23. Hardware VRAM Ceilings & Quantized SFT Constraints (7B+ on 16GB VRAM)
- **Native vs Quantized Training Limits on 16GB Consumer/Workstation GPUs:**
  - **3B Models:** Sweet spot for native BF16 LoRA training with full 4,096-token sequence budget. Requires `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` and activation checkpointing (`use_reentrant: False`), utilizing ~14.2–14.4 GB peak VRAM.
  - **7B Models:** Base weights alone in BF16 consume ~15.2 GB, making native BF16 training impossible on a 16GB GPU.
  - **The 4-Bit QLoRA (NF4) Context Length Barrier on 16GB:**
    - Loading 7B via BitsAndBytes 4-bit NF4 (`load_in_4bit=True`, double quant, compute dtype bf16) shrinks base model memory to ~5.18 GB VRAM.
    - However, during training forward-backward passes with self-attention (SDPA), KV cache and activation states scale quadratically/linearly with sequence length.
    - Even with gradient checkpointing enabled, **4,096 tokens on a 7B model requires an additional ~11–12 GB of dynamic activation memory**, exceeding the remaining ~10.3 GB VRAM and triggering `CUDA out of memory` (attempting to allocate 1.75 GB).
    - **Empirical Threshold for 7B on 16GB VRAM:** 7B QLoRA can only run if sequence length is truncated to `<=1,536–1,800 tokens` with micro-batch size 1. For domain tasks requiring full 4k+ tokens (e.g. multi-page court indictments and testimonies), hardware must be scaled to >=24GB (RTX 3090/4090) or >=48GB/80GB (A100/RTX 6000 Ada) rather than forcing extreme context amputation.
- **TRL ChatML Collator EOS Supervised Token Artifact:**
  - In TRL SFT implementations, ensure that appending a global `eos_token_id` (`<|endoftext|>`) after the chat template's natural `<|im_end|>\n` delimiter does not inject dual conflicting stop targets.
  - Set stopping criteria on both token IDs (`eos_token_id=[tokenizer.encode('<|im_end|>')[0], tokenizer.eos_token_id]`) during generation to guarantee immediate termination regardless of which token achieves dominance.

## 24. Generation Prompt Truncation & Left-Truncation Rule for Long Court Records
- **The Right-Truncation Amputation Trap:**
  - Court cases often contain massive indictments and witness transcripts (>2,500 tokens).
  - When batching prompts for inference/evaluation, standard tokenizer truncation defaults to `truncation_side = 'right'`.
  - **Symptom:** The model never starts judicial deliberation (`[PERTIMBANGAN HUKUM]`) and never reaches the verdict (`[AMAR PUTUSAN]`), generating endlessly in a loop.
  - **Root Cause:** Right-truncation silently discards the *tail* of the prompt containing the final indictment facts and the generation delimiter `<|im_end|>\n<|im_start|>assistant\n`. The model receives a headless prompt and continues generating raw witness statements as user text.
  - **Remedy:** Explicitly enforce `tok.truncation_side = 'left'` and budget sufficient input length (`max_input_length = 2800`). Any truncated tokens are dropped from the beginning of background facts while the critical indictment closing and the `<|im_start|>assistant\n` trigger remain 100% intact.

## 25. Judicial Dictum Termination & Multi-Variant Fee Regex
- **Multi-Variant Indonesian Court Fee Verbs:**
  - District court decisions close with court fee assessments using varying statutory verbs:
    - *"membebankan kepada terdakwa untuk membayar biaya perkara..."*
    - *"membebani terdakwa untuk membayar biaya perkara..."*
    - *"menetapkan biaya perkara kepada terdakwa sejumlah..."*
  - Using a single-verb regex (e.g. only matching `membebankan`) causes decisions with `membebani` to bypass termination and degenerate into hallucinated registrar signatures, docket numbers, or numeric sequences.
  - **Universal Termination Regex:**
    ```python
    pat = re.compile(r'(?:membebankan|membebani|menetapkan)[^\n]*biaya perkara[^\n]*rupiah', re.IGNORECASE)
    m = pat.search(text)
    if m:
        text = text[:m.end()].strip()
    ```
- **N-Gram Penalty in Repetitive Statutory Jargon:**
  - Prevent autoregressive looping on recurring formalisms (*"bahwa benar saksi..."*, *"menimbang bahwa..."*) by enforcing `repetition_penalty = 1.15` and `no_repeat_ngram_size = 8`.
- **Incremental Disk Flushing for Long Evaluation Runs:**
  - For multi-candidate exports (e.g. 30x3 or 100x3 samples requiring 30–90+ minutes), always append rows to disk immediately per completed case with `csv.DictWriter` and `flush=True`. Implement checkpoint-resume logic based on completed `case_id`s to ensure progress survives interruptions or timeouts.

## 26. Autonomous Validation Standard (Zero-Truncation Reporting Rule)
- **User Directive:** "Mending kamu coba2 deh sampai ketemu hasil yg bagus. Baru lapor ke aku.. Itu adalah goal, jangan lapor atau respon jika masih ada yg terpotong atau tidak sesuai."
- When evaluating or generating evaluation candidates for researchers/supervisors:
  1. **Never deliver partial, broken, or mid-sentence truncated outputs.** Reporting a blocker with broken samples creates friction and defeats the purpose of autonomous tooling.
  2. Perform bounded exploratory loops internally: audit output samples for section presence (`[PERTIMBANGAN HUKUM]`, `[AMAR PUTUSAN]`), clean termination (`biaya perkara ... rupiah`), and repetitive loops.
  3. Filter, re-generate, or refine prompt constraints until the exported sample dataset is **100% verified complete** before handing off to the user.

## 27. Gemma 4 Architecture & Thought-Channel SFT Tokenization (`google/gemma-4-12B-it`)
- **Architecture Mapping:** Gemma 4 models (e.g. `google/gemma-4-12B-it`) are identified as `Gemma4UnifiedForConditionalGeneration` (`model_type: gemma4_unified`) and natively mapped under `AutoModelForCausalLM` in `transformers` >= 4.50.
- **LoRA Target Modules:** Linear projections inside the text language model layers:
  `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`.
  Wrapping with PEFT `LoraConfig(task_type="CAUSAL_LM", r=16, lora_alpha=32)` yields ~65.5M trainable parameters (~0.545% of 12B total).
- **The Chat Template Thought-Channel Quirk:**
  - Gemma 4 Canonical template uses: `<bos><|turn>system\n...<turn|>\n<|turn>user\n...<turn|>\n<|turn>model\n...<turn|>\n<eos>`.
  - When `add_generation_prompt=True` is passed to `tok.apply_chat_template`, Gemma 4 automatically appends `<|channel>thought\n<channel|>` unless explicit thinking arguments are passed.
  - In completion-only loss masking, ensure prompt and full message boundaries align without thought-token drift when determining completion mask indices.
- **Hardware Limits (12B on 16GB VRAM):**
  - Native BF16 weights of a 12B model require ~24 GB VRAM. Training natively in BF16 requires >=48GB VRAM (A100 / H100 / RTX 6000 Ada).
  - For local 16GB workstations, 4-bit quantization (QLoRA NF4) or remote preemption-safe cluster execution is required.

## 28. Minimalist Research Progress Slides Standards (PowerPoint `.pptx`)
- When generating weekly progress decks for research advisors:
  - **Aspect Ratio:** 16:9 widescreen (`13.333` $\times$ `7.5` inches).
  - **Typography:** Arial, Title **14pt bold**, Subtitle **12pt muted**, Body bullets **12pt regular** (line spacing 1.25).
  - **Color Palette:** Pure white background (`#ffffff`), dark charcoal headers/body (`#141414`, `#282828`), subtle muted captions (`#646464`).
  - **Content Density:** Direct, informative bullet lines citing real metrics (FLOPs, losses, step counts, hardware allocations) with zero decorative clipart or filler shapes.

## 29. Qwen 3.8 27B Architecture (`Qwen/Qwen3.8-27B`) & Hybrid DeltaNet LoRA
- **Architecture Mapping & Loader Fallback:**
  - `Qwen/Qwen3.8-27B` is governed by `Qwen3_5ForConditionalGeneration` (`model_type: qwen3_5`).
  - *Pitfall:* `AutoModelForCausalLM.from_pretrained` may fail with `AttributeError: 'Qwen3_5Config' object has no attribute 'vocab_size'` because vocabulary attributes reside under `config.text_config`.
  - *Remedy:* Expand the model loader exception catcher to include `AttributeError` alongside `(OSError, ValueError, KeyError)` so it gracefully falls back to `AutoModelForMultimodalLM.from_pretrained()`, which instantiates `Qwen3_5ForConditionalGeneration` directly.
- **Hybrid Linear & Full Attention LoRA Modules:**
  - Qwen 3.8 / 3.5 interleaves standard full attention layers with Gated DeltaNet linear attention layers.
  - Expand `LORA_TARGET_MODULES` to cover linear attention projections (`in_proj_qkv`, `out_proj`) alongside standard projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
  - In a 27.4B model, rank-16 LoRA adapts **100,139,008 parameters (0.3647%)**, maintaining parameter efficiency while adapting both long-range memory and standard self-attention.

## 30. RunPod Cloud Automation & Billing Protection (RTX 6000 Ada / Blackwell 48GB+)
- **One-Click Remote Lifecycle (`scripts/runpod_setup_and_run.sh` & `scripts/runpod_sft_runner.py`):**
  - High-VRAM remote instances (e.g. RunPod RTX 6000 Ada / Blackwell 48GB+) require fully self-contained bootstrap scripts.
  - Maintain a dedicated `requirements-runpod.txt` to install core ML dependencies without wheel conflicts.
  - Automatically verify `HF_TOKEN` from environment variables and perform `huggingface-cli login --add-to-git-credential`.
- **Atomic Train-Upload-Terminate Cycle:**
  - Train adapter $\to$ Auto-generate standard model card (`README.md`) $\to$ Direct upload to target subfolder on Hugging Face Hub (e.g. `ruwwww/faruq-alignment-models/models/sft-v2-qwen38-27b`).
  - **Billing Protection (`--stop-pod-on-completion`):** Automatically invoke `runpodctl stop pod $RUNPOD_POD_ID` immediately following successful upload. Prevents idle cloud billing if the training finishes overnight or while the researcher is away.

## 31. Evaluation Split Integrity & Traceability to Raw Court XMLs
- **Strict Test-Split Evaluation Rule:**
  - When sampling or evaluating model performance for research presentations, **never evaluate on training or validation split cases**.
  - All qualitative generations must originate strictly from the unseen hold-out testing partition (`artifacts/sft_v2/test.jsonl`). Evaluating on training cases introduces severe confirmation bias and memorization artifacts.
- **Traceability to Original Court Dossiers (`source_file`):**
  - Every evaluated sample must maintain bidirectional traceability back to the original Supreme Court XML dossier (`Faruq/dataset/<hash>.xml`).
  - Keep an explicit mapping index linking `sample_id` $\to$ `case_id` (e.g., `test_0027`) $\to$ `source_file` (`Faruq/dataset/6c6747b98a2f944286873b45cfc36ee9.xml`). This enables human evaluators, academic supervisors, and legal experts to cross-examine model-generated pertimbangan and amar against the real historical trial record.
- **LLaMA-Factory Ecosystem Compatibility:**
  - While TRL is used for native orchestration, format dataset schemas using standard ChatML `messages` format (`{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`).
  - This allows frictionless drop-in into LLaMA-Factory (`dataset_info.json` mapping as `formatting: "sharegpt"` / `messages: "messages"`) for rapid scaling exploration across larger open model families (Qwen4, GLM) on multi-GPU cloud nodes.

## 32. Hold-out Test Set Sizing (52 Cases) & XML Provenance Mapping
- **Canonical Hold-out Test Set (52 Cases):**
  - The Tier-1 Gold SFT v2 test set contains exactly 52 cases (4.19% of the 1,241 total; dominated by Narcotics 30 and Theft 10), providing an untainted benchmark for 1-candidate-per-case exports.
  - Every evaluated test candidate must link directly to its origin dossier in `Faruq/dataset/<hash>.xml` alongside the prompt, generated completion, and ground truth completion.

## 34. University DGX A100 (40GB VRAM) Profiling for Intermediate Scales (Qwen 3.5 9B)
- **Architecture & Layer Composition:**
  - `Qwen/Qwen3.5-9B` uses `Qwen3_5ForConditionalGeneration` (9.45B total parameters) with hybrid Gated DeltaNet linear attention and full attention layers.
- **Hardware Sizing on DGX A100 (40GB VRAM):**
  - Base weights in native BF16 consume ~18.9 GB VRAM.
  - On a 40GB A100, micro-batch size 2 with `gradient_accumulation_steps: 4` (effective batch size 8) runs comfortably within ~28–32 GB peak VRAM under 4,096-token context with gradient checkpointing enabled.
  - Trainable LoRA parameters across attention projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `in_proj_qkv`, `out_proj`) and MLP layers (`gate_proj`, `up_proj`, `down_proj`) amount to **36.96M parameters (0.391% of total)**.
  - Provides a powerful, high-throughput stepping stone between 3B local experiments and 27B cloud sweeps.

## 35. Staged Pull Request Hygiene for Multi-Branch AI Research
- When consolidating research code across multiple axes (scaling models, remote automation, training recipes, sampling scripts):
  - **PR Scope:** Group cleanly into production infrastructure (model configs, runner scripts, loader patches, unit tests) and merge via PR.
  - **Exclude Throwaway & Local Artifacts:** Never pollute git history with ad-hoc sampling scripts (`generate_*.py`), raw sample CSV outputs, or uncompiled LaTeX drafts. Keep these in `.gitignore` or local scratch spaces (`artifacts/samples/`).

## 36. Evaluation Sample Distribution & Canonical CLI Standards
- **Keep Git Repositories Lean:** Large generation CSVs (multiple megabytes of output text) and ad-hoc sampling scripts bloat the `.git` directory and degrade repository clarity.
- **Hugging Face Hub as the Single Source of Truth for Evaluations:**
  - Curated, verified benchmark CSVs (e.g. `sft_3b_test_set_25_complete_cases.csv`, `sft_3b_30x3_perfect_samples.csv`) belong in the project's Hugging Face Hub repository under an `evaluations/` directory alongside an informative `README.md`.
  - This keeps code in GitHub and experimental data/checkpoints on Hugging Face Hub, matching production ML standards.
- **Single Canonical Evaluation Runner:**
  - Prune disposable generation scripts and consolidate into a single clean CLI script (e.g. `scripts/evaluate_test_cases.py`) with configurable `--base_model`, `--adapter_path`, `--test_file`, `--output_csv`, left-truncation, and regex verdict clipping.

## 37. Anatomy of Hold-out Test Truncation & Empirical Justification for Model Scaling
- In empirical hold-out testing (52 cases) on smaller 3B models:
  1. **Token Exhaustion on Extensive Trial Records:** Decisions with massive witness testimonies and evidence inventories consume the generation token budget (`max_new_tokens=2200`) during `[PERTIMBANGAN HUKUM]`, cutting off before the model reaches `[AMAR PUTUSAN]`.
  2. **Post-Verdict Registrar Continuation:** Decisions that complete the verdict sometimes append courtroom signatures (*panitera pengganti*) instead of emitting `<|im_end|>`.
  3. **Acquittal (*Vrijspraak*) Divergence:** Decisions acquitting the defendant assess fees to the state (*"membebankan biaya perkara kepada negara"* pursuant to Pasal 191 KUHAP) rather than assessing nominal rupiah fines, causing fee-regex stopping criteria to miss.
- **Academic Thesis Impact:** These empirical failure modes on complex cases provide the rigorous, data-driven rationale for scaling to higher parameter regimes (9B on DGX A100, 27B on RunPod Blackwell) with greater context compression capacity.

## 38. NVIDIA GB10 (Grace Blackwell) Hardware Economics for SFT vs RLHF (PPO/DPO)
- **Architecture Profile:** Single-socket system-on-chip with integrated ARM aarch64 CPU and Blackwell GPU (`sm_121`), 128 GB Unified LPDDR5X RAM, and ~140W TDP (Dell Pro Max with GB10, Asus Ascent GX10, DGX Spark).
- **Economic Evaluation for SFT:**
  - *Capacity:* 128 GB unified memory provides massive headroom, comfortably fitting 12B to 32B models in BF16 LoRA without OOM or complex multi-GPU tensor parallelism.
  - *Throughput vs Bandwidth:* LPDDR5X unified memory bandwidth (~500–800 GB/s) is substantially lower than datacenter HBM3e (>3.0 TB/s). SFT wall-clock time is ~4x–10x slower than dedicated datacenter GPUs (e.g. ~2h40m on GB10 vs ~13m on 8x H200 for 7B models).
  - *Cloud Rental Trade-off:* Rented per hour on cloud platforms, a single fast H100 run finishing in 20 minutes can be cheaper per completed job than running several hours on a slower GB10. However, for an owned on-premise desk-side appliance, 140W power consumption makes long iterative SFT sweeps exceptionally cost-effective.
- **Economic Lifesaver for PPO Prototyping:**
  - PPO requires concurrently hosting four models: Actor ($\pi_\theta$), Reference ($\pi_{\text{ref}}$), Critic ($V_\phi$), and Reward Model ($r_\psi$), plus rollout KV-cache buffers.
  - On standard 40GB/80GB cards, PPO for models $\ge 7\text{B}$ frequently triggers OOM, forcing multi-node/multi-GPU clusters (\$8–\$15/hr).
  - GB10's 128 GB unified address space allows hosting the entire Actor-Critic-Reward quad-model setup on a single machine, dramatically lowering infrastructure barrier and cost for initial PPO prototyping.
  - *Decode Bottleneck:* Rollout token generation in PPO is decode-heavy and constrained by unified memory bandwidth, making batch rollout slower than H100/H200.
- **Software Maturity:** Requires PyTorch nightly + CUDA 13 on ARM aarch64. Native Hugging Face TRL/PEFT is stable; custom distributed frameworks (Megatron-Bridge) require vigilant monitoring for memory fragmentation.

## 39. Modular Academic Thesis LaTeX Architecture & Verifiable Claims Standards
- **Modular Directory Organization:** Maintain chapters cleanly decoupled in `chapters/` (`bab1.tex`, `bab2.tex`, `bab3.tex`) driven by a central `main.tex` and canonical `references.bib`.
- **Verifiable Claim Grounding:**
  - Avoid speculative or ungrounded assertions. Pair every theoretical premise with primary sources:
    - Alignment & Preferences: Rafailov et al. (NeurIPS 2023) for DPO; Schulman et al. (2017) for PPO; Ouyang et al. (NeurIPS 2022) & Christiano et al. (NeurIPS 2017) for RLHF; Hu et al. (ICLR 2022) for LoRA.
    - Statutory Law & Evidence: KUHAP (UU 8/1981 Pasal 184), KUHP, M. Yahya Harahap (2006), Prof. Moeljatno (2008).
    - Legal NLP Benchmarks: Chalkidis et al. (ACL 2022 - LexGLUE), Cui et al. (2023 - ChatLaw), Zhong et al. (ACL 2020), Katz et al. (2024).
- **Placeholder Scaffolding:** Use structured placeholder tables (`[DATA]`) in methodology (Bab III) that define exact metric columns (Amar Completeness, Doom Loop Rate, ROUGE-L, Likert 1–5 Judicial Score, Hallucination Rate) so empirical results from Bab IV seamlessly drop in.

## 40. Multi-GPU Adaptation & Host-RAM Contention in Long-Context Offloading (LLaMA-Factory LongCtx)
- **The Single-GPU Offload Design:**
  - Specialized long-context patch layers (e.g. `llamafactory_textonly_wrapper.py`) fit 32k–128k sequences on 1x A100-40GB by streaming frozen decoder weights from pinned host RAM (`OFFLOAD_WEIGHTS=1`), using Liger kernel fused CE, tiled MLPs, and caching attention forward outputs in pinned RAM (`patch_attention_output_cache`).
  - At 128k context, host RAM footprint per worker is substantial: ~58 GiB for Qwen 3.5 9B and ~89 GiB for Gemma 4 12B (including 16–26 GiB for attention cache).
- **The Multi-GPU DDP Host-RAM Trap:**
  - When adapting to 2x A100 GPUs on a single shared node via standard PyTorch DDP (`torchrun --nproc_per_node=2`):
    - Each GPU worker runs as an independent OS process with its own pinned host allocations (`cudaHostRegister`).
    - Two concurrent workers at 128k require $2 \times 58\text{--}89\text{ GiB} = 116\text{--}178\text{ GiB}$ host RAM.
    - If the physical container/node host RAM is capped at ~130 GiB, the Linux kernel invokes the cgroup OOM killer (`Killed: 9`), terminating the job mid-step.
- **Mitigation & Tuning for 2x A100 Nodes:**
  1. **Disable Attention Output Cache:** Set `export ATTN_CACHE_ABOVE=0`. This forces checkpoint recomputation for attention layers, saving ~16–26 GiB of host RAM per worker with modest compute penalty (~10–15% step time).
  2. **Model Prioritization:** Start multi-GPU sweeps with models with smaller host footprints (Qwen 3.5 9B) before attempting Gemma 4 12B.
  3. **Prefer 2 Independent Single-GPU Runs over DDP:**
     - Instead of running 1 model via DDP (halving epoch time but risking host RAM exhaustion and adding all-reduce communication overhead), allocate GPU 0 to Experiment A (e.g. Qwen 3.5 9B) and GPU 1 to Experiment B (e.g. Gemma 4 12B or Sahabat-AI 9B) using `CUDA_VISIBLE_DEVICES`.
     - Yields two distinct, evaluated model checkpoints in parallel within the same node time window.

## 41. Cloud Marketplace Cost-Throughput Dynamics for Model Scaling (Vast.ai / RunPod)
- **Hourly Price vs Total Job Cost Trap:**
  - Marketplace listings often display similar per-hour rates (e.g. A100 SXM4 80GB @ \$1.059/hr vs RTX PRO 6000 Ada 96GB @ \$1.153/hr).
  - Comparing solely by hourly cost is misleading: RTX PRO 6000 Ada provides 119 TFLOPS and a DLPerf score of ~282.5 (245 DLP/\$/hr), whereas A100 SXM4 delivers 15.6 FP32 TFLOPS and DLPerf of ~120–128 (113 DLP/\$/hr).
  - The 2.3x throughput advantage means an SFT job taking 2.5 hours on A100 completes in ~1.1 hours on RTX PRO 6000 Ada, resulting in lower total cloud expenditure despite the higher hourly rate.
- **VRAM Headroom for Single-Node PPO:**
  - 96 GB VRAM on a single card eliminates the need for multi-GPU sharding or complex FSDP setups when running PPO (which concurrently holds Actor, Critic, Reference, and Reward models).

## 42. Academic Review Dashboard Tunneling & Zero-Trust Faculty Access (Cloudflare Tunnel vs Ngrok)
- **Why Ngrok Creates Friction:**
  - Free ngrok links trigger interstitial warning screens ("You are about to visit an ngrok URL..."), enforce bandwidth/session caps, and change URLs on restarts, creating poor UX for thesis advisors and faculty.
- **Cloudflare Quick Tunnel (Instant & Unthrottled):**
  - Run `cloudflared tunnel --url http://localhost:<port>` to get an instant HTTPS `*.trycloudflare.com` link.
  - Zero registration required, no interstitial warning pages, and no bandwidth throttling.
- **Named Tunnel + Zero Trust Access for Confidential Case Data:**
  - For proprietary or confidential court dossiers, deploy a persistent Named Tunnel on a custom domain (`dashboard.example.com`).
  - Enable Cloudflare Zero Trust Access with an email OTP rule restricted to institutional domains (e.g. `@its.ac.id`) or specific advisor email addresses, ensuring secure, authenticated access without complex VPN setups.



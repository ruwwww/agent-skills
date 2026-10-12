---
name: legal-llm-alignment
description: "Align LLMs on legal and statutory domains (SFT, DPO, PPO)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Legal-LLM, Alignment, DPO, PPO, NeMo-Aligner, Indonesian-Law, RLHF]
---

# Legal LLM Alignment

Methodology and engineering practices for fine-tuning (SFT) and aligning (DPO, PPO, RM) Large Language Models on statutory, criminal, and regulatory legal domains.

## When to Use

- Constructing legal instruction and preference datasets (SFT, DPO, PPO/GRPO, Bradley-Terry RM).
- Defining preference policies (*Chosen* vs *Rejected* criteria) for legal accuracy, due process, and safety.
- Formulating evaluation metrics for legal reasoning (citation recall, hallucination rate, due process compliance).
- Structuring datasets for NVIDIA NeMo-Aligner / Megatron-Core or HuggingFace TRL.

## 1. Legal Preference Policy (Chosen vs Rejected)

In statutory legal domains (e.g., Indonesian Criminal Law / KUHP / KUHAP), preference pairs must enforce legal rigor over persuasive fluency:

### Core Rubric Dimensions

1. **Statutory Citation Precision & Temporal Validity**
   - **Chosen:** Cites exact, applicable articles and paragraphs (e.g., KUHP Pasal 362 vs 363, UU 1/2023 KUHP Nasional, UU ITE 1/2024, UU Tipikor 31/1999 jo UU 20/2001). Distinguishes legacy vs newly enacted statutes.
   - **Rejected:** Hallucinates non-existent statutory numbers, misattributes legal elements, or conflates distinct offenses (e.g., equating premeditated murder Pasal 340 with ordinary murder Pasal 338 based solely on victim count).

2. **Presumption of Innocence (*Asas Praduga Tak Bersalah*)**
   - **Chosen:** Employs objective, conditional language (*cautious legal wording*). Treats allegations as hypotheses requiring judicial proof at trial.
   - **Rejected:** Unilateral conviction (*categorical guilt*), declaring a suspect *"pasti bersalah"*, *"otomatis dipidana"*, or guilty without a court verdict.

3. **Due Process & Burden of Proof (*Beban Pembuktian*)**
   - **Chosen:** Asserts necessity of minimum lawful evidence (e.g., Pasal 184 KUHAP: 2 alat bukti sah), right to legal counsel, and rigorous separation of civil breaches (wanprestasi) from criminal intent (*animus domini*).
   - **Rejected:** Presumes guilt from mere possession or contractual delay, bypassing evidentiary standards.

4. **Non-Malfeasance & Lawful Procedure**
   - **Chosen:** Advises lawful remedies (police reporting, pre-trial motion / *praperadilan*, legal representation).
   - **Rejected:** Advises evidence destruction, evasion of process, witness intimidation, or vigilantism (*eigenrichting*).

See `references/preference-rubric.md` for detailed tabular criteria and concrete Indonesian law case examples.

## 2. Dataset Formats

### NeMo-Aligner Schema
- **SFT:** `{"input": "<prompt>", "output": "<completion>"}`
- **DPO:** `{"prompt": "<prompt>", "chosen_response": "<chosen>", "rejected_response": "<rejected>"}`
- **Reward Model (paired):** Two rows per comparison with `{"text": "<prompt> + <response>", "label": 1}` and `{"text": "<prompt> + <response>", "label": 0}`.
- **PPO:** `{"prompt": "<prompt>"}`

### Hugging Face TRL Schema
- **SFT:** `{"prompt": "<prompt>", "completion": "<completion>"}` (or `{"input": "...", "output": "..."}` mapped with completion-only loss).
- **DPO:** `{"prompt": "<prompt>", "chosen": "<chosen>", "rejected": "<rejected>"}`.

## 3. Legal Evaluation Metrics

Evaluate aligned models along quantitative statutory axes:
- **Citation Recall ($R$):** Fraction of mandatory ground-truth articles correctly cited.
- **Hallucination Rate ($H$):** Ratio of fabricated or invalid statutory citations to total cited articles.
- **Due Process Score ($D$):** Lexical & rubric compliance with procedural safeguards (rewarding *praduga tak bersalah*, *beban pembuktian*, *alat bukti*; penalizing *otomatis bersalah*, *pasti dipidana*).
- **Composite Legal Quality Index ($Q$):** $(R + (1 - H) + D) / 3$.
- **Human Expert Review (0–4 Likert):** Validates nuanced legal reasoning and amar consistency.

## 4. Production Lessons & Pitfalls

See `references/lessons-and-pitfalls.md` for critical empirical lessons from production legal SFT/RLHF runs:
- **The Context Truncation Trap:** Why cross-entropy loss dropping to ~0.90 can be an illusion of legal coherence due to repetitive legal boilerplate memorization under small token caps (2k vs 12k document length).
- **Zero-Prompt Retention & Inviolable Completion Rule:** Ensuring the supervised window captures both indictment facts and terminal verdict (`Amar putusan:`) plus EOS without truncation.
- **5-Pillar Quality Tiering:** Deterministic stratification into Tier 1 (Gold, <=8k tokens, <=2% noise, non-trivial reasoning), Tier 2 (Usable with middle-fact clipping, 8k-16k tokens), and Tier 3 (Reject).
- **Court Document Noise & `_unk_` Normalization:** Contextual normalization of OCR currency and serial placeholders (`[NOMINAL]`, `[NOMOR_SERI]`, `[KODE]`) to prevent repetitive hallucination loops.
- **Split Leakage via Companion Cases (*Perkara Splitsing*):** Deduplicating and grouping near-duplicate court cases before hashing IDs to prevent test contamination.
- **Delivery Standards:** Providing fully executed self-contained `.ipynb` notebooks (native matplotlib/seaborn, no forced HTML wrappers), ready-to-compile Overleaf `.zip` bundles, and 300 DPI / SVG standalone figure galleries over disposable office docs.
- **Compute Dynamics & Epoch Scaling:** Calculating exact step/epoch throughput for curated vs uncurated sets, and scaling multi-hour budgets via epoch depth (3–5 epochs) rather than noise dilution.
- **Daemon VRAM Hygiene:** Safely purging persistent GPU cache from background services (e.g. ComfyUI `/free`) without terminating processes.
- **Unified Multi-Model Hub Staging:** Organizing sequential checkpoints (1-epoch, 5-epoch, DPO, PPO) inside a single Hugging Face project repository using subfolder structures compatible with `PeftModel.from_pretrained(..., subfolder='models/...')` and standalone reproduction recipes.
- **Hardware Economics for SFT vs PPO:** Why compute throughput and VRAM dominate SFT/DPO, whereas HBM memory bandwidth (>2 TB/s) dominates PPO rollout generation, and avoiding activation checkpointing compute traps.
- **Transformers 5.16+ & TRL Compatibility:** Unpacking `_is_package_available` tuple returns to prevent `is_vllm_ascend_available()` false-positive import errors.
- **Judicial Preference Design:** Article 184 KUHAP evidentiary subsumption criteria vs realistic legal LLM failure modes for TRL DPOTrainer.
- **vLLM Rollout & LoRA Weight Streaming:** Dynamic adapter weight synchronization between training policy and vLLM rollout workers.
- **PEFT 0.18 + torchao Dispatch Trap:** Disabling incompatible torchao dispatchers before loading trainable LoRA adapters.
- **Judicial Reward Model Architecture & PPO Scoring Contract:** Sequence classification (`SEQ_CLS`) LoRA training with Bradley-Terry loss and scalar reward batch evaluation decoupled from rollout engines.
- **Multi-Model SFT Candidate Scaling (16GB VRAM Workstation):** Hardware fit guidelines for Qwen2.5-3B (sweet spot BF16 LoRA), Llama-3.2-1B (tokenizer trade-offs), and Qwen2.5-7B (requiring QLoRA NF4).
- **SFT Generation Sample Delivery & Token Budgeting:** Avoiding false-truncation in colleague review samples by setting `max_new_tokens >= 1024` and exporting diagnostic metadata (`is_completed`, `has_amar_putusan`, `finish_reason`).
- **Ephemeral Remote Instance Automation:** Atomic per-experiment lifecycle (Train $\to$ Auto-Eval $\to$ Instant HF Hub Subfolder Upload $\to$ Disk Prune) for preemption-safe cloud ablation sweeps.
- **Verdict Termination Dynamics & Fee Loops:** Halting repetitive *biaya perkara* loops with regex stopping criteria and leveraging batched native PyTorch inference when vLLM CUDA graph capture freezes on CUDA 13.
- **Qwen2.5-3B Scaling & 4096-Token VRAM Budgeting (16GB GPU):** Memory stability recipe (`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, grad accum 8, gradient checkpointing) and snapshot tokenizer symlinking.
- **Parameter Capacity vs Epoch Saturation (3B Doom Loops):** Why 3B models need 5 epochs (705 steps) rather than 3 epochs (423 steps) to saturate the sharp transition from evidence deliberation into terminal verdict dictum (`[AMAR PUTUSAN]`) and `<|im_end|>`.
- **Hardware VRAM Ceilings & Quantized SFT Constraints (7B+ on 16GB VRAM):** The 4,096-token activation barrier for 7B QLoRA on 16GB GPUs, context vs VRAM trade-offs, and dual EOS (`<|im_end|>` vs `<|endoftext|>`) supervision.
- **Left-Truncation Rule in Legal Inference:** Why `truncation_side = 'left'` is strictly required for court dossiers to prevent dropping `<|im_start|>assistant` and causing runaway factual transcription loops.
- **Universal Judicial Dictum Termination & Multi-Variant Fee Regex:** Regex matching `membebankan|membebani|menetapkan` to halt generation cleanly at court fee closures, coupled with `no_repeat_ngram_size = 8` and incremental CSV disk flushing.
- **Autonomous Validation Standard (Zero-Truncation Reporting Rule):** Iterating prompt constraints, token budgets, and stopping criteria autonomously until 100% complete samples are produced before presenting to the user.
- **Gemma 4 Architecture & Thought-Channel SFT Tokenization:** Managing `Gemma4UnifiedForConditionalGeneration`, `<|channel>thought\n<channel|>` chat template behavior, LoRA target modules, and 12B VRAM economics.
- **Minimalist Research Progress Slides Standards:** Clean 16:9 widescreen PowerPoint decks with 14pt bold headers, 12pt body bullets, and direct quantitative reporting for weekly advisor meetings.
- **Qwen 3.8 27B Architecture & Hybrid DeltaNet LoRA:** Resolving `AttributeError` fallback for `Qwen3_5ForConditionalGeneration` and adapting linear + full attention projections (`in_proj_qkv`, `out_proj`).
- **RunPod Cloud Automation & Billing Protection:** End-to-end bootstrap, SFT training, automated subfolder upload to HF Hub, and auto-stop pod termination (`runpodctl stop pod`) on Blackwell / RTX 6000 Ada 48GB+.
- **Evaluation Split Integrity & Raw XML Traceability:** Enforcing zero-train/val leakage in evaluation candidate exports (strictly hold-out `test.jsonl`), linking sample outputs to raw Supreme Court XML dossiers, and maintaining LLaMA-Factory ChatML compatibility for future scaling (Qwen4, GLM).
- **Hold-out Test Set Sizing (52 Cases) & XML Provenance:** Standardized 1-candidate test exports mapped to `Faruq/dataset/<hash>.xml`.
- **Data Cleaning Funnel & Infographic Standards:** High-resolution 4-stage funnel visualization (22.6k raw -> 5-pillar screening -> 3.08k Tier-1 Gold -> 1.24k SFT v2) with explicit drop-off counts and context budgeting rule callouts.
- **University DGX A100 (40GB) Profiling (Qwen 3.5 9B):** Micro-batch 2, grad accum 4, 36.96M trainable LoRA params in 28-32GB peak VRAM.
- **Staged Pull Request Hygiene:** Decoupling core framework/configs into mergeable PRs while isolating local sample CSVs and ad-hoc scripts.
- **Evaluation Sample Distribution & Canonical CLI Standards:** Uploading verified benchmark CSVs directly to Hugging Face Hub (`evaluations/`) rather than bloating Git repositories, while maintaining a single, reusable CLI runner (`scripts/evaluate_test_cases.py`).
- **Hold-out Test Completion Anatomy & Scaling Justification:** Why ~50% of 3B test completions truncate on complex cases (evidence token exhaustion, registrar signatures, and acquittal fee nuances) and how this empirically motivates scaling to 9B/27B.
- **NVIDIA GB10 (Grace Blackwell) Hardware Economics:** Evaluating 128 GB unified memory for SFT (massive headroom vs lower memory bandwidth) and PPO (single-node Actor-Critic-Reward quad-model setup vs multi-GPU clusters).
- **Modular Academic Thesis Scaffolding:** Clean chapter modularity (`main.tex`, `chapters/bab{1,2,3}.tex`, `references.bib`), verifiable grounding in primary citations, and structured placeholder matrices for thesis writing.
- **Multi-GPU Adaptation & Host-RAM Contention in Long-Context Offloading (LLaMA-Factory LongCtx):** Why DDP across 2x A100-40GB can trigger cgroup host RAM OOM-kills at 128k context due to per-worker pinned weight streaming and attention output caching, how setting `ATTN_CACHE_ABOVE=0` mitigates it, and why independent parallel runs on separate GPUs maximize compute cluster allocation.
- **Cloud GPU Marketplace Economics (Vast.ai / RunPod):** Evaluating DLPerf and throughput-per-dollar (e.g. RTX PRO 6000 Ada 96GB @ 245 DLP/$/hr vs A100 SXM4 80GB @ 113 DLP/$/hr) where 2.3x higher compute throughput lowers total job cost despite slightly higher hourly rates.
- **Academic Dashboard Sharing (Cloudflare Tunnel vs Ngrok):** Deploying unthrottled, zero-interstitial web tunnels (`trycloudflare.com`) or Zero Trust named tunnels with institutional email OTP gating (`@its.ac.id`) for advisor review.




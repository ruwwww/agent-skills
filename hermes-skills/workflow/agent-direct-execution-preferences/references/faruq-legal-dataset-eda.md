# Faruq Indonesian Criminal Law Dataset EDA & Alignment Lessons

## 1. Context Window Truncation Bottleneck (The 2,048-Token Failure)
In legal corpora (such as Indonesian Supreme Court / Mahkamah Agung XML decisions):
- **Document Length Reality**: Median full core context (Indictment/Dakwaan + Trial Facts/Fakta + Legal Reasoning/Pertimbangan + Verdict/Amar) is **~12,087 Qwen tokens** (p95: 32,928 tokens).
  - Facts: Median 5,108 tokens
  - Reasoning: Median 3,744 tokens
  - Indictment: Median 2,685 tokens
  - Verdict (Amar): Median 371 tokens
- **The Truncation Trap**: Setting `max_length = 2048` with completion-first packing caused:
  - 15,389 out of 20,457 training examples (75%) to have their completions exceed 2,048 tokens.
  - **Zero prompt tokens**: The prompt (indictment and facts) was completely discarded from the supervised sequence in 75% of examples.
  - **Amputated Amar & EOS**: Only 5,907 examples retained the `Amar putusan:` tag and `<|im_end|>`/EOS token.
  - The model was trained purely to continue arbitrary mid-sentence judicial reasoning without ever seeing the case facts.

## 2. Low-Loss Fallacy & Boilerplate Memorization
- **False Metric**: A cross-entropy loss dropping from 1.76 to 0.903 on legal text is often **not** evidence of coherent legal reasoning.
- **Boilerplate Density**: Indonesian judicial decisions use formulaic boilerplate phrases repeated hundreds of thousands of times (e.g., `menimbang bahwa` appeared >320,000 times in the corpus).
- **Low Entropy**: The model effortlessly minimizes loss by memorizing standard grammatical n-grams (e.g., *"menimbang bahwa berdasarkan keterangan saksi saksi..."*), yielding low loss while producing hallucinatory, unanchored run-on text during generation.

## 3. Traditional Data Science EDA Notebook Contract
When the user requests an EDA notebook and visualizations:
- **No HTML/Slide Hacks**: Do not wrap tables in custom HTML styling or load pre-rendered image files via `display(Image(filename=...))`.
- **Native Inline Plotting**: Every chart must be computed and rendered directly inside code cells using standard `matplotlib.pyplot` and `seaborn` (`fig, ax = plt.subplots(...)`, `sns.barplot(...)`, `plt.tight_layout()`, `fig.savefig('eda/plots/...')`, `plt.show()`).
- **Standard Narrative**: Use clean Markdown cells with domain-informed analysis, followed by native Pandas table inspections (`df.head()`, `df.describe()`).

## 4. GitHub Upload & Delivery: PR Merge vs Direct Push
> "layak di upload tapi bukan melalui push tapi merge"
- When delivering features to collaborative/thesis repositories:
  - Do not direct push (`git push origin main`).
  - Push the dedicated feature branch (`git push -u origin feature/<name>`).
  - Create a GitHub Pull Request (`gh pr create --base main --head feature/<name>`).
  - Merge the PR with `--merge` (`gh pr merge <pr_number> --merge`) so changes enter `main` through a proper merge commit, keeping git history auditable and reviewable.

## 5. Dataset Quality Stratification (Tiering Rubric)
In long-document legal corpora, do not train on raw XML dumps directly. Stratify using explicit criteria:
- **Tier 1 (Gold / High Quality)**: Complete anatomy (Dakwaan, Fakta, Pertimbangan, Amar), non-trivial reasoning (128–4,096 tokens), total core context $\le 8,192$ tokens, noise rate $\le 2\%$, free from heavy OCR artifacts, and substantive-rich.
- **Tier 2 (Usable with Cleaning / Clipping)**: Intact sections, core context 8k–16k tokens, requires section-aware context packing or witness testimony deduplication/middle-clipping.
- **Tier 3 (Reject / Filter Out)**: Runaway reasoning (>4k tokens), runaway context (>16k tokens), missing sections, or purely procedural formality.

## 6. OCR Noise Artifacts & ChatML Normalization
- **`_unk_` Token Source**: In scraped/OCR legal text, `_unk_` tokens typically arise from currency symbols (`Rp`, `Rp.`) before numeric amounts (e.g. `denda sejumlah _unk_ 000 000`) or chassis/engine/indictment serial codes.
- **Normalization Policy**: Intelligently map `_unk_` into semantic placeholders (`[NOMINAL]`, `[NOMOR_SERI]`, `[KODE]`) rather than letting the LLM memorize and echo raw `_unk_` tokens.
- **Inviolable Completion Rule**: In SFT token budgeting, allocate max ~2,500 tokens for prompt and ~1,500 tokens for completion. If facts are too long, clip from the middle of witness lists, but NEVER clip Indictment, Legal Reasoning, Amar Putusan, or EOS (`<|im_end|>`).
- **Completion-Only Loss Masking**: Always mask system and user prompt tokens with label `-100`, supervising strictly after `<|im_start|>assistant\n`.

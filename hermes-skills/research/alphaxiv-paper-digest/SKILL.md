---
name: alphaxiv-paper-digest
description: Digest arXiv and alphaXiv papers using alphaXiv MCP tools.
version: 0.1.0
author: Izzuddin Al Faruq (ruwwww), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, alphaxiv, paper-digest, arxiv, mcp]
    related_skills: [arxiv, literature-review]
---

# AlphaXiv Paper Digest Skill

Digest and analyze research papers from arXiv and alphaXiv into structured, high-signal technical digests using alphaXiv MCP tools.

## When to Use

- When the user asks to summarize, digest, or analyze a paper via alphaXiv or arXiv URL / ID / title.
- When extracting deep technical architectures, mathematical formulations, benchmarks, or ablation results.
- When synthesizing cross-paper lineages and comparing distillation/diffusion/ML architectures.

Don't use for:
- Generic non-academic web pages (use `web_extract`).
- In-depth multi-source systematic literature mapping over dozens of papers (use `literature-review`).

## Prerequisites

- Access to `alphaxiv` MCP tools:
  - `mcp__alphaxiv__get_paper_content` (fetch structured report or raw full text).
  - `mcp__alphaxiv__answer_pdf_queries` (query specific sections or equations directly from PDF).
  - `mcp__alphaxiv__discover_papers` (find related works or citations).

## Procedure

1. **Retrieve Paper Content**:
   - Call `mcp__alphaxiv__get_paper_content(url=...)` to retrieve the structured intermediate report.
   - If output spills over to disk (`/home/kuroko/.hermes/cache/spillover/...`), inspect with `read_file` or `execute_code` without re-fetching.
   - If deeper equation verification or specific section analysis is needed, call `mcp__alphaxiv__answer_pdf_queries(paper=..., queries=[...])`.

2. **Extract Core Technical Artifacts**:
   - **TL;DR & Problem Statement**: Exact bottleneck in prior work (e.g., latent vs pixel diffusion, distillation instabilities).
   - **Core Novelty & Architecture**: Specific mathematical formulations, loss functions, and architectural changes.
   - **Empirical Results & Benchmarks**: Exact benchmark figures (NFE, FID, GenEval, DPG-Bench, CLIP, throughput s/step).
   - **Ablation Studies**: Component breakdown (contributions of each loss/module, hyperparameter sweeps).
   - **Lineage & Context**: Direct predecessor methods and related papers.

3. **Format & Delivery SOP (High Signal, Structured & Actionable)**:
   - Karena pengguna menginginkan format penjelasan yang matang dan langsung pakai, terapkan struktur standar **"High-Signal Paper Breakdown"**:
     - **Ringkasan Eksekutif (TL;DR 3 Poin Kunci)**: Masalah utama yang dipecahkan, inti solusi/inovasi baru, dan hasil kuantitatif terbesar.
     - **Akar Masalah & Keterbatasan Metode Terdahulu**: Mengapa pendekatan sebelumnya (SOTA lama) gagal atau tidak efisien.
     - **Arsitektur & Inovasi Teknis (How It Works)**:
       - Mekanisme kerja inti, diagram alur/komponen, formulasi matematis utama (dalam plain-text/LaTeX bersih).
       - Modifikasi arsitektural spesifik (misal: layer DiT, mekanisme atensi, loss function).
     - **Tolok Ukur & Hasil Eksperimen (Empirical Benchmarks)**:
       - Metrik terverifikasi (FID, CLIP score, throughput, latency per step, VRAM).
       - Studi ablasi kunci: modul mana yang paling berdampak besar.
     - **Relevansi & Takeaways Praktis**:
       - Bagaimana teknik ini bisa diimplementasikan atau diadaptasi pada stack/proyek kita sendiri (misal: Anima DiT, LoRA training, inference fast-path).
       - Trade-off, keterbatasan, dan jebakan implementasi yang perlu diwaspadai.
   - **Gaya Bahasa & Nada Bicara**:
     - Bahasa Indonesia teknis, padat, lugas, presisi tinggi.
     - Hindari analogi/metafora berlebihan. Fokus pada angka, bukti eksperimen, dan mekanisme komputasi riil.
     - Pada Discord: Gunakan format list berlabel atau bullet points terstruktur (jangan gunakan tabel markdown lebar yang rusak di mobile Discord).
   - **Google Docs Export (Opsional via Composio jika diminta / laporan panjang)**:
     - Jika dokumen memerlukan arsip laporan lengkap, buat via Composio Google Docs dan sertakan tautannya di Discord.

## Pitfalls

- **Spillover Handling**: Do NOT re-fetch large papers from the remote API if cached on disk. Use Python via `execute_code` or `read_file`.
- **Discord Rendering**: Standard markdown tables break on mobile Discord. Use clean labeled lines, monospace code blocks, or nested bullet lists for metrics.
- **Precision**: Report exact metric names and steps (e.g., NFEs, DPG-Bench, GenEval, IS, NIQE, VQAScore).

## Verification

- Confirm all core loss formulas, parameters, and benchmark numbers match the paper data directly.
- Verify the digest satisfies user-specific formatting preferences (Concise Indonesian, TL;DR top, layered details, no metaphors).

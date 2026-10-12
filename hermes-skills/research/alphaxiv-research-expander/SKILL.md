---
name: alphaxiv-research-expander
description: Expand known papers into related research and brainstorms.
version: 0.1.0
author: Izzuddin Al Faruq (ruwwww), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, alphaxiv, paper-expansion, brainstorming, lineage, mcp]
    related_skills: [alphaxiv-paper-digest, alphaxiv-problem-scout]
---

# AlphaXiv Research Expander Skill

Expand from a known/digested paper to discover upstream foundations, downstream successors, parallel ideas, and actionable brainstorming angles.

## When to Use

- When the user already knows or has digested a paper (e.g., FreeFlux, Engram, RAE, TinyEngram) and asks:
  - "Paper apa lanjutannya / yang mencite paper ini?"
  - "Bagaimana cara mengekspansi ide ini ke domain/kasus lain?"
  - "Cari varian/paper pembanding yang mengambil ide serupa."
  - "Brainstorming arah riset/eksperimen lanjutan dari paper ini."

Don't use for:
- Initial single-paper breakdown (use `alphaxiv-paper-digest`).
- Scouting from an open/generic problem without a seed paper (use `alphaxiv-problem-scout`).

## Prerequisites

- Access to `alphaxiv` MCP tools:
  - `mcp__alphaxiv__discover_papers`
  - `mcp__alphaxiv__get_paper_content`
  - `mcp__alphaxiv__answer_pdf_queries`

## Procedure

1. **Map Lineage & Connected Nodes**:
   - Ambil paper benih (*seed paper*). Identifikasi mekanisme inti yang membuatnya berhasil.
   - Telusuri 3 arah silsilah:
     - **Downstream Successors (Penerus Langsung)**: Paper terbaru yang mencite, memperbaiki kelemahan, atau mengoptimalkan paper benih (misal: FreeFlux -> SynPS).
     - **Cross-Domain Adaptations (Ekspansi Domain)**: Adaptasi mekanisme yang sama ke domain/modalitas berbeda (misal: LLM Engram -> DiT TinyEngram).
     - **Orthogonal Combinations (Kombinasi Silang)**: Paper independen lain yang bisa dikawinkan untuk efek sinergis.

2. **Structure the Expansion & Brainstorm**:
   Sajikan laporan ekspansi dengan struktur lugas tanpa basa-basi:
   - **Seed Anchor (1-2 kalimat)**: Mekanisme inti dari paper rujukan yang sedang diekspansi.
   - **Direct Evolution & Successors (Paper Penerus Terkuat)**:
     - Nama paper, arXiv ID, dan perbaikan spesifik apa yang ditawarkan terhadap keterbatasan paper benih.
   - **Cross-Domain & Parallel Counterparts**:
     - Paper atau karya yang menerapkan intuisi serupa di modalitas/arsitektur lain.
   - **Concrete Brainstorming Angles (Ide Eksperimen Terapan)**:
     - 2–3 ide eksperimen/proyek spesifik yang menggabungkan teknik ini ke dalam stack lokal kita (misal: Anima DiT, LoRA fastpath, RL alignment, dataset curation).
     - Hipotesis teknis: mengapa kombinasi ini masuk akal secara matematika/komputasi.
   - **Next Immediate Action**: Satu langkah verifikasi/pengujian tercepat (kode/skrip/paper lanjutan) yang paling menjanjikan.

## Rules & Constraints

- **To-The-Point & Direct**: Tanpa basa-basi, langsung sajikan data dan ide teknis.
- **Discord-Friendly**: Gunakan bullet points atau labeled lines yang rapi di Discord mobile.
- **No Speculative Fluff**: Semua rekomendasi paper harus berbasis karya ilmiah riil di arXiv/alphaXiv dengan ID jelas.

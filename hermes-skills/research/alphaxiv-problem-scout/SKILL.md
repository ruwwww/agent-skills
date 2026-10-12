---
name: alphaxiv-problem-scout
description: Scout and explore papers on alphaXiv to solve ML problems.
version: 0.1.0
author: Izzuddin Al Faruq (ruwwww), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, alphaxiv, problem-scouting, literature-exploration, arxiv, mcp]
    related_skills: [alphaxiv-paper-digest, literature-review, arxiv]
---

# AlphaXiv Problem Scout Skill

Systematically scout, discover, and synthesize research papers from alphaXiv/arXiv to solve specific technical problems, bottlenecks, or exploratory research directions.

## When to Use

- When the user asks to explore literature for a specific research problem or engineering bottleneck (e.g. "how to fix attribute bleeding in DiT", "approaches for non-rigid pose editing", "fast ODE samplers for flow-matching").
- When comparing competing paradigms/approaches across multiple papers to solve a single problem.
- When finding relevant papers or lineage when the exact paper title is not yet known.

Don't use for:
- Deep breakdown of a single known paper (use `alphaxiv-paper-digest`).
- General web search without academic literature focus (use `web_search`).

## Prerequisites

- Access to `alphaxiv` MCP tools:
  - `mcp__alphaxiv__discover_papers(keywords=..., question=..., difficulty=..., prioritize=...)`
  - `mcp__alphaxiv__get_paper_content(url=...)`
  - `mcp__alphaxiv__answer_pdf_queries(paper=..., queries=[...])`

## Procedure

1. **Formulate Search Queries & Problem Angles**:
   - Deconstruct the user's problem into core scientific keywords, mechanisms, and constraints.
   - Call `mcp__alphaxiv__discover_papers` with targeted queries, setting `prioritize='recency'` or `'relevance'` as needed.
   - Identify candidate papers that tackle the same core problem from distinct angles.

2. **Cross-Paper Analysis & Clustering**:
   - Group discovered approaches into 2-4 distinct technical paradigms (e.g., Training-Free Attention Manipulation vs Latent Regularization vs Architecture Modification).
   - Read/inspect the candidate papers using `mcp__alphaxiv__get_paper_content`.

3. **Format & Delivery (Problem-Driven Synthesis)**:
   Deliver a high-signal report structured as:
   - **Problem Framing & Core Dilemma**: Concise definition of why this problem is hard.
   - **Landscape of Approaches (Peta Solusi Literatur)**:
     - Kelompokkan paper ke dalam rumpun pendekatan (misal: Paradigma A vs Paradigma B).
     - Untuk setiap paper kunci: sebutkan nama paper, tahun/arXiv ID, mekanisme inti, dan kelebihan/kelemahannya.
   - **Trade-off Comparison**:
     - Bandingkan dari segi biaya komputasi, kemudahan implementasi, kebutuhan pelatihan vs training-free, dan retensi kualitas.
   - **Actionable Verdict & Recommended Path**:
     - Rekomendasi pendekatan terbaik yang paling cocok dengan hardware/stack kita (misal: RTX 5060 Ti, ComfyUI, Cosmos 2 DiT).
     - Langkah konkret pertama untuk menguji atau memvalidasi solusi tersebut.

## Rules & Constraints

- **Discord-Friendly**: Use bullet lists, labeled rows, or code blocks. Never use wide Markdown tables.
- **Empirical & Direct**: Avoid speculative claims or vague hand-waving. Cite exact arXiv IDs and empirical metrics reported by authors.
- **Concise Indonesian**: Professional, high-density technical Indonesian. No unnecessary metaphors or STEM analogies.

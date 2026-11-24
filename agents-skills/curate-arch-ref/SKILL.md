---
name: curate-arch-ref
description: Creates curated architectural reference entries for the Architectural Reference Index at ~/arch-ref. Use when the user asks to add a repository to the index, wants to catalog a reference project, or says "curate this repo."
---

# Locations

- **Entries directory:** `~/arch-ref/entries/` — contains one `{slug}.yml` file per entry
- **Template:** `~/arch-ref/entries/_template.yml` — use as reference for field structure
- **Index + MCP server:** `~/arch-ref/mcp/index.py` and `server.py`
- **Skill file (this file):** `~/.agents/skills/curate-arch-ref/SKILL.md`

Before curating a new entry, read at least 2-3 existing entries from the entries directory to absorb the conventions for domain naming, concern vocabulary, narrative tone, and tag style.

# Curation Process

Given a GitHub repository URL, create a standardized entry for the Architectural Reference Index.

## Steps

### 1. Multi-turn DeepWiki exploration

Do NOT stop after a single read or one question. Conduct **at least 3-4 rounds** of DeepWiki queries to build proper understanding. The goal is **problem-space understanding**, not technical documentation — avoid gathering file paths, module listings, or implementation details.

**Round 1 — Orientation:** Start with `deepwiki_read_wiki_contents` to get the overall structure and surface topics. Then probe the project's identity:

- What problem does this project solve in the real world?
- What gap does it fill that alternatives don't?
- What is the core architectural challenge or pattern that makes this project interesting?

**Round 2 — Deepen:** Follow up on what you found in Round 1. Ask about specific architectural patterns, design decisions, or trade-offs that seemed interesting:

- "You mentioned X pattern — what makes this approach different from Y?"
- "How does the project handle [specific concern like offline sync, multi-tenancy, etc.]?"
- "What were the key design trade-offs in [area that seemed relevant]?"

**Round 3 — Reference extraction:** Probe for what someone would learn from studying this codebase:

- "What are 2-4 specific architectural patterns or decisions in this project that are worth studying in isolation?"
- "What recurring design problems does this project solve in an elegant way?"
- "If someone wanted to extract one pattern from this codebase for use in another project, what would it be?"

**Round 4 — Gap check:** Ask yourself: can I write all four narrative fields from what I know? If any field feels thin, ask one more targeted question. Common gaps:

- The real-world problem isn't sharply stated → ask about alternatives and what makes this one necessary
- The core architectural challenge is vague → ask about the hardest design decision
- The reference patterns aren't concrete → ask what decisions a new contributor should understand first

Do NOT proceed to writing until you could explain the project's architecture to another engineer without referring to specific file paths.

### 2. Determine the slug

Format: `{owner}_{repo}` (GitHub owner and repo name, case-sensitive).

### 3. Classify the entry

| Field | How to determine |
|---|---|
| `domain` | The single best category (knowledge-base, auth, payments, cms, dev-tools, monitoring, ci-cd, music-streaming, etc.) |
| `tech_stack` | Only the primary language per layer. List items not versions. |
| `concerns` | 3-6 architectural concerns this repo addresses (content-management, permissions-and-access-control, offline-sync, realtime-collaboration, multi-tenancy, event-sourcing, cqrs, etc.) |
| `tags` | Free-form: self-hosted, SaaS, PWA, open-source, cross-platform, local-first, etc. No stack names. |

### 4. Write the four narrative fields

Each field is a **single paragraph** — 2-4 sentences. These are embedding targets for vector search, so write naturally but densely.

The narrative must focus on **technologies, techniques, and problems** — not specific frameworks, languages, or libraries. The `tech_stack` field captures the implementation choices; the narrative fields capture what is architecturally interesting regardless of stack.

| Field | What to write | Do NOT mention |
|---|---|---|
| `description` | One-liner: what the project is in plain terms. "A self-hosted X that does Y." | Specific frameworks, languages, libraries |
| `problem` | The real-world gap. "How do you build an X that handles Y while also Z?" Frame as a question or need. | Language/framework justifications |
| `concern` | The core architectural challenge. "The main design challenge is..." Focus on what makes the architecture worth studying. | Specific stack choices — use general technique names (dual rendering pipeline, service-repository pattern, daemon-sidecar, etc.) |
| `reference` | What to extract from studying it. "Demonstrates how to..." 2-4 specific patterns or decisions worth noting. | Framework-specific terminology — use generalizable pattern names |

Good narrative example (concern field):
> "The main design challenge is composing and enforcing a multi-layered prompt stack that makes a general-purpose coding agent behave like a senior designer. This requires orchestrating a daemon-and-runtime architecture where a privileged local process manages agent lifecycle, filesystem access, and plugin resolution, while a library of brand contracts and a structured quality-gate pipeline provide quality enforcement — all without owning the underlying AI model."

Bad narrative example (too stack-specific):
> "Built with Node.js and Express on the backend with a React frontend..."

### 5. Save the entry

Save to `~/arch-ref/entries/{slug}.yml`.

Follow the format in `_template.yml` exactly. Use `>` for multi-line YAML strings (folded block scalars — newlines become spaces).

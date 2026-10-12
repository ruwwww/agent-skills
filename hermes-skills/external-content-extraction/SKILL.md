---
name: external-content-extraction
description: "Extract and analyze content from external sources (GitHub PRs, blogs, docs) without authentication. Digest, summarize, and provide structured insights."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Extraction, Analysis, Summarization, External-Content]
    related_skills: [github-code-review, web-search, debugging-hermes-tui-commands]
---

# External Content Extraction & Analysis

Extract, analyze, and summarize content from external sources without requiring authentication or API access. Useful for research, understanding PRs, reading documentation, and providing structured insights.

## Prerequisites

- No special setup needed — uses built-in web extraction capabilities
- For web extraction, the web tool is automatically configured for standard web pages

---

## Use Cases

This skill is appropriate when:

1. **User provides a URL to extract:**
   - GitHub PR/Issue URLs
   - Blog posts (Medium, Zhihu, personal blogs)
   - Documentation pages
   - Research papers (arXiv)
   - Any publicly accessible webpage

2. **Content needs structured analysis:**
   - Summarize key points
   - Extract technical details
   - Create structured digests
   - Compare with local knowledge

3. **Cross-lingual content:**
   - Extract content in any language
   - Output summary in user's preferred language

4. **No authentication available:**
   - Content behind GitHub requires auth (web extraction may still get metadata)
   - Private repos, docs with auth walls
   - Rate-limited APIs

---

## 1. URL Extraction Workflow

### Step 1: Try Direct Extraction

When the user provides a URL, attempt direct extraction first:

```bash
# Extract content from the URL
web_extract(["https://github.com/owner/repo/pull/123"])
# or
web_extract(["https://zhuanlan.zhihu.com/p/123456"])
```

**If extraction succeeds:**
- Parse the markdown/raw content
- Identify key sections (title, body, discussion, code changes)
- Generate structured summary

**If extraction fails (HTTP 403, 404, etc.):**
- Fall back to web search for metadata
- Explain the limitation to the user
- Offer alternatives (search, manual input, authenticated access)

### Step 2: Parse and Analyze

For each extracted source, identify:

**For GitHub PRs:**
- Title and description
- Author and date
- Branch information
- Files changed
- Commits list
- Reviewer comments/discussion
- Labels/milestones (if available)

**For Blogs/Articles:**
- Title and subtitle
- Author and publication date
- Key sections/headings
- Main arguments or findings
- Code examples (if any)
- Links to related content

**For Documentation:**
- Section hierarchy
- API signatures
- Usage examples
- Prerequisites and setup

### Step 3: Generate Digest

Create a structured summary with:

```markdown
## 📋 Summary

[High-level overview in 2-3 sentences]

## 🔍 Key Findings

- [Finding 1 with context]
- [Finding 2 with context]
- [Finding 3 with context]

## 💡 Technical Details

- [API signature, formula, or method]
- [Parameters and behavior]
- [Dependencies or prerequisites]

## ⚠️ Notes/Caveats

- [Important limitations]
- [Version-specific behavior]
- [Known issues]

## 🔗 Related Links

- [Link 1]
- [Link 2]
```

---

## 2. Analysis Techniques

### For Technical Content (Code, Algorithms)

Identify and extract:

1. **Key contributions/improvements:**
   - New features, optimizations, bug fixes
   - Performance metrics (throughput, latency, memory)
   - Comparison with alternatives

2. **Implementation details:**
   - Architecture or algorithm explanations
   - Data structures and patterns
   - Configuration parameters

3. **Validation/testing:**
   - Test coverage, benchmarks
   - Validation results
   - Performance comparisons

### For Research/Analysis Content

Identify and extract:

1. **Core hypothesis/methodology:**
   - Problem statement
   - Proposed solution/approach
   - Key insights

2. **Experimental results:**
   - Setup (model size, dataset, epochs)
   - Comparison baselines
   - Metrics achieved

3. **Conclusions and implications:**
   - What works, what doesn't
   - Practical recommendations
   - Open questions

### For Hyperparameter/Architecture Exploration

Special attention to:

1. **Ablation studies:**
   - Which components matter most
   - Tradeoffs explored
   - Surprising findings (e.g., "Simpler approach beats complex one")

2. **Design decisions:**
   - Why X over Y
   - Alternative approaches considered
   - What was tried but rejected

---

## 3. Cross-Lingual & Style Handling

### Language Detection
1. **Extract content in original language** (preserve source text)
2. **Identify user's preferred language** from conversation context
3. **Summarize and analyze in user's language** (default to Indonesian if user uses Indonesian/Malay)
4. **Preserve key terms in original** (technical terms, code, model names)

### User Preference Defaults
When user requests paper digest/summary:
- **Default output format:** Structured markdown with TL;DR at top
- **Audience:** Layperson-friendly explanations (avoid jargon without plain-language analogies)
- **Structure:** 
  - TL;DR (1-3 sentences, high-level)
  - Key findings (table + bullet points)
  - Technical details (simplified)
  - Comparative analysis if multiple sources
- **Tone:** Direct, actionable, no lengthy explanations
- **Visuals:** Use tables, bold text, and structured sections for readability

**Example flow:**
```
Input: "tolong digest dan berikan tldr" (Indonesian)
→ Extract paper (English content)
→ Output digest in Indonesian with:
   - TL;DR singkat
   - Ringkasan poin kunci (dengan analogi awam)
   - Detail teknis sederhana
   - Perbandingan jika ada banyak paper
```

---

## 3.1 Scientific Paper Digest Format

When digesting research papers (Nature, arXiv, etc.):

```markdown
## 📄 Digest: [Paper Title]

**Journal** • **Published**  
**DOI:** [link]

---

### 🎯 TL;DR (Singkatnya)
[1-3 sentence high-level summary in layperson terms]

### 🔬 Apa yang Mereka Temukan?
| Step | Apa yang Terjadi |
|------|------------------|
| 1 | [Brief description] |
| 2 | [Brief description] |

### ⚡ TL;DR Fundamental
[Even simpler analogy for lay audience]

### ⚠️ Keterbatasan
- [Limitation 1]
- [Limitation 2]
```

**Best Practices for Research Digests:**
1. **Layered explanation:** Start with TL;DR, then build detail
2. **Analogies for lay audience:** Compare complex mechanisms to everyday concepts
3. **Comparative analysis:** When multiple papers exist, highlight connections
4. **Direct over verbose:** Prefer structured digests over lengthy essays

---

## 4. Output Formats

By default, provide a structured markdown digest. You can adapt based on context:

### Research/Digest Format (Default)

Structured sections:
- Summary
- Key findings
- Technical details
- Conclusions
- Related links

### Code Review Format

When analyzing GitHub PRs:
- Critical issues
- Warnings
- Suggestions
- Files changed
- Line-by-line review (if needed)

### Comparative Format

When comparing multiple sources:
- Side-by-side comparison
- Synthesis of findings
- Contradictions or disagreements
- Unified recommendations

---

## 5. Limitations

### What This Skill Does NOT Handle:

1. **Private content:**
   - Private GitHub repos/issues
   - Authenticated-only pages
   - Content behind paywalls

2. **Non-web sources:**
   - Files on local filesystem (use `read_file` instead)
   - Local git repositories (use `github-repo-management` instead)
   - Database/query results

3. **Interactive content:**
   - JavaScript-heavy web apps
   - Content loaded after JS execution
   - Dynamic dashboards

### Workarounds:

- For private GitHub content: Use `github-auth` skill to authenticate, then `github-code-review`
- For complex apps: Use `browser` tool to navigate and inspect
- For local content: Use local file tools instead

---

## 6. Best Practices

1. **Always mention source:** Include URLs in summaries for reproducibility

2. **Acknowledge uncertainty:** If source is unclear or partial, note it

3. **Preserve key details:** Don't copy-paste entire articles; summarize

4. **Cross-reference:** Link back to original sources when possible

5. **Respect context:** Adapt depth of analysis to user's expertise level and question

---

## 7. Example Workflows

### Workflow 1: GitHub PR Analysis

User: "Review this PR: https://github.com/NVIDIA-NeMo/Automodel/pull/3747"

Agent:
1. `web_extract(["https://github.com/NVIDIA-NeMo/Automodel/pull/3747"])`
2. Parse PR markdown content
3. Identify: title, author, commits, changes, review comments
4. Generate structured analysis:
   - What does the PR do?
   - Changes made
   - Validation performed
   - Review feedback
   - Technical approach

### Workflow 2: Research Blog Digest

User: "Digest this article: https://zhuanlan.zhihu.com/p/12345"

Agent:
1. `web_extract(["https://zhuanlan.zhihu.com/p/12345"])`
2. Parse content, identify key sections
3. Extract: hypothesis, methodology, results, conclusions
4. Generate bilingual summary (content in Chinese, output in user's language)

### Workflow 3: Comparative Analysis

User: "Compare these two PRs: https://github.com/A/pull/123 and https://github.com/B/pull/456"

Agent:
1. `web_extract(["https://github.com/A/pull/123", "https://github.com/B/pull/456"])`
2. Parse both PRs
3. Create comparison table
4. Highlight similarities, differences, tradeoffs

---

## 8. Integration with Other Skills

This skill complements:

- **`github-code-review`**: Handle public URL extraction when auth isn't available
- **`web-search`**: Fallback when direct extraction fails
- **`debugging-hermes-tui-commands`**: Extract context for TUI debugging
- **`documentation-and-adrs`**: External docs as source for local ADRs
- **`research-paper-writing`**: External sources for literature review

---

## 9. Pitfalls & Gotchas

### Web Extraction Issues

1. **403 Forbidden:**
   - GitHub blocks some extraction attempts
   - **Fix:** Fall back to web search for metadata, or use auth via `github-code-review`

2. **Login-walled content:**
   - Zhihu, some blogs require login
   - **Fix:** Acknowledge limitation, offer search-based info

3. **JavaScript-heavy pages:**
   - Content loaded via client-side JS isn't captured
   - **Fix:** Use `browser` tool if available

### Analysis Issues

1. **Over-extraction:** Don't copy-paste entire articles; summarize
2. **Out of context:** Note if findings depend on specific version/setup
3. **Inaccurate extraction:** If extraction fails, note partial info only

---

## 10. Quick Reference

| User Input | Action | Tool |
|------------|--------|------|
| GitHub URL | Extract PR/Issue | `web_extract` + Parse |
| Blog URL | Extract article | `web_extract` + Summarize |
| Doc URL | Extract sections | `web_extract` + Structure |
| Authenticated content | Extract + Review | `github-auth` + `github-code-review` |
| Cross-lingual | Extract + Translate | `web_extract` → Summarize in target language |
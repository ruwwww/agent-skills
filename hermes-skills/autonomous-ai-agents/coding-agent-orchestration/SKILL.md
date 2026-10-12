---
name: coding-agent-orchestration
description: Use when orchestrating Codex CLI for implementation tasks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [autonomous-agents, coding-agent, codex, delegation, orchestration]
    related_skills: [codex, claude-code, subagent-driven-development]
---

# Coding Agent Orchestration

Orchestrate external CLI coding agents (such as OpenAI Codex CLI or Claude Code) as bounded, cost-effective implementation workers while Hermes retains supervisory ownership, context setup, verification, and reporting.

## Core Philosophy: Pre-Spawn Context & Token Optimization

External coding models (especially deep-reasoning models like GPT-5.6 Luna xhigh or Claude 3.7 Sonnet thinking) consume substantial tokens and time if forced to explore the environment, search for datasets, install dependencies, or infer architecture decisions.

Hermes must do the heavy lifting **before** spawning the agent:
1. **Dependency & Environment Verification**: Inspect and verify interpreters, packages, and GPU devices.
2. **Data & Path Preparation**: Locate and verify dataset directories, sample formats, and paths.
3. **Repository & Config Scaffolding**: Initialize git repositories, add directories to trusted configurations (e.g. `~/.codex/config.toml`), and create clear architecture specifications (`README.md`, `tasks/plan.md`, or `tasks/todo.md`).
4. **Baseline Smoke Tests**: Write and verify data loaders or minimal scripts first so the subagent has a working ground-truth reference.

## Workflow & Lifecycle

### 1. Preparation Phase (Hermes-Owned)
- **Git Repository**: Initialize a clean git repo if one does not exist (`git init && git commit -m "initial scaffolding"`). Codex refuses to run outside a git repository.
- **Trust Configuration**: Ensure the target directory is added to `~/.codex/config.toml` under `[projects."/path/to/repo"] trust_level = "trusted"`.
- **Pre-flight Checks**: Verify GPU/CUDA availability, Python virtual environments, and required packages. Write a verified baseline loader or entry point.
- **Specification Document**: Write a concise `README.md` or task specification detailing:
  - Exact file paths to implement.
  - Core architectural equations, channel counts, and hyperparameter constraints.
  - Expected unit tests and validation metrics.

### 2. Spawning Phase (Token-Efficient Delegation)
- **Command Selection**:
  - For single-shot autonomous builds: `codex exec --yolo "<concise_instruction>"`.
  - For long-running tasks: Run in background with `pty=true`, `background=true`, and `notify=true`.
  - Pass the concrete tasks file or refer to `README.md` rather than pasting giant raw text blobs in the prompt.
- **Model & Reasoning Control**:
  - Respect requested model configurations (e.g. `-m gpt-5.6-luna -c model_reasoning_effort=xhigh`).

### 3. Monitoring & Triage
- Poll the background process (`process(action="poll", session_id=...)`) and inspect logs without sending disruptive inputs.
- If the agent hangs or enters recursive reasoning loops without producing files, inspect git status to check partial progress.

### 4. Reconciliation, Verification & Reporting
- **Independent Verification**: Never trust the subagent's self-report. Hermes must independently run tests using the target environment:
  `PYTHONPATH=. <python_path> -m pytest tests/`
  and execute a minimal real training/inference smoke test.
- **Visual Artifacts**: When image or media artifacts are generated, inspect them and deliver them directly via native platform handlers (e.g. `MEDIA:/absolute/path/to/file` on Discord).
- **Technical Reporting (Google Docs)**:
  - Export structured findings, architectural breakdowns, and benchmark metrics to Google Docs via Composio (`GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN` or `GOOGLEDOCS_INSERT_TEXT_ACTION`).
  - Share the clean reading link with the user alongside a concise executive summary.
  - **Legibility Rule**: Strictly avoid raw, unrendered LaTeX markup in Discord and Google Docs markdown. Use clean plain-text or unicode formulas.

## Common Pitfalls

- **Spawning into an unconfigured directory**: Codex prompts for interactive trust confirmation if not pre-configured in `~/.codex/config.toml`. Always set trust level beforehand.
- **Vague specifications**: If instructions do not specify exact layer dimensions, downsampling factors, or normalization formulas, the agent will guess or write overly complex stubs.
- **Assuming self-reported tests passed**: Always re-run pytest and check git diff from Hermes.

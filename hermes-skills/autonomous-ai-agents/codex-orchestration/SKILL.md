---
name: codex-orchestration
description: Use when delegating to Codex CLI. Prepares env & context.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [autonomous-agents, codex, orchestration, token-efficiency, code-generation]
    related_skills: [codex, kanban-codex-lane, hermes-agent]
---

# Codex Orchestration & Cost-Efficient Babysitting

This skill defines the operational protocol for Hermes to orchestrate, babysit, and verify OpenAI Codex CLI (`codex`) execution across **any stack or domain** (Python, TypeScript/Node, Rust, C++/CUDA, Go).

The core principle is **Zero-Token-Waste**: Hermes performs all environment verification, dependency resolution, workspace isolation, architectural scaffolding, and test harness setup *before* spawning Codex. Codex is invoked strictly as a scoped implementation worker—never for open-ended environment discovery, trial-and-error dependency installations, or exploratory planning.

---

## 1. The Zero-Token-Waste Architecture

Codex uses heavy reasoning models (such as `gpt-5.6-luna` with `xhigh` reasoning effort). Token consumption and runtime explode if Codex is allowed to:
- Probe system compilers, package managers, CUDA drivers, or runtime environments.
- Guess file paths, schemas, or trial-and-error install missing dependencies.
- Plan broad architecture from open-ended natural language prompts.

### Responsibility Matrix
| Stage | Hermes Agent (Orchestrator) | Codex CLI (Worker) |
| :--- | :--- | :--- |
| **1. Toolchain & Env** | Detects & verifies exact binary paths (`python`, `node`, `cargo`, `nvcc`). Pre-installs all packages. | Consumes exact pre-verified toolchain without querying environment. |
| **2. Workspace & Git** | Creates git repo or isolated `git worktree`. Configures `~/.codex/config.toml` trust level. | Works strictly within the designated git workspace. |
| **3. Contract & Specs** | Writes `README.md`, `tasks/plan.md`, public API contracts, and test harness. | Reads concrete contracts, implements required modules. |
| **4. Execution & Watch** | Spawns background process with PTY; monitors logs and resource usage. | Writes code, runs provided test suite, exits upon completion. |
| **5. Reconciliation** | Independently inspects `git diff`, reruns test suite, benchmarks performance. | N/A (Codex self-reports are treated as unverified). |
| **6. Delivery** | Exports full technical records (e.g. Google Docs) & delivers high-signal summary. | N/A. |

---

## 2. Pre-Spawn Protocol (Universal Checklist)

Before launching Codex on *any* project, Hermes must execute the following 4 steps:

### Step 1: Toolchain Matrix & Pre-Installation
Audit and verify the exact executable and packages for the target language:
- **Python / PyTorch:**
  ```bash
  /path/to/python -c "import sys, torch; print(sys.executable, torch.cuda.is_available())"
  ```
  *Pre-install all requirements via pip/uv before spawning Codex.*
- **TypeScript / Node.js:**
  ```bash
  node -v && npm -v && npm ls --depth=0 || npm install
  ```
- **Rust:**
  ```bash
  cargo --version && rustc --version && cargo check
  ```
- **C++ / CUDA:**
  ```bash
  cmake --version && ninja --version && nvcc --version
  ```

### Step 2: Workspace Isolation & Git Trust
Codex **requires a git repository** and prompts for interactive confirmation unless trusted:
1. **Fresh Scratch Project:**
   ```bash
   mkdir -p /path/to/project && cd /path/to/project && git init
   ```
2. **Existing Dirty Repo (Worktree Isolation):**
   ```bash
   git -C "$REPO" worktree add -b "codex/task-$(date +%s)" "/tmp/codex-worktree" HEAD
   ```
3. **Configure Trust (`~/.codex/config.toml`):**
   Ensure the target directory is added to `~/.codex/config.toml` under `[projects."/path/to/workdir"] trust_level = "trusted"` to eliminate blocking permission prompts in non-interactive background sessions.

### Step 3: Scaffold Context & Explicit Contracts
Create concrete specification files inside the repository so Codex does not spend reasoning tokens inventing architecture:
- `README.md` or `ARCHITECTURE.md`: Technical requirements, mathematical formulas, tensor shapes, or database schemas.
- `tasks/plan.md` & `tasks/todo.md`: Step-by-step checklist with exact input/output file paths.
- Initial verified stubs: Data loaders, configuration files, or dummy fixtures verified by Hermes.
- Initial test suite (`tests/`): Unit test skeletons or contract tests that define "done".

Commit this scaffold:
```bash
git add . && git commit -m "chore: scaffold project contracts and test harness"
```

---

## 3. Spawning & Prompt Engineering

Keep the prompt brief, declarative, and bounded. Reference the pre-written specification files rather than injecting verbose text into CLI arguments.

### Universal Spawn Command
Always use `background=true`, `pty=true`, and `notify=true`:

```python
terminal(
    command="""codex exec --yolo 'Read README.md and tasks/plan.md. Implement modules according to specifications:
1. Implement <module_1>
2. Implement <module_2>
3. Implement <entrypoint/cli>
Verify by executing: <TEST_COMMAND> (e.g. /path/to/python -m pytest tests/ OR npm test OR cargo test).
Ensure all tests pass and commit changes when finished.'""",
    workdir=WORKSPACE_DIR,
    background=True,
    pty=True,
    notify=True,
    timeout=600,
)
```

### Prompt Guardrails
- **Language / Toolchain:** State the exact binary command (`/path/to/venv/bin/python`, `npm`, `cargo`).
- **Scope Restriction:** "Work strictly inside this repository. Do not modify files outside this directory. Do not add or upgrade dependencies unless strictly required by the spec."
- **Exit Condition:** "Run the test suite. Once all tests pass, exit cleanly."

---

## 4. Babysitting Lifecycle & Kill Conditions

While Codex executes in the background:
1. **Log & Progress Monitoring:**
   - Check status: `process(action="poll", session_id=...)`.
   - Inspect progress: `process(action="log", session_id=..., limit=50)`.
   - Check compute: `nvidia-smi` (for GPU workloads) or `top` / `ps` (for CPU/compile workloads).
2. **Kill Conditions:**
   - Process hanging on an unexpected interactive prompt or network timeout.
   - Runaway token spend (>250k tokens on a narrow task).
   - Codex editing files outside the assigned scope.
   Kill immediately via: `process(action="kill", session_id=...)`.

---

## 5. Post-Execution Reconciliation & Independent Verification

**Never trust Codex's self-report of success.** Hermes must perform independent verification:
1. **Working Tree & Commits:**
   ```bash
   git status --short
   git log -n 5 --oneline
   git diff HEAD~1 --stat
   ```
2. **Independent Test Execution:**
   Hermes re-runs the test suite directly from its own terminal:
   ```bash
   <TEST_COMMAND>  # e.g. PYTHONPATH=. /path/to/venv/bin/pytest tests/
   ```
3. **Smoke Execution:**
   Execute a 5-step training pass, binary execution, or integration endpoint test to confirm numerical stability, memory footprint, and absence of runtime regressions.

---

## 6. Reporting & Delivery SOP

1. **Detailed Technical Report (Google Docs via Composio):**
   - For non-trivial engineering tasks, record the full technical brief, mathematical formulas, commit diff summaries, and benchmark tables in Google Docs using `GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN` or `GOOGLEDOCS_INSERT_TEXT_ACTION`.
2. **Discord Delivery (High Signal):**
   - Provide a 2–3 bullet TL;DR at the top.
   - Include the Google Docs link.
   - Attach media or benchmark artifacts (`MEDIA:/path/to/file.png`).
   - Report 3–4 essential quantitative metrics (e.g. latency, memory, accuracy/loss, test results).

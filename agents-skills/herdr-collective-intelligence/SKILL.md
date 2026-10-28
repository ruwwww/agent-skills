---
name: herdr-collective-intelligence
description: Coordinate multiple coding agents with Herdr for collective intelligence, horizontal scaling, structured discussion, and vibe coding. Use when the user asks to collaborate with OpenCode or other agents, delegate independent work, compare models, or establish a persistent Hermes-friendly agent workflow. Always inspect available OpenCode models and verify free usage before delegating to a model presented as free.
---

# Herdr collective intelligence

Use Herdr as a shared workspace for coordinating agents, not as a substitute for reasoning. Keep the human's goal central, divide work by independent evidence or deliverable, and synthesize claims only after checking their support. This workflow is usable from Hermes, Codex, or a terminal; adapt command syntax to the installed versions.

## 1. Establish the live setup

Before directing agents, inspect the current workspace, repository state, available agents, and CLI versions. Never assume the pane list, model, directory, or agent state from an earlier session is still current.

```sh
herdr --version
herdr status
herdr agent list
herdr api snapshot
opencode --version
opencode models opencode
opencode providers list
opencode stats --models
```

Use `herdr agent get <id>` and `herdr agent read <id>` to inspect a specific agent. Treat pane/workspace state as live data. All agents may share the same filesystem: tell them the exact working directory and whether edits are allowed. Check `git status --short` before parallel work and again before integrating changes.

## 2. Probe OpenCode models and usage first

Model catalogs and quotas change. Refresh and inspect the catalog at the start of a session when current availability matters:

```sh
opencode models opencode --refresh
opencode models opencode --verbose
opencode providers list
opencode stats --models
```

Classify evidence carefully:

- Catalog cost fields of zero mean OpenCode's current metadata lists zero per-token price. A `free` suffix is only a naming hint.
- A successful provider response proves the model is callable with the current credentials at that moment. It does not prove unlimited use or future availability.
- `opencode stats` shows recorded usage and cost for this local OpenCode history; it does not reveal a provider's complete quota policy.
- Provider credentials listed as configured do not prove that a particular model is free. Never print, read, or paste auth files, API keys, or secret environment values.
- Record check date, provider/model ID, source of zero-cost evidence, callable result, token counts/cost if returned, and any rate-limit or quota caveat. Recheck when the session changes or a request fails.

If a free model will be used and its callable state is unknown, make at most one minimal, harmless probe after checking its metadata. Use a tiny context and no repository files/tools, for example:

```sh
opencode run --model opencode/<model-id> --format json --dir /tmp 'Reply exactly: probe-ok'
opencode stats --models
```

The installed OpenCode system prompt may still make the input large. Capture reported input/output tokens and cost; do not infer low usage from a short user prompt. Avoid probing multiple models just to compare them. If free status or quota cannot be established, say so and ask before using a model that may incur cost. Never use `--auto` for a probe.

## 3. Scale horizontally without duplicating effort

Choose the smallest number of agents that can produce independent value. Good parallel tasks have separate evidence, files, or questions, and can be integrated cleanly. For example:

- Agent A: independently inspect a specific artifact or behavior and report evidence.
- Agent B: search for a different evidence source or derive an alternative explanation.
- Agent C: adversarially check assumptions and try to falsify the leading explanation.
- Lead agent: own the plan, shared edits, synthesis, and user communication.

Give each agent a bounded task, relevant context, exact directory, expected output, time/effort boundary, and write permissions. Ask for findings, evidence with file paths/line numbers or reproducible commands, confidence, and unresolved questions. Ask agents to work independently before sharing a leading hypothesis when anchoring is a risk.

Do not assign two agents the same broad investigation. Do not let multiple agents edit the same file or run competing commands in a shared worktree. Prefer read-only analysis in parallel, then assign one implementation owner. If parallel edits are necessary, use separate Herdr worktrees and integrate deliberately. Check for existing agent sessions before starting more; reuse idle sessions only after verifying their directory and history.

## 4. Run useful discussion, not a vote

Structure collaboration as a short evidence loop:

1. **Independent pass:** agents analyze separate evidence or provide independent approaches without seeing each other's conclusions when practical.
2. **Cross-examination:** share concise claims and ask each agent to identify unsupported leaps, counterexamples, and what observation would distinguish competing explanations.
3. **Revision:** let agents respond to specific criticism and update or defend their claims with evidence.
4. **Synthesis:** the lead groups results into verified facts, plausible hypotheses, rejected paths, and next discriminating action. Resolve disagreements with evidence or preserve them explicitly; do not decide by majority vote or model reputation.
5. **Stop:** stop redundant work when the next action is clear. Capture the decision and remaining uncertainty for the human.

Keep each round focused. Ask agents to challenge the current framing rather than merely extend it. For CTF/reverse/forensics tasks, ask what artifacts establish the claim, what alternative interpretation fits, and what smallest observation can rule alternatives out. Avoid brute force until a concrete hypothesis narrows the search space.

## 5. Vibe coding with control of the shared workspace

Treat “vibe coding” as fast, conversational iteration with an explicit owner and a visible scope:

1. Restate the requested outcome and inspect the relevant files before changing anything.
2. Let agents explore independent options, review requirements, or inspect failure modes. Keep one implementation owner for each overlapping code area.
3. Make a small coherent change. Tell reviewers what changed and what behavior should remain true.
4. Ask a separate agent to review the diff for correctness, edge cases, and unintended scope. Reviews should cite exact evidence and not silently edit files.
5. Verify only as requested by the user or required by project instructions. If verification is run, report the exact command and result.
6. Summarize changed files, decisions, verification, unresolved risks, and agent contributions. Do not claim an agent finding as verified until inspected.

Use Herdr commands shown by `herdr agent --help`; common operations include:

```sh
herdr agent list
herdr agent get <agent-id>
herdr agent prompt <agent-id> "<bounded task and constraints>"
herdr agent read <agent-id>
herdr agent wait <agent-id>
```

Check installed help before relying on flags or positional syntax. Send a prompt that explicitly says `read-only; do not edit files` for reviews and investigations. Do not send messages outside the local agent workspace or publish/share sessions unless the user explicitly asks.

## 6. Hermes-friendly operating pattern

When Hermes is the primary assistant, keep the orchestration loop in Hermes and use Herdr as the agent/pane control plane. Hermes should:

- preserve the user's goal and constraints in a short shared brief;
- use Herdr to inspect/start/prompt/read/wait for agents;
- keep a small task ledger with owner, status, and deliverable to prevent duplicated work;
- independently inspect important evidence and diffs before accepting agent conclusions;
- update the user at meaningful milestones, not after every agent message;
- leave a compact handoff note when the persistent session will continue later.

Do not assume Hermes exposes a particular Herdr integration or tool schema. Use the installed CLI/API help and adapt the same sequence to available Hermes tools. Keep model selection explicit in each OpenCode session where possible, and record the actual model ID rather than a nickname.

## 7. Closeout checklist

Before reporting completion, make sure the lead has:

- checked agent outputs and working-tree changes;
- separated confirmed evidence from inference and speculation;
- noted model IDs and current free-usage evidence if OpenCode was used;
- ended or left idle any unnecessary agent work;
- provided the user a concise result, changed paths, verification performed, and open questions.

## Current environment snapshot (2026-10-19)

This is an observation, not a promise of future availability. The inspected environment had Herdr 0.7.5 and OpenCode 1.18.10. The OpenCode catalog listed `opencode/deepseek-v4.1-flash-free` with zero input/output/cache cost metadata and an active status. A single `opencode run` probe returned `probe-ok`, with reported cost 0 and 35,237 input tokens plus 5 output tokens. `opencode stats --models` showed historical use of multiple OpenCode free-labelled models at `$0.0000`. These facts do not establish quota limits or future availability; repeat the preflight above.

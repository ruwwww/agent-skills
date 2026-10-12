---
name: formal-theorem-proving
description: "Use when training LLM theorem provers with RL or Lean."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [lean, lean4, theorem-proving, formal-math, rlvr, leandojo, mcts]
---

# Formal Theorem Proving & RL for Formal Mathematics

Methodologies, architecture patterns, and training criteria for developing autonomous AI theorem provers and reinforcement learning environments using Interactive Proof Assistants (specifically Lean 4 and LeanDojo).

## Core Principles: Formal Proving vs. Standard RL

1. **Absolute Soundness as a Hard Constraint:**
   Unlike RLHF where rewards are soft, subjective, and probabilistic, formal mathematical proofs must be certified by the proof assistant kernel (e.g. Lean 4 type-checker). There is zero tolerance for logical hallucination.
2. **First Error Propagation (Causal Proof Property):**
   A formal proof is a sequential proof-state transformation. Once a tactic fails or introduces an invalid type, *all subsequent tactics are conditioned on a broken state*. Consequently, any tactic generated after the first failure must be penalized as an error regardless of whether it looks syntactically valid in isolation.
3. **Representational Mismatch:**
   Lean's elaboration engine works over an Abstract Syntax Tree (AST) and tactic boundaries, while LLMs operate over autoregressive token streams. Transforming symbolic AST feedback into scalar, token-level training advantages requires principled projection.

## Verified RL (RLVR) Training Architecture

When training models with Group Relative Policy Optimization (GRPO) or PPO using Lean 4 verification:

### 1. Dual Outcome & Process Rewards
Outcome-only reward (1 on QED, 0 otherwise) suffers from extreme sparsity and optimization plateaus. Use Lean as a **Symbolic Process Oracle**:
- **Outcome Signal:** $g(Y) \in \{0, 1\}$.
- **Tactic Process Score $\phi(Y, T)$:**
  - $\phi(Y, T) = 1.0$ if the entire proof succeeds ($g(Y) = 1$).
  - $\phi(Y, T) = d_1$ (e.g. $-0.05$) if $g(Y) = 0$ but tactic $T$ elaborates without error (*locally sound, globally failing*).
  - $\phi(Y, T) = d_2$ (e.g. $-0.10$) if $g(Y) = 0$ and tactic $T$ fails ($d_1 > d_2$).
- **Difficulty-Normalized Baseline:**
  Subtract the group mean outcome reward from the process score:
  $$A_{\text{process}, i, j} = r_{\text{process}, i, j} - \text{mean}(g(Y_1), \dots, g(Y_G))$$
  This penalizes errors on easy problems severely while cushioning failures on hard problems.

### 2. The First-Token Assignment Trick
In autoregressive policy gradient updates, **assign the tactic process advantage ONLY to the first token (the tactic keyword)** of that tactic (e.g., `induction`, `apply`, `rw`, `simp`, `exact`).
- Distributing credit across all tokens or only to the last token degrades stability and performance.
- The tactic keyword sets the semantic trajectory for the subsequent proof branch.

### 3. Verification Timeout Sweetspot
- Maintain a **15-second timeout** per Lean proof attempt.
- Timeouts $< 5\text{s}$ introduce severe false negatives (killing valid algebraic simplifications like `ring` or `nlinarith`).
- Timeouts $> 30\text{s}$ incentivize bloated, computationally inefficient tactic paths.

## Search-Aware Generation & Inference Search

1. **Truncate-and-Resume (DeepSeek-Prover Paradigm):**
   Do not force a binary choice between single-shot whole-proof generation and purely step-by-step search. Generate full proofs; if step $t$ fails, truncate at $t-1$ and use the valid prefix as the root for subsequent tree expansions.
2. **Intrinsic Exploration in Tree Search (RMaxTS):**
   Incorporate visit-count exploration bonuses into MCTS:
   $$R_{\text{intrinsic}}(s, a) = \sqrt{\frac{\log N(s)}{N(s, a)}}$$
   This prevents proof search from collapsing into redundant minor tactic variations.
3. **Compute-Aligned Training (CAT / UA Loss):**
   Standard Cross-Entropy training optimizes for greedy next-token prediction, which is misaligned with test-time search budgets. Weight gradient steps based on target expansion budget (16 to 256 expansions).
4. **Interleaved Natural Language Chain-of-Thought (CoT):**
   Allowing the agent to verbalize an informal proof sketch in comments before emitting formal Lean syntax dramatically increases success rates on competition-level math (MiniF2F, Putnam, IMO).

## Environment Infrastructure with LeanDojo-v2

- **Persistent REPL Pool:** Never invoke `lean` CLI from scratch per step. Use persistent LeanDojo REPL workers with pre-compiled `Mathlib` olean caches.
- **Worker Recycling:** Cycle worker processes every $N$ executions to prevent memory leaks from heavy unification tables.
- **Monad State Snapshotting:** Cache proof-state monads in memory to enable sub-millisecond tree backtracking without re-executing prefixes.

See `references/rlvr-training-guide.md` for formal formulations, empirical ablation figures, and hyperparameter tables.

# RLVR for Formal Theorem Proving: Empirical Guide & Recipes

Detailed empirical takeaways, formal reward definitions, and operational recipes derived from recent literature (KAIST ICLR 2026, DeepSeek-Prover-V1.5, UMich 2026).

## Formal Advantage Formulation (Kim & Yun, 2026)

For prompt $q$ with $G$ candidate proofs $\{Y_1, \dots, Y_G\}$:

### 1. Global Outcome Advantage
$$A_{\text{outcome}, i, t} = \frac{g(Y_i) - \text{mean}(\{g(Y_k)\})}{\text{std}(\{g(Y_k)\}) + \epsilon}$$
where $g(Y) = 1$ if Lean verification succeeds with zero open goals, and $0$ otherwise.

### 2. Process Advantage with First Error Propagation
Let proof $Y_i = (T_{i, 1}, T_{i, 2}, \dots, T_{i, N})$. Let $j^*$ be the first tactic index where Lean reports an error:
$$r_{\text{process}, i, j} = \begin{cases}
1.0 & \text{if } g(Y_i) = 1 \\
d_1 & \text{if } g(Y_i) = 0 \text{ and } j < j^* \\
d_2 & \text{if } g(Y_i) = 0 \text{ and } j \ge j^*
\end{cases}$$
Default parameters: $d_1 = -0.05$, $d_2 = -0.10$.

Baseline-subtracted process advantage:
$$A_{\text{process}, i, j} = r_{\text{process}, i, j} - \frac{1}{G} \sum_{k=1}^G g(Y_k)$$

### 3. Token-Level Mapping
$$A_{i, t} = A_{\text{outcome}, i, t} + \mathbb{I}(t = \text{first\_token}(T_{i, s(i, t)})) \cdot A_{\text{process}, i, s(i, t)}$$
Only the very first token (the tactic head keyword) receives the process advantage update.

---

## Empirical Ablations & Lessons

| Mechanism / Setting | Impact on Pass Rate | Explanation |
| :--- | :--- | :--- |
| **First Error Propagation** | **Critical (+1.8 to +2.5 p.p.)** | Subsequent tactics conditioned on an invalid state are logically meaningless. Rewarding locally valid syntax after an error confuses policy gradients. |
| **First Token Credit vs All Tokens** | **+1.2 to +1.9 p.p. gain** | Assigning process reward across all tokens dilutes credit onto filler syntax/variables rather than the strategic tactic decision. |
| **Differentiated Penalties ($d_1 > d_2$)** | **+0.8 to +1.4 p.p. gain** | Encourages the model to find locally correct proof directions even when missing the final QED step. Collapsing $d_1 = d_2$ causes gradient stagnation. |
| **Timeout = 15s** | **Optimal** | $5\text{s}$ yields high false negative rates; $30\text{s}$ causes training wall-clock blowup with negligible accuracy gain. |

---

## Infrastructure Sizing Guidelines

- **Rollout Workers:** 1 Lean 4 persistent REPL daemon per CPU core. 64-128 cores recommended for concurrent batch generation ($G=4$ to $G=8$).
- **Memory Ceiling:** Reserve 3.5 GiB per Lean REPL worker when Mathlib is fully loaded. Set memory limits via Linux cgroups.
- **Ray Actor Pattern:** Wrap LeanDojo REPL instances in stateful Ray Actors (`@ray.remote(num_cpus=1)`) communicating asynchronously with policy generators on GPU nodes.

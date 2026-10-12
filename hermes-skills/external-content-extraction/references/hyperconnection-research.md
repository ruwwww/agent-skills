# Hyper-Connection (HC) Research Findings

## Summary

Research into DeepSeek's mHC (manifold-constrained Hyper-Connections) revealed that the core "manifold constraint" on H^res matrix is **unnecessary** — **Identity HC (H_res = I)** performs better than the original mHC approach.

## Key Discovery

**Identity HC > mHC > mHC lite > mHC orthogonal**

Experimental evidence from Qwen3 1.7B and 8B models (150B tokens training):

### Original mHC Problem

1. **Single-layer behavior:** H_res ≈ Identity (diagonal ~0.96, off-diagonal ~0.01)
2. **Multi-layer accumulation:** 10+ layers → uniform 0.25 matrix (complete collapse)
3. **Mathematical cause:** Doubly-stochastic matrices have Dobrushin coefficient τ(P) ≤ 1 - dδ < 1, causing geometric decay: τ(A_n) ≤ (1 - dδ)^n → 0

**For Qwen3-1.7B (56 HC modules):**
- Sinkhorn H_res min eigenvalue: 0.49
- σ_min ≈ 0.49^56 ≈ 10^-17
- **Real measurement:** 9.2 × 10^-18 ✅ matches

**Signal decay:** Shallow signals decay to zero after 56 HC modules (except mean direction).

### Identity HC Advantages

| Metric | Sinkhorn (mHC) | Identity HC |
|--------|---------------|-------------|
| Accumulated product | rank-1 collapse (κ = 10^17) | I (κ = 1) |
| Approximation error | Row sum std = 0.12 | Exact |
| Additional compute | 20 iterations + recompute | Zero |
| Additional parameters | nC × n^2 | None |
| Signal passing | Exponential decay in shallow layers | Lossless |

**Flow consistency:** With H_res = I, all residual flows maintain their positions:
- Flow 0 always at position 0
- Flow 1 always at position 1
- H_pre/H_post learn "from which flow read, to which flow write" directly
- No flow shuffling confusion

## Why Cross-Stream Mixing Happens Elsewhere

Even with H_res = I, cross-stream mixing still occurs through:

1. **φ (phi) projection:** Cross-stream information mixing happens here
   - Projects nC-dimensional input to (n² + 2n)-dimensional space
   - Then extracts h_pre, h_post, h_res matrices (e.g., 4, 4, 4×4 for n=4)
   
2. **Dynamic weights:** h_pre and h_post are input-dependent via sigmoid activations

```
Input: x_l = [s, b, n*C] (4 flows flattened)

Step 1: φ projection (cross-stream fusion happens here)
   x̂' · φ → [s, b, 2n]  (Identity mode: only 2n=8 dims)
   φ's input contains all 4 flows' information

Step 2: Activation
   h_pre = sigmoid(α_pre · proj[:n] + b[:n])  ← dynamic aggregation weights
   h_post = 2·sigmoid(α_post · proj[n:2n] + b[n:2n])  ← dynamic expansion weights

Step 3: Aggregation (cross-stream fusion explicit)
   aggregated = Σ h_pre_i · x_stream_i  ← [s, b, C]

Step 4: Transformation
   output = f(aggregated)  ← Attention or MLP

Step 5: Identity residual + dynamic write-back
   x_{l+1} = I · x_l + diag(h_post) · f(...)
           = x_l + diag(h_post) · f(...)  ← Each flow independently preserves residual
```

**Key insight:** **Φ is the cross-stream mixing mechanism**, not H_res!

## Channel Strength Analysis

Effective channel between layers i and j:

```
c_ij = h_j^pre · (∏_{k=i+1}^{j-1} H_k^res) · h_i^post^T
```

### With mHC (H_res ≈ doubly-stochastic)
- Channel decays with layer gap
- Gap 1-15: strength 0.3~0.5
- Gap > 20: significant decay
- Pattern: "middle layer radiation, deep layer convergence"

### With Identity HC (H_res = I)
- **Direct communication:** c_ij = h_j^pre · I · h_i^post^T = h_j^pre · h_i^post^T
- No intermediate decay — depends only on h_pre/h_post of source/dest layers
- Simplifies signal tracking across network depth

## Failed Attempts at Simplification

1. **mHC lite convex combination:** Tries to make exact doubly-stochastic
   - Result: Performance worse than original mHC

2. **Alpha-res enlargement (0.01 → 2.0):**
   - Softmax temperature decreases
   - Output tends to one-hot
   - Mixing reduces

3. **Orthogonalization (Cayley, Givens rotation):**
   - Spectral norm maintained at 1
   - **Problem:** Negative values allowed
   - Flows can be negated → capacity collapse
   - Poor internal metrics

## Recommendation

**For new models or modifications to existing architectures:**

1. **Use Identity HC (H_res = I)** for residual flow handling
2. **Cross-stream mixing via φ projection** instead of per-layer H_res mixing
3. **No need for Sinkhorn-Knopp iteration** — significant compute savings
4. **Better flow semantic consistency** across network depth
5. **No additional parameters** beyond original HC formula

## References

- Original mHC paper: DeepSeek's Hyper-Connection research
- Zhihu blog post: "你的 deepseek mHC 可能不需要'm" (Your DeepSeek mHC Might Not Need the 'm')
  - URL: https://zhuanlan.zhihu.com/p/2010852389670908320
- Experimental setup: Qwen3 1.7B and 8B dense models, 150B tokens training

---

**Note:** This research finding may supersede original mHC implementation guidance. Consider revisiting architectures that use manifold-constrained HC matrices.
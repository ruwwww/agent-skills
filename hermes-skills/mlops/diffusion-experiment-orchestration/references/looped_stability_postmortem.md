# Post-Mortem: Numerical Instability in Recurrent Looped-DiT Architectures

## Problem Description
In the first training run of CelebA-HQ Looped-DiT (~49M params, 4 loops over core blocks, depth 20 effective layers), training was stable from step 1 to 28,000 (loss ~0.79). Around step 29,000, loss oscillations emerged, escalating to a loss spike of 3.2e6 at step 54,000, and terminating in `FloatingPointError: non-finite training loss at step 58,395: nan`.

## Root Cause Analysis
1. **Compounding Scale in adaLN Modulation:**
   - Standard DiT adaLN calculates:
     `attention_input = norm(x) * (1 + scale) + shift`
   - In feed-forward DiT (12 unique blocks), layers learn independent scale shifts.
   - In looped DiT (4 core blocks called 4 times sequentially), the activations pass through the exact same modulation weights 4 times per denoising step.
   - As weights grew slightly over 50k steps, `scale` reached ~2461.0, causing the hidden state norm (`hidden_norm`) to explode from 22.0 to 25,000,000,000.
2. **Attention Logit Drift:**
   - Without Query/Key normalization, dot products `Q @ K.T / sqrt(d)` drift to extreme magnitudes across multiple loop cycles, saturating the softmax into one-hot vectors and zeroing out gradients or blowing up backprop.

## Validated Resolution Recipe
1. **QK-Norm:** Apply RMSNorm on Query and Key projections per head prior to scaled dot-product attention.
2. **Loop-Boundary RMSNorm:** Explicitly re-normalize `hidden = loop_norm(hidden)` at each transition between loop iterations ($r \in \{1, \dots, N\}$).
3. **Bounded adaLN:**
   - Clamp `scale = torch.clamp(scale, -2.0, 2.0)`
   - Clamp `gate = torch.clamp(gate, -4.0, 4.0)`
4. **Normalized Deep Supervision:** Ensure the sum of all exit weights across loops equals a constant (e.g. 2.0).
5. **Tight Gradient Clipping:** Clamp gradient norms to 0.5.

## Result
Applying this recipe in `Looped-DiT-50M-Stabilized` resulted in:
- Hidden norms locked strictly between 22.6 and 25.2 across the entire training run.
- Zero loss spikes or NaNs over the full 105,000 steps (~120 epochs).
- Convergence loss down to 0.81–0.98.

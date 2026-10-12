# Perceptual Supervision and Pure Linear Readouts for Pixel-Space DiTs

## 1. The Mode-Averaging Dilemma in Pixel-Space Diffusion
Standard flow-matching or diffusion trained with pure pixel-wise MSE/L2 loss treats all pixels and frequency bands uniformly. Under high dimensionality ($256 \times 256 \times 3$), when the network cannot perfectly resolve high-frequency stochastic details (skin pores, eyelashes, fine hair strands), minimizing L2 loss mathematically converges to predicting the conditional mean. This creates the characteristic "airbrushed / melted wax / painterly" blur.

---

## 2. Multi-Objective Objective Formulation (PixelGen & Linum AI)

Direct clean-image prediction ($\hat{x}_0$) provides a clean interface to pre-trained perceptual networks:

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{FM-final}} + 1.0 \cdot \mathcal{L}_{\text{FM-pyramid}} + g(t) \cdot \left(0.1 \cdot \mathcal{L}_{\text{LPIPS}} + 0.01 \cdot \mathcal{L}_{\text{P-DINO}}\right) + 0.5 \cdot \mathcal{L}_{\text{REPA}}$$

### A. Flow Matching Rectified Loss ($\mathcal{L}_{\text{FM}}$)
- Formulate with $v$-weighted velocity:
  $$\hat{v} = \frac{\hat{x}_0 - x_t}{\max(1 - t, 0.05)}, \quad \mathcal{L}_{\text{FM}} = \|\hat{v} - v\|^2$$

### B. Perceptual Losses (PixelGen Recipe)
- **LPIPS ($\mathcal{L}_{\text{LPIPS}}$):** VGG-based feature distance between $\hat{x}_0$ and $x_0$. Forces sharp local contrast and edge definition.
- **P-DINO ($\mathcal{L}_{\text{P-DINO}}$):** Cosine distance between patch-level tokens of frozen DINOv2 (`dinov2_vitb14` or `vits14`), specifically targeting **layer 11** (`dino_layers=[11]`):
  $$\mathcal{L}_{\text{P-DINO}} = \frac{1}{|P|} \sum_{p \in P} \left(1 - \cos\left(f_{\text{DINO}}^{p, 11}(\hat{x}_0), f_{\text{DINO}}^{p, 11}(x_0)\right)\right)$$
- **REPA ($\mathcal{L}_{\text{REPA}}$):** Representation alignment on intermediate DiT layers (e.g. layer 8). Aligns internal DiT tokens to clean DINOv2 features via a **3-layer MLP projector with SiLU** (`Linear -> SiLU -> Linear -> SiLU -> Linear`), NOT a single linear layer.

### C. Noise Gating ($g(t)$)
At high noise timesteps ($t < 0.3$, where $t=1$ is clean and $t=0$ is pure noise), $\hat{x}_0$ is still coarse and unstructured. Forcing feature alignment against clean image encoders early in the diffusion trajectory over-constrains early denoising and severely degrades sample diversity and recall.
- **Gate definition:**
  $$g(t) = \mathbb{I}(t \ge 0.3)$$
- Activates perceptual terms only during the final 70% clean-regime steps.

---

## 3. Pure Linear Heads vs. Patch Seam / Checkerboard Pitfalls

When using direct linear patch unpatchify (`unpatchify`), models are susceptible to severe **patch boundary seams** and **checkerboard grid patterns** where adjacent $16 \times 16$ blocks fail to blend continuously.

### Mandatory Rules for Pure Linear Heads:
1. **Zero Initialization of Output Projection (`linear.weight = 0`, `linear.bias = 0`):**
   - The final linear projection (`FinalLayer`) and its adaLN modulation projection MUST be initialized to zero:
     ```python
     nn.init.zeros_(self.final_head.linear.weight)
     nn.init.zeros_(self.final_head.linear.bias)
     nn.init.zeros_(self.final_head.adaLN_modulation[-1].weight)
     nn.init.zeros_(self.final_head.adaLN_modulation[-1].bias)
     ```
   - *Pitfall:* Initializing the final projection with `xavier_uniform_` causes adjacent patches to start with random offset discontinuities that persist for tens of thousands of steps.
2. **Never Apply `torch.tanh` on Unpatchify:**
   - Unpatchify must output raw linear pixel predictions in $[-1, 1]$.
   - *Pitfall:* `tanh` squashes gradients to zero near boundaries ($\pm 1.0$), exacerbating blocky seam edges and clipping high-contrast lines.
3. **2D Spatial Inductive Biases (2D RoPE & 2D Sin-Cos PosEmbed):**
   - Use fixed 2D Sin-Cos positional embeddings (`get_2d_sincos_pos_embed`) and 2D Rotary Position Embeddings (`VisionRotaryEmbeddingFast`) across self-attention blocks. 1D learned sequence positional embeddings lose 2D neighbor awareness.

---

## 4. ModelEMA Dilution Trap in Early-to-Mid Training

With a static high decay such as `decay = 0.9999`:
$$\text{Weight}_{\text{initial}} = (0.9999)^S$$
- At step 1,000: $(0.9999)^{1000} \approx 0.905$ (90.5% initial random noise).
- At step 10,000: $(0.9999)^{10000} \approx 0.368$ (36.8% initial random noise).
- At step 50,000: $(0.9999)^{50000} \approx 0.0067$ (essentially washed out).

### Consequences & Fix:
- Generating sample previews from `ema.module` early in training results in muddy, desaturated static noise with tiny variance ($\sigma \approx 0.14$ vs real $\sigma \approx 0.49$), giving a false impression that the model is failing to learn.
- **Fix:** Implement **EMA warmup decay**:
  $$\text{decay}_s = \min\left(\text{target\_decay}, \frac{1 + s}{10 + s}\right)$$
  Or log samples from both the raw training model and the EMA model for diagnostic clarity.

# Flow Matching, Lagrangian Trajectories & Decoupled Jacobian Denoiser

## 1. Lagrangian View of Flow Matching
- Velocity field: $v(x, t) = \frac{D(x, t) - x}{1 - t}$ where $D(x, t) \approx \mathbb{E}[x_1 \mid x_t = x]$.
- Trajectory acceleration (curvature):
  $$\mathbf{a}(t) = \frac{dv}{dt} = \frac{\frac{\partial D}{\partial t} + \mathbf{J}_D(x_t, t) v_t}{1 - t}$$
  where $\mathbf{J}_D = \nabla_x D(x, t)$ is the Jacobian matrix of the denoiser.
- **Target Conservation:** If $\frac{dD}{dt} = 0$, then $\mathbf{a}(t) = 0 \implies$ straight-line constant velocity flow ($v = x_1 - x_0$).
- **Curvature Source:** All trajectory bending is driven by non-zero Jacobian $\mathbf{J}_D v$.

## 2. Decoupled Architectures for Low-Cost Jacobian Estimation
Computing full autodiff/JVP on 12B+ DiTs introduces ~200% VRAM / 2x forward compute overhead. Decoupled architectural alternatives:
1. **Auxiliary Curvature Head (Shadow Head):**
   - Attach a 2-layer MLP to intermediate feature maps ($h_{\text{mid}}$ around layer 18-20).
   - Directly predict $J_D v$ in a single forward pass without backward autodiff graph retention.
2. **Linear-Residual Decomposition:**
   - Decompose $D(x, t) = W_t x + g_\theta(\text{Downsample}(x), t)$.
   - Linear component has constant/zero-cost Jacobian; non-linear residual evaluated at downsampled latent token resolution.
3. **Low-Rank Factorized Denoiser:**
   - Parameterize denoiser Jacobian with rank $r \ll d$ ($J_D = U_t \text{diag}(\phi') V_t^\top + I$) to cut vector-Jacobian product complexity from $O(d^2)$ to $O(r \cdot d)$.

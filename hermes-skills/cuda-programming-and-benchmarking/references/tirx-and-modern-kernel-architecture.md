# Modern GPU Kernel Architecture & TIRx Design Patterns

Authoritative reference for architecting production-grade GPU kernels based on patterns from `mlc-ai/TIRx-kernels` and modern hardware targets (Blackwell SM100–SM120, Rubin SM107, Hopper SM90).

## 1. Asymmetric Warp Specialization & Dynamic Register Budgeting
Traditional SIMT assigns uniform register counts and instruction paths to all threads in a CTA. Modern architectures suffer severe occupancy degradation under register pressure.

- **Role Partitioning:**
  - **Loader Warps (TMA Producers):** Calculate coordinates and issue asynchronous bulk tensor transfers (TMA). Do not execute ALU or epilogue math. Allocate minimal registers (e.g. 56 regs).
  - **Scheduler Warps:** Manage persistent tile dispatch, Cluster Launch Control (CLC), and work stealing.
  - **MMA Warps:** Dispatch Tensor Core matrix instructions (`tcgen05.mma` on Blackwell, WGMMA on Hopper).
  - **Consumer Warps (Epilogue):** Wait on accumulators, unpack/scale/quantize, and stream out to DRAM. Allocate full register ceiling (up to 224-255 regs).
- **Register Scope Control:** Use hardware or DSL primitives (e.g. `txl.specialize()` register scopes) to balance register distribution across warps in the same CTA.

## 2. Asynchronous Multi-Stage Pipelining & Hardware Barriers
- **Eliminate `__syncthreads()`:** Synchronous barrier stalls all warps across the entire CTA. Replace with hardware asynchronous transaction tracking (`mbarrier`).
- **TMA Direct Staging:** Use `cp.async.bulk.tensor` to move data directly from DRAM into Shared Memory without register staging.
- **Phase Inversion:** Maintain circular pipelines (depth 4–8) using stage indices and single-bit phase tracking (`phase ^ 1`).
- **Transaction Accounting:** Issue `mbarrier.arrive.expect_tx` with the exact byte payload before launching TMA loads; consumer awaits arrival phase via non-blocking hardware polling (`mbarrier.try_wait` or `mbarrier_wait`).

## 3. Bank Conflict Elimination via Swizzling Atoms
- **XOR Swizzle Modes:** Shared Memory bank conflicts (32 banks, 4-byte width) on 2D stride loads are resolved by XOR swizzling the row bits with column bits.
- **Atom Matching:**
  - `SW128B`: Use when row byte stride is a multiple of 128 bytes (64 half elements).
  - `SW64B`: Use when row byte stride is a multiple of 64 bytes.
  - `SW32B`: Use when row byte stride is a multiple of 32 bytes.
- Direct pointer indexing must go through swizzled tile views (`m8n8`, `m8n8x4`, `mma_desc`) rather than raw 2D index arithmetic.

## 4. Hardware-Specific Primitives (SM100–SM120 Blackwell)
- **`tcgen05.mma`:** 5th Generation Tensor Core instructions supporting FP16, BF16, FP8, and NVFP4.
- **Tensor Memory (TMEM):** Accumulator storage resides in dedicated on-chip TMEM (`tcgen05.alloc`), preventing FP32 accumulator matrices from occupying Shared Memory or register files.
- **2-SM CTA Clustering (`cta_group::2`):** Pair adjacent SMs into a hardware cluster to share MMA execution context and distributed Shared Memory barriers (`shared::cluster`).
- **L2 Cache Policy Hints:** Tag bulk stores with cache eviction hints (e.g. `L2::cache_hint` / `evict_first`) to avoid polluting L2 cache with epilogue outputs that will not be immediately reread.

## 5. Persistent Thread Blocks & L2 Locality Traversal
- **Launch SM-Count Sized Grid:** Grid size equals device physical SM count (or small integer multiple), keeping CTAs resident.
- **Persistent While-Loop:** CTAs continuously poll for tile tasks until work queue exhaustion, eliminating kernel re-launch overhead.
- **Group-Major / Hilbert Tile Ordering:** Traversal order of matrix tiles (M, N) is structured in groups (`l2_group_size=4` or `8`) to reuse stationary weights or activations already cached in L2.

## 6. Predicated Execution & Vectorization
- **Vectorized Loads/Stores:** Always maximize transaction width (`ld.global.v4.b32` / `st.global.v4.b32` = 128 bits per thread).
- **Single-Lane Instruction Gating:** Gate collective setup (TMA initiation, descriptor prefetch) to a single elected lane (`elect_sync() != 0`) rather than all threads in the warp.
- **Global Offset Hoisting:** Compute and cast global tensor indexing offsets into a single widened integer local before addressing to avoid PTX generating redundant `IMAD.WIDE` instructions inside tight unrolled loops.

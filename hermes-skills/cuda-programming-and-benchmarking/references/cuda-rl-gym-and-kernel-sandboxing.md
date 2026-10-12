# CUDA RL Environments, Gymnasium Contracts, and Sandboxed Kernel Rollouts

Guidelines for building autonomous reinforcement learning (RL) environments and evaluation harnesses for CUDA engineering on local hardware (e.g., NVIDIA RTX 50-series SM120).

---

## 1. Single-GPU Sizing: GRPO with ~2B Code Policy

When training or running agent rollouts for CUDA kernel optimization entirely on a local consumer workstation (e.g., 16 GB RTX 5060 Ti):

- **Model Sizing:** Use ~2B parameter code models (such as `Qwen/Qwen2.5-Coder-1.5B-Instruct` or `Qwen2.5-Coder-0.5B-Instruct`). In BF16, model weights take ~1.0–3.1 GB VRAM (or <2.2 GB with LoRA).
- **Critic Elimination via GRPO:** Standard PPO requires an Actor and a Critic network, doubling memory footprint and optimizer state. Group Relative Policy Optimization (GRPO) generates a group of $G$ rollouts per prompt and normalizes advantages across the group:
  $$A_i = \frac{R_i - \mu(\{R\})}{\sigma(\{R\}) + \epsilon}$$
- **VRAM Headroom:** A ~2–3 GB model footprint leaves $>12$ GB VRAM for ephemeral kernel execution, PyTorch reference buffers, and cuBLAS baseline runs with zero risk of OOM.

---

## 2. Sandboxed Subprocess Execution & Watchdog

Model-generated CUDA code is untrusted and can crash the CUDA driver context or freeze the GPU:

1. **Security Filtering:** Reject dangerous system calls (`system(`, `popen(`, `fork(`, `exec(`, `<fstream>`) before compilation.
2. **Ephemeral Build Workspace:** Write source code into a unique directory under `/tmp` and clean up immediately upon context exit.
3. **Compilation Flags for Diagnostic Extraction:**
   ```bash
   /usr/local/cuda/bin/nvcc -O3 -arch=sm_120 -lineinfo -Xptxas -v source.cu -o kernel_bin
   ```
   Parse `ptxas` diagnostics to extract register count and shared memory allocation:
   - `Used (\d+) registers, (\d+) bytes cmem`
   - Check spill stores/loads: `(\d+) bytes spill stores, (\d+) bytes spill loads`
4. **Kernel-Only Syntax Verification:**
   If the agent emits only `__global__ void kernel(...)` without a host `main()`, compile with `-c`:
   ```bash
   /usr/local/cuda/bin/nvcc -c -O3 -arch=sm_120 -lineinfo -Xptxas -v kernel.cu -o kernel.o
   ```
   This validates syntax, register allocation, and shared memory without link errors.
5. **Execution Watchdog:** Run the compiled executable via `subprocess.Popen` with a strict timeout (e.g. 5 seconds) and send `SIGKILL` on timeout. Always run kernels **sequentially** on the GPU to avoid timing interference and memory corruption.

---

## 3. Gymnasium Contract Gotchas (`spaces.Text`)

When exposing a CUDA kernel environment via `gymnasium.Env`:

- **Character Set Trap:** `gymnasium.spaces.Text` defaults to `string.ascii_letters + string.digits`. CUDA source code contains braces, newlines, pointers (`*`), preprocessor directives (`#`), and tabs.
  ```python
  import string
  import gymnasium as gym

  # Pass full printable ASCII and allow empty diagnostics string:
  gym.spaces.Text(
      max_length=65536,
      min_length=0,
      charset=string.printable,
  )
  ```
- **Numeric Bounds:** Ensure observation `Box` spaces have finite bounds (e.g. `low=-1e9, high=1e9`) to satisfy `gymnasium.utils.env_checker.check_env`.
- **One-Step MDP:** For single-turn kernel generation/optimization, set `terminated = True` after the benchmark step.

---

## 4. Multi-Tier Reward Formulation

To guide policy exploration from compilation to peak hardware efficiency:

| Tier | Condition | Reward |
|------|-----------|--------|
| **Compilation Failure** | NVCC error / syntax invalid | `-1.0` (with stderr diagnostics) |
| **Runtime Failure** | Timeout (>5s), illegal memory access, crash | `-0.5` |
| **Correctness Failure** | Mismatch vs PyTorch reference ($\text{atol} > 10^{-3}$) | `-0.3 \times \min(1.0, \text{rel\_err})` |
| **Functional Pass** | Matches reference within tolerance | `+1.0` base |
| **Speedup Bonus** | Faster than naive baseline ($T_{\text{base}} / T_{\text{kernel}}$) | $\min(4.0, \max(0.0, \text{speedup} - 1.0))$ |
| **cuBLAS / Peak Bonus** | High hardware utilization | $2.0 \times (\text{GFLOP/s}_{\text{kernel}} / \text{GFLOP/s}_{\text{cuBLAS}})$ |
| **Register Efficiency** | Registers $\le 64$ and 0 spill stores | `+0.2` |

---

## 5. Production RL Libraries & Fast Rollout Backend (TRL + vLLM)

Instead of implementing custom policy gradient loops or manual rollout workers from scratch, use maintained libraries for direct value delivery:

### 5.1 Hugging Face TRL GRPOTrainer
Use `trl.GRPOTrainer` with `trl.GRPOConfig`:
```python
from trl import GRPOConfig, GRPOTrainer
from peft import LoraConfig

config = GRPOConfig(
    output_dir="./outputs/cuda_grpo",
    learning_rate=1e-5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_generations=4,                      # Group size G sampled in parallel
    max_prompt_length=1024,
    max_completion_length=512,             # Keep completion budget realistic for kernels
    use_vllm=True,                         # Native fast rollout backend
    vllm_mode="server",
    vllm_gpu_memory_utilization=0.35,      # Strictly cap VRAM for vLLM
)
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
)
```

### 5.2 VRAM Budgeting on Single 16 GB GPUs (RTX 5060 Ti)
- **vLLM Engine Allocation:** Set `vllm_gpu_memory_utilization = 0.35` (~5.5 GB VRAM). This provides ample PagedAttention KV-cache for $G=4$ to $G=8$ rollouts at 2k context.
- **LoRA Policy Weights:** ~2.2 GB VRAM for 1.5B/2B parameters with FP16/BF16 weights and gradient checkpointing.
- **Dedicated Execution Headroom:** Leaves $>8.0$ GB VRAM completely free for ephemeral NVCC compilation processes, PyTorch ground-truth tensors, and isolated candidate kernel execution.

### 5.3 TRL-Compatible Reward Functions & Batch Columns
TRL passes completions as a list of strings (or chat message lists). Crucially, dataset columns are forwarded via `kwargs` as **lists of batch values** matching the batch size, NOT single scalar values:
```python
def cuda_composite_reward_func(prompts: list[str], completions: list, **kwargs) -> list[float]:
    rewards = []
    task_names = kwargs.get("task_name", [])
    baseline_codes = kwargs.get("baseline_code", [])

    for i, (prompt, completion) in enumerate(zip(prompts, completions)):
        text = completion[0]["content"] if isinstance(completion, list) else str(completion)
        code = extract_cuda_code(text)
        task_name = task_names[i] if i < len(task_names) else None
        reward = evaluate_in_sandbox(code, prompt, task_name=task_name)
        rewards.append(reward)
    return rewards
```

### 5.4 PEFT / TRL Compatibility Traps
1. **Missing `warnings_issued` attribute:** `trl.GRPOTrainer` expects `model.warnings_issued` before parent `Trainer` initialization. If wrapping via `peft.PeftModel`, ensure `model.warnings_issued = {}` or patch the class fallback `PeftModel.warnings_issued = {}`.
2. **Optional `torchao` Linear Dispatch:** PEFT's optional `dispatch_torchao` check fails on some torchao installs missing `LinearActivationQuantizedTensor`. Catch this and disable the torchao dispatcher so standard PyTorch `nn.Linear` dispatch runs cleanly.
3. **Completion Length Budgeting:** Defaulting `max_completion_length` to 2048 causes single-GPU eager rollouts to take >60s per step. For CUDA kernel generation, limit `max_completion_length` to 384–512 tokens to drop step times to ~14–16s while giving ample room for complete CUDA functions.

---

## 6. veRL & Uni-Agent Multi-Turn Architecture

For full autonomous RL loops where the agent iteratively compiles, inspects diagnostics, and tunes performance across multiple steps per episode:

### 6.1 Decoupled Three-Tier Sandbox
- **Parallel CPU Compilation Pool:** Use `concurrent.futures.ProcessPoolExecutor(max_workers=CPU_CORES)` to compile candidate kernels concurrently on CPU. Never serialize NVCC across batch rollouts.
- **SHA256 Content-Addressed Cache:** Compute `sha256(source + flags)`. Store compile and benchmark artifacts by hash to bypass NVCC when agents regenerate identical kernels.
- **Exclusive GPU Mutex Lock (`filelock`):** Serializing GPU benchmark passes via an OS-level file lock prevents concurrent worker interference, ensuring true GFLOP/s and latency measurements while keeping overall execution under 50 ms.
- **Watchdog Subprocess:** Subprocess binary execution with 5s timeout and SIGKILL to protect the main Ray/veRL daemon from `cudaErrorIllegalAddress` or infinite GPU loops.

### 6.2 Uni-Agent ReAct Tools for CUDA Optimization
Define 3 core tools in `cuda_task_config_react.yaml`:
1. `cuda_kernel_editor`: String-replacement editor to update candidate kernel source.
2. `nvcc_compile_and_benchmark`: Executes the parallel compilation and locked GPU benchmark pass, returning structured feedback:
   - Compile stderr & diagnostic line numbers on failure.
   - Ptxas register counts, local/shared memory bytes, and spill counts.
   - Runtime, speedup vs baseline, and cuBLAS percentage on success.
3. `submit`: Validates that a successful benchmark exists and locks the candidate file (`chmod 0444`) to complete the episode.


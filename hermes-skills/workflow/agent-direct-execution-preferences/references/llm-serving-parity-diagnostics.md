# LLM Serving & Model Parity Diagnostics (NInfer / llama.cpp / Blackwell SM120)

## 1. Stop Token vs End-Of-Text Incoherence Trap
When serving conversational or thinking LLMs (such as Qwen 3.5/3.6 hybrid GDN architectures or Ornith-1.5) via OpenAI-compatible endpoints (`/v1/chat/completions`) in OpenCode, LibreChat, or custom agents:
- **Symptom**: Model generates hallucinatory recursive conversational turns (`\n<|im_start|>user...`, fake thought loops, "Thought: 697ms... The user is just giving me random keywords now..."), looping until `max_tokens` (`finish_reason: length`).
- **Root Cause**: The model metadata's `generation_config.json` frequently records only the base pre-training end-of-text token (`eos_token_id: 248044` / `<|endoftext|>`), but NOT the chat template turn closure token (`<|im_end|>` / ID `248046`). If the server runtime only stops on the configured `eos_token_id` and does not default to or expose `<|im_end|>` as a stop token, the model will not stop upon finishing its response.
- **Diagnostic API Pattern**: Always run an API probe with and without explicit stop tokens:
  ```python
  # Probe without stop vs with stop
  payload = {
      "model": "model-id",
      "messages": [{"role": "user", "content": "Say 'DONE' and nothing else."}],
      "max_tokens": 128,
      "stop": ["<|im_end|>"]
  }
  ```
- **Remediation**:
  1. Register `<|im_end|>` (and other template special tokens) into the C++ tokenizer default stop token collection (`default_stop_token_ids`) so the server halts naturally without relying on client-supplied parameters.
  2. Ensure client harnesses (OpenCode, agent runners) explicitly send `"stop": ["<|im_end|>", "<|endoftext|>"]` in completion requests.

## 2. CUDA Graphs vs Kernel Launch Latency on Blackwell SM120
- **Symptom**: llama.cpp or custom engine decodes at half roofline (e.g. 22-25 t/s instead of 46-48 t/s on 27B) during initial tokens, then suddenly leaps to ~46 t/s.
- **Root Cause**: CPU-to-GPU launch overhead when dispatching hundreds of separate small kernels (FWHT, Hadamard slices, Q8_1 quantization, MMVQ) per decode step without graph replay.
- **Remediation**:
  - Enable `GGML_CUDA_GRAPHS=1` and `GGML_CUDA_PDL=1` with `CUDA_SCALE_LAUNCH_QUEUES=4x`.
  - In native engines (NInfer), capture exact-batch CUDA graphs (`--prefill-chunk 4096`, batched decode graphs) so driver launch bottlenecks are eliminated.

## 3. Communication & Execution Rules for Benchmark Iterations
- User directive: "lapor kembali hanya jika kamu atau codex sudah mempercepat... hanya laporan itu yg ingin kudengar bukan alasan".
- When optimizing, execute real benchmarks directly and report pure token generation speed (`S_TG`), step latency in milliseconds, and memory bandwidth utilization.
- Never present theoretical explanations or architectural post-mortems in lieu of measurable acceleration artifacts.

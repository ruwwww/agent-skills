---
name: model-inference-verification
description: "Use when implementing models. Verify serving beyond tests."
version: 1.0.0
---

# Model Inference Verification & Serving Standard

## Governing Directive
Unless explicitly stated otherwise by the user, every model implementation, conversion, adaptation, or kernel optimization must be verified end-to-end to run or serve outside of unit testing with demonstrated good performance.

## Key Principles
1. **Beyond Unit Tests**: Unit and parity tests only verify isolated numerical consistency. A model feature is complete only when:
   - The full model can be converted and packaged without failure.
   - The standalone CLI binary (`ninfer`, etc.) or serving daemon (`ninfer-serve`) loads the model weights and initializes runtime state cleanly.
   - Real forward inference (generation/decoding) executes successfully on representative input prompts.
2. **Performance Verification**:
   - Verify that execution throughput (tokens/second) meets or exceeds expected performance baselines.
   - Monitor peak VRAM usage to ensure it remains strictly within targeted hardware bounds (e.g. 16GB VRAM on consumer GPUs).
   - Ensure CUDA Graph capture, KV cache management, and continuous batching run reliably during real workloads.
3. **Serving Readiness**:
   - Verify OpenAI-compatible HTTP endpoints or CLI interactive generation under real conditions.

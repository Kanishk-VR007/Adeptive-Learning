# Hardware & Runtime Compatibility Audit Report
**Project:** Adaptive Exam-Prep Tutor  
**Milestone:** 3 – Local AI Infrastructure & Sequential GPU Execution  
**Audit Date:** 2026-10-31  
**Operating System:** Windows 11 (64-bit)  

---

## 1. Executive Summary

A comprehensive pre-implementation audit was conducted on the development machine to verify hardware capabilities, GPU driver functionality, VRAM capacity, runtime installation status, model availability, and baseline test suite integrity.

All **54 out of 54** existing Milestone 1 & 2 tests passed without error. Database connectivity, BKT math, and learner mastery persistence have been verified.

Both required models (**DeepSeek-R1-Distill-7B** and **Llama 3.2**) are already downloaded and present locally. No large model downloads are required.

---

## 2. Hardware Environment

| Component | Specification | Observed Status | Compatibility |
| :--- | :--- | :--- | :--- |
| **GPU** | NVIDIA GeForce RTX 4050 Laptop GPU | Active, WDDM Driver Model | COMPATIBLE |
| **Dedicated VRAM** | 6,141 MiB (6.0 GB GDDR6) | 228 MiB used / 5,913 MiB free (at idle) | COMPATIBLE |
| **GPU Driver Version** | NVIDIA Display Driver 592.82 | Installed & Healthy | COMPATIBLE |
| **CUDA Version** | CUDA 13.1 Driver API Support | Supported | COMPATIBLE |
| **GPU Temperature** | ~50°C | Normal idle thermal range | COMPATIBLE |
| **System RAM** | 16.0 GB (16,408,932 KB) | ~3.38 GB free (physical) | COMPATIBLE (RAM caching supported via mmap) |
| **Monitoring Tools** | `nvidia-smi` CLI & `nvidia-ml-py` (NVML) | Both verified operational | COMPATIBLE |

---

## 3. Local AI Runtimes

### Runtime 1: LM Studio
- **Status:** Installed (`D:\LM Studio\`, CLI at `C:\Users\rames\.lmstudio\bin\lms.exe`).
- **CLI (`lms`):** Operational (`lms server`, `lms load`, `lms unload`, `lms ls`, `lms ps`).
- **Server Port:** `http://localhost:1234`
- **Native REST API Version:** `v1` (endpoints `/api/v1/models`, `/api/v1/models/load`, `/api/v1/models/unload`, `/v1/chat/completions`).
- **Discovered Model for Model A:**
  - **Key:** `oreal-deepseek-r1-distill-qwen-7b`
  - **Publisher:** `lmstudio-community`
  - **Architecture:** `qwen2`
  - **Parameters:** 7B
  - **Quantization:** `Q4_K_M` (4-bit)
  - **File Size:** 4.68 GB (4,683,073,856 bytes)
  - **Context Length Support:** Up to 131,072 tokens
- **Offload Configuration:** Supports `--gpu <offload-ratio>` (`max` for full GPU offload) and native load parameter `offload_kv_cache_to_gpu: true`.

### Runtime 2: Ollama
- **Status:** Installed and background service active.
- **CLI (`ollama`):** Operational (`ollama list`, `ollama run`).
- **Server Port:** `http://localhost:11434`
- **Endpoints:** `/api/tags`, `/api/chat`, `/api/ps`, `/api/generate`.
- **Discovered Model for Model B:**
  - **Name:** `llama3.2:latest` (family: llama)
  - **Parameters:** 3.2B
  - **Quantization:** `Q4_K_M`
  - **File Size:** 2.01 GB (2,019,393,189 bytes)
  - **Unload Behavior:** Verified via `keep_alive: 0` / inspection via `GET /api/ps`.

---

## 4. VRAM Budget & Sequential Execution Rationale

```
Total Dedicated VRAM: 6,141 MiB (~6.0 GB)

DeepSeek-R1-Distill-7B (Q4_K_M):
- Weights: ~4.68 GB
- KV Cache (4K ctx) + CUDA context: ~0.8 - 1.0 GB
- Peak VRAM footprint: ~5.4 - 5.7 GB

Llama 3.2 (3.2B, Q4_K_M):
- Weights: ~2.01 GB
- KV Cache + CUDA context: ~0.5 - 0.7 GB
- Peak VRAM footprint: ~2.5 - 2.7 GB

COMBINED SIMULTANEOUS FOOTPRINT:
~5.7 GB + ~2.7 GB = ~8.4 GB > 6.0 GB (OUT OF MEMORY / SWAP THRASHING)
```

**Conclusion:** Running both models simultaneously on the GPU is **strictly impossible** within the 6 GB hardware limit. The `GPUExecutionManager` must enforce strict sequential mutual exclusion:
1. DeepSeek load $\to$ reasoning inference $\to$ unload $\to$ verify unloaded.
2. Llama load $\to$ formatting inference $\to$ unload $\to$ verify unloaded.
3. Optional think-time prewarming of DeepSeek while the student solves problems.

---

## 5. Software Baseline Validation

- **Pytest Suite:** 54 passed in 24.27s.
- **Database Engine:** SQLite `PRAGMA foreign_keys=ON` with Alembic migration `c478b4c80894`.
- **BKT Deterministic Engine:** Verified mathematically and through database persistence.

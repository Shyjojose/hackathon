# ThesisClaw Agent Memory — Root (Template)

## Project Identity

- **Project name:** ThesisClaw
- **Hackathon:** NVIDIA Claw Agent Challenge: Berlin
- **Supervisor:** Prof. Dr. Matthias Gorka, THD Campus Cham
- **Document ID:** 260803 abstract attention optimisation v003
- **Thesis Title (DE):** *Echtzeit- und datenschutzkonforme Sprachtranskription mittels lokaler Verarbeitung: Entwurf einer End-to-End-Systemarchitektur mit Small Language Models für RISC-basierte eingebettete Systeme.*
- **Deadline:** 2026-10-02 12:00 CEST (internal freeze)
- **Repo:** https://github.com/Shyjojose/hackathon

---

## Central Research Area & Claims

**Research Area:** 
Real-Time, Privacy-Preserving Automatic Speech Recognition (ASR) & Small Language Model (SLM) Inference on Resource-Constrained RISC Hardware (Raspberry Pi 5 16GB, Quad-Core ARM Cortex-A76 @ 2.4 GHz, LPDDR4X ~3,631 MiB/s).

**Core Model Focus:** 
Moonshine Tiny, local sliding window attention $O(N \times W)$, intermediate encoder caching, and Post-Training Quantization (PTQ) across FP16, INT8, and INT4 using 128-bit ARM NEON SIMD integer matrix operations.

**Deployment Architecture:** 
Unprivileged Podman container isolation with CPU core affinity, strictly adhering to GDPR, StGB § 201, and EU AI Act Article 50 (no cloud telemetry, raw audio destroyed post-inference).

---

## Central Hypotheses

**Main Hypothesis:**
> "If symmetric integer quantization compresses ASR models below INT8 precision, then the Real-Time Factor (RTF) and memory consumption decrease on ARM Cortex-A76 processors without exceeding 6% Word Error Rate (WER) degradation compared to the FP16 baseline."

**Supporting Sub-Hypotheses:**
1. **Memory:** Compressing model tensors from FP16 to INT4 decreases peak RAM allocation by $\ge 50\%$ while keeping WER degradation $\le 6\%$.
2. **Cache & Bandwidth:** Decreasing quantization bit-width to INT4 reduces L2/L3 cache miss rates proportionally, mitigating memory bandwidth bottlenecks (~3,631 MiB/s limit) and boosting throughput.

---

## S.M.A.R.T. Engineering Verification Targets

| Metric | Target Threshold | Measurement Method |
|---|---|---|
| **1. Streaming Speed** | **RTF $\le 0.5$** (Processing time / audio duration) | Real-time audio stream benchmark |
| **2. Quantization Accuracy** | **WER $\le 6\%$** degradation vs. FP16 baseline | Standard speech test set evaluation |
| **3. Memory Footprint** | **Peak RAM $\le 1.0\text{ GB}$** at INT4 | `podman stats` / `cgroup v2` memory accounting |
| **4. Acoustic DoS Resistance** | **0 OOM crashes** under continuous token-flood | Continuous adversarial audio stress loop |
| **5. Container Isolation** | **0 security escapes** / 24 hours | Unprivileged Podman user namespace audit logs |

---

## Paper Classification Boundary Conditions

### 🟢 Papers that SUPPORT this claim:
- Post-Training Quantization (PTQ) benchmarks showing symmetric INT4/INT8 ASR models retain within 6% WER of FP16.
- 128-bit ARM NEON SIMD integer-arithmetic optimizations for low-bit tensor convolutions/GEMM on Cortex-A76.
- Sliding window attention / localized attention optimizations that reduce $O(N^2)$ decode loops to $O(N \times W)$ on edge CPUs.
- Zero-leakage containerized edge deployment patterns (Podman, unprivileged namespaces, cgroups v2).

### 🟡 Papers that EXTEND this claim:
- Mixed-precision quantization (e.g., INT4 weights with INT8 activations or sensitive attention heads kept in FP16).
- Speculative decoding for edge ASR using micro-SLMs.
- Hardware-aware kernel compilation (TVM, ExecuTorch, llama.cpp / ggml optimizations specifically tuned for Cortex-A76 memory buses).
- Novel regulatory compliance frameworks for edge AI auditing under the EU AI Act Article 50.

### 🔴 Papers that THREATEN this claim:
- Empirical studies showing that INT4 quantization on small ASR models (<100M params like Moonshine Tiny) suffers catastrophic perplexity/WER degradation (>6%).
- Benchmarks demonstrating that CPU-bound decode loops on Cortex-A76 are compute-bound rather than memory-bound (disproving sub-hypothesis 2).
- Security vulnerability disclosures demonstrating container breakout or memory scraping on Linux ARM cgroups.

### ⚪ Papers that are IRRELEVANT:
- Server-side multi-GPU (H100/A100) distributed training.
- Diffusion, image generation, or multi-modal vision-only architectures.
- Cloud-dependent ASR architectures requiring persistent external API access.

---

## Active Projects

- `rpi5-moonshine-int4` — Profiling Moonshine Tiny with INT4/INT8 PTQ on Raspberry Pi 5 under unprivileged Podman containers.

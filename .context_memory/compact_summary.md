# ThesisClaw Project — Compact Context & Knowledge Base

This file condenses all preceding architectural decisions, system requirements, and research parameters into a single persistent reference to keep model context compact.

---

## 1. Project Identity & Objective
- **Project**: ThesisClaw
- **Challenge**: NVIDIA Claw Agent Challenge: Berlin (Submission deadline: October 2, 2026, 12:00 CEST).
- **Mission**: A long-running autonomous research agent that monitors daily arXiv literature, evaluates every paper against a student's academic thesis, warns when research is scooped or supported, proposes next experiments, and connects to a physical desk companion (ESP32-S3).

---

## 2. Real Academic Thesis Profile
- **German Title**: *Echtzeit- und datenschutzkonforme Sprachtranskription mittels lokaler Verarbeitung: Entwurf einer End-to-End-Systemarchitektur mit Small Language Models für RISC-basierte eingebettete Systeme.*
- **Supervisor**: Prof. Dr. Matthias Gorka, THD Campus Cham (Document ID: 260803 abstract attention optimisation v003).
- **Hardware & Architecture**:
  - Target: Raspberry Pi 5 16GB, Quad-Core ARM Cortex-A76 @ 2.4 GHz, LPDDR4X ~3,631 MiB/s.
  - Model: Moonshine Tiny / Small Language Models (SLMs) with localized sliding-window attention $O(N \times W)$ and intermediate encoder state caching.
  - Quantization: Post-Training Quantization (PTQ) across FP16, INT8, and INT4 utilizing 128-bit ARM NEON SIMD integer matrix operations.
  - Security / Compliance: Unprivileged Podman container isolation with CPU core affinity, zero cloud telemetry, strict GDPR, StGB § 201, and EU AI Act Article 50 compliance.
- **Main Hypothesis**:
  > *"If symmetric integer quantization compresses ASR models below INT8 precision, then real-time factor (RTF) and memory consumption decrease on ARM Cortex-A76 processors without exceeding 6% WER degradation."*
- **S.M.A.R.T. Targets**:
  1. Streaming Speed: $\text{RTF} \le 0.5$ (processing time / audio duration).
  2. Quantization Accuracy: $\text{WER} \le 6\%$ degradation vs. FP16 baseline.
  3. Memory Footprint: Peak $\text{RAM} \le 1.0\text{ GB}$ at INT4.
  4. Acoustic DoS Resistance: 0 OOM crashes under load.
  5. Container Isolation: 0 escapes / 24 hours.

---

## 3. Technology Stack & Component Map
- **Runtime Environment**: Python 3.12 managed exclusively with `uv`.
- **Primary Model Provider**: NVIDIA Build API (`integrate.api.nvidia.com`) via `langchain-nvidia-ai-endpoints`.
  - Worker Model: `nvidia/llama-3.1-nemotron-70b-instruct` (128k context window).
  - Critic Model: `nvidia/nemotron-4-340b-instruct` (high-parameter quote verifier).
  - Fast Pre-filter: `meta/llama-3.1-8b-instruct`.
  - Embeddings: `nvidia/llama-3.2-nv-embedqa-1b-v2`.
- **Agent Orchestrator**: LangChain `deepagents` harness with `SqliteSaver` checkpointing (`checkpoints/thesisclaw.sqlite3`).
- **Subagents**: `paper-reader`, `thesis-matcher`, `pathfinder`, `critic`, `publisher`.
- **Human Approval**: Web interface (`GET /notes`, `POST /approve/{job_id}`); approvals strictly forbidden via chat/MCP.
- **External Interfaces**:
  - Telegram: Interactive bot interface for daily briefings, alerts, and paper links.
  - MCP Server: Model Context Protocol (SDK v2) Streamable HTTP on port 8080.
  - Voice Companion: XiaoZhi ESP32-S3 firmware client (`voice/src/mcp_pipe.py`, MCP SDK v1 `FastMCP`, ≤600 chars plain text).

---

## 4. Execution Sequence (Telegram-First, MCP-Last)
- **Milestone 0**: Seed Thesis Memory & Context Memory Init.
- **Milestone 1**: Config (`settings.py`) & Pydantic Data Models (`paper.py`, `job.py`).
- **Milestone 2**: Ingestion & Embeddings Tools (`fetch.py`, `embed.py`).
- **Milestone 3**: Deep Agents Multi-Subagent Pipeline (`orchestrator.py`, `subagents.py`).
- **Milestone 4**: Background Execution Jobs (`scan.py`, `backfill.py`, `sleep.py`).
- **Milestone 5**: Interactive Telegram Bot Channel.
- **Milestone 6**: Web Approval Dashboard.
- **Milestone 7**: Static Public Site & Site Builder.
- **Milestone 8**: MCP Server (v2) & XiaoZhi ESP32-S3 Voice Bridge.
- **Milestone 9**: Final Quality Gate, Ruff Lint Clean, and Test Suite Pass.

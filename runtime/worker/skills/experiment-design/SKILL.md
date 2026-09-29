---
name: experiment-design
description: >
  Use when the pathfinder subagent proposes a next experiment for an ESP32-S3
  edge AI project. Covers constraints, falsifiability rules, and the approval
  gate before any code change is proposed.
---

# Experiment Design Skill

## Hardware Constraints (ESP32-S3)

- RAM: 512 KB SRAM + optional PSRAM (up to 8 MB)
- Flash: up to 16 MB
- No GPU. Inference must use TensorFlow Lite Micro, ONNX Runtime for MCUs, or
  custom quantised models.
- Power: battery-constrained for standalone deployments.
- Any proposed experiment must be runnable within these constraints.

## Falsifiability Rules

Every proposed experiment must have:
1. A **measurable outcome** (e.g. inference latency in ms, accuracy on a fixed test set).
2. A **success criterion** (e.g. "latency < 50 ms at 90% accuracy").
3. A **failure criterion** (e.g. "if latency > 100 ms, the approach is not viable").

## Approval Gate

Before calling `propose_code_change`:
1. Call `interrupt()` with a human-readable description of the proposed change.
2. Wait for the human to approve on the web UI.
3. Only after approval, emit the `propose_code_change` action.

Never skip the approval gate, even if the change looks trivial.

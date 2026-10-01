# 🦅 ThesisClaw — NVIDIA Claw Agent Challenge Submission

**Hackathon Track:** NVIDIA Claw Agent Challenge: Berlin 🇩🇪  
**Submission Deadline:** October 2, 2026, 12:00 CEST  
**Project Name:** ThesisClaw (Autonomous Literature Agent & Thesis Defense Monitor)  
**Author:** Shyjojose  
**Repository:** Private GitHub Repository (`Shyjojose/hackathon`) — *kept private to protect ongoing academic thesis research findings*.  
**Live Project URL:** [https://democratic-decade-memorabilia-copying.trycloudflare.com/leaderboard](https://democratic-decade-memorabilia-copying.trycloudflare.com/leaderboard)

---

## 📋 Form Question 1: Which agent harness did you use for your project?

**Primary Selection:** `LangGraph`  
**Detailed Specification:**  
`LangGraph (Adversarial Multi-Agent Debate Arena) + Deep Agents Sequential Pipeline (Python 3.12 / uv) + OpenClaw Gateway (Model Context Protocol v2 Streamable HTTP)`

### Architectural Breakdown:
1. **LangGraph StateGraph (`src/thesisclaw/arena/graph.py`):** Coordinates the adversarial **Paper Arena (Agent Wars)**. Features parallel opening argument fan-outs using the LangGraph `Send` API, structured cross-examination, common-ground synthesis, deterministic quote verification, and dual-run symmetrical judging.
2. **Deep Agents Sequential Worker Pipeline (`src/thesisclaw/agent/`):** Orchestrates a 5-subagent literature analysis flow (`paper-reader`, `thesis-matcher`, `critic`, `pathfinder`, `publisher`) backed by SQLite checkpointers and strict token budgeting (`ORCHESTRATOR_TOKEN_BUDGET`).
3. **OpenClaw Gateway & Model Context Protocol (MCP SDK v2):** Separates the host conversational system (Telegram bot and CLI) from sandboxed worker agents over local HTTP (`:8080/mcp`).
4. **XiaoZhi Voice Bridge (`voice/`):** Standalone FastMCP v1 companion project communicating with a physical ESP32-S3 desk companion with a strict $\le 600$ plain-text character privacy ceiling.

---

## 📝 Form Question 2: Claw Agent Description

> **Tell us what your agent does and why you built it: what problem does it solve, and who does this help?**

### 1. Why I Built It: The Problem with LLMs in Deep Research
Next semester, my academic master's thesis begins. When speaking with colleagues and seniors who recently completed their theses, one recurring failure pattern stood out: **research overload and "LLM hallucination drift"**.

Tools like Claude Code or ChatGPT give an initial sense of direction, but as research progresses through weeks of literature, their chain-of-thought inevitably breaks. They lose the specific technical parameters of the thesis, hallucinate paper citations, or overlook preprints that quietly scoop the project or invalidate baseline benchmarks. By the time the researcher discovers the discrepancy, weeks of engineering have been derailed.

### 2. The Anchor: A Concrete Ground-Truth Engineering Thesis
Unlike generic summarizers that produce generic abstracts, **ThesisClaw is permanently anchored to a real, high-stakes engineering thesis**:
- **Topic:** Real-time, privacy-compliant edge speech recognition on resource-constrained ARM Cortex-A76 hardware (Raspberry Pi 5 16GB).
- **The Core Hypothesis:** Symmetric integer quantization below INT8 precision can decrease real-time factor (RTF) and memory footprint on ARM processors without exceeding a 6% Word Error Rate (WER) degradation compared to the FP16 baseline.
- **S.M.A.R.T. Target Parameters:**
  - Streaming Speed: **RTF $\le 0.5$**
  - Quantization Accuracy: **WER $\le 6\%$** degradation
  - Peak Memory: **RAM $\le 1.0\text{ GB}$** at INT4
  - Continuous DoS Protection: **0 OOM crashes** under continuous audio stream flood
  - Container Security: **0 escapes / 24 hours** in unprivileged Podman containers

### 3. What ThesisClaw Does: Autonomous Sentinel & Adversarial Paper Arena
ThesisClaw turns research papers from passive PDFs into active, autonomous agents that fight for their position on an Elo leaderboard against the ground truth thesis:

1. **Autonomous Nightly Scan & Pre-Flight Similarity Gate:**  
   Monitors arXiv preprints nightly. Before triggering expensive LLM reasoning, a pre-flight cosine embedding filter ($\ge 0.35$ threshold) weeds out irrelevant papers (e.g., filtering out computer vision models from audio quantization).
2. **Paper Arena (Agent Wars Mode):**  
   Relevant papers enter a 4-round moderated LangGraph debate ring:
   - **Round 1 (Parallel Openings):** Fighters extract their strongest claims using verbatim quotations.
   - **Round 2 (Cross-Examination):** Contenders challenge each other’s benchmark methodologies and hardware assumptions.
   - **Round 3 (Common Ground & Synthesis):** The moderator extracts hybrid engineering insights and novel benchmark ideas.
3. **Deterministic Verbatim Quote Verifier ($\ge 90\%$ Gate):**  
   To prevent hallucinated citations, a deterministic code verifier normalizes unicode ligatures, soft hyphens, and whitespace against the original paper text. Any unverified citation is penalized by the judge and struck through on generated dashboards.
4. **Symmetrical Dual-Run Judging:**  
   Powered by **NVIDIA Llama-3.1-Nemotron-70B/340B**, the judge evaluates the debate twice with swapped perspective order to eliminate positional bias, requiring $\ge 80\%$ agreement.
5. **Dynamic Chess-Style Elo Leaderboard:**  
   The student's **Thesis Draft is permanently grounded as Rank #1**. Existing champion papers defend their rankings whenever newcomers enter the ring, giving the student an immediate, ranked hierarchy of literature that supports, extends, or threatens their thesis.
6. **Hardware Pathfinder & Human Approval Gate:**  
   For papers that extend or threaten the thesis, the agent designs an executable Raspberry Pi 5 benchmark experiment and drafts an APA citation. Any proposed code modification or GitHub PR is paused at a secure web approval gate (`:8080/notes`) requiring human review.
7. **Mobile Telegram Integration & Physical Desk Companion:**  
   Backed by an auto-managed Cloudflare Quick Tunnel, the Telegram bot provides real-time animated debate commentary (`editMessageText`) and mobile-optimized WebApp buttons, while a physical XiaoZhi ESP32-S3 desk device delivers voice briefings.

### 4. Who This Helps
- **Graduate and PhD Researchers:** Who need a reliable, 24/7 autonomous literature sentinel that never drifts from their thesis claims.
- **R&D Engineers & Systems Labs:** Benchmarking edge AI or embedded models who cannot afford to waste engineering cycles on scooped or invalidated hypotheses.

---

## 🎥 Form Question 3: Demo Video URL or Project Link

> **Show us your long-running agent in action! Submit either a demo video (up to 3 minutes; 30-90 seconds preferred) or a link to your project where we can explore what you built.**

### 🔗 Project Links (Live & Private Repo Strategy)
- **Live Interactive Dashboard (Cloudflare Tunnel):**  
  👉 [https://democratic-decade-memorabilia-copying.trycloudflare.com/leaderboard](https://democratic-decade-memorabilia-copying.trycloudflare.com/leaderboard)  
  *(Judges can explore live Elo standings, two-column debate transcripts, and 4-tab literature breakdowns directly without needing repository access).*
- **Private GitHub Repository:** `https://github.com/Shyjojose/hackathon`  
  *(Because this repository contains confidential master's thesis research, it is kept private. Hackathon judges can be granted immediate read collaborator access upon request: contact Shyjojose on GitHub or via hackathon submission email).*
- **Demo Video (Unlisted YouTube / Loom):** `[INSERT YOUR LOOM OR UNLISTED YOUTUBE LINK HERE]`  
  *(Use the 90-second recording script below).*

---

### ⏱️ 90-Second Demo Video Recording Script

| Timestamp | Visual on Screen | Spoken Voiceover / Audio |
|---|---|---|
| **0:00 – 0:15** | Show `README.md` and the Thesis Anchor: RPi5 Edge ASR Quantization (RTF $\le 0.5$, RAM $\le 1.0\text{ GB}$). | *"Hello! Next semester I start my master's thesis on edge speech recognition on Raspberry Pi 5. Most researchers struggle with literature overload and LLM drift that derails their work. I built ThesisClaw—an autonomous agent permanently anchored to my thesis claims."* |
| **0:15 – 0:40** | Switch to Telegram chat on phone or desktop. Type `/fight 2410.05229` (or tap `⚔️ Paper Fight`). Show the live animated message editing in real time. | *"Here in Telegram, I pit newly ingested arXiv preprints into the Paper Arena. The LangGraph engine runs parallel openings, cross-examination, and common-ground discovery. Notice how the bot streams round-by-round progress live using in-place message editing."* |
| **0:40 – 1:05** | Tap the **"🏆 Open Leaderboard"** button or open `/leaderboard` in the browser via Cloudflare Tunnel. | *"Before judging, a deterministic code verifier checks every quote against the source paper—requiring 90% verbatim backing to eliminate hallucinations. NVIDIA Nemotron judges the fight symmetrically, updating our chess-style Elo leaderboard where my thesis is grounded as #1."* |
| **1:05 – 1:20** | Click on a paper in the gallery or show the Human Approval Gate (`/notes`). | *"For papers that threaten or extend my thesis, the Pathfinder subagent synthesizes a concrete Raspberry Pi 5 experiment and citable paragraph. Any code change pauses for human approval on the web dashboard before execution."* |
| **1:20 – 1:30** | Show the XiaoZhi ESP32-S3 desk device (or photo/clip) receiving a concise voice summary. | *"With zero-config Cloudflare Tunnels for mobile and an ESP32-S3 voice companion on my desk, ThesisClaw keeps my thesis defended 24/7. Thank you!"* |

---

## 💬 Form Question 4: Tell us about your experience with the Claw Agent Challenge

> **What worked well, what was challenging, and what would you change about the Claw Agent Challenge?**

### 1. What Worked Well
- **NVIDIA Build Cloud (NIM) & Nemotron Models:** The inference speed and reasoning depth of `nvidia/llama-3.1-nemotron-70b-instruct` and `nemotron-3-ultra` were exceptional. They followed complex debate personas and produced rigorous cross-examinations without straying from provided paper snippets.
- **Model Context Protocol (MCP v2):** Separating the host gateway (Telegram / CLI) from the worker execution environment using streamable HTTP MCP tools (`/mcp` and read-only `/voice-mcp`) created a clean, modular architecture that made debugging subagents straightforward.
- **LangGraph Multi-Agent Orchestration:** The `StateGraph` state machine with `Send` fan-outs enabled parallel opening arguments, structured turn-taking, and SQLite checkpointing so debates can resume without duplicate compute.
- **Cloudflare Quick Tunnels:** Providing zero-config public HTTPS port forwarding without needing a cloud VM or domain purchase allowed instant testing of Telegram mobile links and responsive dashboards.

### 2. What Was Challenging
- **Hallucination Containment in Academic Debates:** LLMs naturally want to paraphrase or invent quotes during high-stakes debate. Resolving this required building an offline deterministic quote verifier (`arena/verify.py`) that normalizes unicode ligatures, soft hyphens, and whitespace, enforcing a hard $\ge 90\%$ verbatim quotation threshold.
- **Positional Bias in LLM Judging:** When judging adversarial debates, LLMs often favor whichever fighter speaks first or second. We overcame this by implementing **symmetrical dual-run judging** (Run 1: A vs B; Run 2: B vs A with swapped roles), enforcing an 80% agreement threshold before awarding Elo points.
- **Real-Time UX in Messaging Apps:** Long-running multi-round debates can leave chat users waiting in silence. Integrating asynchronous progress callbacks into the LangGraph loop and dynamically updating the Telegram message via `editMessageText` created an engaging, animated commentary experience.

### 3. What I Would Change About the Challenge
- **Standardized Multi-Agent Adversarial Benchmarks:** It would be valuable to have pre-defined benchmark suites or evaluation metrics specifically for multi-agent adversarial debate quality, citation grounding, and position-bias mitigation.
- **More Mobile Channel Starter Kits:** Having official NVIDIA starter templates connecting MCP server tools directly with mobile messaging channels (Telegram, Discord, WebSockets) would accelerate development for teams building mobile-first long-running agents.

---

## 📊 Technical Verification Summary

- **Automated Test Suite:** `150 passed, 4 skipped` (`uv run pytest -m "not live"`).
- **Code Style & Linting:** `ruff check src/ tests/ evals/` $\rightarrow$ Clean (0 warnings).
- **Security & Privacy:**
  - Secrets stored exclusively in `.env` (gitignored).
  - Human Approval Gate for code mutations (ADR-005).
  - ESP32-S3 voice output strictly truncated to $\le 600$ characters (ADR-004).
  - Prompt injection canary containment preventing adversarial papers from executing tool calls.

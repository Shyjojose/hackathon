# ThesisClaw — End-to-End Build Plan & Execution Prompt

This file serves as your editable guide and master execution prompt for building the complete ThesisClaw agent. You can review, adjust, and customize any section before running the build.

---

## 1. What You Should Do Right Now (Prerequisites)

Before triggering the build, complete these quick local setup steps:

### A. Set Up Environment Variables (`.env`)
Run the following in your terminal to create your `.env` file from the example:
```bash
cp .env.example .env
```
Open `.env` and fill in:
- `NVIDIA_API_KEY` & `NVIDIA_INFERENCE_API_KEY`: Your NVIDIA API key.
- `TELEGRAM_BOT_TOKEN`: The bot token obtained from `@BotFather`.
- `TELEGRAM_ALLOWED_IDS`: Your personal Telegram user ID (numeric) to ensure strict allowlisting.
- `GITHUB_TOKEN`: A token with repo access if you plan to let pathfinder open draft PRs.
- `LAMBDA_API_KEY`: (Optional for local testing, required for cloud instance demo).

### B. Seed the Agent's Thesis Memory (`research/agent.md`)
The matcher needs a ground-truth thesis statement to know whether an incoming paper supports, extends, or threatens your work.
```bash
mkdir -p research
cp templates/research/agent.md research/agent.md
```
Open `research/agent.md` and fill in:
- Your research topic (e.g., *Efficient INT4 Edge AI Inference on ESP32-S3*).
- Your central claim and boundary criteria.

---

## 2. How to Use and Edit This File

- **Customize**: You can tweak the model names, file paths, rate limits, or verification tests in Section 3 below.
- **Run the Build**: When ready, either tell Antigravity:
  > `"Read build.md and implement the end-to-end agent according to Section 3."`
  or copy-paste the prompt block in Section 3 directly into the chat.

---

## 3. The Master Execution Prompt

*(Copy and run the prompt below, or edit it directly in this file)*

```markdown
/plan implement the ThesisClaw working agent end-to-end following this priority order:

### 1. Configuration & Settings
- File: `src/thesisclaw/config/settings.py`
- Description: Pydantic BaseSettings loading from `.env`. Must include keys for NVIDIA, Telegram, GitHub, Lambda, MCP tokens, and token budgets.

### 2. Data Models
- Files: `src/thesisclaw/models/paper.py`, `src/thesisclaw/models/job.py`
- Description: Strict Pydantic models for PaperContent, PaperVerdict, CriticResult, PathfinderResult, BriefingResult, and ScanJob.

### 3. Core Tools
- Files: `src/thesisclaw/tools/fetch.py`, `src/thesisclaw/tools/embed.py`
- Description:
  - arXiv fetcher using `arxiv-txt.org` first, falling back to experimental arXiv HTML and PDF fallback (`pymupdf4llm`). Wrap in tenacity retry logic and enforce 1 req / 3 sec.
  - NVIDIA Embeddings integration using `langchain-nvidia-ai-endpoints` (`nvidia/nv-embedqa-e5-v5`) and cosine similarity helper.

### 4. MCP Server (SDK v2)
- Files: `src/thesisclaw/mcp/server.py`, `src/thesisclaw/mcp/main.py`
- Description:
  - Implement full `/mcp` surface and read-only `/voice-mcp` surface via Streamable HTTP (MCP SDK v2 `MCPServer`).
  - Enforce separate bearer tokens (`MCP_BEARER_TOKEN` and `VOICE_MCP_BEARER_TOKEN`).
  - Implement tools: `analyze_paper`, `get_briefing`, `get_paper_summary`, `get_status`, and `add_note`.
  - Cap individual messages at 128 KiB.

### 5. Deep Agents Orchestrator & Subagents
- Files: `src/thesisclaw/agent/orchestrator.py`, `src/thesisclaw/agent/subagents.py`
- Description:
  - Build orchestrator using `create_deep_agent` with `SqliteSaver` checkpointer.
  - Wire the 5 subagents (`paper-reader`, `thesis-matcher`, `pathfinder`, `critic`, `publisher`), loading their respective prompts from `runtime/worker/prompts/` and skills from `runtime/worker/skills/`.
  - Enforce human approval via `interrupt()` for any side-effecting code change or new topic creation.

### 6. Background Jobs & Execution Loops
- Files: `src/thesisclaw/jobs/scan.py`, `src/thesisclaw/jobs/backfill.py`, `src/thesisclaw/jobs/sleep.py`
- Description:
  - `scan.py`: Daily automated literature ingestion and checkpoint updates.
  - `backfill.py`: Batch historical processing of papers for demo evidence.
  - `sleep.py`: Polling/idle task maintaining session state and periodic note synthesis.

### 7. Human-in-the-Loop Web UI
- File: `src/thesisclaw/web/app.py`
- Description:
  - Lightweight FastAPI application providing a simple web dashboard for human review.
  - Allows approving pending `pathfinder` proposals (which generates GitHub PRs).
  - Approvals MUST only be accepted via web UI, never via MCP or chat.

### 8. Site Generator
- Files: `src/thesisclaw/site_builder/stats.py`, `src/thesisclaw/site_builder/pages.py`
- Description:
  - Reads checkpoint databases and live memory to update `site/public/stats.json`.
  - Generates static HTML summary pages for evaluated papers using Jinja2 without external JS.

### 9. Static Public Judge Dashboard
- File: `site/public/index.html`
- Description:
  - Clean vanilla HTML/CSS dashboard displaying long-running agent stats, session timelines, and verdict breakdowns.

### 10. Voice Bridge
- File: `voice/src/mcp_pipe.py`
- Description:
  - Standalone MCP v1 (`FastMCP`) client bridging the XiaoZhi ESP32-S3 firmware with ThesisClaw.
  - Strict handshake handling (`initialize` -> `notifications/initialized`).
  - Hard limit of ≤600 plain text characters per voice reply. Never expose private thesis drafts to third-party voice cloud.

### 11. Infrastructure & Demo Automation
- Files: `infra/lambda_control.py`, `infra/cloudflared.yaml`
- Description:
  - Safe programmatic Lambda API lifecycle control (`launch`, `terminate`, `status`). NEVER run `sudo shutdown`.
  - Cloudflare Tunnel config for forwarding the local judge site and MCP endpoint.

---

### Strict Quality Rules
- Maintain `uv` exclusively; run `uv sync` in the respective projects (`.` and `voice/`).
- Verify each step with unit tests in `tests/unit/` using mocked HTTP (`respx`).
- Run `uv run pytest -m "not live"` and `uv run ruff check src/ tests/ evals/` after implementation.
```

---

## 4. Key Verification & Definition of Done

Once the build finishes, ensure the following pass:
1. **Tests & Linting**:
   ```bash
   uv run pytest -m "not live"
   uv run ruff check src/ tests/ evals/
   ```
2. **Secret Scan**:
   ```bash
   grep -rn "nvapi-\|ghp_\|github_pat_" . --exclude-dir=.git --exclude-dir=.venv
   ```
3. **Voice Subproject Isolation**:
   ```bash
   cd voice && uv sync && uv run python -c "import mcp; print(mcp.__version__)" && cd ..
   ```
4. **Safety Hook**:
   ```bash
   python scripts/hooks/guard.py "sudo shutdown -h now"  # Should exit with code 1
   ```

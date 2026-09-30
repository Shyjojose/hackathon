# Architecture Decision Records

## ADR-001 — Root `AGENTS.md`, Not `copilot-instructions.md`

**Decision:** Use `AGENTS.md` in the repo root.
**Reason:** `AGENTS.md` is the open standard read by Copilot, Cursor, Aider, and other coding agents.
VS Code only allows one of the two files; `AGENTS.md` is the more portable choice.

---

## ADR-002 — Separate Homes for Coding and Runtime Skills

**Decision:** Coding skills in `.github/skills/` and `.agents/skills/`. Runtime skills in
`runtime/openclaw/skills/` and `runtime/worker/skills/`.
**Reason:** VS Code loads skills from `.github/skills/` and `.agents/skills/`. Runtime folders
must never be in a path VS Code loads skills from, to prevent the coding agent from following
the Telegram agent's rules.

---

## ADR-003 — Two Separate uv Projects for MCP SDK Versions

**Decision:** Root project uses `mcp>=2.2,<3`; `voice/` uses `mcp>=1.28,<2`. These are
separate uv projects, not a uv workspace.
**Reason:** `mcp_pipe.py` (XiaoZhi) requires MCP SDK v1. A uv workspace can only resolve
one version of a package. Two separate projects are the only safe approach.

---

## ADR-004 — Two MCP Endpoints with Separate Tokens

**Decision:** `/mcp` (full tools, `MCP_BEARER_TOKEN`) and `/voice-mcp` (read-only, `VOICE_MCP_BEARER_TOKEN`).
**Reason:** The voice bridge (ESP32-S3 / XiaoZhi) is connected to a third-party cloud.
Limiting it to read-only tools prevents a compromised voice session from triggering
side-effecting actions.

---

## ADR-005 — Approvals via Web UI Only, Never via MCP or Telegram

**Decision:** All side-effecting actions (PR creation, experiment approval, code changes)
require a click on the logged-in notes web page.
**Reason:** An injected prompt inside a paper could otherwise trigger approvals via Telegram
or an MCP tool call. The web UI requires a browser session, which a paper cannot fake.

---

## ADR-006 — Live Research Memory Outside Git

**Decision:** `research/` is gitignored. Templates are tracked in `templates/research/`.
**Reason:** The live memory files contain the researcher's thesis text and unpublished
analysis. These must not appear in a public repo. The live copy lives on the Lambda
persistent filesystem and is backed up to a separate private repo.

---

## ADR-007 — Public Site via Local Port Forwarding (Cloudflare Tunnel)

**Decision:** The public judge page is served from localhost via `cloudflared tunnel`.
No cloud VM for the site.
**Reason:** Eliminates the need for a separate hosting account and keeps the bill down.
The Cloudflare Tunnel URL is stable for the duration of the hackathon.

---

## ADR-008 — arXiv Text via `arxiv-txt.org`

**Decision:** Primary paper text source is `https://arxiv-txt.org/abs/<id>`, not PDF parsing.
**Reason:** PDF-to-text conversion is slow and error-prone. `arxiv-txt.org` provides
LLM-friendly clean text with no dependencies. Fall back to arXiv HTML, then PDF.

---

## ADR-009 — Hackathon Repo is the Main Repo

**Decision:** `https://github.com/Shyjojose/hackathon` is the main project repo.
There is no separate thesis repo. The ESP32-S3 firmware lives at `/Users/shyjojose/esp32`
(local, separate repo, not the primary hackathon submission).
**Reason:** This is a hackathon project, not an academic thesis. The submission is the agent.

---

## ADR-010 — NVIDIA Nemotron Models

**Decision:** Default model: `nvidia/nemotron-3-super-120b-a12b`. Critic/verification:
`nvidia/nemotron-3-ultra-550b-a55b`. Budget check with Nano first.
**Reason:** As documented in `goal.md`. Eval on 30 test papers to pick the right model
per role before the deadline.

---

## ADR-011 — Paper Arena (AgentWars Integration)

**Decision:** Add `src/thesisclaw/arena/` as an isolated module alongside the existing sequential pipeline.
No existing module is modified until the arena is fully working.
**Reason:** Papers-as-agents fight adds a unique, differentiated demo hook for the hackathon.
The existing pipeline remains untouched. Arena uses LangGraph Send API for parallel fighter openings
and SqliteSaver for resumable checkpoints. Leaderboard uses **Elo rating**: papers defend rating
against newcomers.

---

## ADR-012 — Voice Bridge Deferred (Not Dropped)

**Decision:** `voice/` project and `/voice-mcp` endpoint are kept as-is and not modified during
arena development. Resume after arena is complete and tested.
**Reason:** Voice has demo value; focus is arena first (user decision 2026-09-30).

---

## ADR-013 — Ground Fighter Document Composition

**Decision:** Ground fighter = `research/agent.md` (primary) + project brief S.M.A.R.T. section
+ any `*.draft.md` files in `research/`. Draft thesis text included; user approved NVIDIA endpoint use.
**Reason:** Richer Ground document produces stronger, more specific fight arguments.

---

## ADR-014 — Fight-Trace Evaluation Harness

**Decision:** Add `evals/fights/` with `run_fight_eval.py` (live) and `score_fight.py` (offline).
Pre-recorded JSONL fixtures scored against 4 thresholds offline in `pytest -m "not live"`.
**Reason:** Judges need verifiable numbers. Harness runs without live API calls in CI.

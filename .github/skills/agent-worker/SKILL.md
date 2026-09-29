---
name: agent-worker
description: >
  Use when writing or debugging the Deep Agents worker: orchestrator, subagents,
  MCP server (v2), LangGraph persistence, checkpoint resumption, human-in-the-loop
  approvals, or LangSmith tracing. Also use when writing tests for any of these.
---

# Agent Worker Skill

Load the docs-first skill before proceeding.

## Deep Agents Patterns

- **Create an agent:** Use `create_deep_agent(model, tools, skills=["path/to/skills/folder"])`.
  The `skills=` parameter takes the **folder that contains skill folders**, not the skill folder itself.
- **Custom subagents** do not inherit the main agent's skills. Each subagent needs its own
  `skills=` list.
- **Reload a thread's skills** without starting a new thread: set `skills_metadata: None` in
  the thread config.
- **Human approval gate:** Use the built-in `interrupt()` primitive. Never build a custom
  approval mechanism — the built-in one is what the judges will inspect in the LangSmith trace.

## MCP Server (v2) Patterns

- Use `MCPServer`, not `FastMCP` (that is v1, used only in `voice/`).
- All tool inputs and outputs must be Pydantic models.
- Keep individual MCP messages ≤ 128 KiB (NemoClaw hard limit).
- The `/mcp` endpoint requires a bearer token from `MCP_BEARER_TOKEN` env var.
- The `/voice-mcp` endpoint is read-only and uses a separate `VOICE_MCP_BEARER_TOKEN`.

## LangGraph Persistence

- Use `langgraph-checkpoint-sqlite` for local checkpoints during development.
- The checkpoint file goes in `checkpoints/` (gitignored).
- To prove resumption for the demo: terminate the Lambda instance via the API,
  relaunch it, and show the agent picking up from the last checkpoint.

## Testing Patterns

- Tag live tests with `@pytest.mark.live` so they are skipped in CI.
- Use `respx` to mock all HTTP calls to NVIDIA, arXiv, Lambda, and GitHub.
- Wiring test for the orchestrator: inject a fake model that always returns
  a fixed tool call, verify the subagent is invoked.
- Checkpoint resumption test: run the orchestrator to step N, kill it, reload
  from checkpoint, verify step N+1 runs correctly.
- LangSmith traces: enable with `LANGCHAIN_TRACING_V2=true` for live runs.

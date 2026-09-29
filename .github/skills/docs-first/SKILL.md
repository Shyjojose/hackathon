---
name: docs-first
description: >
  Use when touching any external library or API — langchain, mcp, nvidia,
  deepagents, arxiv, openclaw, telegram, lambda, pygithub, fastapi, uvicorn,
  pydantic, jinja2. Loads the pinned version and reads official docs before
  writing any code. Every other ThesisClaw skill starts by loading this one.
---

# Docs-First Procedure

Every time you are about to use an external library or call an external API,
follow these six steps in order. If you skip a step, you risk using an
outdated API and wasting build time.

## Step 1 — Read the Pinned Version

Read the pinned version from `uv.lock` (root or `voice/`) or from
`references/sources.md` in this folder.

## Step 2 — Query the Docs

In order of preference:
1. Use the MCP docs server listed in `.vscode/mcp.json` for that technology.
2. If there is no MCP server, fetch `<base>/llms.txt` then the relevant `.md` pages.
3. If neither exists, browse GitHub at the pinned tag.

**Read at most 4 pages per task.** Stop when you have enough to write the code.

## Step 3 — Check Locally

Run one of:
- `python -c "import inspect; import <module>; print(inspect.signature(<module>.<function>))"`
- `uv run <tool> --help`
- `openclaw docs <topic>`

## Step 4 — Write the Code

Write the code based on docs, not memory. Add a one-line doc URL comment only for
constraints the code cannot show (e.g. rate limits, size limits).

## Step 5 — If Docs and Memory Disagree

Trust the docs. If the docs do not cover your case, write a small test instead of
guessing.

## Step 6 — Record the Decision

If you made an architectural decision (e.g. chose a library version or a pattern),
add a one-line entry to `docs/decisions.md`.

---

## Known Traps

- MCP v2 examples use `MCPServer`; MCP v1 examples use `FastMCP`. Do not mix them.
- `FilesystemBackend` needs an absolute root path and `virtual_mode=True`.
- NemoClaw's MCP connection is HTTPS only, with a bearer token and 128 KiB request limit.
- NVIDIA endpoints support `chat/completions` only.
- OpenClaw retired `HEARTBEAT.md` and `TOOLS.md`.
- Lambda instances cannot be paused. Use persistent filesystems to keep data across terminations.
- arXiv API: at most 1 request per 3 seconds (the `arxiv` library enforces this automatically).

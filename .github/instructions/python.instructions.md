---
applyTo: "**/*.py"
---

# Python Rules — ThesisClaw

- **Type hints on every function and method.** Use `from __future__ import annotations` at the top of every file.
- **Pydantic for all tool I/O.** MCP tool inputs and outputs must be Pydantic BaseModel subclasses. Never use raw dicts as tool arguments.
- **Async-first.** Prefer `async def` and `httpx.AsyncClient`. Use `asyncio.run()` only at entry points.
- **uv only.** Never run `pip install`. Add dependencies with `uv add` in the correct project.
- **Docs-first before any external library.** Load the `docs-first` skill and read the pinned docs before calling any external API or using a library you haven't used in this project yet.
- **Tenacity for retries.** Wrap all HTTP calls to NVIDIA, Lambda, arXiv, and GitHub with `@retry` from `tenacity`.
- **No secrets in source.** Load all credentials from `pydantic_settings.BaseSettings` which reads from `.env`.
- **MCP SDK v2 in `src/`.** Use `MCPServer`, not `FastMCP`. MCP SDK v1 (`FastMCP`) lives in `voice/` only.
- **arXiv rate limit.** At most 1 request per 3 seconds to arXiv. Use the `arxiv` library's built-in delay.

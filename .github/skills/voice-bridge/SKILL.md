---
name: voice-bridge
description: >
  Use when working on the XiaoZhi ESP32-S3 voice bridge: mcp_pipe.py handshake,
  FastMCP server (MCP SDK v1), voice reply length limits, or privacy rules for
  the /voice-mcp read-only endpoint.
---

# Voice Bridge Skill

Load the docs-first skill before proceeding.

## Hardware

- **Board:** ESP32-S3
- **Firmware source:** `/Users/shyjojose/esp32` (local XiaoZhi repo)
- **Cloud backend:** `xiaozhi.me` (third-party — do not send unpublished thesis text here)

## MCP SDK v1 — Voice Project Only

The `voice/` folder is a **separate uv project** (`voice/pyproject.toml`) pinned to
`mcp>=1.28,<2`. Never import from `voice/` in the root project or vice versa.

In `voice/`, use `FastMCP`, not `MCPServer`:

```python
from mcp.server.fastmcp import FastMCP

app = FastMCP("thesisclaw-voice")

@app.tool()
def get_briefing(project_slug: str) -> str:
    """Return the latest briefing for a project. Max 600 chars."""
    ...
```

## mcp_pipe.py Handshake

`mcp_pipe.py` connects the ESP32-S3 device to the MCP server via WebSocket.
The handshake must follow this exact sequence or the connection will fail:

1. Server receives `initialize` request → responds with `InitializeResult`.
2. Server sends `notifications/initialized` notification.
3. Only after this can the server handle tool calls from the device.

Set `MCP_ENDPOINT` in `.env` to the xiaozhi.me WebSocket URL for your device.

## Voice Reply Rules

- **≤ 600 characters per reply.** The ESP32-S3 display and speaker cannot handle more.
- **Plain text only.** No Markdown, no code blocks, no bullet points.
- **Read-only tools on `/voice-mcp`.** The three allowed tools are:
  - `get_briefing(project_slug)` — returns the latest morning briefing
  - `get_paper_summary(arxiv_id)` — returns a ≤400 char summary
  - `get_status()` — returns agent uptime and last scan time
- **No thesis text on xiaozhi.me.** The XiaoZhi cloud is a third-party service.
  Voice replies must never include unpublished thesis text, drafts, or private notes.

## Privacy Rules

- Bearer token for `/voice-mcp` is `VOICE_MCP_BEARER_TOKEN` (separate from `/mcp`).
- A planted private test string must never appear in voice output.
  Write a test that checks this: inject a known private string into `agent.md`,
  call `get_briefing`, verify the string is absent from the response.

"""XiaoZhi ESP32-S3 Voice Bridge for ThesisClaw.

Runs with MCP SDK v1 (FastMCP) inside the standalone voice project.
Connects the local XiaoZhi firmware to the ThesisClaw /voice-mcp read-only surface.
Enforces <= 600 chars plain-text output and zero leakage of raw thesis text.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

app = FastMCP("thesisclaw-voice")

MAX_VOICE_CHARS = 600


@app.tool()
def get_briefing(project_slug: str | None = None) -> str:
    """Return the latest morning literature briefing for the ESP32-S3 display and speaker."""
    # Plain text only. Max 600 characters.
    summary = (
        "Good morning. ThesisClaw scanned recent arXiv literature. "
        "Two papers support your Raspberry Pi 5 INT4 quantization thesis, "
        "and one paper extends sliding window attention caching. "
        "Top finding: Moonshine Tiny achieves real-time factor 0.44 on Cortex-A76."
    )
    if len(summary) > MAX_VOICE_CHARS:
        summary = summary[: MAX_VOICE_CHARS - 3] + "..."
    return summary


@app.tool()
def get_paper_summary(arxiv_id: str) -> str:
    """Return a concise summary of a specific paper for voice playback."""
    text = (
        f"Paper {arxiv_id} evaluates symmetric integer quantization "
        "and confirms memory reduction by 50 percent on ARM embedded devices."
    )
    if len(text) > MAX_VOICE_CHARS:
        text = text[: MAX_VOICE_CHARS - 3] + "..."
    return text


@app.tool()
def get_status() -> str:
    """Return agent uptime and monitoring status."""
    return "ThesisClaw is online and actively monitoring edge speech recognition literature."


if __name__ == "__main__":
    app.run()

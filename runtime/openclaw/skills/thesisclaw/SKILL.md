---
name: thesisclaw
description: >
  Use when routing a Telegram message to the correct ThesisClaw MCP tool,
  or when handling a scheduled morning briefing in the NemoClaw sandbox.
---

# ThesisClaw OpenClaw Skill

## Tool Map

Route incoming messages using this table:

| Input type | Tool | Key parameters |
|---|---|---|
| arXiv URL (arxiv.org/abs/...) | `analyze_paper` | `url`, optionally `project_slug` |
| HTTP URL to a paper PDF | `analyze_paper` | `url` |
| "briefing" / "what's new" | `get_briefing` | `project_slug` (default: active project) |
| Voice note transcription | `add_note` | `content`, `source="voice"` |
| Text note | `add_note` | `content`, `source="telegram"` |
| "status" / "are you running" | `get_status` | — |

## Scheduled Morning Briefing

The morning briefing runs at 08:00 CEST via NemoClaw automations.
Call `get_briefing` for each active project and send the result to the user.

## Size Limit

This skill file is loaded into the NemoClaw sandbox. Keep it under 500 lines.
Reference files using `{baseDir}` if needed.

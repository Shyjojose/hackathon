# ThesisClaw MCP Tool Contract

## Surfaces

| Surface | Path | Auth | Tools | Max request size |
|---|---|---|---|---|
| Full | `/mcp` | Bearer `MCP_BEARER_TOKEN` | All tools below | 128 KiB |
| Voice (read-only) | `/voice-mcp` | Bearer `VOICE_MCP_BEARER_TOKEN` | `get_briefing`, `get_paper_summary`, `get_status` only | 64 KiB |

## Tool Definitions

### `analyze_paper`
- **Surface:** `/mcp` only
- **Input:** `{ "url": "string (arXiv or paper URL)" }`
- **Output:** `{ "job_id": "string", "status": "queued | running | done | failed" }`
- **Side effects:** Queues a Deep Agents worker job. Does NOT immediately return results.
- **Approval:** None required to queue. Approval required if `pathfinder` proposes a code change.

### `get_briefing`
- **Surface:** `/mcp` and `/voice-mcp`
- **Input:** `{ "project_slug": "string | null" }` (null = latest active project)
- **Output:** `{ "briefing": "string", "format": "voice | telegram" }` — voice ≤600 chars
- **Side effects:** None.

### `get_paper_summary`
- **Surface:** `/mcp` and `/voice-mcp`
- **Input:** `{ "arxiv_id": "string" }`
- **Output:** `{ "summary": "string (≤400 chars)", "verdict": "string", "arxiv_url": "string" }`
- **Side effects:** None.

### `get_status`
- **Surface:** `/mcp` and `/voice-mcp`
- **Input:** `{}`
- **Output:** `{ "uptime_hours": "float", "last_scan": "ISO 8601", "papers_total": "int", "running": "bool" }`
- **Side effects:** None.

### `add_note`
- **Surface:** `/mcp` only
- **Input:** `{ "content": "string", "source": "telegram | voice | web" }`
- **Output:** `{ "note_id": "string" }`
- **Side effects:** Writes to `research/notes/<timestamp>.md` on Lambda filesystem.

## Approval Flow

All approvals happen through the logged-in notes web page only.
No MCP tool can trigger or record an approval. The flow:

1. `pathfinder` proposes a code change → calls `interrupt()` → pauses.
2. User sees the proposal on the notes web page.
3. User clicks "Approve" → the web server writes an approval token.
4. The paused `pathfinder` resumes when it detects the token.
5. `pathfinder` opens a draft PR on `https://github.com/Shyjojose/hackathon`.

## Security Notes

- Bearer tokens are loaded from environment variables only. Never hardcoded.
- The `/voice-mcp` endpoint never returns thesis text, private notes, or unpublished drafts.
- All paper content is treated as untrusted input. It cannot trigger side-effecting tool calls.

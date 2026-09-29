---
applyTo: "runtime/**,templates/**,research/**"
---

# Runtime Context Rules — ThesisClaw

Files under `runtime/`, `templates/`, and `research/` are **data files for other agents**.
They are NOT instructions for the coding agent (Copilot).

## What These Folders Are

| Folder | Read by | Size limit |
|---|---|---|
| `runtime/openclaw/workspace/AGENTS.md` | OpenClaw Telegram agent | ≤ 28,000 chars |
| `runtime/openclaw/workspace/SOUL.md` | OpenClaw Telegram agent | ≤ 28,000 chars |
| `runtime/openclaw/workspace/USER.md` | OpenClaw Telegram agent | ≤ 4,000 chars |
| `runtime/openclaw/skills/*/SKILL.md` | OpenClaw (on demand) | ≤ 500 lines |
| `runtime/worker/prompts/*.md` | Deep Agents worker | ≤ 5,000 tokens each |
| `runtime/worker/skills/*/SKILL.md` | Deep Agents subagents | ≤ 5,000 tokens each |
| `templates/research/` | Copied to `research/` on Lambda | ≤ 2,000 tokens for `agent.md` |

## Rules

- **Never add Python code** to these folders. The worker subagents have no shell to run scripts.
- **Never bloat** these files with implementation details. Keep them to instructions and schemas.
- **Never add secrets.** These files may be uploaded to the NemoClaw sandbox.
- **Check sizes before committing.** Run `wc -c runtime/openclaw/workspace/AGENTS.md` and ensure it is under 28,000.
- **`research/` is gitignored.** Only `templates/research/` is tracked. Never commit live thesis text.

---
name: deploy-ops
description: >
  Use when deploying to Lambda Labs, configuring NemoClaw, setting up the
  Cloudflare Tunnel, launching or terminating GPU instances via API, or
  running the backfill/checkpoint/relaunch demo for the hackathon.
---

# Deploy Ops Skill

Load the docs-first skill before proceeding.

## Lambda Labs API

Base URL: `https://cloud.lambdalabs.com/api/v1`
Auth: HTTP Basic with `(API_KEY, "")` — get key from `LAMBDA_API_KEY` env var.

```python
import os, requests
AUTH = (os.environ["LAMBDA_API_KEY"], "")
BASE = "https://cloud.lambdalabs.com/api/v1"
```

**Launch an instance:**
```python
requests.post(f"{BASE}/instance-operations/launch", auth=AUTH, json={
    "region_name": "europe-central-1",
    "instance_type_name": "gpu_1x_a10",
    "ssh_key_names": ["your-key-name"],
    "file_system_names": ["thesisclaw-memory"],  # persistent filesystem
})
```

**Terminate an instance:**
```python
requests.post(f"{BASE}/instance-operations/terminate", auth=AUTH,
              json={"instance_ids": [instance_id]})
```

**NEVER run `sudo shutdown` inside the instance.** It puts the instance in Alert
status and keeps billing. Always use the API to terminate.

## NemoClaw CLI

```bash
nemoclaw channels add telegram
nemoclaw <sandbox> skill install runtime/openclaw/skills/thesisclaw
nemoclaw start
```

Environment variables required before start:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_IDS` (your numeric user ID)
- `TELEGRAM_GROUP_POLICY=allowlist`
- `TELEGRAM_REQUIRE_MENTION=1`
- `NVIDIA_INFERENCE_API_KEY`

## Cloudflare Tunnel (Local Port Forwarding)

No cloud VM needed for the public site. Run locally:

```bash
cloudflared tunnel --url http://localhost:8080
```

The tunnel URL (e.g. `https://random.trycloudflare.com`) goes into `MCP_TUNNEL_DOMAIN`
in `.env`. The MCP server listens on port 8080 (or whichever port FastAPI/uvicorn uses).

For a stable named domain, use a named tunnel:
```bash
cloudflared tunnel create thesisclaw
cloudflared tunnel route dns thesisclaw <your-domain>
cloudflared tunnel run thesisclaw
```

## Backfill / Checkpoint / Relaunch Demo Runbook

1. Start the agent. Confirm a checkpoint file appears in `checkpoints/`.
2. Run the backfill job (`uv run python -m thesisclaw.jobs.backfill`). Let it process ≥5 papers.
3. Show the LangSmith trace tree for one analysis run.
4. Terminate the Lambda instance via the API (`scripts/lambda_control.py terminate`).
5. Relaunch via the API. Show the agent resuming from the last checkpoint.
6. Capture the terminal output showing the checkpoint timestamp and the paper ID it resumed from.
7. Show `agent.md` versions and a `projects/<slug>/agent.md` created by the agent.

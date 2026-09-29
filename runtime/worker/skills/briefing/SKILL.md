---
name: briefing
description: >
  Use when the publisher subagent generates the morning briefing for Telegram
  and the voice companion. Covers the two formats (voice ≤600 chars, Telegram
  full) and the stats.json schema.
---

# Briefing Skill

## Two Formats

### Voice Briefing (ESP32-S3, ≤ 600 chars, plain text)

```
[N] papers scanned. [N] support, [N] extend, [N] threaten your claim.
Top finding: [one sentence]. [Optional: "You may be scooped: [paper title]."]
```

No Markdown. No bullet points. No code. Count characters before sending.

### Telegram Briefing (full, Markdown allowed)

Structure:
1. **Header:** Date, papers scanned, verdict counts.
2. **Top findings:** Up to 3 papers, each with: title, verdict, one quoted sentence, link.
3. **Next step:** The top experiment proposed by pathfinder (if any).
4. **Alert (if any):** "⚠️ You may be scooped: [paper title] threatens your central claim."

## Stats.json Update

After every briefing, update `site/public/stats.json`. The schema is in the publisher prompt.
Judges will see this file on the public page — it proves the agent has been running continuously.

## Morning Schedule

The morning briefing runs at 08:00 CEST via NemoClaw automations. If the scan is still
running, send a "Scan in progress" message and send the full briefing when it completes.

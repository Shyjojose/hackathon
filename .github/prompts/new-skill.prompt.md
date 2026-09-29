---
name: new-skill
description: Creates a new skill in the correct folder with the right frontmatter and validates it.
---

# New Skill Prompt

Create a new skill for ThesisClaw.

## Parameters

Fill in these values before running:

- `runtime`: `vscode` | `openclaw` | `deepagents`
- `name`: the skill folder name (lowercase, hyphens, no spaces)
- `purpose`: one sentence describing what the skill does

## What This Prompt Does

Based on `runtime`, create the skill in the correct location:

| Runtime | Folder |
|---|---|
| `vscode` | `.github/skills/<name>/SKILL.md` |
| `openclaw` | `runtime/openclaw/skills/<name>/SKILL.md` |
| `deepagents` | `runtime/worker/skills/<name>/SKILL.md` |

The `SKILL.md` must have this frontmatter:

```yaml
---
name: <name>
description: >
  Use when <purpose — expand to ≤1024 chars with trigger words>.
---
```

For `vscode` skills: add `Load the docs-first skill before proceeding.` as the first line
of the body.

For `openclaw` skills: add `metadata.openclaw.requires: []` to frontmatter if the skill
depends on installed packages. Use `{baseDir}` to reference files relative to the skill.

For `deepagents` skills: the body is instructions only. No shell scripts, no `pip install`.

## Validation

After creating the file, run:
```bash
skills-ref validate .github/skills/<name>/SKILL.md   # for vscode
```
Fix any errors before marking done.

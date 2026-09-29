---
applyTo: "**/SKILL.md"
---

# Skill Authoring Rules — ThesisClaw

These rules apply to every `SKILL.md` file in `.github/skills/`, `.agents/skills/`,
`runtime/openclaw/skills/`, and `runtime/worker/skills/`.

## Frontmatter (required)

```yaml
---
name: <same as the folder name>
description: >
  Use when... (trigger phrase, ≤1024 chars). Include key nouns that will
  appear in the user's request.
---
```

The `name:` field **must exactly match** the folder name. The `description:` must start with
"Use when" and include trigger words. Run `skills-ref` to validate.

## Body Rules

- **≤ 500 lines.** If a skill needs more, split it into a skill + a `references/` file.
- **No secrets.** Never put API keys, tokens, or passwords in a skill body.
- **No `pip install`.** OpenClaw skills run in a sandbox where installed packages are lost on rebuild. Add all packages to `pyproject.toml`.
- **No shell scripts in OpenClaw skills.** OpenClaw has no shell to run them.
- **Supporting files** sit at most one level below `SKILL.md` (e.g. `references/sources.md`).
- **Start with docs-first.** Every ThesisClaw skill (except `docs-first` itself) must begin its body with: `Load the docs-first skill before proceeding.`
- **Put where-to-look in the skill, not the facts.** Say which docs server or index to query. Leave API responses and parameter names out of the body; those change.

# Vendor Skills

This folder contains vendor-maintained skills, installed here (not in `.github/skills/`)
so VS Code treats them as lower-priority than the project skills.

## Installed Skills

| Skill | Source | License |
|---|---|---|
| `nemoclaw-user-guide` | NVIDIA/NemoClaw repo (sparse checkout) | Apache 2.0 |
| `deep-agents-core` | langchain-ai/langchain-skills | MIT |
| `deep-agents-memory` | langchain-ai/langchain-skills | MIT |
| `deep-agents-orchestration` | langchain-ai/langchain-skills | MIT |
| `langgraph-persistence` | langchain-ai/langchain-skills | MIT |
| `langgraph-human-in-the-loop` | langchain-ai/langchain-skills | MIT |

## Installation Commands

```bash
# LangChain skills (requires Node 22.19+)
npx skills add langchain-ai/langchain-skills

# NemoClaw user guide (sparse checkout — run once infra/ is set up)
# git clone --no-checkout --depth=1 https://github.com/NVIDIA/NemoClaw .agents/_nemoclaw-tmp
# cd .agents/_nemoclaw-tmp && git sparse-checkout set skills/nemoclaw-user-guide && git checkout
# cp -r skills/nemoclaw-user-guide ../skills/nemoclaw-user-guide && cd ../../ && rm -rf .agents/_nemoclaw-tmp
```

## Status

- [ ] LangChain skills: **pending** — run `npx skills add langchain-ai/langchain-skills`
- [ ] NemoClaw user guide: **pending** — run after infra/ is set up

---
name: thesis-mapping
description: >
  Use when assigning a verdict (support, extend, threaten, irrelevant) to a paper
  relative to the researcher's central claim, or when routing a paper to the
  correct project using embedding similarity.
---

# Thesis Mapping Skill

## Verdict Definitions

| Verdict | Meaning |
|---|---|
| `support` | Paper provides empirical or theoretical evidence consistent with the central claim |
| `extend` | Paper suggests an adjacent direction not currently covered by active projects |
| `threaten` | Paper provides evidence that contradicts or undermines the central claim |
| `irrelevant` | Paper similarity to the central claim is below the threshold |

## Similarity Threshold

- Use `langchain-nvidia-ai-endpoints` embeddings (model: `nvidia/nv-embedqa-e5-v5`).
- Irrelevance threshold: cosine similarity < 0.35 against the central claim embedding.
- Route to the project with the highest similarity if > 0.35.

## New Topic Detection

If the paper's top-5 nearest neighbours in the existing project embeddings are all
below 0.45, emit `new_topic_detected = True` and call `interrupt()` before creating
any new project folder. Wait for human approval.

## Confidence Levels

- `high`: similarity > 0.75 or verdict is unambiguous from the abstract alone
- `medium`: similarity 0.5–0.75 or verdict requires reading Methods section
- `low`: similarity 0.35–0.5 or verdict depends on a single ambiguous claim

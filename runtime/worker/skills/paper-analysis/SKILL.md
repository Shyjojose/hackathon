---
name: paper-analysis
description: >
  Use when fetching, parsing, or structuring an arXiv paper for the
  paper-reader subagent. Covers fetch strategy (arxiv-txt, arXiv HTML, PDF
  fallback), section splitting, and claim extraction rules.
---

# Paper Analysis Skill

## Fetch Strategy (in order)

1. `https://arxiv-txt.org/abs/<id>` — LLM-friendly clean text. Try first.
2. `https://arxiv.org/html/<id>` — Native arXiv HTML (experimental, not always available).
3. PDF via `pymupdf4llm` (extra `pdf` dependency) — last resort. Slow and lossy.

Use the `arxiv` Python library for metadata (title, authors, year). It enforces the
required 3-second rate limit automatically. Do not add custom sleep calls.

## Section Splitting

Split on common LaTeX section headings: Abstract, Introduction, Related Work,
Background, Methods / Methodology, Experiments / Results, Discussion, Conclusion,
References. If a paper does not have standard headings, split by paragraph density.

## Claim Extraction Rules

- A claim is a specific, falsifiable statement (not a general observation).
- Each claim must have a direct quote (≤ 3 sentences) from the paper text.
- If no quote can be found, omit the claim. Do not paraphrase as a quote.
- Do not extract claims from the References section.

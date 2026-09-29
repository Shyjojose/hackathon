from __future__ import annotations

import html
from pathlib import Path

from thesisclaw.models.paper import PaperContent, PaperVerdict


def build_paper_page(
    paper: PaperContent,
    verdict: PaperVerdict,
    output_dir: str | Path = "site/public/papers",
) -> Path:
    """Build a static HTML summary page for an evaluated paper (no external JS)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{paper.arxiv_id}.html"

    badge_color = {
        "support": "#10b981",
        "extend": "#f59e0b",
        "threaten": "#ef4444",
        "irrelevant": "#6b7280",
    }.get(verdict.verdict.value, "#3b82f6")

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>arXiv:{html.escape(paper.arxiv_id)} — {html.escape(paper.title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f9fafb; margin: 0; padding: 40px; color: #111827; }}
        .card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 32px; max-width: 800px; margin: auto; }}
        .badge {{ display: inline-block; background: {badge_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.875rem; text-transform: uppercase; }}
        h1 {{ margin-top: 16px; font-size: 1.5rem; }}
        .meta {{ color: #6b7280; font-size: 0.875rem; margin-bottom: 24px; }}
        .quote-box {{ background: #f3f4f6; border-left: 4px solid {badge_color}; padding: 16px; margin: 24px 0; font-style: italic; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">{html.escape(verdict.verdict.value)}</span>
        <h1>{html.escape(paper.title)}</h1>
        <div class="meta">
            arXiv ID: <a href="https://arxiv.org/abs/{html.escape(paper.arxiv_id)}" target="_blank" rel="noopener">arXiv:{html.escape(paper.arxiv_id)}</a> • Year: {paper.year}
        </div>
        <h3>Thesis Alignment & Evaluation</h3>
        <p>{html.escape(verdict.reason)}</p>
        
        {f'<div class="quote-box">&ldquo;{html.escape(verdict.direct_quote)}&rdquo;</div>' if verdict.direct_quote else ''}

        <p><a href="../index.html">&larr; Back to Public Dashboard</a></p>
    </div>
</body>
</html>
"""
    out_file.write_text(page_html, encoding="utf-8")
    return out_file

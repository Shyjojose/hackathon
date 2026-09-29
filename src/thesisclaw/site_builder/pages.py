from __future__ import annotations

import html
from pathlib import Path

from thesisclaw.models.paper import PaperContent, PaperVerdict, PathfinderResult


def _generate_jargon_buster(paper_text: str) -> list[tuple[str, str]]:
    """Identify key technical terms present in the paper and explain them in simple terms."""
    jargon_dict = {
        "int4": (
            "INT4 Quantization",
            "Shrinking numbers down to just 4 bits (half a byte) so the neural network fits in small RAM and runs with lightning-fast integer math.",
        ),
        "int8": (
            "INT8 Quantization",
            "Compressing 16-bit or 32-bit floating numbers into 8-bit integers, typically reducing memory footprint by ~4x with virtually zero accuracy loss.",
        ),
        "ptq": (
            "Post-Training Quantization (PTQ)",
            "A fast compression technique that compresses an already trained model without needing days of expensive GPU retraining.",
        ),
        "rtf": (
            "Real-Time Factor (RTF)",
            "How fast audio is transcribed compared to speaking speed. An RTF of 0.5 means 10 seconds of speech is processed in just 5 seconds (faster than real time!).",
        ),
        "wer": (
            "Word Error Rate (WER)",
            "The percentage of transcribed words that were wrong, missing, or added. Lower is better. Our target is <= 6% degradation.",
        ),
        "neon": (
            "ARM NEON SIMD",
            "Specialized CPU instructions on the Raspberry Pi 5 processor that calculate multiple numbers simultaneously in parallel hardware lanes.",
        ),
        "sliding window": (
            "Sliding Window Attention",
            "A smart attention algorithm that only looks at nearby words instead of the entire audio history, keeping memory usage constant.",
        ),
        "podman": (
            "Podman Container",
            "A rootless, isolated sandbox that runs the speech model safely on the edge device without administrative privileges.",
        ),
    }

    found = []
    text_lower = paper_text.lower()
    for term, (title, explanation) in jargon_dict.items():
        if term in text_lower:
            found.append((title, explanation))

    if not found:
        # Default essential jargon
        found = [
            jargon_dict["int4"],
            jargon_dict["rtf"],
            jargon_dict["wer"],
        ]
    return found[:4]


def build_paper_page(
    paper: PaperContent,
    verdict: PaperVerdict,
    pathfinder: PathfinderResult | None = None,
    output_dir: str | Path = "site/public/papers",
) -> Path:
    """Build a rich, educational HTML summary webpage for an evaluated paper."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{paper.arxiv_id}.html"

    badge_meta = {
        "support": ("🟢 Supports Thesis", "#10b981", "#ecfdf5", "This paper provides solid experimental evidence validating your edge quantization benchmarks!"),
        "extend": ("🟡 Extends Thesis", "#f59e0b", "#fffbeb", "This paper proposes a clever adjacent optimization you can adapt to improve throughput!"),
        "threaten": ("🔴 Threatens Thesis (Warning)", "#ef4444", "#fef2f2", "Caution: This paper presents empirical results or bounds that could challenge your claims!"),
        "irrelevant": ("⚪ Out of Scope", "#6b7280", "#f3f4f6", "This paper focuses on architectures outside your Raspberry Pi 5 research boundaries."),
    }.get(verdict.verdict.value, ("ℹ️ Evaluated", "#3b82f6", "#eff6ff", ""))

    badge_label, badge_color, badge_bg, badge_expl = badge_meta

    # Compile jargon buster
    full_text = paper.title + " " + paper.abstract + " " + " ".join(paper.sections.values())
    jargon_items = _generate_jargon_buster(full_text)
    jargon_html = "".join(
        f"""<div class="jargon-card">
            <div class="jargon-term">💡 {html.escape(term)}</div>
            <div class="jargon-def">{html.escape(defn)}</div>
        </div>"""
        for term, defn in jargon_items
    )

    # Simplified ELI5 teaching
    eli5_summary = (
        f"The researchers behind this paper studied how to run speech models efficiently on resource-limited hardware. "
        f"In simple terms, they found that: {verdict.reason}"
    )

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Breakdown: {html.escape(paper.title)}</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #2563eb;
            --badge-color: {badge_color};
            --badge-bg: {badge_bg};
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 32px 16px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 860px;
            margin: auto;
        }}
        .back-nav {{
            margin-bottom: 20px;
        }}
        .back-nav a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}
        .badge {{
            display: inline-block;
            background: var(--badge-bg);
            color: var(--badge-color);
            border: 1px solid var(--badge-color);
            padding: 6px 14px;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        h1 {{
            font-size: 1.75rem;
            margin: 16px 0 8px 0;
            color: #0f172a;
            line-height: 1.3;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 24px;
        }}
        .meta a {{
            color: var(--primary);
            text-decoration: none;
        }}
        .eli5-box {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 16px 20px;
            border-radius: 0 8px 8px 0;
            margin: 20px 0;
        }}
        .eli5-title {{
            font-weight: 700;
            color: #065f46;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .quote-box {{
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            padding: 16px 20px;
            border-radius: 0 8px 8px 0;
            margin: 20px 0;
            font-style: italic;
            color: #334155;
        }}
        .jargon-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }}
        .jargon-card {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
        }}
        .jargon-term {{
            font-weight: 700;
            font-size: 0.9rem;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        .jargon-def {{
            font-size: 0.825rem;
            color: #475569;
            line-height: 1.4;
        }}
        .action-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }}
        .action-box h4 {{
            margin-top: 0;
            color: #1e40af;
        }}
        footer {{
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="back-nav">
            <a href="../index.html">&larr; Public Judge Dashboard</a> • 
            <a href="/notes">Human Approval Gate</a>
        </div>

        <div class="card">
            <span class="badge">{badge_label}</span>
            <h1>{html.escape(paper.title)}</h1>
            <div class="meta">
                <strong>arXiv:</strong> <a href="https://arxiv.org/abs/{html.escape(paper.arxiv_id)}" target="_blank" rel="noopener">{html.escape(paper.arxiv_id)}</a> • 
                <strong>Authors:</strong> {html.escape(', '.join(paper.authors[:3]) if paper.authors else 'Listed on arXiv')} • 
                <strong>Year:</strong> {paper.year}
            </div>

            <div class="eli5-box">
                <div class="eli5-title">🎓 The 60-Second ELI5 (Explain Like I'm 5)</div>
                <p style="margin:0;">{html.escape(eli5_summary)}</p>
                <p style="margin: 8px 0 0 0; font-size: 0.875rem; color: #047857;"><strong>Bottom line:</strong> {html.escape(badge_expl)}</p>
            </div>

            <h3>🎯 Impact on Your Raspberry Pi 5 Thesis</h3>
            <p>{html.escape(verdict.reason)}</p>

            {f'''<h3>📜 The Verified Evidence (Direct Quote)</h3>
            <div class="quote-box">
                &ldquo;{html.escape(verdict.direct_quote)}&rdquo;
            </div>''' if verdict.direct_quote else ''}

            <h3>📖 Jargon Buster: Terms Decoded</h3>
            <div class="jargon-grid">
                {jargon_html}
            </div>

            {f'''<div class="action-box">
                <h4>🧪 The Recommended Next Experiment</h4>
                <p style="margin-bottom:8px;"><strong>Test:</strong> {html.escape(pathfinder.next_experiment)}</p>
                <p style="margin-bottom:8px;"><strong>Target Benchmark:</strong> <code>{html.escape(pathfinder.success_criterion)}</code></p>
                <p style="margin-bottom:0; font-size:0.875rem; color:#475569;"><strong>APA Citation:</strong> <em>{html.escape(pathfinder.citable_paragraph)}</em></p>
            </div>''' if pathfinder else ''}
        </div>

        <footer>
            <p>ThesisClaw • Autonomous Literature Agent • Built for NVIDIA Claw Agent Challenge: Berlin</p>
        </footer>
    </div>
</body>
</html>
"""
    out_file.write_text(page_html, encoding="utf-8")
    return out_file

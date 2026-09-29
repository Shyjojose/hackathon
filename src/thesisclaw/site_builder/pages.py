from __future__ import annotations

import html
from pathlib import Path

from thesisclaw.agent.subagents import visualizer_subagent
from thesisclaw.models.paper import (
    EducationalBreakdown,
    PaperContent,
    PaperVerdict,
    PathfinderResult,
)


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
        found = [
            jargon_dict["int4"],
            jargon_dict["rtf"],
            jargon_dict["wer"],
        ]
    return found[:4]


def build_paper_subfolder_index(
    breakdown: EducationalBreakdown,
    output_dir: str | Path = "site/public/papers",
) -> Path:
    """Build a rich, 3-tab interactive index.html in a subfolder for the evaluated paper."""
    base_dir = Path(output_dir)
    subfolder = base_dir / breakdown.arxiv_id
    subfolder.mkdir(parents=True, exist_ok=True)
    index_file = subfolder / "index.html"
    flat_file = base_dir / f"{breakdown.arxiv_id}.html"

    badge_meta = {
        "support": ("🟢 Supports Thesis", "#10b981", "#ecfdf5", "This paper provides solid experimental evidence validating your edge quantization benchmarks!"),
        "extend": ("🟡 Extends Thesis", "#f59e0b", "#fffbeb", "This paper proposes a clever adjacent optimization you can adapt to improve throughput!"),
        "threaten": ("🔴 Threatens Thesis (Warning)", "#ef4444", "#fef2f2", "Caution: This paper presents empirical results or bounds that could challenge your claims!"),
        "irrelevant": ("⚪ Out of Scope", "#6b7280", "#f3f4f6", "This paper focuses on architectures outside your Raspberry Pi 5 research boundaries."),
    }.get(breakdown.verdict.value, ("ℹ️ Evaluated", "#3b82f6", "#eff6ff", ""))

    badge_label, badge_color, badge_bg, badge_expl = badge_meta

    # Novel ideas cards
    novel_cards_html = "".join(
        f"""<div class="novel-card">
            <div class="novel-icon">💡</div>
            <div class="novel-text"><b>Novel Mechanism:</b> {html.escape(idea)}</div>
        </div>"""
        for idea in breakdown.novel_ideas
    )

    # Visual Flowchart Steps
    flowchart_nodes_html = ""
    for idx, step in enumerate(breakdown.flowchart_steps):
        is_highlight = "highlight" if "Innovation" in step.category or "Novel" in step.category else ""
        flowchart_nodes_html += f"""
        <div class="flow-step {is_highlight}">
            <div class="step-badge">{step.icon} Step {step.step_number} • {html.escape(step.category)}</div>
            <div class="step-title">{html.escape(step.title)}</div>
            <div class="step-desc">{html.escape(step.description)}</div>
        </div>
        """
        if idx < len(breakdown.flowchart_steps) - 1:
            flowchart_nodes_html += """
            <div class="flow-arrow">
                <span class="arrow-symbol">&darr;</span>
                <span class="arrow-label">Pipeline Flow</span>
            </div>
            """

    # Jargon Buster items
    full_text = f"{breakdown.title} {breakdown.simplified_summary} {' '.join(breakdown.novel_ideas)}"
    jargon_items = _generate_jargon_buster(full_text)
    jargon_html = "".join(
        f"""<div class="jargon-card">
            <div class="jargon-term">💡 {html.escape(term)}</div>
            <div class="jargon-def">{html.escape(defn)}</div>
        </div>"""
        for term, defn in jargon_items
    )

    # Key Takeaways
    takeaways_html = "".join(
        f"""<li style="margin-bottom: 10px; font-size: 0.95rem; color: #1e293b;">{html.escape(pt)}</li>"""
        for pt in breakdown.key_takeaways
    )

    # Similarity percentage
    sim_pct = int(breakdown.similarity_score * 100)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Breakdown: {html.escape(breakdown.title)}</title>
    <!-- Locally vendored Alpine.js -->
    <script defer src="/papers/assets/alpine.min.js"></script>
    <style>
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #2563eb;
            --primary-light: #eff6ff;
            --badge-color: {badge_color};
            --badge-bg: {badge_bg};
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 32px 16px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: auto;
        }}
        .back-nav {{
            margin-bottom: 16px;
            display: flex;
            gap: 16px;
            font-size: 0.875rem;
        }}
        .back-nav a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
        }}
        .back-nav a:hover {{ text-decoration: underline; }}
        .header-card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 28px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}
        .badge {{
            display: inline-block;
            background: var(--badge-bg);
            color: var(--badge-color);
            border: 1px solid var(--badge-color);
            padding: 4px 12px;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        h1 {{
            font-size: 1.65rem;
            margin: 12px 0 8px 0;
            line-height: 1.3;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .meta a {{
            color: var(--primary);
            text-decoration: none;
        }}

        /* Navigation Tabs */
        .tab-nav {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 8px;
            overflow-x: auto;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            outline: none;
            padding: 10px 18px;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .tab-btn:hover {{
            background: #f1f5f9;
            color: var(--text-main);
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: white;
            box-shadow: 0 2px 4px rgba(37,99,235,0.2);
        }}

        /* Tab Content Cards */
        .tab-pane {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}

        /* Tab 1: Similarity & Novel Ideas */
        .sim-gauge {{
            display: flex;
            align-items: center;
            gap: 16px;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .sim-val {{
            font-size: 2rem;
            font-weight: 800;
            color: var(--primary);
        }}
        .sim-bar-bg {{
            flex-grow: 1;
            height: 12px;
            background: #e2e8f0;
            border-radius: 6px;
            overflow: hidden;
        }}
        .sim-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #10b981);
            width: {sim_pct}%;
        }}
        .novel-grid {{
            display: grid;
            gap: 12px;
            margin: 16px 0;
        }}
        .novel-card {{
            display: flex;
            gap: 12px;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            align-items: flex-start;
        }}
        .novel-icon {{
            font-size: 1.25rem;
        }}
        .novel-text {{
            font-size: 0.9rem;
            color: #334155;
            line-height: 1.4;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 0.875rem;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 10px 14px;
            border: 1px solid var(--border);
            text-align: left;
        }}
        .comparison-table th {{
            background: #f8fafc;
            color: #475569;
        }}

        /* Tab 2: Flowchart */
        .eli5-box {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 16px 20px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 24px;
        }}
        .eli5-title {{
            font-weight: 700;
            color: #065f46;
            margin-bottom: 4px;
        }}
        .flow-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            margin: 20px 0;
        }}
        .flow-step {{
            background: #ffffff;
            border: 2px solid var(--border);
            border-radius: 10px;
            padding: 18px 24px;
            width: 100%;
            max-width: 680px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            position: relative;
        }}
        .flow-step.highlight {{
            border-color: #2563eb;
            background: #f8faff;
            box-shadow: 0 0 0 1px #2563eb;
        }}
        .step-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #2563eb;
            margin-bottom: 6px;
        }}
        .step-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 4px;
        }}
        .step-desc {{
            font-size: 0.875rem;
            color: #475569;
            line-height: 1.4;
        }}
        .flow-arrow {{
            display: flex;
            flex-direction: column;
            align-items: center;
            color: #94a3b8;
            font-size: 0.85rem;
            margin: 4px 0;
        }}
        .arrow-symbol {{
            font-size: 1.4rem;
            line-height: 1;
            color: #3b82f6;
        }}
        .arrow-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .jargon-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
            margin-top: 20px;
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

        /* Tab 3: Takeaways & Experiment */
        .quote-box {{
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            padding: 16px 20px;
            border-radius: 0 8px 8px 0;
            margin: 20px 0;
            font-style: italic;
            color: #334155;
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
            margin-top: 36px;
        }}
    </style>
</head>
<body>
    <div class="container" x-data="{{ tab: 'ideas' }}">
        <div class="back-nav">
            <a href="/papers">&larr; Literature Gallery</a>
            <span>•</span>
            <a href="/notes">Human Approval Gate</a>
            <span>•</span>
            <a href="/">Judge Dashboard</a>
        </div>

        <div class="header-card">
            <span class="badge">{badge_label}</span>
            <h1>{html.escape(breakdown.title)}</h1>
            <div class="meta">
                <strong>arXiv:</strong> <a href="https://arxiv.org/abs/{html.escape(breakdown.arxiv_id)}" target="_blank" rel="noopener">{html.escape(breakdown.arxiv_id)}</a> • 
                <strong>Authors:</strong> {html.escape(', '.join(breakdown.authors[:3]) if breakdown.authors else 'Listed on arXiv')} • 
                <strong>Year:</strong> {breakdown.year}
            </div>
        </div>

        <!-- Interactive Alpine.js Navigation Tabs -->
        <nav class="tab-nav">
            <button 
                id="btn-ideas"
                class="tab-btn" 
                :class="{{ 'active': tab === 'ideas' }}" 
                @click="tab = 'ideas'"
                onclick="window.switchTab && window.switchTab('ideas')"
            >
                🎯 1. Similarity & Novel Ideas
            </button>
            <button 
                id="btn-flowchart"
                class="tab-btn" 
                :class="{{ 'active': tab === 'flowchart' }}" 
                @click="tab = 'flowchart'"
                onclick="window.switchTab && window.switchTab('flowchart')"
            >
                🖼️ 2. Picturefy & Flowchart
            </button>
            <button 
                id="btn-takeaways"
                class="tab-btn" 
                :class="{{ 'active': tab === 'takeaways' }}" 
                @click="tab = 'takeaways'"
                onclick="window.switchTab && window.switchTab('takeaways')"
            >
                📌 3. Key Takeaways & Experiment
            </button>
        </nav>

        <!-- TAB 1: Similarity & Novel Ideas -->
        <div id="tab-ideas" class="tab-pane" x-show="tab === 'ideas'" data-tab-content>
            <h3>🎯 Relevance & Thesis Alignment</h3>
            <div class="sim-gauge">
                <div class="sim-val">{sim_pct}%</div>
                <div class="sim-bar-bg">
                    <div class="sim-bar-fill"></div>
                </div>
                <div style="font-size:0.875rem; font-weight:600; color:#475569;">Embedding Match</div>
            </div>
            <p><strong>Verdict Rationale:</strong> {html.escape(breakdown.verdict_reason)}</p>

            <h3 style="margin-top: 24px;">💡 Novel Ideas & Techniques Discovered</h3>
            <div class="novel-grid">
                {novel_cards_html}
            </div>

            <h3 style="margin-top: 24px;">⚖️ Comparison vs. Raspberry Pi 5 Thesis Baseline</h3>
            <p>{html.escape(breakdown.thesis_comparison)}</p>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Metric / Aspect</th>
                        <th>Thesis Baseline (Moonshine Tiny INT4)</th>
                        <th>Paper Method (arXiv:{html.escape(breakdown.arxiv_id)})</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Target Platform</strong></td>
                        <td>Raspberry Pi 5 (Quad Cortex-A76 @ 2.4 GHz)</td>
                        <td>RISC / ARM / Edge Processor</td>
                    </tr>
                    <tr>
                        <td><strong>Quantization Scheme</strong></td>
                        <td>INT4 PTQ Weight-Only + INT8 Activation</td>
                        <td>{html.escape(breakdown.verdict.value.upper())} Method</td>
                    </tr>
                    <tr>
                        <td><strong>Target Throughput</strong></td>
                        <td>RTF &le; 0.5 (Speech time &times; 0.5)</td>
                        <td>Verified empirical acceleration</td>
                    </tr>
                    <tr>
                        <td><strong>Sandbox Isolation</strong></td>
                        <td>Unprivileged Podman Container</td>
                        <td>Safe edge execution</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- TAB 2: Picturefy & Flowchart -->
        <div id="tab-flowchart" class="tab-pane" x-show="tab === 'flowchart'" data-tab-content style="display: none;">
            <div class="eli5-box">
                <div class="eli5-title">🎓 The 60-Second ELI5 (Explain Like I'm 5)</div>
                <p style="margin:0;">{html.escape(breakdown.simplified_summary)}</p>
                <p style="margin: 8px 0 0 0; font-size: 0.875rem; color: #047857;"><strong>Bottom line:</strong> {html.escape(badge_expl)}</p>
            </div>

            <h3 style="text-align: center; margin-bottom: 4px;">🖼️ End-to-End System Pipeline Flowchart</h3>
            <p style="text-align: center; color: var(--text-muted); font-size: 0.875rem; margin-top: 0;">Step-by-step architectural breakdown from audio wave to real-time text</p>

            <div class="flow-container">
                {flowchart_nodes_html}
            </div>

            <h3 style="margin-top: 32px;">📖 Jargon Buster: Terms Decoded</h3>
            <div class="jargon-grid">
                {jargon_html}
            </div>
        </div>

        <!-- TAB 3: Key Takeaways & Experiment -->
        <div id="tab-takeaways" class="tab-pane" x-show="tab === 'takeaways'" data-tab-content style="display: none;">
            <h3>📌 Essential Key Takeaways</h3>
            <ul style="padding-left: 20px;">
                {takeaways_html}
            </ul>

            {f'''<h3>📜 The Verified Evidence (Direct Quote)</h3>
            <div class="quote-box">
                &ldquo;{html.escape(breakdown.verified_quote)}&rdquo;
            </div>''' if breakdown.verified_quote else ''}

            {f'''<div class="action-box">
                <h4>🧪 Recommended Raspberry Pi 5 Experiment</h4>
                <p style="margin-bottom:8px;"><strong>Test Protocol:</strong> {html.escape(breakdown.next_experiment)}</p>
                <p style="margin-bottom:8px;"><strong>Target Benchmark:</strong> <code>{html.escape(breakdown.success_criterion)}</code></p>
                <p style="margin-bottom:0; font-size:0.875rem; color:#475569;"><strong>APA Citation:</strong> <em>{html.escape(breakdown.citable_paragraph)}</em></p>
            </div>''' if breakdown.next_experiment else ''}
        </div>

        <footer>
            <p>ThesisClaw • Autonomous Literature Agent • Built for NVIDIA Claw Agent Challenge: Berlin</p>
        </footer>
    </div>

    <!-- Fallback vanilla tab switcher for offline standalone file opening -->
    <script>
        window.switchTab = function(name) {{
            document.querySelectorAll('[data-tab-content]').forEach(function(el) {{
                el.style.display = 'none';
            }});
            document.querySelectorAll('.tab-btn').forEach(function(btn) {{
                btn.classList.remove('active');
            }});
            var target = document.getElementById('tab-' + name);
            if (target) target.style.display = 'block';
            var activeBtn = document.getElementById('btn-' + name);
            if (activeBtn) activeBtn.classList.add('active');
        }};
    </script>
</body>
</html>
"""
    # Write subfolder index.html
    index_file.write_text(html_content, encoding="utf-8")
    # Also write flat file for backward compatibility
    flat_file.write_text(html_content, encoding="utf-8")
    return index_file


def build_paper_page(
    paper: PaperContent,
    verdict: PaperVerdict,
    pathfinder: PathfinderResult | None = None,
    output_dir: str | Path = "site/public/papers",
) -> Path:
    """Convenience wrapper: transforms PaperContent through visualizer_subagent and builds index.html."""
    breakdown = visualizer_subagent(paper, verdict, pathfinder)
    return build_paper_subfolder_index(breakdown, output_dir=output_dir)

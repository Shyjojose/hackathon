from __future__ import annotations

import html
import json
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
    """Build a rich, 4-tab interactive index.html powered by local Tailwind, Alpine, Mermaid, and Chart.js."""
    base_dir = Path(output_dir)
    subfolder = base_dir / breakdown.arxiv_id
    subfolder.mkdir(parents=True, exist_ok=True)
    index_file = subfolder / "index.html"
    flat_file = base_dir / f"{breakdown.arxiv_id}.html"

    badge_meta = {
        "support": ("🟢 Supports Thesis", "bg-emerald-100 text-emerald-800 border-emerald-300", "This paper provides solid experimental evidence validating your edge quantization benchmarks!"),
        "extend": ("🟡 Extends Thesis", "bg-amber-100 text-amber-800 border-amber-300", "This paper proposes a clever adjacent optimization you can adapt to improve throughput!"),
        "threaten": ("🔴 Threatens Thesis", "bg-rose-100 text-rose-800 border-rose-300", "Caution: This paper presents empirical results or bounds that could challenge your claims!"),
        "irrelevant": ("⚪ Out of Scope", "bg-slate-100 text-slate-800 border-slate-300", "This paper focuses on architectures outside your Raspberry Pi 5 research boundaries."),
    }.get(breakdown.verdict.value, ("ℹ️ Evaluated", "bg-blue-100 text-blue-800 border-blue-300", ""))

    badge_label, badge_classes, badge_expl = badge_meta

    # Novel ideas cards
    novel_cards_html = "".join(
        f"""<div class="flex items-start gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50/80 hover:bg-slate-50 transition">
            <span class="text-xl">💡</span>
            <div>
                <span class="font-semibold text-slate-900 block text-sm mb-1">Novel Technique</span>
                <p class="text-sm text-slate-700 m-0">{html.escape(idea)}</p>
            </div>
        </div>"""
        for idea in breakdown.novel_ideas
    )

    # Jargon Buster items
    full_text = f"{breakdown.title} {breakdown.simplified_summary} {' '.join(breakdown.novel_ideas)}"
    jargon_items = _generate_jargon_buster(full_text)
    jargon_html = "".join(
        f"""<div class="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
            <div class="font-bold text-sm text-slate-800 mb-1">💡 {html.escape(term)}</div>
            <div class="text-xs text-slate-600 leading-relaxed">{html.escape(defn)}</div>
        </div>"""
        for term, defn in jargon_items
    )

    # Key Takeaways
    takeaways_html = "".join(
        f"""<li class="flex items-start gap-2 text-sm text-slate-800 mb-2">
            <span class="text-emerald-500 font-bold">•</span>
            <span>{html.escape(pt)}</span>
        </li>"""
        for pt in breakdown.key_takeaways
    )

    sim_pct = int(breakdown.similarity_score * 100)
    chart_json = json.dumps(breakdown.chart_data)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Breakdown: {html.escape(breakdown.title)}</title>
    <!-- 100% Locally Vendored Frontend Libraries (Zero External CDNs) -->
    <script src="/papers/assets/tailwind.js"></script>
    <script defer src="/papers/assets/alpine.min.js"></script>
    <script src="/papers/assets/chart.min.js"></script>
    <script src="/papers/assets/mermaid.min.js"></script>
    <style>
        /* Mobile Touch & Self-Contained Styles (Clean Fallback without Tailwind/Alpine) */
        :root {{
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
        }}
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 12px;
            background-color: var(--bg);
            color: var(--text-main);
            -webkit-font-smoothing: antialiased;
        }}
        @media (min-width: 768px) {{
            body {{ padding: 2rem; }}
        }}
        /* Tab Bar Mobile Touch Scrolling */
        nav.tab-nav-bar {{
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
            margin-bottom: 1.5rem;
            scrollbar-width: thin;
        }}
        .tab-btn {{
            cursor: pointer;
            border: none;
            background: transparent;
            font-family: inherit;
            padding: 0.6rem 1rem;
            border-radius: 0.75rem;
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            white-space: nowrap;
            transition: all 0.15s ease-in-out;
        }}
        .tab-btn:hover {{ background-color: #f1f5f9; }}
        .tab-btn.active {{
            background-color: var(--primary) !important;
            color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
        }}
        /* Fallback Tab Display (Tab 1 visible by default) */
        .tab-pane {{ display: none; }}
        .tab-pane.active, #tab-ideas {{ display: block; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; border: 1px solid var(--border); text-align: left; font-size: 0.875rem; }}
        th {{ background: #f8fafc; font-weight: 600; }}
        .overflow-x-auto {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        [x-cloak] {{ display: none !important; }}
    </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased font-sans p-4 md:p-8">
    <div class="max-w-4xl mx-auto" x-data="{{ tab: 'ideas', mode: 'eli5', copied: false }}">
        
        <!-- Navigation Header -->
        <nav class="flex items-center gap-3 text-sm font-medium text-slate-500 mb-4">
            <a href="/papers" class="text-blue-600 hover:underline">&larr; Literature Gallery</a>
            <span>•</span>
            <a href="/notes" class="text-blue-600 hover:underline">Human Approval Gate</a>
            <span>•</span>
            <a href="/" class="text-blue-600 hover:underline">Judge Dashboard</a>
        </nav>

        <!-- Header Card -->
        <header class="bg-white border border-slate-200 rounded-2xl p-6 md:p-8 mb-6 shadow-xs">
            <div class="flex items-center gap-3 mb-3">
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border {badge_classes}">
                    {badge_label}
                </span>
                <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    arXiv:{html.escape(breakdown.arxiv_id)}
                </span>
            </div>
            <h1 class="text-2xl md:text-3xl font-extrabold text-slate-900 leading-tight mb-3">
                {html.escape(breakdown.title)}
            </h1>
            <div class="text-sm text-slate-500 flex flex-wrap items-center gap-x-4 gap-y-1">
                <span><strong>Authors:</strong> {html.escape(', '.join(breakdown.authors[:3]) if breakdown.authors else 'Listed on arXiv')}</span>
                <span>•</span>
                <span><strong>Year:</strong> {breakdown.year}</span>
                <span>•</span>
                <a href="https://arxiv.org/abs/{html.escape(breakdown.arxiv_id)}" target="_blank" rel="noopener" class="text-blue-600 font-medium hover:underline">
                    View on arXiv &rarr;
                </a>
            </div>
        </header>

        <!-- 4-Tab Navigation Bar -->
        <nav class="flex gap-2 overflow-x-auto pb-2 border-b-2 border-slate-200 mb-6 tab-nav-bar">
            <button 
                id="btn-ideas"
                class="tab-btn px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition whitespace-nowrap"
                :class="{{ 'active': tab === 'ideas' }}" 
                @click="tab = 'ideas'"
                onclick="window.switchTab && window.switchTab('ideas')"
            >
                🎯 1. Alignment & Novel Ideas
            </button>
            <button 
                id="btn-pipeline"
                class="tab-btn px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition whitespace-nowrap"
                :class="{{ 'active': tab === 'pipeline' }}" 
                @click="tab = 'pipeline'; $nextTick(() => window.renderMermaid && window.renderMermaid())"
                onclick="window.switchTab && window.switchTab('pipeline')"
            >
                🖼️ 2. Architecture & Pipeline
            </button>
            <button 
                id="btn-benchmarks"
                class="tab-btn px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition whitespace-nowrap"
                :class="{{ 'active': tab === 'benchmarks' }}" 
                @click="tab = 'benchmarks'; $nextTick(() => window.initCharts && window.initCharts())"
                onclick="window.switchTab && window.switchTab('benchmarks')"
            >
                📊 3. Tradeoffs & Benchmarks
            </button>
            <button 
                id="btn-experiment"
                class="tab-btn px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition whitespace-nowrap"
                :class="{{ 'active': tab === 'experiment' }}" 
                @click="tab = 'experiment'"
                onclick="window.switchTab && window.switchTab('experiment')"
            >
                🧪 4. Experiment & Citations
            </button>
        </nav>

        <!-- TAB 1: Alignment & Novel Ideas -->
        <section id="tab-ideas" class="tab-pane space-y-6" x-show="tab === 'ideas'" data-tab-content>
            <!-- Similarity & Verdict -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <span>🎯</span> Thesis Relevance & Alignment Score
                </h3>
                <div class="flex items-center gap-4 bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
                    <div class="text-3xl font-extrabold text-blue-600">{sim_pct}%</div>
                    <div class="flex-grow">
                        <div class="w-full bg-slate-200 h-3 rounded-full overflow-hidden">
                            <div class="bg-gradient-to-r from-blue-500 to-emerald-500 h-3 rounded-full" style="width: {sim_pct}%"></div>
                        </div>
                        <div class="text-xs font-semibold text-slate-500 mt-1">Cosine Embedding Similarity vs. Thesis Profile</div>
                    </div>
                </div>
                <p class="text-sm text-slate-700 leading-relaxed">
                    <strong>Verdict Rationale:</strong> {html.escape(breakdown.verdict_reason)}
                </p>
            </div>

            <!-- Novel Discoveries -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <span>💡</span> Novel Mechanisms & Ideas in this Paper
                </h3>
                <div class="grid gap-3">
                    {novel_cards_html}
                </div>
            </div>

            <!-- Side-by-Side Comparison -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>⚖️</span> Comparison vs. Thesis Baseline
                    </h3>
                    <!-- Alpine ELI5 vs Deep Dive Switcher -->
                    <div class="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-100 text-xs font-semibold">
                        <button 
                            class="px-2.5 py-1 rounded-md transition" 
                            :class="mode === 'eli5' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-500'" 
                            @click="mode = 'eli5'"
                        >
                            ELI5 Summary
                        </button>
                        <button 
                            class="px-2.5 py-1 rounded-md transition" 
                            :class="mode === 'deep' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-500'" 
                            @click="mode = 'deep'"
                        >
                            Deep Specs
                        </button>
                    </div>
                </div>

                <div x-show="mode === 'eli5'" class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-sm mb-4">
                    <div class="font-bold mb-1 flex items-center gap-1.5 text-emerald-800">
                        <span>🎓</span> The 60-Second ELI5 (Explain Like I'm 5)
                    </div>
                    <p class="m-0 leading-relaxed">{html.escape(breakdown.simplified_summary)}</p>
                    <p class="mt-2 mb-0 font-semibold text-xs text-emerald-700">{badge_expl}</p>
                </div>

                <p class="text-sm text-slate-700 mb-4">{html.escape(breakdown.thesis_comparison)}</p>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr class="bg-slate-50 text-slate-600 border-b border-slate-200">
                                <th class="p-3 font-semibold">Aspect</th>
                                <th class="p-3 font-semibold">Thesis Baseline (Moonshine Tiny)</th>
                                <th class="p-3 font-semibold">Paper Method (arXiv:{html.escape(breakdown.arxiv_id)})</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 text-slate-800">
                            <tr>
                                <td class="p-3 font-medium text-slate-600">Hardware Target</td>
                                <td class="p-3">Raspberry Pi 5 (Quad Cortex-A76 @ 2.4 GHz)</td>
                                <td class="p-3">ARM / RISC Edge Architecture</td>
                            </tr>
                            <tr>
                                <td class="p-3 font-medium text-slate-600">Quantization Scheme</td>
                                <td class="p-3">INT4 PTQ Weight-Only + INT8 Activation</td>
                                <td class="p-3 font-semibold text-blue-600">{html.escape(breakdown.verdict.value.upper())} Technique</td>
                            </tr>
                            <tr>
                                <td class="p-3 font-medium text-slate-600">Throughput Target</td>
                                <td class="p-3">RTF &le; 0.5 (2x Real-Time Speed)</td>
                                <td class="p-3">Verified empirical speedup</td>
                            </tr>
                            <tr>
                                <td class="p-3 font-medium text-slate-600">Isolation Policy</td>
                                <td class="p-3">Unprivileged Podman Container</td>
                                <td class="p-3">Non-root edge execution</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- TAB 2: Architecture & Pipeline -->
        <section id="tab-pipeline" class="tab-pane space-y-6" x-show="tab === 'pipeline'" data-tab-content style="display: none;">
            <!-- Model Architecture Flowchart -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="mb-4">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>🖼️</span> Neural Architecture Dataflow
                    </h3>
                    <p class="text-xs text-slate-500 mt-1">Rendered dynamically via local Mermaid.js</p>
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 overflow-x-auto flex justify-center">
                    <pre class="mermaid">{breakdown.mermaid_architecture}</pre>
                </div>
            </div>

            <!-- Streaming Execution Sequence -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="mb-4">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>⚡</span> Real-Time Streaming Audio Sequence
                    </h3>
                    <p class="text-xs text-slate-500 mt-1">Sequence diagram between microphone chunker, SIMD registers, and output</p>
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 overflow-x-auto flex justify-center">
                    <pre class="mermaid">{breakdown.mermaid_sequence}</pre>
                </div>
            </div>

            <!-- Jargon Buster -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <span>📖</span> Jargon Buster: Key Terms Decoded
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {jargon_html}
                </div>
            </div>
        </section>

        <!-- TAB 3: Benchmarks & Tradeoffs -->
        <section id="tab-benchmarks" class="tab-pane space-y-6" x-show="tab === 'benchmarks'" data-tab-content style="display: none;">
            <!-- RTF vs WER Chart -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="mb-4">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>📊</span> Accuracy vs. Speed Tradeoff (WER vs. RTF)
                    </h3>
                    <p class="text-xs text-slate-500 mt-1">Target boundary: RTF &le; 0.5 (lower is faster) and WER degradation &le; 6%</p>
                </div>
                <div class="h-64 w-full">
                    <canvas id="rtfWerChart"></canvas>
                </div>
            </div>

            <!-- Memory Footprint Chart -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="mb-4">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>🧠</span> Peak Memory Footprint on Edge (RAM in MB)
                    </h3>
                    <p class="text-xs text-slate-500 mt-1">Comparing peak runtime RAM against the 1.0 GB container boundary on Raspberry Pi 5</p>
                </div>
                <div class="h-64 w-full">
                    <canvas id="ramChart"></canvas>
                </div>
            </div>

            <!-- Hardware Metrics Pill -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-xs text-center">
                    <div class="text-xs font-semibold text-slate-500 uppercase">Target RTF</div>
                    <div class="text-2xl font-extrabold text-blue-600 mt-1">&le; 0.50</div>
                    <div class="text-xs text-slate-400 mt-1">2x Real-Time Speed</div>
                </div>
                <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-xs text-center">
                    <div class="text-xs font-semibold text-slate-500 uppercase">Max WER Drop</div>
                    <div class="text-2xl font-extrabold text-emerald-600 mt-1">&le; 6.0%</div>
                    <div class="text-xs text-slate-400 mt-1">Acoustic Degradation Limit</div>
                </div>
                <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-xs text-center">
                    <div class="text-xs font-semibold text-slate-500 uppercase">RAM Ceiling</div>
                    <div class="text-2xl font-extrabold text-purple-600 mt-1">&le; 1,000 MB</div>
                    <div class="text-xs text-slate-400 mt-1">Podman Container Limit</div>
                </div>
            </div>
        </section>

        <!-- TAB 4: Experiment & Citations -->
        <section id="tab-experiment" class="tab-pane space-y-6" x-show="tab === 'experiment'" data-tab-content style="display: none;">
            <!-- Essential Key Takeaways -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <span>📌</span> Essential Key Takeaways
                </h3>
                <ul class="space-y-1">
                    {takeaways_html}
                </ul>
            </div>

            <!-- Next Experiment Proposal -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <span>🧪</span> Proposed Raspberry Pi 5 Hardware Experiment
                </h3>
                <div class="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-950 text-sm mb-4">
                    <p class="font-medium mb-2"><strong>Test Protocol:</strong> {html.escape(breakdown.next_experiment)}</p>
                    <p class="text-xs font-mono bg-blue-100/70 p-2.5 rounded-lg border border-blue-200">
                        podman run --rm --security-opt no-new-privileges --cpus 4 -m 1000m thesisclaw:rpi5-asr-eval
                    </p>
                </div>
                <p class="text-sm text-slate-700">
                    <strong>Target Benchmark Criterion:</strong> <code class="px-2 py-0.5 rounded-md bg-slate-100 text-xs font-bold text-blue-700">{html.escape(breakdown.success_criterion)}</code>
                </p>
            </div>

            <!-- Verified Academic Proof -->
            {f'''<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <h3 class="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <span>📜</span> Verified Academic Evidence (Direct Quote)
                </h3>
                <blockquote class="p-4 rounded-xl bg-slate-50 border-l-4 border-blue-600 text-slate-700 italic text-sm">
                    &ldquo;{html.escape(breakdown.verified_quote)}&rdquo;
                </blockquote>
                <div class="text-xs text-slate-400 mt-2">Verified verbatim by Critic Subagent (Quality Gate Passed)</div>
            </div>''' if breakdown.verified_quote else ''}

            <!-- Citable APA Paragraph -->
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <span>📝</span> Citable APA Reference Paragraph
                    </h3>
                    <button 
                        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
                        @click="navigator.clipboard.writeText('{html.escape(breakdown.citable_paragraph).replace("'", "\\'")}'); copied = true; setTimeout(() => copied = false, 2000)"
                    >
                        <span x-text="copied ? '✅ Copied!' : '📋 Copy Citation'"></span>
                    </button>
                </div>
                <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-700 italic leading-relaxed">
                    {html.escape(breakdown.citable_paragraph)}
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="text-center text-xs text-slate-400 mt-10">
            <p>ThesisClaw • Autonomous Literature Agent • Built for NVIDIA Claw Agent Challenge: Berlin</p>
        </footer>
    </div>

    <!-- Chart.js & Mermaid Interactive Initializers -->
    <script>
        const chartData = {chart_json};
        let chartsInitialized = false;

        window.renderMermaid = function() {{
            if (window.mermaid) {{
                mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
                mermaid.run();
            }}
        }};

        window.initCharts = function() {{
            if (chartsInitialized || !window.Chart) return;
            chartsInitialized = true;

            // Chart 1: RTF & WER
            const ctx1 = document.getElementById('rtfWerChart');
            if (ctx1) {{
                new Chart(ctx1, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.labels,
                        datasets: [
                            {{
                                label: 'Real-Time Factor (RTF - lower is faster)',
                                data: chartData.rtf,
                                backgroundColor: 'rgba(37, 99, 235, 0.75)',
                                borderColor: 'rgb(37, 99, 235)',
                                borderWidth: 1,
                                yAxisID: 'y'
                            }},
                            {{
                                label: 'WER Degradation (% - lower is better)',
                                data: chartData.wer_degradation,
                                type: 'line',
                                borderColor: 'rgb(16, 185, 129)',
                                backgroundColor: 'rgb(16, 185, 129)',
                                borderWidth: 2,
                                yAxisID: 'y1'
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{ display: true, text: 'RTF' }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                grid: {{ drawOnChartArea: false }},
                                title: {{ display: true, text: 'WER Degradation (%)' }}
                            }}
                        }}
                    }}
                }});
            }}

            // Chart 2: RAM Footprint
            const ctx2 = document.getElementById('ramChart');
            if (ctx2) {{
                new Chart(ctx2, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.labels,
                        datasets: [{{
                            label: 'Peak RAM (MB)',
                            data: chartData.ram_mb,
                            backgroundColor: [
                                'rgba(239, 68, 68, 0.7)',
                                'rgba(245, 158, 11, 0.7)',
                                'rgba(59, 130, 246, 0.7)',
                                'rgba(16, 185, 129, 0.8)',
                                'rgba(147, 51, 234, 0.7)'
                            ],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{ display: true, text: 'Memory in Megabytes (MB)' }}
                            }}
                        }}
                    }}
                }});
            }}
        }};

        // Vanilla Fallback Tab Switcher for Standalone Offline Opening
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

            if (name === 'pipeline') {{
                setTimeout(window.renderMermaid, 50);
            }} else if (name === 'benchmarks') {{
                setTimeout(window.initCharts, 50);
            }}
        }};

        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('[x-cloak]').forEach(function(el) {{
                el.removeAttribute('x-cloak');
            }});
            window.renderMermaid && window.renderMermaid();
        }});
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
    similarity_score: float | None = None,
) -> Path:
    """Convenience wrapper: transforms PaperContent through visualizer_subagent and builds index.html."""
    breakdown = visualizer_subagent(
        paper,
        verdict,
        pathfinder,
        similarity_score=similarity_score if similarity_score is not None else 0.76,
    )
    return build_paper_subfolder_index(breakdown, output_dir=output_dir)


def build_fight_page(
    fight_id: str,
    output_dir: str | Path = "site/public/fight",
) -> Path:
    """
    Build a rich two-column HTML page for a completed or in-progress Paper Arena fight.
    Displays side-by-side round exchanges, stance badges, verified quote badges,
    scorecards, and ranked ideas per agentwars.md specifications.
    """
    from thesisclaw.arena.memory import get_fight, read_entries
    from thesisclaw.arena.models import FightRecord, FightState, MemoryEntry

    record = get_fight(fight_id)
    if record is None:
        record = FightRecord(
            fight_id=fight_id,
            fighter_a={"kind": "ground", "doc_id": "ground"},
            fighter_b={"kind": "paper", "doc_id": "unknown"},
            state=FightState.QUEUED,
        )

    entries = read_entries(fight_id)
    out_dir = Path(output_dir) / fight_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"

    doc_a = html.escape(record.fighter_a.doc_id)
    doc_b = html.escape(record.fighter_b.doc_id)
    status_label = html.escape(record.state.value.upper())

    mv = record.merged_verdict
    winner_text = html.escape(mv.winner.upper()) if mv and mv.winner else "IN PROGRESS"
    swap_agree = f"{mv.swap_agreement * 100:.1f}%" if mv else "Pending"
    verified_ratio = f"{mv.all_entries_verified_ratio * 100:.1f}%" if mv else "Pending"
    score_a = f"{mv.final_scores.get('fighter_a', 0.0):.1f}" if mv else "-"
    score_b = f"{mv.final_scores.get('fighter_b', 0.0):.1f}" if mv else "-"

    # Group entries by round
    rounds_map: dict[int, list[MemoryEntry]] = {}
    for e in entries:
        rounds_map.setdefault(e.round, []).append(e)

    def render_entry_card(e: MemoryEntry) -> str:
        quote_html = ""
        if e.quote:
            badge_class = "quote-verified" if e.verified else ("quote-near" if e.near_exact else "quote-unverified")
            badge_text = "✓ Verified Quote" if e.verified else ("~ Near Match" if e.near_exact else "⚬ Unverified Quote")
            quote_html = (
                f'<div class="quote-box {badge_class}">'
                f'<span class="badge {badge_class}">{badge_text}</span>'
                f'<blockquote>&ldquo;{html.escape(e.quote)}&rdquo;</blockquote>'
                f'</div>'
            )

        strike_style = 'style="text-decoration: line-through; opacity: 0.7;"' if e.quote and not e.verified and not e.near_exact else ""
        stance_class = f"stance-{e.stance.value.lower()}"
        return (
            f'<div class="entry-card {stance_class}">'
            f'<div class="entry-header">'
            f'<span class="entry-author">{html.escape(e.author.upper())}</span>'
            f'<span class="badge badge-stance">{html.escape(e.stance.value)}</span>'
            f'</div>'
            f'<p class="entry-text" {strike_style}>{html.escape(e.text)}</p>'
            f'{quote_html}'
            f'</div>'
        )

    rounds_html = []
    round_titles = {
        0: "Setup & Framing (Moderator)",
        1: "Round 1 — Independent Openings",
        2: "Round 2 — Cross-Examination & Direct Clashes",
        3: "Round 3 — Common Ground & Novel Ideas",
    }

    for r_num in sorted(rounds_map.keys()):
        r_entries = rounds_map[r_num]
        title = round_titles.get(r_num, f"Round {r_num}")

        col_a_entries = [e for e in r_entries if e.author == "fighter_a"]
        col_b_entries = [e for e in r_entries if e.author == "fighter_b"]
        other_entries = [e for e in r_entries if e.author not in ("fighter_a", "fighter_b")]

        moderator_section = ""
        if other_entries:
            cards = "".join(render_entry_card(e) for e in other_entries)
            moderator_section = f'<div class="moderator-block"><h4>Moderator</h4>{cards}</div>'

        cols_section = ""
        if col_a_entries or col_b_entries:
            cards_a = "".join(render_entry_card(e) for e in col_a_entries) or '<p class="text-muted">No statements</p>'
            cards_b = "".join(render_entry_card(e) for e in col_b_entries) or '<p class="text-muted">No statements</p>'
            cols_section = (
                f'<div class="fight-columns">'
                f'<div class="fight-col fight-col-a"><h5>{doc_a}</h5>{cards_a}</div>'
                f'<div class="fight-col fight-col-b"><h5>{doc_b}</h5>{cards_b}</div>'
                f'</div>'
            )

        rounds_html.append(
            f'<section class="round-section">'
            f'<h3>{title}</h3>'
            f'{moderator_section}'
            f'{cols_section}'
            f'</section>'
        )

    all_rounds_content = "\n".join(rounds_html) if rounds_html else '<p class="text-muted">Fight in progress or queued.</p>'

    ideas_html = ""
    if mv and mv.ranked_ideas:
        idea_items = "".join(f"<li><code>{html.escape(iid)}</code></li>" for iid in mv.ranked_ideas)
        ideas_html = f'<div class="card"><h4>💡 Ranked Novel Ideas</h4><ul>{idea_items}</ul></div>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arena Fight: {doc_a} vs {doc_b} — ThesisClaw</title>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f2937;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px 16px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1040px; margin: 0 auto; }}
        header {{ margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
        .nav-back {{ color: var(--primary); text-decoration: none; font-size: 0.9rem; }}
        .title {{ font-size: 1.8rem; font-weight: 800; margin: 8px 0; color: #fff; }}
        .header-meta {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
        .badge-status {{ background: #1e3a8a; color: #93c5fd; }}
        .badge-winner {{ background: #064e3b; color: #6ee7b7; }}
        .badge-stance {{ background: #374151; color: #d1d5db; }}
        .quote-verified {{ background: rgba(16, 185, 129, 0.1); border-left: 3px solid var(--success); color: #a7f3d0; }}
        .quote-near {{ background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--warning); color: #fde68a; }}
        .quote-unverified {{ background: rgba(239, 68, 68, 0.1); border-left: 3px solid var(--danger); color: #fca5a5; }}
        .scoreboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }}
        .score-box {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }}
        .score-val {{ font-size: 1.6rem; font-weight: 800; color: var(--primary); }}
        .score-lbl {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; }}
        .round-section {{ margin-bottom: 32px; }}
        .round-section h3 {{ border-bottom: 1px solid var(--border); padding-bottom: 8px; color: #e5e7eb; }}
        .fight-columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }}
        @media (max-width: 768px) {{ .fight-columns {{ grid-template-columns: 1fr; }} }}
        .fight-col {{ background: rgba(17, 24, 39, 0.6); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
        .fight-col h5 {{ margin: 0 0 12px 0; color: var(--primary); font-size: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
        .entry-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }}
        .entry-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .entry-author {{ font-size: 0.8rem; font-weight: 700; color: var(--text-muted); }}
        .entry-text {{ margin: 0 0 8px 0; font-size: 0.9rem; }}
        .quote-box {{ padding: 8px; border-radius: 4px; font-size: 0.85rem; margin-top: 6px; }}
        .quote-box blockquote {{ margin: 4px 0 0 0; font-style: italic; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
        .text-muted {{ color: var(--text-muted); }}
        footer {{ text-align: center; font-size: 0.8rem; color: var(--text-muted); margin-top: 48px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="/leaderboard" class="nav-back">&larr; Back to Leaderboard</a>
            <h1 class="title">⚔️ {doc_a} <span style="color:var(--text-muted)">vs</span> {doc_b}</h1>
            <div class="header-meta">
                <span class="badge badge-status">Fight: {html.escape(fight_id)}</span>
                <span class="badge badge-status">State: {status_label}</span>
                <span class="badge badge-winner">Winner: {winner_text}</span>
            </div>
        </header>

        <div class="scoreboard">
            <div class="score-box">
                <div class="score-lbl">{doc_a} Score</div>
                <div class="score-val">{score_a}/5</div>
            </div>
            <div class="score-box">
                <div class="score-lbl">{doc_b} Score</div>
                <div class="score-val">{score_b}/5</div>
            </div>
            <div class="score-box">
                <div class="score-lbl">Swap Agreement</div>
                <div class="score-val" style="color:var(--success);">{swap_agree}</div>
            </div>
            <div class="score-box">
                <div class="score-lbl">Verified Quotes</div>
                <div class="score-val" style="color:var(--success);">{verified_ratio}</div>
            </div>
        </div>

        {ideas_html}

        <div class="card">
            <h4 style="margin-top:0;">🛡️ Fight Rules & Verifier Legend</h4>
            <p style="margin:0; font-size:0.85rem; color:var(--text-muted);">
                Each fighter may only cite verbatim quotes from its source document. 
                <span style="color:#a7f3d0">✓ Verified quotes</span> count towards scoring.
                <span style="color:#fca5a5; text-decoration:line-through">Strikethrough claims</span> contain unverified quotes and were excluded from judging.
            </p>
        </div>

        {all_rounds_content}

        <footer>
            <p>ThesisClaw Paper Arena • Powered by LangGraph & Nemotron • Berlin Hackathon</p>
        </footer>
    </div>
</body>
</html>
"""
    out_file.write_text(html_content, encoding="utf-8")
    return out_file


def build_leaderboard_page(
    output_path: str | Path = "site/public/leaderboard/index.html",
) -> Path:
    """Build the Elo leaderboard page ranking all papers and Ground."""
    from thesisclaw.arena.memory import get_leaderboard, list_fights

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    entries = get_leaderboard(limit=50)
    recent_fights = list_fights(limit=10)

    rows_html = []
    for i, e in enumerate(entries):
        badge = '<span class="badge badge-ground">Ground Thesis</span>' if e.doc_id == "ground" else ""
        link = f'<a href="https://arxiv.org/abs/{html.escape(e.doc_id)}" target="_blank">{html.escape(e.doc_id)}</a>' if e.doc_id != "ground" else "Ground (Thesis Anchor)"
        rows_html.append(
            f"<tr>"
            f"<td>#{i+1}</td>"
            f"<td><strong>{link}</strong> {badge}</td>"
            f"<td><span class='elo-val'>{e.rating:.0f}</span></td>"
            f"<td>{e.wins}</td>"
            f"<td>{e.losses}</td>"
            f"<td>{e.draws}</td>"
            f"<td>{e.fights}</td>"
            f"</tr>"
        )
    table_body = "\n".join(rows_html) if rows_html else "<tr><td colspan='7' class='text-muted'>No fights recorded yet.</td></tr>"

    fights_html = []
    for f in recent_fights:
        mv = f.merged_verdict
        winner = mv.winner.upper() if mv and mv.winner else f.state.value.upper()
        fights_html.append(
            f"<tr>"
            f"<td><a href='/fight/{html.escape(f.fight_id)}'><code>{html.escape(f.fight_id)}</code></a></td>"
            f"<td>{html.escape(f.fighter_a.doc_id)} vs {html.escape(f.fighter_b.doc_id)}</td>"
            f"<td><span class='badge'>{winner}</span></td>"
            f"<td>{f.started_at[:19].replace('T', ' ') if f.started_at else '-'}</td>"
            f"</tr>"
        )
    fights_body = "\n".join(fights_html) if fights_html else "<tr><td colspan='4' class='text-muted'>No recent fights.</td></tr>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Arena Leaderboard — ThesisClaw</title>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f2937;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #3b82f6;
            --success: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px 16px;
            line-height: 1.5;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        header {{ margin-bottom: 32px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
        .title {{ font-size: 2rem; font-weight: 800; margin: 0 0 8px 0; color: #fff; }}
        .subtitle {{ color: var(--text-muted); font-size: 1.05rem; margin: 0; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }}
        th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); }}
        th {{ background: #1f2937; color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        .elo-val {{ font-weight: 800; color: var(--primary); font-size: 1.05rem; }}
        .badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
        .badge-ground {{ background: #065f46; color: #6ee7b7; }}
        a {{ color: var(--primary); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .text-muted {{ color: var(--text-muted); }}
        footer {{ text-align: center; font-size: 0.8rem; color: var(--text-muted); margin-top: 48px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1 class="title">🏆 Paper Arena Leaderboard</h1>
            <p class="subtitle">Adversarial Research Debates &bull; Elo Ratings Defended Against Newcomers</p>
        </header>

        <div class="card">
            <h3 style="margin-top:0;">⚡ Current Standings</h3>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Fighter / Paper</th>
                        <th>Elo Rating</th>
                        <th>Wins</th>
                        <th>Losses</th>
                        <th>Draws</th>
                        <th>Fights</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3 style="margin-top:0;">⚔️ Recent Fights</h3>
            <table>
                <thead>
                    <tr>
                        <th>Fight ID</th>
                        <th>Matchup</th>
                        <th>Outcome</th>
                        <th>Started</th>
                    </tr>
                </thead>
                <tbody>
                    {fights_body}
                </tbody>
            </table>
        </div>

        <footer>
            <p>ThesisClaw • NVIDIA Claw Agent Challenge: Berlin • LangGraph Arena</p>
        </footer>
    </div>
</body>
</html>
"""
    out_file.write_text(html_content, encoding="utf-8")
    return out_file

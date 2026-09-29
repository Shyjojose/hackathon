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
) -> Path:
    """Convenience wrapper: transforms PaperContent through visualizer_subagent and builds index.html."""
    breakdown = visualizer_subagent(paper, verdict, pathfinder)
    return build_paper_subfolder_index(breakdown, output_dir=output_dir)

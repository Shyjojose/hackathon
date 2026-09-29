from __future__ import annotations

import json
import sqlite3

from thesisclaw.models.paper import PaperContent, PaperVerdict, VerdictEnum
from thesisclaw.site_builder.pages import build_paper_page
from thesisclaw.site_builder.stats import generate_stats_json


def test_generate_stats_json(tmp_path, monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE processed_papers (arxiv_id TEXT, title TEXT, verdict TEXT, reason TEXT, processed_at TIMESTAMP)")
        conn.execute("INSERT INTO processed_papers VALUES ('2404.12345', 'Paper A', 'support', 'Good fit', CURRENT_TIMESTAMP)")
        conn.execute("INSERT INTO processed_papers VALUES ('2404.67890', 'Paper B', 'threaten', 'Scoop', CURRENT_TIMESTAMP)")

    stats_out = tmp_path / "stats.json"
    stats = generate_stats_json(output_path=stats_out)

    assert stats["total_papers_evaluated"] == 2
    assert stats["verdicts"]["support"] == 1
    assert stats["verdicts"]["threaten"] == 1
    assert stats_out.exists()

    with stats_out.open() as f:
        data = json.load(f)
        assert data["project"] == "ThesisClaw"


def test_build_paper_page(tmp_path):
    paper = PaperContent(
        arxiv_id="2404.12345",
        title="Edge ASR Quantization",
        year=2026,
    )
    verdict = PaperVerdict(
        arxiv_id="2404.12345",
        verdict=VerdictEnum.SUPPORT,
        reason="Demonstrates INT4 RTF <= 0.5",
        direct_quote="We observe an RTF of 0.44 on Raspberry Pi 5.",
    )

    out_file = build_paper_page(paper, verdict, output_dir=tmp_path)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "Edge ASR Quantization" in content
    assert "2404.12345" in content
    assert "RTF of 0.44" in content

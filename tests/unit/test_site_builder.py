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


def test_build_fight_page(tmp_path, monkeypatch):
    from thesisclaw.arena.models import (
        Fighter,
        FighterKind,
        FightRecord,
        FightState,
        MemoryEntry,
        MergedVerdict,
        Stance,
    )
    from thesisclaw.site_builder.pages import build_fight_page

    record = FightRecord(
        fight_id="fight-test-99",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.12345"),
        state=FightState.DONE,
        merged_verdict=MergedVerdict(
            fight_id="fight-test-99",
            winner="fighter_a",
            swap_agreement=0.92,
            final_scores={"fighter_a": 4.5, "fighter_b": 3.6},
            ranked_ideas=["idea_alpha"],
            all_entries_verified_ratio=1.0,
            struck_count=0,
            upheld_count=3,
        ),
    )
    entries = [
        MemoryEntry(
            fight_id="fight-test-99",
            round=1,
            author="fighter_a",
            entry_type="claim",
            text="INT4 reduces RAM by 52%",
            quote="reduces peak RAM by 52%",
            doc_id="ground",
            stance=Stance.SUPPORTS,
            verified=True,
        ),
        MemoryEntry(
            fight_id="fight-test-99",
            round=1,
            author="fighter_b",
            entry_type="claim",
            text="Speculative decoding provides 2.5x throughput",
            quote="2.5x throughput improvement",
            doc_id="2608.12345",
            stance=Stance.CONTRADICTS,
            verified=False,
        ),
    ]

    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record if fid == "fight-test-99" else None)
    monkeypatch.setattr("thesisclaw.arena.memory.read_entries", lambda fid: entries if fid == "fight-test-99" else [])

    out_file = build_fight_page("fight-test-99", output_dir=tmp_path)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "fight-test-99" in content
    assert "ground" in content
    assert "2608.12345" in content
    assert "Verified Quote" in content
    assert "INT4 reduces RAM" in content


def test_build_leaderboard_page(tmp_path, monkeypatch):
    from thesisclaw.arena.models import EloEntry
    from thesisclaw.site_builder.pages import build_leaderboard_page

    entries = [
        EloEntry(doc_id="ground", rating=1264.0, wins=3, losses=0, draws=1, fights=4),
        EloEntry(doc_id="2608.12345", rating=1215.0, wins=2, losses=1, draws=0, fights=3),
    ]
    monkeypatch.setattr("thesisclaw.arena.memory.get_leaderboard", lambda limit=50: entries)
    monkeypatch.setattr("thesisclaw.arena.memory.list_fights", lambda limit=10: [])

    out_path = tmp_path / "leaderboard.html"
    res = build_leaderboard_page(output_path=out_path)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "Paper Arena Leaderboard" in content
    assert "ground" in content
    assert "1264" in content
    assert "2608.12345" in content

from __future__ import annotations

import pytest
import respx

from thesisclaw.jobs.backfill import run_backfill
from thesisclaw.jobs.scan import query_arxiv_rss_or_api
from thesisclaw.jobs.sleep import idle_sleep_loop


@pytest.mark.asyncio
async def test_idle_sleep_loop():
    # Test that the sleep loop exits cleanly after 1 iteration
    await idle_sleep_loop(interval_seconds=0, max_iterations=1)


@pytest.mark.asyncio
@respx.mock
async def test_query_arxiv_api_mocked():
    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2404.99991</id>
        <title>Quantized Edge ASR</title>
      </entry>
      <entry>
        <id>http://arxiv.org/abs/2404.99992</id>
        <title>Sliding Window Attention</title>
      </entry>
    </feed>
    """
    respx.get("http://export.arxiv.org/api/query").respond(
        status_code=200,
        text=xml_response,
    )

    ids = await query_arxiv_rss_or_api("edge ASR", max_results=2)
    assert len(ids) == 2
    assert "http://arxiv.org/abs/2404.99991" in ids


@pytest.mark.asyncio
@respx.mock
async def test_run_backfill_mocked(tmp_path, monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))

    paper_id = "2404.12345"
    respx.get(f"https://arxiv-txt.org/abs/{paper_id}").respond(
        status_code=200,
        text="Title: Backfill Benchmark\n\nAbstract\nBenchmarking edge models.",
    )

    briefing = await run_backfill(paper_ids=[paper_id])
    assert briefing.papers_processed == 1
    assert "Daily Briefing" in briefing.telegram_briefing

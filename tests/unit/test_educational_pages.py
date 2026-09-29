from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from thesisclaw.models.paper import PaperContent, PaperVerdict, PathfinderResult, VerdictEnum
from thesisclaw.site_builder.pages import build_paper_page
from thesisclaw.telegram.bot import TelegramBotClient
from thesisclaw.web.app import app


def test_build_educational_paper_page(tmp_path):
    paper = PaperContent(
        arxiv_id="2608.99999",
        title="Streaming INT4 Quantization on ARM Cortex-A76",
        authors=["Alice Smith", "Bob Jones"],
        year=2026,
        abstract="We demonstrate Post-Training Quantization with RTF <= 0.45 and low WER degradation.",
        sections={"methodology": "We employ 128-bit ARM NEON SIMD instructions."},
    )
    verdict = PaperVerdict(
        arxiv_id="2608.99999",
        verdict=VerdictEnum.SUPPORT,
        reason="Confirms that INT4 achieves RTF <= 0.5 without exceeding 6% WER degradation.",
        direct_quote="Achieved RTF of 0.44 on Raspberry Pi 5 hardware.",
    )
    pathfinder = PathfinderResult(
        arxiv_id="2608.99999",
        project_slug="rpi5-moonshine-int4",
        next_experiment="Deploy INT4 Moonshine Tiny profile inside Podman container.",
        success_criterion="RTF <= 0.5",
        citable_paragraph="Smith & Jones (2026) show that INT4 quantization preserves speech accuracy.",
    )

    out_file = build_paper_page(paper, verdict, pathfinder, output_dir=tmp_path)
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "The 60-Second ELI5" in content
    assert "Jargon Buster: Key Terms Decoded" in content
    assert "INT4 Quantization" in content
    assert "Proposed Raspberry Pi 5 Hardware Experiment" in content
    assert "Deploy INT4 Moonshine Tiny" in content
    assert "RTF of 0.44" in content
    assert "Alignment & Novel Ideas" in content
    assert "Architecture & Pipeline" in content
    assert "Tradeoffs & Benchmarks" in content
    assert "Experiment & Citations" in content
    assert "mermaid.min.js" in content
    assert "chart.min.js" in content
    assert "tailwind.js" in content

    # Verify subfolder index.html exists
    subfolder_index = tmp_path / "2608.99999" / "index.html"
    assert subfolder_index.exists()
    assert "alpine.min.js" in subfolder_index.read_text(encoding="utf-8")


def test_view_paper_page_web_endpoint(tmp_path, monkeypatch):
    client = TestClient(app)

    # 404 test for non-existent paper
    resp_404 = client.get("/papers/9999.00000")
    assert resp_404.status_code == 404

    # Generate a real page into site/public/papers
    paper = PaperContent(arxiv_id="2608.11111", title="Test Serving Paper")
    verdict = PaperVerdict(arxiv_id="2608.11111", verdict=VerdictEnum.SUPPORT, reason="Valid test")
    build_paper_page(paper, verdict, output_dir="site/public/papers")

    # Both without and with trailing slash should return 200
    resp_200 = client.get("/papers/2608.11111")
    assert resp_200.status_code == 200
    assert "Test Serving Paper" in resp_200.text
    assert "Alignment & Novel Ideas" in resp_200.text

    resp_slash = client.get("/papers/2608.11111/")
    assert resp_slash.status_code == 200
    assert "Test Serving Paper" in resp_slash.text


@pytest.mark.asyncio
@respx.mock
async def test_telegram_forwards_educational_link(monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    token = "mock-bot-token"
    sent_payloads = []

    def mock_send(request):
        import json

        data = json.loads(request.content)
        sent_payloads.append(data)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    import httpx

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(side_effect=mock_send)
    respx.post(f"https://api.telegram.org/bot{token}/sendDocument").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 2}})
    )
    respx.get("https://arxiv-txt.org/abs/2608.22222").respond(
        status_code=200,
        text="Title: ARM ASR Benchmark\n\nAbstract\nWe evaluate INT4 on Cortex-A76.",
    )

    bot = TelegramBotClient(token=token)
    update = {
        "update_id": 10,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "https://arxiv.org/abs/2608.22222",
        },
    }

    res = await bot.handle_update(update)
    assert res == "Paper evaluated."

    # Verify that the message sent to Telegram contains the link to the educational page
    matching_messages = [p["text"] for p in sent_payloads if "/papers/2608.22222" in p.get("text", "")]
    assert len(matching_messages) >= 1
    assert "Interactive 3-Tab Breakdown" in matching_messages[0]

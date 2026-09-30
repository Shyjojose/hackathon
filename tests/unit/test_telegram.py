from __future__ import annotations

import json
import sqlite3
from typing import Any

import httpx
import pytest
import respx

from thesisclaw.telegram.bot import TelegramBotClient


def test_telegram_user_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111,222")
    bot = TelegramBotClient(token="mock-token")
    assert bot.is_user_allowed(111) is True
    assert bot.is_user_allowed(222) is True
    assert bot.is_user_allowed(333) is False


@pytest.mark.asyncio
@respx.mock
async def test_telegram_send_message() -> None:
    token = "mock-bot-token"
    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").respond(
        status_code=200,
        json={"ok": True, "result": {"message_id": 42}},
    )

    bot = TelegramBotClient(token=token)
    res = await bot.send_message(chat_id=12345, text="Test Message")
    assert res.get("ok") is True


@pytest.mark.asyncio
@respx.mock
async def test_telegram_handle_update_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    token = "mock-bot-token"
    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").respond(
        status_code=200,
        json={"ok": True},
    )

    bot = TelegramBotClient(token=token)

    # Test /start command
    update_start = {
        "update_id": 1,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "/start",
        },
    }
    res_start = await bot.handle_update(update_start)
    assert res_start == "Start handled."

    # Test /status command
    update_status = {
        "update_id": 2,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "/status",
        },
    }
    res_status = await bot.handle_update(update_status)
    assert res_status == "Status handled."


@pytest.mark.asyncio
@respx.mock
async def test_telegram_first_message_sends_tags_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    bot = TelegramBotClient(token=token)

    # First interaction with greeting "Hello"
    update_hello = {
        "update_id": 10,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "Hello",
        },
    }
    res = await bot.handle_update(update_hello)
    assert res == "Start handled."
    assert len(sent_payloads) >= 1
    first_msg = sent_payloads[0]
    assert "/links" in first_msg["text"]
    assert "/papers" in first_msg["text"]
    assert "/thesis" in first_msg["text"]
    assert "reply_markup" in first_msg
    assert "keyboard" in first_msg["reply_markup"]


@pytest.mark.asyncio
@respx.mock
async def test_telegram_links_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    token = "mock-bot-token"

    # Set up sqlite db with processed_papers
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE processed_papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT,
                verdict TEXT,
                confidence TEXT,
                reason TEXT,
                backed_ratio REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO processed_papers (arxiv_id, title, verdict, confidence, reason, backed_ratio)
            VALUES ('2410.05229', 'Moonshine: Speech Recognition for Edge Devices', 'support', 'high', 'Low latency', 1.0)
        """)
        conn.execute("""
            INSERT INTO processed_papers (arxiv_id, title, verdict, confidence, reason, backed_ratio)
            VALUES ('2401.99999', 'Speculative Decoding on Cortex', 'extend', 'medium', 'Mixed precision', 0.9)
        """)

    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)  # Mark as already seen to isolate /links

    update_links = {
        "update_id": 11,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "/links",
        },
    }
    res = await bot.handle_update(update_links)
    assert res == "Links handled."
    assert len(sent_payloads) == 1
    msg_text = sent_payloads[0]["text"]
    assert "**Total Evaluated Papers:** `2`" in msg_text
    assert "**Supports Thesis:** `1`" in msg_text
    assert "**Extends Thesis:** `1`" in msg_text
    assert "/papers/2410.05229/" in msg_text
    assert "/papers/" in msg_text

    # Test button tap alias "🔗 Paper Links"
    update_btn = {
        "update_id": 12,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "🔗 Paper Links",
        },
    }
    res_btn = await bot.handle_update(update_btn)
    assert res_btn == "Links handled."


@pytest.mark.asyncio
@respx.mock
async def test_telegram_conversational_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    monkeypatch.setattr("thesisclaw.config.settings.settings.nvidia_api_key", "")
    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    update_chat = {
        "update_id": 13,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "What is our INT4 quantization target?",
        },
    }
    res = await bot.handle_update(update_chat)
    assert res == "Chat handled."
    assert len(sent_payloads) == 1
    assert "INT4" in sent_payloads[0]["text"]


@pytest.mark.asyncio
@respx.mock
async def test_telegram_conversational_chat_with_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    class MockLLM:
        async def ainvoke(self, messages: Any) -> Any:
            class MockResp:
                content = "AI: Our Moonshine INT4 target on RPi5 achieves RTF 0.18."
            return MockResp()

    monkeypatch.setattr("thesisclaw.telegram.bot.get_llm_client", lambda: MockLLM())

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    update_chat = {
        "update_id": 14,
        "message": {
            "chat": {"id": 999},
            "from": {"id": 111},
            "text": "Tell me about our Moonshine latency target.",
        },
    }
    res = await bot.handle_update(update_chat)
    assert res == "Chat handled."
    assert len(sent_payloads) == 1
    assert "Moonshine INT4" in sent_payloads[0]["text"]
    assert len(bot.chat_history[999]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_telegram_additional_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    token = "mock-bot-token"
    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").respond(
        status_code=200,
        json={"ok": True},
    )

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    # /thesis
    res_thesis = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/thesis"}
    })
    assert res_thesis == "Thesis handled."

    # /papers
    res_papers = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/papers"}
    })
    assert res_papers == "Papers gallery handled."

    # /notes
    res_notes = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/notes"}
    })
    assert res_notes == "Notes handled."


@pytest.mark.asyncio
@respx.mock
async def test_telegram_history_discarded_similar_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    monkeypatch.setattr("thesisclaw.config.settings.settings.nvidia_api_key", "")
    token = "mock-bot-token"

    # Set up sqlite db with processed_papers
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE processed_papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT,
                verdict TEXT,
                confidence TEXT,
                reason TEXT,
                backed_ratio REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO processed_papers (arxiv_id, title, verdict, confidence, reason, backed_ratio)
            VALUES ('2410.05229', 'Moonshine: Speech Recognition for Edge Devices', 'support', 'high', 'Fast latency on ARM', 1.0)
        """)
        conn.execute("""
            INSERT INTO processed_papers (arxiv_id, title, verdict, confidence, reason, backed_ratio)
            VALUES ('2609.99999', 'Large Server LLM Training', 'irrelevant', 'high', 'Embedding similarity below threshold', 0.0)
        """)

    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    # 1. Test /history command
    res_hist = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/history"}
    })
    assert res_hist == "History handled."
    assert "Literature Review History" in sent_payloads[-1]["text"]
    assert "Total Papers" in sent_payloads[-1]["text"]
    assert "Moonshine" in sent_payloads[-1]["text"]
    assert "Large Server" in sent_payloads[-1]["text"]

    # 2. Test /discarded command
    res_disc = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/discarded"}
    })
    assert res_disc == "Discarded handled."
    assert "Discarded / Out-of-Scope Papers" in sent_payloads[-1]["text"]
    assert "2609.99999" in sent_payloads[-1]["text"]
    assert "Embedding similarity below threshold" in sent_payloads[-1]["text"]

    # 3. Test /similar command
    res_sim = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/similar"}
    })
    assert res_sim == "Similar handled."
    assert "Similar & Thesis-Aligned" in sent_payloads[-1]["text"]
    assert "2410.05229" in sent_payloads[-1]["text"]

    # 4. Test button tap "📚 Review History"
    res_btn_hist = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "📚 Review History"}
    })
    assert res_btn_hist == "History handled."

    # 5. Test button tap "🚫 Discarded Papers"
    res_btn_disc = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "🚫 Discarded Papers"}
    })
    assert res_btn_disc == "Discarded handled."

    # 6. Test button tap "🟢 Similar Papers"
    res_btn_sim = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "🟢 Similar Papers"}
    })
    assert res_btn_sim == "Similar handled."

    # 7. Test conversational query: "How many literature papers reviewed?"
    res_q_count = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "How many literature papers reviewed?"}
    })
    assert res_q_count == "Chat handled."
    assert "Total Papers Reviewed: `2`" in sent_payloads[-1]["text"]
    assert "Similar / Thesis-Aligned: `1`" in sent_payloads[-1]["text"]
    assert "Discarded / Out-of-Scope: `1`" in sent_payloads[-1]["text"]

    # 8. Test conversational query: "Which papers did you discard and why?"
    res_q_disc = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "Which papers did you discard and why?"}
    })
    assert res_q_disc == "Chat handled."
    assert "Discarded / Out-of-Scope Papers" in sent_payloads[-1]["text"]
    assert "Embedding similarity below threshold" in sent_payloads[-1]["text"]


@pytest.mark.asyncio
@respx.mock
async def test_telegram_research_scout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    token = "mock-bot-token"

    sent_payloads: list[dict[str, Any]] = []

    def capture_message(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content.decode()))
        return httpx.Response(status_code=200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        side_effect=capture_message
    )

    from thesisclaw.models.paper import ResearchScoutResult, ScoutedPaper, VerdictEnum

    mock_scout_result = ResearchScoutResult(
        query="int4 speech",
        total_scanned=8,
        new_papers_found=3,
        papers=[
            ScoutedPaper(
                arxiv_id="2609.11111",
                title="INT4 Moonshine on Edge",
                abstract="INT4 quantized model on Cortex-A76.",
                similarity_score=0.84,
                verdict=VerdictEnum.SUPPORT,
                reason="Direct fit for edge ASR.",
                arxiv_url="https://arxiv.org/abs/2609.11111",
                dashboard_url="http://192.168.178.46:8080/papers/2609.11111/",
            ),
            ScoutedPaper(
                arxiv_id="2609.22222",
                title="Sliding Window KV Cache",
                abstract="Bounded cache strategy.",
                similarity_score=0.76,
                verdict=VerdictEnum.EXTEND,
                reason="Extends thesis attention mechanism.",
                arxiv_url="https://arxiv.org/abs/2609.22222",
                dashboard_url="http://192.168.178.46:8080/papers/2609.22222/",
            ),
            ScoutedPaper(
                arxiv_id="2609.33333",
                title="Memory Bandwidth Limits on Cortex",
                abstract="Memory wall prevents RTF <= 0.5.",
                similarity_score=0.68,
                verdict=VerdictEnum.THREATEN,
                reason="Warns of bus bandwidth bottleneck.",
                arxiv_url="https://arxiv.org/abs/2609.33333",
                dashboard_url="http://192.168.178.46:8080/papers/2609.33333/",
            ),
        ],
        summary_text="Scanned 8 candidates and found 3 new papers.",
    )

    async def mock_research_scout(*args: Any, **kwargs: Any) -> ResearchScoutResult:
        return mock_scout_result

    monkeypatch.setattr("thesisclaw.agent.subagents.research_scout_subagent", mock_research_scout)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    # 1. Test /research command
    res_cmd = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/research INT4 on ARM"}
    })
    assert res_cmd == "Research handled."
    assert any("Discovered 3 Brand New Research Papers" in p.get("text", "") for p in sent_payloads)
    summary_msg = next(p["text"] for p in sent_payloads if "Discovered 3 Brand New" in p.get("text", ""))
    assert "84%" in summary_msg
    assert "76%" in summary_msg
    assert "68%" in summary_msg
    assert "https://arxiv.org/abs/2609.11111" in summary_msg
    assert "http://192.168.178.46:8080/papers/2609.11111/" in summary_msg

    # 2. Test quick reply button tap: "🔍 Research 3 New Papers"
    sent_payloads.clear()
    res_btn = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "🔍 Research 3 New Papers"}
    })
    assert res_btn == "Research handled."
    assert any("Discovered 3 Brand New Research Papers" in p.get("text", "") for p in sent_payloads)

    # 3. Test conversational query: "Can you find 3 new papers for my thesis?"
    sent_payloads.clear()
    res_chat = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "Can you find 3 new papers for my thesis?"}
    })
    assert res_chat == "Research handled."
    assert any("Discovered 3 Brand New Research Papers" in p.get("text", "") for p in sent_payloads)


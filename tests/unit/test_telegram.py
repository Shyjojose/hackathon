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


@pytest.mark.asyncio
@respx.mock
async def test_telegram_leaderboard_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from thesisclaw.arena.models import EloEntry
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    monkeypatch.setattr(
        "thesisclaw.arena.memory.get_leaderboard",
        lambda limit=10: [
            EloEntry(doc_id="ground", rating=1264.0, wins=3, losses=0, draws=1, fights=4),
            EloEntry(doc_id="2608.12345", rating=1215.0, wins=2, losses=1, draws=0, fights=3),
        ],
    )

    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def mock_send(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        sent_payloads.append(data)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 100}})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(side_effect=mock_send)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    # 1. Test /leaderboard command
    res = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/leaderboard"}
    })
    assert res == "Leaderboard handled."
    assert len(sent_payloads) == 1
    assert "Paper Arena Elo Leaderboard" in sent_payloads[0]["text"]
    assert "Ground (Thesis Anchor)" in sent_payloads[0]["text"]
    assert "1264" in sent_payloads[0]["text"]

    # 2. Test button tap: 🏆 Elo Leaderboard
    sent_payloads.clear()
    res_btn = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "🏆 Elo Leaderboard"}
    })
    assert res_btn == "Leaderboard handled."
    assert len(sent_payloads) == 1
    assert "Paper Arena Elo Leaderboard" in sent_payloads[0]["text"]


@pytest.mark.asyncio
@respx.mock
async def test_telegram_fight_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock

    from thesisclaw.arena.models import MergedVerdict

    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    # Mock run_fight to return a verdict
    mv = MergedVerdict(
        fight_id="fight-mock",
        winner="fighter_a",
        swap_agreement=0.9,
        final_scores={"fighter_a": 4.5, "fighter_b": 3.5},
        ranked_ideas=["idea_1"],
        all_entries_verified_ratio=1.0,
        struck_count=0,
        upheld_count=3,
    )
    monkeypatch.setattr("thesisclaw.arena.graph.run_fight", AsyncMock(return_value=mv))

    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def mock_send(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        sent_payloads.append(data)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 101}})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(side_effect=mock_send)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    # Test /fight with specific paper
    res = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/fight 2608.12345"}
    })
    assert "queued" in res
    assert len(sent_payloads) >= 1
    ack = sent_payloads[0]["text"]
    assert "Paper Arena Fight Queued!" in ack
    assert "Ground Thesis 🆚 arXiv:2608.12345" in ack


@pytest.mark.asyncio
@respx.mock
async def test_telegram_verdict_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState, MergedVerdict

    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")
    record = FightRecord(
        fight_id="fight-v-test",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.12345"),
        state=FightState.DONE,
        merged_verdict=MergedVerdict(
            fight_id="fight-v-test",
            winner="fighter_a",
            swap_agreement=0.95,
            final_scores={"fighter_a": 4.6, "fighter_b": 3.7},
            ranked_ideas=["idea_alpha"],
            all_entries_verified_ratio=0.96,
            struck_count=0,
            upheld_count=4,
        ),
    )
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record if fid == "fight-v-test" else None)
    monkeypatch.setattr("thesisclaw.arena.memory.list_fights", lambda limit=1: [record])

    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []

    def mock_send(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        sent_payloads.append(data)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 102}})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(side_effect=mock_send)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    res = await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/verdict"}
    })
    assert res == "Verdict handled."
    assert len(sent_payloads) == 1
    assert "fight-v-test" in sent_payloads[0]["text"]
    assert "FIGHTER_A" in sent_payloads[0]["text"] or "Ground Thesis" in sent_payloads[0]["text"]


@pytest.mark.asyncio
async def test_telegram_chat_arena_intents(monkeypatch: pytest.MonkeyPatch) -> None:
    from thesisclaw.arena.models import EloEntry
    monkeypatch.setattr(
        "thesisclaw.arena.memory.get_leaderboard",
        lambda limit=10: [EloEntry(doc_id="ground", rating=1264.0, wins=3, fights=3)],
    )
    bot = TelegramBotClient(token="mock-token")
    # Test leaderboard intent
    resp_lb = await bot.chat_with_agent("who is winning the paper fights?", chat_id=123)
    assert "Paper Arena Elo Leaderboard" in resp_lb

    # Test fight intent
    resp_fight = await bot.chat_with_agent("start fight with a paper", chat_id=123)
    assert "Paper Arena Debates" in resp_fight
    assert "/fight" in resp_fight


@pytest.mark.asyncio
@respx.mock
async def test_telegram_registered_bot_commands() -> None:
    token = "mock-bot-token"
    payloads: list[dict[str, Any]] = []

    def mock_set_commands(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        payloads.append(data)
        return httpx.Response(200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/setMyCommands").mock(side_effect=mock_set_commands)

    bot = TelegramBotClient(token=token)
    ok = await bot.register_bot_commands()
    assert ok is True
    assert len(payloads) == 1
    cmd_names = [c["command"] for c in payloads[0]["commands"]]
    assert "fight" in cmd_names
    assert "leaderboard" in cmd_names


@pytest.mark.asyncio
@respx.mock
async def test_telegram_edit_message_text() -> None:
    token = "mock-bot-token"
    respx.post(f"https://api.telegram.org/bot{token}/editMessageText").respond(
        status_code=200,
        json={"ok": True, "result": {"message_id": 42, "text": "Updated content"}},
    )

    bot = TelegramBotClient(token=token)
    res = await bot.edit_message_text(chat_id=12345, message_id=42, text="Updated content")
    assert res.get("ok") is True
    assert res.get("result", {}).get("text") == "Updated content"


@pytest.mark.asyncio
@respx.mock
async def test_telegram_fight_similarity_rejection_updates_message(monkeypatch: pytest.MonkeyPatch) -> None:
    from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState

    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")

    # Mock run_fight to reject due to low similarity and invoke on_progress("rejected", ...)
    async def fake_run_fight(fighter_a, fighter_b, *, fight_id=None, token_cap=None, min_similarity=0.35, on_progress=None):
        reason = (
            "🚫 **Paper Arena Fight Ineligible (< 0.35 Gate)**\n\n"
            "• **Matchup:** Ground Thesis 🆚 arXiv:2608.99999\n"
            "• **Similarity Score:** `15%` (Required Minimum: `≥ 35%`)\n"
            "• **Reason:** This paper is out-of-scope."
        )
        if on_progress:
            await on_progress("rejected", reason)

    record = FightRecord(
        fight_id="fight-rej-test",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.99999"),
        state=FightState.REJECTED,
        error="Similarity score 0.15 is below threshold 0.35",
    )

    monkeypatch.setattr("thesisclaw.arena.graph.run_fight", fake_run_fight)
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record)

    token = "mock-bot-token"
    edit_payloads: list[dict[str, Any]] = []

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").respond(
        status_code=200, json={"ok": True, "result": {"message_id": 888}}
    )

    def mock_edit(request: httpx.Request) -> httpx.Response:
        edit_payloads.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/editMessageText").mock(side_effect=mock_edit)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/fight 2608.99999"}
    })

    # Wait briefly for background task
    import asyncio
    await asyncio.sleep(0.05)

    # editMessageText must have received the rejection card
    assert len(edit_payloads) >= 1
    rejection_card = edit_payloads[0]["text"]
    assert "Paper Arena Fight Ineligible (< 0.35 Gate)" in rejection_card
    assert "Similarity Score:" in rejection_card


@pytest.mark.asyncio
@respx.mock
async def test_telegram_fight_live_progress_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState, MergedVerdict

    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111")

    # Mock run_fight invoking on_progress for several debate stages
    async def fake_run_fight(fighter_a, fighter_b, *, fight_id=None, token_cap=None, min_similarity=0.35, on_progress=None):
        if on_progress:
            await on_progress("moderator_setup", "🔔 R0: Moderator framed focal questions")
            await on_progress("cross_exam", "⚔️ R2: Direct cross-examination complete")
            await on_progress("common_ground", "🤝 R3: Synthesizing common ground")
            await on_progress("judge_run_1", "⚖️ Judge: Dual Nemotron run 1 completed")
        return MergedVerdict(
            fight_id=fight_id or "fight-live",
            winner="fighter_a",
            swap_agreement=0.92,
            final_scores={"fighter_a": 4.5, "fighter_b": 3.8},
            ranked_ideas=["idea_alpha"],
            all_entries_verified_ratio=0.95,
            struck_count=0,
            upheld_count=5,
        )

    record = FightRecord(
        fight_id="fight-live",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.12345"),
        state=FightState.DONE,
    )

    monkeypatch.setattr("thesisclaw.arena.graph.run_fight", fake_run_fight)
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record)

    token = "mock-bot-token"
    sent_payloads: list[dict[str, Any]] = []
    edit_payloads: list[dict[str, Any]] = []

    def mock_send(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        sent_payloads.append(data)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 999}})

    def mock_edit(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content.decode("utf-8"))
        edit_payloads.append(data)
        return httpx.Response(200, json={"ok": True})

    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(side_effect=mock_send)
    respx.post(f"https://api.telegram.org/bot{token}/editMessageText").mock(side_effect=mock_edit)

    bot = TelegramBotClient(token=token)
    bot.seen_users.add(111)

    await bot.handle_update({
        "message": {"chat": {"id": 999}, "from": {"id": 111}, "text": "/fight 2608.12345"}
    })

    import asyncio
    await asyncio.sleep(0.05)

    # Initial message sent + final verdict message sent
    assert len(sent_payloads) >= 2
    assert "Paper Arena Fight Queued!" in sent_payloads[0]["text"]
    assert "Fight Verdict:" in sent_payloads[1]["text"]

    # In-place edits took place through rounds
    assert len(edit_payloads) >= 4
    # Check that Common Ground and Judge round were reported in edits
    all_edit_text = " ".join(e["text"] for e in edit_payloads)
    assert "common ground" in all_edit_text.lower() or "R3" in all_edit_text
    assert "judge" in all_edit_text.lower() or "Nemotron" in all_edit_text



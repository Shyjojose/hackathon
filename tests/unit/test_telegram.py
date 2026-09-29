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

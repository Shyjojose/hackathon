from __future__ import annotations

import pytest
import respx

from thesisclaw.telegram.bot import TelegramBotClient


def test_telegram_user_allowlist(monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.telegram_allowed_ids", "111,222")
    bot = TelegramBotClient(token="mock-token")
    assert bot.is_user_allowed(111) is True
    assert bot.is_user_allowed(222) is True
    assert bot.is_user_allowed(333) is False


@pytest.mark.asyncio
@respx.mock
async def test_telegram_send_message():
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
async def test_telegram_handle_update_commands(monkeypatch):
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

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.config.settings import settings
from thesisclaw.models.paper import VerdictEnum

logger = logging.getLogger(__name__)


class TelegramBotClient:
    """Async Telegram Bot client powered by httpx for lightweight interaction."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.orchestrator = ThesisOrchestrator()

    async def send_message(self, chat_id: int | str, text: str, parse_mode: str = "Markdown") -> dict[str, Any]:
        """Send message to a telegram chat."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; message dropped.")
            return {}

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                # Fallback to plain text if markdown parsing fails
                payload["parse_mode"] = ""
                resp = await client.post(url, json=payload)
            return resp.json() if resp.status_code == 200 else {}

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user_id is in the configured allowlist."""
        allowed = settings.get_allowed_telegram_ids()
        # If no allowlist is configured in dev, log warning but allow
        if not allowed:
            logger.warning("TELEGRAM_ALLOWED_IDS is empty; allowlisting is open in dev mode.")
            return True
        return user_id in allowed

    async def handle_update(self, update: dict[str, Any]) -> str:
        """Process an incoming Telegram update payload."""
        message = update.get("message", {})
        from_user = message.get("from", {})
        user_id = from_user.get("id", 0)
        chat_id = message.get("chat", {}).get("id", 0)
        text = message.get("text", "").strip()

        if not text or not chat_id:
            return "No text in update."

        if not self.is_user_allowed(user_id):
            await self.send_message(chat_id, "⛔ Access denied. Your User ID is not allowlisted.")
            return "Access denied."

        # Command /start
        if text.startswith("/start"):
            msg = (
                "👋 **Welcome to ThesisClaw!**\n\n"
                "I am your autonomous research assistant monitoring academic literature for your "
                "Raspberry Pi 5 Edge AI thesis.\n\n"
                "**Commands:**\n"
                "• Send any arXiv link to evaluate it against your thesis\n"
                "• `/briefing` — Get the latest literature scan summary\n"
                "• `/status` — View agent status and processed paper counts"
            )
            await self.send_message(chat_id, msg)
            return "Start handled."

        # Command /status
        if text.startswith("/status"):
            msg = (
                "⚙️ **ThesisClaw Agent Status**\n\n"
                f"• **Thesis Area:** {settings.resolve_memory_path().name}\n"
                f"• **Checkpoints DB:** `{settings.checkpoints_dir}/thesisclaw.sqlite3`\n"
                "• **Worker:** Deep Agents subagents active\n"
                "• **Status:** Running & ready"
            )
            await self.send_message(chat_id, msg)
            return "Status handled."

        # Command /briefing
        if text.startswith("/briefing"):
            briefing = await self.orchestrator.run_batch_evaluation([])
            await self.send_message(chat_id, briefing.telegram_briefing)
            return "Briefing handled."

        # Check if text contains an arXiv link
        if "arxiv.org" in text or "arxiv:" in text.lower():
            await self.send_message(chat_id, "🔍 Analyzing paper against your thesis claim... Please wait.")
            try:
                res = await self.orchestrator.evaluate_single_paper(text)
                v = res["verdict"]
                paper = res["paper"]

                badge = {
                    VerdictEnum.SUPPORT: "🟢 **[SUPPORTS THESIS]**",
                    VerdictEnum.EXTEND: "🟡 **[EXTENDS THESIS]**",
                    VerdictEnum.THREATEN: "🔴 **[THREATENS THESIS - SCOOP WARNING]**",
                    VerdictEnum.IRRELEVANT: "⚪ **[IRRELEVANT]**",
                }.get(v.verdict, "ℹ️")

                reply_parts = [
                    f"{badge}\n**{paper.title}** (arXiv:{paper.arxiv_id})\n",
                    f"**Why:** {v.reason}\n",
                ]
                if v.direct_quote:
                    reply_parts.append(f"**Direct Quote:**\n> \"{v.direct_quote}\"\n")

                if res.get("pathfinder"):
                    reply_parts.append(
                        f"🧪 **Next Experiment:**\n{res['pathfinder'].next_experiment}\n\n"
                        f"📝 **Citable APA Paragraph:**\n_{res['pathfinder'].citable_paragraph}_\n"
                    )

                # Generate interactive educational webpage and forward link
                try:
                    from thesisclaw.site_builder.pages import build_paper_page

                    build_paper_page(paper, v, res.get("pathfinder"))
                    domain = (
                        settings.mcp_tunnel_domain.strip()
                        if settings.mcp_tunnel_domain.strip()
                        else f"http://{settings.mcp_host}:{settings.mcp_port}"
                    )
                    page_url = f"{domain}/papers/{paper.arxiv_id}" if domain.startswith("http") else f"https://{domain}/papers/{paper.arxiv_id}"
                    reply_parts.append(f"🌐 **Interactive Educational Page:**\n{page_url}")
                except Exception as page_exc:  # noqa: BLE001
                    logger.warning("Could not generate paper webpage: %s", page_exc)

                await self.send_message(chat_id, "\n".join(reply_parts))
                return "Paper evaluated."
            except Exception as exc:  # noqa: BLE001
                await self.send_message(chat_id, f"❌ Evaluation failed: {exc}")
                return f"Error: {exc}"

        # Otherwise treated as research note
        await self.send_message(chat_id, f"📝 Note recorded: \"{text[:50]}...\"")
        return "Note recorded."


async def run_telegram_polling(poll_interval: float = 2.0) -> None:
    """Long-polling runner for receiving updates without webhooks."""
    bot = TelegramBotClient()
    if not bot.token:
        logger.error("TELEGRAM_BOT_TOKEN not configured in .env.")
        print("\n❌ Error: TELEGRAM_BOT_TOKEN is not set in .env.")
        print("Please add your Telegram bot token from @BotFather into .env and try again.\n")
        return

    logger.info("Starting Telegram long polling for ThesisClaw...")
    print("\n🤖 ThesisClaw Telegram Bot is ACTIVE and listening!")
    print(f"Allowlisted User IDs: {settings.get_allowed_telegram_ids() or 'ALL (Open Dev Mode)'}")
    print("Press Ctrl+C to stop.\n")

    offset = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                url = f"{bot.base_url}/getUpdates?offset={offset}&timeout=20"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await bot.handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Polling error: %s", exc)
                await asyncio.sleep(poll_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    try:
        asyncio.run(run_telegram_polling())
    except KeyboardInterrupt:
        print("\nTelegram bot stopped by user.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import logging
import socket
import sqlite3
from pathlib import Path
from typing import Any

import anyio
import httpx

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.agent.subagents import get_llm_client
from thesisclaw.config.settings import settings
from thesisclaw.models.paper import VerdictEnum

logger = logging.getLogger(__name__)


def get_lan_ip() -> str:
    """Detect local network IP for mobile device access on Wi-Fi."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except Exception:  # noqa: BLE001
        return "127.0.0.1"


class TelegramBotClient:
    """Async Telegram Bot client powered by httpx for lightweight interaction."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.orchestrator = ThesisOrchestrator()
        self.seen_users: set[int] = set()
        self.chat_history: dict[int, list[dict[str, str]]] = {}

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send message to a telegram chat with optional inline or reply keyboard."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; message dropped.")
            return {}

        url = f"{self.base_url}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                # Fallback to plain text if markdown parsing fails
                payload["parse_mode"] = ""
                resp = await client.post(url, json=payload)
            return resp.json() if resp.status_code == 200 else {}

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Edit an existing message in a telegram chat with optional inline keyboard."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; message edit dropped.")
            return {}

        url = f"{self.base_url}/editMessageText"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                payload["parse_mode"] = ""
                resp = await client.post(url, json=payload)
            return resp.json() if resp.status_code == 200 else {}

    async def send_document(
        self,
        chat_id: int | str,
        file_path: str | Any,
        caption: str = "",
    ) -> dict[str, Any]:
        """Send a local file (e.g. interactive educational index.html) to a telegram chat."""
        path = Path(file_path)
        if not path.exists():
            logger.warning("File %s does not exist; cannot send document.", file_path)
            return {}

        url = f"{self.base_url}/sendDocument"
        async with await anyio.open_file(path, "rb") as f:
            file_bytes = await f.read()

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"document": (path.name, file_bytes, "text/html")}
            data = {"chat_id": str(chat_id), "caption": caption}
            resp = await client.post(url, data=data, files=files)
            return resp.json() if resp.status_code == 200 else {}

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user_id is in the configured allowlist."""
        allowed = settings.get_allowed_telegram_ids()
        # If no allowlist is configured in dev, log warning but allow
        if not allowed:
            logger.warning("TELEGRAM_ALLOWED_IDS is empty; allowlisting is open in dev mode.")
            return True
        return user_id in allowed

    def get_base_page_url(self) -> str:
        """Resolve current reachable URL for paper dashboards (tunnel or mobile Wi-Fi LAN IP)."""
        raw_domain = settings.mcp_tunnel_domain.split("#")[0].strip()
        if raw_domain:
            if not raw_domain.startswith(("http://", "https://")):
                return f"https://{raw_domain}"
            return raw_domain
        host = settings.mcp_host
        if host in ("127.0.0.1", "0.0.0.0", "localhost"):
            lan_ip = get_lan_ip()
            return f"http://{lan_ip}:{settings.mcp_port}"
        return f"http://{host}:{settings.mcp_port}"

    def get_welcome_card(self) -> tuple[str, dict[str, Any]]:
        """Return the first-message directory with all communication tags and quick reply markup."""
        lan_ip = get_lan_ip()
        msg = (
            "👋 **Welcome to ThesisClaw!**\n\n"
            "I am your autonomous research partner monitoring academic literature for your "
            "Raspberry Pi 5 Edge AI thesis.\n\n"
            "🏷️ **Communication Tags & Commands:**\n"
            "• `/research [topic]` — Autonomous scout discovers & evaluates 3 brand new unreviewed papers\n"
            "• `/history` — Full chronological log of all reviewed research papers\n"
            "• `/similar` — List of papers found similar / aligned with thesis\n"
            "• `/discarded` — List of discarded / out-of-scope papers with rejection reasons\n"
            "• `/links` — View count of processed papers & direct HTML dashboard links\n"
            "• `/papers` — Open the 4-tab interactive literature dashboard gallery\n"
            "• `/briefing` — Generate or fetch the latest literature scan briefing\n"
            "• `/status` — View agent health, active models, and pipeline metrics\n"
            "• `/thesis` — View active thesis claims, hypotheses & benchmark targets\n"
            "• `/fight [arxiv_id]` — Run an adversarial Paper Arena debate (Ground vs paper or paper vs paper)\n"
            "• `/leaderboard` — View current Elo ratings & adversarial debate standings\n"
            "• `/notes` — Access the human approval gate for code & experiment proposals\n"
            "• `/help` — Display this communication guide\n\n"
            "💬 **Ways to Interact:**\n"
            "• **Research Scout:** Tap `🔍 Research 3 New Papers` or run `/research` to discover and evaluate novel arXiv literature on demand.\n"
            "• **Paper Arena:** Tap `⚔️ Paper Fight` or run `/fight [arxiv_id]` to trigger a 4-round moderated debate against the thesis.\n"
            "• **Leaderboard:** Tap `🏆 Elo Leaderboard` to inspect live chess-style paper rankings.\n"
            "• **arXiv Links:** Paste any arXiv link (e.g. `https://arxiv.org/abs/2410.05229`) "
            "to run an instant deep analysis, generate a 4-tab dashboard, and receive the offline `.html` document.\n"
            "• **AI Research Chat:** Ask questions like *'How many papers have been reviewed?'*, "
            "*'Who is winning the paper fights?'*, or *'Find 3 new papers'*.\n"
            "• **Voice Companion:** Speak with the XiaoZhi ESP32-S3 voice bridge for hands-free queries.\n"
            "• **Approval Gate:** Review and approve proposed experiments at `/notes`.\n\n"
            f"📱 **Mobile Browser on Wi-Fi:** Open `http://{lan_ip}:{settings.mcp_port}/papers/`\n\n"
            "Tap any quick button below or type a message to start!"
        )
        reply_markup = {
            "keyboard": [
                [{"text": "🔍 Research 3 New Papers"}, {"text": "📚 Review History"}],
                [{"text": "⚔️ Paper Fight"}, {"text": "🏆 Elo Leaderboard"}],
                [{"text": "🟢 Similar Papers"}, {"text": "🚫 Discarded Papers"}],
                [{"text": "🔗 Paper Links"}, {"text": "📰 Briefing"}],
                [{"text": "🎯 View Thesis"}, {"text": "⚙️ Agent Status"}],
                [{"text": "🔬 Approval Gate"}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }
        return msg, reply_markup

    def get_review_history(self) -> list[dict[str, Any]]:
        """Fetch all processed papers from SQLite checkpoint DB ordered by date."""
        db_file = Path(f"{settings.checkpoints_dir}/thesisclaw.sqlite3")
        if not db_file.exists():
            return []
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT arxiv_id, title, verdict, confidence, reason, backed_ratio, processed_at "
                    "FROM processed_papers ORDER BY processed_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]
            except sqlite3.OperationalError:
                return []

    def get_discarded_papers(self) -> list[dict[str, Any]]:
        """Fetch all papers discarded / deemed irrelevant to the thesis."""
        return [
            p
            for p in self.get_review_history()
            if str(p.get("verdict", "")).lower() == "irrelevant"
        ]

    def get_similar_papers(self) -> list[dict[str, Any]]:
        """Fetch all papers that support, extend, or threaten the thesis."""
        return [
            p
            for p in self.get_review_history()
            if str(p.get("verdict", "")).lower() in ("support", "extend", "threaten")
        ]

    def get_processed_papers_summary(self, limit: int = 10) -> dict[str, Any]:
        """Fetch total count, verdict breakdown, and recent papers from SQLite checkpoint DB."""
        history = self.get_review_history()
        total_papers = len(history)
        verdicts: dict[str, int] = {"support": 0, "extend": 0, "threaten": 0, "irrelevant": 0}
        for r in history:
            v_key = str(r.get("verdict", "")).lower()
            verdicts[v_key] = verdicts.get(v_key, 0) + 1

        return {
            "total": total_papers,
            "verdicts": verdicts,
            "recent": history[:limit],
        }

    def format_history_message(self) -> str:
        """Format full chronological review history."""
        history = self.get_review_history()
        if not history:
            return "📚 **Review History:** No research papers evaluated yet."

        total = len(history)
        support_cnt = sum(1 for p in history if str(p.get("verdict", "")).lower() == "support")
        extend_cnt = sum(1 for p in history if str(p.get("verdict", "")).lower() == "extend")
        threaten_cnt = sum(1 for p in history if str(p.get("verdict", "")).lower() == "threaten")
        discarded_cnt = sum(1 for p in history if str(p.get("verdict", "")).lower() == "irrelevant")

        lines = [
            f"📚 **ThesisClaw Literature Review History ({total} Total Papers)**\n",
            f"• 🟢 **Similar / Supporting:** `{support_cnt}`",
            f"• 🟡 **Extending Claims:** `{extend_cnt}`",
            f"• 🔴 **Threatening Claims:** `{threaten_cnt}`",
            f"• ⚪ **Discarded / Out-of-Scope:** `{discarded_cnt}`\n",
            "**Chronological Review Log:**",
        ]

        base_url = self.get_base_page_url()
        for i, p in enumerate(history, 1):
            aid = p["arxiv_id"]
            verd = str(p.get("verdict", "")).lower()
            badge = {
                "support": "🟢 [SUPPORTS]",
                "extend": "🟡 [EXTENDS]",
                "threaten": "🔴 [THREATENS]",
                "irrelevant": "⚪ [DISCARDED]",
            }.get(verd, "ℹ️")
            title = p.get("title", f"arXiv:{aid}")
            reason = p.get("reason", "No reason recorded.")
            lines.append(f"{i}. {badge} **{title}** (arXiv:{aid})\n   _Reason:_ {reason}")
            if verd != "irrelevant":
                lines.append(f"   🔗 {base_url}/papers/{aid}/")

        return "\n".join(lines)

    def format_discarded_message(self) -> str:
        """Format list of discarded / irrelevant papers with reasons."""
        discarded = self.get_discarded_papers()
        if not discarded:
            return "⚪ **Discarded Papers:** None discarded so far. All evaluated papers were thesis-relevant."

        lines = [
            f"🚫 **Discarded / Out-of-Scope Papers ({len(discarded)} total)**\n",
            "These papers were screened and discarded because they fall outside our Raspberry Pi 5 Edge AI thesis boundaries:\n",
        ]
        for i, p in enumerate(discarded, 1):
            aid = p["arxiv_id"]
            title = p.get("title", f"arXiv:{aid}")
            reason = p.get("reason", "Irrelevant to thesis claim.")
            lines.append(f"{i}. ⚪ **{title}** (arXiv:{aid})\n   • **Why Discarded:** {reason}")

        return "\n".join(lines)

    def format_similar_message(self) -> tuple[str, dict[str, Any] | None]:
        """Format list of similar / thesis-aligned papers with interactive links."""
        similar = self.get_similar_papers()
        if not similar:
            return (
                "🟢 **Similar Papers:** No thesis-aligned papers found yet. Send an arXiv link to evaluate one!",
                None,
            )

        base_url = self.get_base_page_url()
        lines = [
            f"🟢 **Similar & Thesis-Aligned Research Papers ({len(similar)} total)**\n",
            "These papers validate, extend, or directly impact our edge ASR quantization claims:\n",
        ]

        inline_buttons: list[list[dict[str, Any]]] = []
        for i, p in enumerate(similar, 1):
            aid = p["arxiv_id"]
            title = p.get("title", f"arXiv:{aid}")
            verd = str(p.get("verdict", "")).lower()
            badge = {
                "support": "🟢 [SUPPORTS]",
                "extend": "🟡 [EXTENDS]",
                "threaten": "🔴 [THREATENS]",
            }.get(verd, "🟢")
            reason = p.get("reason", "Validates benchmark claims.")
            p_url = f"{base_url}/papers/{aid}/"
            lines.append(
                f"{i}. {badge} **{title}** (arXiv:{aid})\n   • **Finding:** {reason}\n   • 🔗 {p_url}"
            )

            if i <= 4:
                short_title = title[:24] + "..." if len(title) > 24 else title
                btn_text = f"{badge[:2]} {aid}: {short_title}"
                if base_url.startswith("https://"):
                    inline_buttons.append([{"text": btn_text, "web_app": {"url": p_url}}])
                else:
                    inline_buttons.append([{"text": btn_text, "url": p_url}])

        reply_markup = {"inline_keyboard": inline_buttons} if inline_buttons else None
        return "\n".join(lines), reply_markup

    def format_links_message(self) -> tuple[str, dict[str, Any] | None]:
        """Format processed papers count, breakdown, and direct HTML links."""
        summary = self.get_processed_papers_summary()
        total = summary["total"]
        verdicts = summary["verdicts"]
        recent = summary["recent"]
        base_url = self.get_base_page_url()
        lan_ip = get_lan_ip()

        lines = [
            "📚 **ThesisClaw Processed Research Papers & Links**\n",
            f"• **Total Evaluated Papers:** `{total}`",
            f"• 🟢 **Supports Thesis:** `{verdicts.get('support', 0)}`",
            f"• 🟡 **Extends Thesis:** `{verdicts.get('extend', 0)}`",
            f"• 🔴 **Threatens Thesis:** `{verdicts.get('threaten', 0)}`",
            f"• ⚪ **Irrelevant:** `{verdicts.get('irrelevant', 0)}`\n",
            f"🏛️ **Master Paper Gallery:**\n👉 {base_url}/papers/\n",
            f"📱 **Mobile LAN URL:** `http://{lan_ip}:{settings.mcp_port}/papers/`\n",
        ]

        inline_buttons: list[list[dict[str, Any]]] = []

        if base_url.startswith("https://"):
            inline_buttons.append([
                {
                    "text": "🏛️ Open Paper Gallery (In-App)",
                    "web_app": {"url": f"{base_url}/papers/"},
                },
                {"text": "🌐 Browser", "url": f"{base_url}/papers/"},
            ])
        else:
            inline_buttons.append(
                [{"text": "🏛️ Open Master Paper Gallery", "url": f"{base_url}/papers/"}]
            )

        if recent:
            lines.append("📄 **Interactive 4-Tab Paper Dashboards:**")
            for i, p in enumerate(recent[:5], 1):
                aid = p["arxiv_id"]
                title = p.get("title", f"Paper {aid}")
                verdict_badge = {
                    "support": "🟢",
                    "extend": "🟡",
                    "threaten": "🔴",
                    "irrelevant": "⚪",
                }.get(str(p.get("verdict", "")).lower(), "📄")
                p_url = f"{base_url}/papers/{aid}/"
                lines.append(f"{i}. {verdict_badge} **{title}**\n   🔗 {p_url}")

                if i <= 3:
                    short_title = title[:24] + "..." if len(title) > 24 else title
                    btn_text = f"{verdict_badge} {aid}: {short_title}"
                    if base_url.startswith("https://"):
                        inline_buttons.append([
                            {"text": f"📖 {btn_text}", "web_app": {"url": p_url}}
                        ])
                    else:
                        inline_buttons.append([{"text": f"🌐 {btn_text}", "url": p_url}])
        else:
            lines.append(
                "ℹ️ _No papers evaluated yet. Send an arXiv link to evaluate your first paper!_"
            )

        reply_markup = {"inline_keyboard": inline_buttons} if inline_buttons else None
        return "\n".join(lines), reply_markup

    def format_leaderboard_message(self, limit: int = 10) -> tuple[str, dict[str, Any] | None]:
        """Format the Paper Arena Elo leaderboard standings for Telegram chat."""
        from thesisclaw.arena.memory import get_leaderboard

        entries = get_leaderboard(limit=limit)
        base_url = self.get_base_page_url()
        lb_url = f"{base_url}/leaderboard"

        if not entries:
            msg = (
                "🏆 **Paper Arena Elo Leaderboard**\n\n"
                "ℹ️ _No arena fights recorded yet._\n\n"
                "Run `/fight` or tap `⚔️ Paper Fight` to start an adversarial debate against the thesis!"
            )
            return msg, None

        lines = [
            "🏆 **Paper Arena Elo Leaderboard**",
            "_Adversarial Research Debates • Elo Defended Against Newcomers_\n",
        ]
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        for i, e in enumerate(entries):
            rank_str = medals.get(i, f"#{i+1}")
            if e.doc_id == "ground":
                name = "🟢 **Ground (Thesis Anchor)**"
            else:
                name = f"📄 **arXiv:{e.doc_id}**"
            lines.append(
                f"{rank_str} {name} — `{round(e.rating)}` Elo\n"
                f"   └ Record: `{e.wins}W / {e.losses}L / {e.draws}D` ({e.fights} fights)"
            )

        lines.extend([
            "",
            f"🏛️ **Full Interactive Standings:**\n👉 {lb_url}",
        ])

        reply_markup = None
        if lb_url.startswith("https://"):
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "🏆 Open Leaderboard (In-App)", "web_app": {"url": lb_url}},
                        {"text": "🌐 Browser", "url": lb_url},
                    ]
                ]
            }
        else:
            reply_markup = {
                "inline_keyboard": [[{"text": "🏆 Open Leaderboard", "url": lb_url}]]
            }

        return "\n".join(lines), reply_markup

    async def handle_fight_request(self, chat_id: int, text: str) -> str:
        """
        Handle /fight command:
          - /fight                     -> Ground vs top similar paper from DB
          - /fight <arxiv_id>          -> Ground vs specific paper
          - /fight <id_a> <id_b>       -> Paper vs Paper
        """
        import uuid

        from thesisclaw.arena.docs import load_fighter_doc
        from thesisclaw.arena.memory import upsert_fight
        from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState
        from thesisclaw.arena.select import get_candidates_from_db, top_opponent

        parts = text.strip().split()
        args = parts[1:] if text.startswith("/fight") else []

        if len(args) == 0:
            # Auto: Ground vs most similar candidate in DB
            ground_doc = await load_fighter_doc("ground", "ground")
            candidates = get_candidates_from_db(settings.checkpoints_dir / "thesisclaw.sqlite3")
            best = top_opponent(ground_doc["text"], candidates)
            if best is None:
                await self.send_message(
                    chat_id,
                    "⚠️ **No Opponents Available:** No processed papers found in database for auto-matchmaking.\n"
                    "Run `/research` first or specify an arXiv ID: `/fight <arxiv_id>`.",
                )
                return "No auto opponent."
            fighter_a = Fighter(kind=FighterKind.GROUND, doc_id="ground")
            fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=best.doc_id)
        elif len(args) == 1:
            aid = args[0].replace("https://arxiv.org/abs/", "").replace("arXiv:", "").strip()
            fighter_a = Fighter(kind=FighterKind.GROUND, doc_id="ground")
            fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=aid)
        else:
            aid_a = args[0].replace("https://arxiv.org/abs/", "").replace("arXiv:", "").strip()
            aid_b = args[1].replace("https://arxiv.org/abs/", "").replace("arXiv:", "").strip()
            fighter_a = Fighter(kind=FighterKind.PAPER, doc_id=aid_a)
            fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=aid_b)

        fight_id = f"fight-{uuid.uuid4().hex[:8]}"
        record = FightRecord(fight_id=fight_id, fighter_a=fighter_a, fighter_b=fighter_b, state=FightState.QUEUED)
        upsert_fight(record)

        label_a = "Ground Thesis" if fighter_a.doc_id == "ground" else f"arXiv:{fighter_a.doc_id}"
        label_b = "Ground Thesis" if fighter_b.doc_id == "ground" else f"arXiv:{fighter_b.doc_id}"

        ack_msg = (
            f"⚔️ **Paper Arena Fight Queued!**\n\n"
            f"• **Matchup:** {label_a} 🆚 {label_b}\n"
            f"• **Fight ID:** `{fight_id}`\n\n"
            "⏳ _Checking thesis similarity gate (≥ 0.35) and framing debate questions..._"
        )
        sent = await self.send_message(chat_id, ack_msg)
        status_msg_id = sent.get("result", {}).get("message_id") if isinstance(sent, dict) else None

        # Launch fight in background task and notify upon completion
        asyncio.create_task(
            self._execute_and_notify_fight(chat_id, fighter_a, fighter_b, fight_id, status_msg_id)
        )
        return f"Fight {fight_id} queued."

    async def _execute_and_notify_fight(
        self,
        chat_id: int,
        fighter_a: Any,
        fighter_b: Any,
        fight_id: str,
        status_msg_id: int | None = None,
    ) -> None:
        """Run the fight graph in background and notify Telegram chat upon completion."""
        from thesisclaw.arena.graph import run_fight
        from thesisclaw.arena.memory import get_fight
        from thesisclaw.arena.models import FightState

        base_url = self.get_base_page_url()
        fight_url = f"{base_url}/fight/{fight_id}"

        label_a = "Ground Thesis" if fighter_a.doc_id == "ground" else f"arXiv:{fighter_a.doc_id}"
        label_b = "Ground Thesis" if fighter_b.doc_id == "ground" else f"arXiv:{fighter_b.doc_id}"

        round_updates: list[str] = []

        async def on_progress(step: str, message: str) -> None:
            if step == "rejected":
                if status_msg_id:
                    await self.edit_message_text(chat_id, status_msg_id, message)
                else:
                    await self.send_message(chat_id, message)
                return

            if message not in round_updates:
                round_updates.append(message)
                bullets = "\n".join(f"• {u}" for u in round_updates)
                live_text = (
                    f"⚔️ **Paper Arena Debate in Progress (`{fight_id}`)**\n\n"
                    f"• **Matchup:** {label_a} 🆚 {label_b}\n\n"
                    f"**Live Debate Feed:**\n{bullets}\n\n"
                    f"⏳ _Debate graph active..._"
                )
                if status_msg_id:
                    await self.edit_message_text(chat_id, status_msg_id, live_text)

        try:
            verdict = await run_fight(fighter_a, fighter_b, fight_id=fight_id, on_progress=on_progress)
            record = get_fight(fight_id)
            if not record:
                if status_msg_id:
                    await self.edit_message_text(
                        chat_id,
                        status_msg_id,
                        f"❌ **Fight Failed (`{fight_id}`):** Record not found. Please check logs.",
                    )
                else:
                    await self.send_message(
                        chat_id,
                        f"❌ **Fight Failed (`{fight_id}`):** Record not found. Please check logs.",
                    )
                return

            if record.state == FightState.REJECTED:
                return

            if not verdict or record.state == FightState.FAILED:
                err_detail = f"\nReason: {record.error}" if record.error else ""
                fail_msg = f"❌ **Fight Failed (`{fight_id}`):** Unable to complete debate.{err_detail}"
                if status_msg_id:
                    await self.edit_message_text(chat_id, status_msg_id, fail_msg)
                else:
                    await self.send_message(chat_id, fail_msg)
                return

            winner_name = "Draw 🤝"
            if verdict.winner == "fighter_a":
                winner_name = f"{label_a} 🏆"
            elif verdict.winner == "fighter_b":
                winner_name = f"{label_b} 🏆"

            score_a = verdict.final_scores.get("fighter_a", 0.0)
            score_b = verdict.final_scores.get("fighter_b", 0.0)
            verified_pct = round(verdict.all_entries_verified_ratio * 100)
            swap_pct = round(verdict.swap_agreement * 100)

            ideas_preview = ""
            if verdict.ranked_ideas:
                ideas_preview = f"\n💡 **Novel Ideas Discovered:** `{len(verdict.ranked_ideas)}` generated\n"

            # Finalize progress card
            if status_msg_id and round_updates:
                bullets = "\n".join(f"• {u}" for u in round_updates)
                done_feed = (
                    f"⚔️ **Paper Arena Debate Concluded (`{fight_id}`)**\n\n"
                    f"• **Matchup:** {label_a} 🆚 {label_b}\n\n"
                    f"**Completed Debate Feed:**\n{bullets}\n\n"
                    f"✅ _All rounds, verification, and dual judging finished!_"
                )
                await self.edit_message_text(chat_id, status_msg_id, done_feed)

            msg = (
                f"⚔️ **Fight Verdict: {label_a} vs {label_b}**\n\n"
                f"🏆 **Winner:** {winner_name}\n"
                f"📊 **Scores:** {label_a} `{score_a:.1f}/5` • {label_b} `{score_b:.1f}/5`\n"
                f"✅ **Verified Quotes:** `{verified_pct}%` verbatim backed\n"
                f"🔄 **Swap Symmetry Agreement:** `{swap_pct}%` consistent\n"
                f"{ideas_preview}\n"
                f"🌐 **Interactive 2-Column Fight Dashboard:**\n👉 {fight_url}"
            )

            reply_markup = None
            if fight_url.startswith("https://"):
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "⚔️ Open Fight Dashboard (In-App)", "web_app": {"url": fight_url}},
                            {"text": "🌐 Browser", "url": fight_url},
                        ]
                    ]
                }
            else:
                reply_markup = {
                    "inline_keyboard": [[{"text": "⚔️ Open Fight Dashboard", "url": fight_url}]]
                }

            await self.send_message(chat_id, msg, reply_markup=reply_markup)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error executing fight %s: %s", fight_id, exc)
            await self.send_message(chat_id, f"❌ **Error running fight `{fight_id}`:** {exc}")

    async def handle_verdict_request(self, chat_id: int, text: str) -> str:
        """Handle /verdict [fight_id] to view latest or specific fight result."""
        from thesisclaw.arena.memory import get_fight, list_fights

        parts = text.strip().split()
        fight_id = parts[1] if len(parts) > 1 else None

        if fight_id:
            record = get_fight(fight_id)
        else:
            fights = list_fights(limit=1)
            record = fights[0] if fights else None

        if not record or not record.merged_verdict:
            await self.send_message(
                chat_id,
                "ℹ️ **No Verdict Available:** No completed fight found. Run `/fight` to start one!",
            )
            return "No verdict."

        mv = record.merged_verdict
        base_url = self.get_base_page_url()
        fight_url = f"{base_url}/fight/{record.fight_id}"

        label_a = "Ground Thesis" if record.fighter_a.doc_id == "ground" else f"arXiv:{record.fighter_a.doc_id}"
        label_b = "Ground Thesis" if record.fighter_b.doc_id == "ground" else f"arXiv:{record.fighter_b.doc_id}"

        msg = (
            f"⚖️ **Latest Verdict: `{record.fight_id}`**\n\n"
            f"• **Matchup:** {label_a} vs {label_b}\n"
            f"• **Winner:** {mv.winner.upper()}\n"
            f"• **Scores:** {label_a} `{mv.final_scores.get('fighter_a', 0.0):.1f}/5` • {label_b} `{mv.final_scores.get('fighter_b', 0.0):.1f}/5`\n"
            f"• **Verified Quotes:** `{round(mv.all_entries_verified_ratio * 100)}%`\n"
            f"• **Swap Agreement:** `{round(mv.swap_agreement * 100)}%`\n\n"
            f"🔗 {fight_url}"
        )
        await self.send_message(chat_id, msg)
        return "Verdict handled."

    async def handle_research_request(self, chat_id: int, topic: str | None = None) -> str:
        """Execute autonomous Research Scout Subagent: discover 3 brand new papers and reply with similarity scores and links."""
        topic_desc = f" on '{topic}'" if topic else " matching thesis focus"
        await self.send_message(
            chat_id,
            f"🔍 **Research Scout Subagent Activated**\n"
            f"Scanning arXiv for 3 brand new, unreviewed research papers{topic_desc}... Please wait.",
        )

        try:
            from thesisclaw.agent.subagents import research_scout_subagent

            base_url = self.get_base_page_url()
            result = await research_scout_subagent(
                query=topic,
                limit=3,
                base_url=base_url,
            )

            if not result.papers:
                await self.send_message(
                    chat_id,
                    f"ℹ️ **No new papers discovered:** Scanned {result.total_scanned} candidate papers on arXiv, but all matching papers have already been evaluated!\n"
                    "Try specifying a different sub-topic with `/research [query]`.",
                )
                return "No new papers."

            msg_lines = [
                f"🎯 **Discovered {len(result.papers)} Brand New Research Papers!**",
                f"_(Scanned {result.total_scanned} candidates from arXiv, skipped all previously reviewed papers)_\n",
            ]

            inline_buttons = []
            for i, p in enumerate(result.papers, 1):
                badge = {
                    VerdictEnum.SUPPORT: "🟢 [SUPPORTS THESIS]",
                    VerdictEnum.EXTEND: "🟡 [EXTENDS THESIS]",
                    VerdictEnum.THREATEN: "🔴 [THREATENS THESIS]",
                    VerdictEnum.IRRELEVANT: "⚪ [IRRELEVANT]",
                }.get(p.verdict, "ℹ️")
                pct = round(p.similarity_score * 100)
                msg_lines.extend([
                    f"**{i}. {p.title}** (arXiv:{p.arxiv_id})",
                    f"• 🎯 **Similarity Score:** `{pct}%` (`{p.similarity_score:.2f}`)",
                    f"• 🏷️ **Verdict:** {badge}",
                    f"• 💡 **Reason:** _{p.reason}_",
                    f"• 📄 **arXiv:** {p.arxiv_url}",
                    f"• 🌐 **4-Tab Breakdown:** {p.dashboard_url}",
                    "",
                ])
                inline_buttons.append([
                    {"text": f"🌐 Read arXiv:{p.arxiv_id} Breakdown", "url": p.dashboard_url}
                ])

            msg_lines.append("Use `/history` to view your updated audit log or tap any paper breakdown link above!")

            reply_markup = {"inline_keyboard": inline_buttons} if inline_buttons else None
            await self.send_message(chat_id, "\n".join(msg_lines), reply_markup=reply_markup)

            # Send offline .html document attachments directly to chat
            for p in result.papers:
                doc_path = Path(f"site/public/papers/{p.arxiv_id}/index.html")
                if doc_path.exists():
                    try:
                        pct = round(p.similarity_score * 100)
                        await self.send_document(
                            chat_id,
                            doc_path,
                            caption=f"📄 Offline 4-Tab Breakdown (arXiv:{p.arxiv_id}) | Similarity: {pct}% | Verdict: {p.verdict.value.upper()}",
                        )
                    except Exception as doc_exc:  # noqa: BLE001
                        logger.debug("Failed sending document attachment for %s: %s", p.arxiv_id, doc_exc)

            return "Research handled."
        except Exception as exc:  # noqa: BLE001
            logger.error("Research Scout Subagent failed: %s", exc)
            await self.send_message(chat_id, f"❌ Research Scout Subagent encountered an error: {exc}")
            return f"Error: {exc}"

    def format_thesis_message(self) -> str:
        """Format active thesis claims, hypotheses, and benchmark targets."""
        path = settings.resolve_memory_path()
        return (
            "🎯 **Active Thesis Profile & Benchmark Targets**\n\n"
            "**Research Area:** Real-Time, Privacy-Preserving ASR on Raspberry Pi 5 (ARM Cortex-A76).\n"
            "**Target SLM:** Moonshine Tiny with symmetric INT4/INT8 PTQ & 128-bit ARM NEON SIMD.\n"
            "**Deployment:** Unprivileged Podman container, GDPR & EU AI Act Art. 50 compliant.\n\n"
            "**Verification Targets:**\n"
            "• RTF ≤ 0.20 on 10s audio chunks\n"
            "• WER degradation ≤ 6% relative to FP16\n"
            "• RAM working set ≤ 512 MB\n\n"
            f"📄 Memory stored in `{path.name}`."
        )

    async def chat_with_agent(self, user_text: str, chat_id: int) -> str:
        """Provide intelligent academic research responses grounded in thesis memory and review logs."""
        lower = user_text.lower()

        # 1. Direct intent recognition for review history, discarded papers, and similar papers
        if any(w in lower for w in ["how many papers", "paper count", "number of papers", "literature papers reviewed"]):
            summary = self.get_processed_papers_summary()
            discarded = len(self.get_discarded_papers())
            similar = len(self.get_similar_papers())
            return (
                f"📚 **Literature Review Summary:**\n"
                f"• Total Papers Reviewed: `{summary['total']}`\n"
                f"• 🟢 Similar / Thesis-Aligned: `{similar}`\n"
                f"• ⚪ Discarded / Out-of-Scope: `{discarded}`\n\n"
                "Use `/history` to view the full audit log, `/similar` for aligned papers, or `/discarded` for rejected papers!"
            )

        if any(w in lower for w in ["discarded", "rejected", "which papers did you discard", "why discarded"]):
            return self.format_discarded_message()

        if any(w in lower for w in ["which papers are similar", "similar papers", "aligned papers", "papers found similar"]):
            msg, _ = self.format_similar_message()
            return msg

        if any(w in lower for w in ["history", "review history", "reviews", "list all papers", "audit log"]):
            return self.format_history_message()

        if any(w in lower for w in ["paper links", "show papers", "list papers"]):
            msg, _ = self.format_links_message()
            return msg

        if any(w in lower for w in ["what is your thesis", "thesis topic", "thesis claim"]):
            return self.format_thesis_message()

        if any(w in lower for w in ["leaderboard", "ranking", "standings", "who is winning", "top papers", "elo"]):
            msg, _ = self.format_leaderboard_message()
            return msg

        if any(w in lower for w in ["start fight", "paper fight", "fight paper", "challenge paper", "paper arena"]):
            return (
                "⚔️ **Paper Arena Debates:**\n"
                "To trigger an adversarial debate between research papers and your thesis, run:\n"
                "• `/fight` — Auto-select highest similarity candidate from DB vs Ground\n"
                "• `/fight <arxiv_id>` — Match Ground against a specific paper\n"
                "• `/fight <id_a> <id_b>` — Match two papers against each other\n\n"
                "Or tap `⚔️ Paper Fight` on your quick keyboard!"
            )

        # 2. Grounded LLM Chat (ChatNVIDIA)
        llm = get_llm_client()
        if llm:
            try:
                from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

                memory_path = settings.resolve_memory_path()
                memory_text = ""
                if memory_path.exists():
                    memory_text = memory_path.read_text(encoding="utf-8")

                soul_path = Path("runtime/openclaw/workspace/SOUL.md")
                soul_text = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""

                history = self.get_review_history()
                discarded = self.get_discarded_papers()
                similar = self.get_similar_papers()
                discarded_items = [
                    f"arXiv:{p['arxiv_id']} ({p.get('reason', '')})" for p in discarded[:5]
                ]
                discarded_str = ", ".join(discarded_items)
                similar_items = [f"arXiv:{p['arxiv_id']} ({p['verdict']})" for p in similar[:5]]
                similar_str = ", ".join(similar_items)

                review_context = (
                    "## Live Database Review State:\n"
                    f"- Total evaluated papers: {len(history)}\n"
                    f"- Discarded papers ({len(discarded)}): {discarded_str}\n"
                    f"- Similar papers ({len(similar)}): {similar_str}\n"
                )

                system_prompt = (
                    f"{soul_text}\n\n"
                    f"## Researcher Memory & Thesis Claims:\n{memory_text}\n\n"
                    f"{review_context}\n\n"
                    "Instructions: Answer concisely (under 600 chars if practical for edge displays), "
                    "intellectually honest, grounded strictly in the thesis, literature review history, "
                    "and ARM Cortex-A76 / RPi5 constraints."
                )

                chat_hist = self.chat_history.get(chat_id, [])
                messages = [SystemMessage(content=system_prompt)]
                for msg in chat_hist[-6:]:
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg.get("content", "")))
                messages.append(HumanMessage(content=user_text))

                resp = await llm.ainvoke(messages)
                content = str(resp.content) if hasattr(resp, "content") else str(resp)

                if chat_id not in self.chat_history:
                    self.chat_history[chat_id] = []
                self.chat_history[chat_id].append({"role": "user", "content": user_text})
                self.chat_history[chat_id].append({"role": "assistant", "content": content})
                if len(self.chat_history[chat_id]) > 10:
                    self.chat_history[chat_id] = self.chat_history[chat_id][-10:]

                return content
            except Exception as exc:  # noqa: BLE001
                logger.debug("LLM chat invocation error: %s, falling back to rule-based.", exc)

        # 3. Rule-based / offline intelligent fallback
        if any(w in lower for w in ["quant", "int4", "int8", "ptq"]):
            return (
                "💡 **Quantization Strategy:**\n"
                "In ThesisClaw, symmetric INT4 Post-Training Quantization (PTQ) compresses Moonshine Tiny's "
                "weights to saturate the Cortex-A76 LPDDR4X bandwidth (~3.6 GB/s). Our benchmark target is "
                "RTF ≤ 0.20 with <6% relative WER degradation compared to FP16."
            )
        if any(w in lower for w in ["rpi", "pi", "raspberry", "hardware", "cpu", "arm"]):
            return (
                "⚙️ **Target Hardware Profile:**\n"
                "• Platform: Raspberry Pi 5 (Quad-Core ARM Cortex-A76 @ 2.4 GHz, 16GB RAM)\n"
                "• Acceleration: 128-bit ARM NEON SIMD integer matrix operations\n"
                "• Container: Unprivileged Podman with CPU affinity pinning."
            )
        if any(w in lower for w in ["privacy", "gdpr", "security", "law", "stgb"]):
            return (
                "🔒 **Privacy & Compliance:**\n"
                "All speech transcription executes strictly on-device with zero cloud telemetry, satisfying "
                "GDPR, StGB § 201, and EU AI Act Article 50. Audio frames are processed in-memory and destroyed."
            )
        if any(w in lower for w in ["moonshine", "model", "slm", "asr"]):
            return (
                "🎙️ **Moonshine Tiny Architecture:**\n"
                "Moonshine Tiny is our primary SLM candidate due to its localized sliding-window attention "
                "O(N × W), requiring substantially less memory footprint than vanilla Whisper on edge CPUs."
            )

        return (
            f"🤖 **ThesisClaw Research Partner:**\n"
            f"I noted: \"{user_text}\".\n\n"
            "I'm monitoring edge ASR literature for your Raspberry Pi 5 thesis. "
            "You can ask me about INT4 quantization, ARM NEON SIMD, or paste an arXiv link to evaluate!"
        )

    async def register_bot_commands(self) -> bool:
        """Register slash commands with Telegram Bot API."""
        if not self.token:
            return False
        url = f"{self.base_url}/setMyCommands"
        commands = [
            {"command": "start", "description": "Welcome guide & all communication tags"},
            {"command": "research", "description": "Scout & evaluate 3 brand new unreviewed papers"},
            {"command": "history", "description": "Full literature review history & counts"},
            {"command": "similar", "description": "List papers matching/extending thesis"},
            {"command": "discarded", "description": "List discarded papers with rejection reasons"},
            {"command": "links", "description": "Processed research papers count & HTML links"},
            {"command": "papers", "description": "Interactive 4-tab literature gallery"},
            {"command": "briefing", "description": "Latest literature scan briefing"},
            {"command": "status", "description": "Agent status & system health"},
            {"command": "thesis", "description": "Active thesis claims & benchmark targets"},
            {"command": "fight", "description": "Trigger an adversarial Paper Arena fight"},
            {"command": "leaderboard", "description": "Current Elo rankings & fight standings"},
            {"command": "notes", "description": "Human approval gate for experiments"},
            {"command": "help", "description": "Communication directory and how to interact"},
        ]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"commands": commands})
                return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed registering bot commands: %s", exc)
            return False

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

        # Check if this is the user's first message
        is_first_interaction = user_id not in self.seen_users
        if is_first_interaction:
            self.seen_users.add(user_id)

        # Handle greetings, /start, and /help
        if is_first_interaction or text.startswith(("/start", "/help")) or text.lower() in ["hi", "hello", "hey"]:
            msg, reply_markup = self.get_welcome_card()
            await self.send_message(chat_id, msg, reply_markup=reply_markup)
            if text.startswith(("/start", "/help")) or text.lower() in ["hi", "hello", "hey"]:
                return "Start handled."

        # Command /research or /scout or button tap or conversational triggers
        if (
            text.startswith(("/research", "/scout"))
            or text == "🔍 Research 3 New Papers"
            or any(
                phrase in text.lower()
                for phrase in [
                    "find 3 new papers",
                    "research new papers",
                    "find new papers",
                    "scout papers",
                    "research 3 papers",
                    "scout 3 papers",
                    "find papers for me",
                ]
            )
        ):
            topic = None
            if text.startswith(("/research ", "/scout ")):
                topic = text.split(" ", 1)[1].strip()
            return await self.handle_research_request(chat_id, topic=topic)

        # Command /history or /reviews or button tap
        if text.startswith(("/history", "/reviews")) or text == "📚 Review History":
            msg = self.format_history_message()
            await self.send_message(chat_id, msg)
            return "History handled."

        # Command /discarded or /rejected or button tap
        if text.startswith(("/discarded", "/rejected")) or text == "🚫 Discarded Papers":
            msg = self.format_discarded_message()
            await self.send_message(chat_id, msg)
            return "Discarded handled."

        # Command /similar or /relevant or button tap
        if text.startswith(("/similar", "/relevant")) or text == "🟢 Similar Papers":
            msg, reply_markup = self.format_similar_message()
            await self.send_message(chat_id, msg, reply_markup=reply_markup)
            return "Similar handled."

        # Command /links or button tap
        if text.startswith("/links") or text == "🔗 Paper Links":
            msg, reply_markup = self.format_links_message()
            await self.send_message(chat_id, msg, reply_markup=reply_markup)
            return "Links handled."

        # Command /papers or /gallery or button tap
        if text.startswith(("/papers", "/gallery")) or text == "📚 Paper Gallery":
            base_url = self.get_base_page_url()
            gallery_url = f"{base_url}/papers/"
            reply_markup = None
            if gallery_url.startswith("https://"):
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "🏛️ Open Paper Gallery (In-App)",
                                "web_app": {"url": gallery_url},
                            },
                            {"text": "🌐 Browser", "url": gallery_url},
                        ]
                    ]
                }
            else:
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🏛️ Open Master Paper Gallery", "url": gallery_url}]
                    ]
                }
            await self.send_message(
                chat_id,
                f"📚 **ThesisClaw Literature Gallery:**\n👉 {gallery_url}\n\nExplore interactive 4-tab dashboards for all evaluated papers.",
                reply_markup=reply_markup,
            )
            return "Papers gallery handled."

        # Command /thesis or button tap
        if text.startswith("/thesis") or text == "🎯 View Thesis":
            msg = self.format_thesis_message()
            await self.send_message(chat_id, msg)
            return "Thesis handled."

        # Command /notes or button tap
        if text.startswith(("/notes", "/approvals")) or text == "🔬 Approval Gate":
            base_url = self.get_base_page_url()
            notes_url = f"{base_url}/notes"
            reply_markup = {"inline_keyboard": [[{"text": "🔬 Open Approval Gate", "url": notes_url}]]}
            await self.send_message(
                chat_id,
                f"🔬 **Human Approval Gate:**\n👉 {notes_url}\n\nReview, inspect diffs, and approve experiment proposals before execution.",
                reply_markup=reply_markup,
            )
            return "Notes handled."

        # Command /status or button tap
        if text.startswith("/status") or text == "⚙️ Agent Status":
            summary = self.get_processed_papers_summary()
            msg = (
                "⚙️ **ThesisClaw Agent Status**\n\n"
                f"• **Thesis Area:** {settings.resolve_memory_path().name}\n"
                f"• **Total Evaluated Papers:** `{summary['total']}`\n"
                f"• **Checkpoints DB:** `{settings.checkpoints_dir}/thesisclaw.sqlite3`\n"
                "• **Worker:** Deep Agents subagents active\n"
                "• **Status:** Running & ready"
            )
            await self.send_message(chat_id, msg)
            return "Status handled."

        # Command /briefing or button tap
        if text.startswith("/briefing") or text in ["📰 Briefing", "📰 Morning Briefing"]:
            briefing = await self.orchestrator.run_batch_evaluation([])
            await self.send_message(chat_id, briefing.telegram_briefing)
            return "Briefing handled."

        # Command /leaderboard or /ranking or button tap
        if text.startswith(("/leaderboard", "/ranking", "/standings")) or text == "🏆 Elo Leaderboard":
            msg, reply_markup = self.format_leaderboard_message()
            await self.send_message(chat_id, msg, reply_markup=reply_markup)
            return "Leaderboard handled."

        # Command /fight or button tap
        if text.startswith("/fight") or text == "⚔️ Paper Fight":
            return await self.handle_fight_request(chat_id, text)

        # Command /verdict
        if text.startswith("/verdict"):
            return await self.handle_verdict_request(chat_id, text)

        # Check if text contains an arXiv link
        if "arxiv.org" in text or "arxiv:" in text.lower():
            await self.send_message(
                chat_id, "🔍 Analyzing paper against your thesis claim... Please wait."
            )
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
                reply_markup = None
                gen_file = None
                try:
                    from thesisclaw.site_builder.pages import build_paper_page

                    gen_file = build_paper_page(paper, v, res.get("pathfinder"))
                    domain = self.get_base_page_url()
                    page_url = f"{domain}/papers/{paper.arxiv_id}/"
                    reply_parts.append(f"🌐 **Interactive 4-Tab Breakdown:**\n{page_url}")

                    # Build inline keyboard for Telegram
                    if page_url.startswith("https://"):
                        reply_markup = {
                            "inline_keyboard": [
                                [
                                    {"text": "📖 Open Breakdown (In-App)", "web_app": {"url": page_url}},
                                    {"text": "🌐 Browser", "url": page_url},
                                ]
                            ]
                        }
                    else:
                        reply_markup = {
                            "inline_keyboard": [
                                [{"text": "🌐 Open in Browser", "url": page_url}]
                            ]
                        }
                except Exception as page_exc:  # noqa: BLE001
                    logger.warning("Could not generate paper webpage: %s", page_exc)

                await self.send_message(
                    chat_id, "\n".join(reply_parts), reply_markup=reply_markup
                )

                # Send offline document attachment directly to chat
                if gen_file and Path(gen_file).exists():
                    try:
                        await self.send_document(
                            chat_id,
                            gen_file,
                            caption=f"📄 Offline 4-Tab Breakdown (arXiv:{paper.arxiv_id}) with Flowchart, Chart.js & Alpine.js.",
                        )
                    except Exception as doc_exc:  # noqa: BLE001
                        logger.debug("Failed sending document attachment: %s", doc_exc)

                return "Paper evaluated."
            except Exception as exc:  # noqa: BLE001
                await self.send_message(chat_id, f"❌ Evaluation failed: {exc}")
                return f"Error: {exc}"

        # Explicit note recording
        if text.startswith("/note "):
            note_content = text[6:].strip()
            await self.send_message(chat_id, f"📝 Note recorded: \"{note_content[:60]}...\"")
            return "Note recorded."

        # Conversational AI Research Partner
        chat_reply = await self.chat_with_agent(text, chat_id)
        await self.send_message(chat_id, chat_reply)
        return "Chat handled."


async def run_telegram_polling(poll_interval: float = 2.0) -> None:
    """Long-polling runner for receiving updates without webhooks."""
    bot = TelegramBotClient()
    if not bot.token:
        logger.error("TELEGRAM_BOT_TOKEN not configured in .env.")
        print("\n❌ Error: TELEGRAM_BOT_TOKEN is not set in .env.")
        print("Please add your Telegram bot token from @BotFather into .env and try again.\n")
        return

    # Automatically register bot slash commands
    await bot.register_bot_commands()

    logger.info("Starting Telegram long polling for ThesisClaw...")
    print("\n🤖 ThesisClaw Telegram Bot is ACTIVE and listening!")
    print(f"Allowlisted User IDs: {settings.get_allowed_telegram_ids() or 'ALL (Open Dev Mode)'}")
    print(f"Mobile Reachable Base URL: {bot.get_base_page_url()}")
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
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    try:
        asyncio.run(run_telegram_polling())
    except KeyboardInterrupt:
        print("\nTelegram bot stopped by user.")


if __name__ == "__main__":
    main()

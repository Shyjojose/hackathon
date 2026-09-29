from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for ThesisClaw loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── NVIDIA Models & API ───────────────────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_inference_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    default_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    critic_model: str = "nvidia/nemotron-4-340b-instruct"
    prefilter_model: str = "meta/llama-3.1-8b-instruct"
    embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"

    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_allowed_ids: str = ""  # Comma-separated user IDs e.g. "12345678,87654321"

    # ── Model Context Protocol (MCP) ──────────────────────────────────────────
    mcp_bearer_token: str = "dev-mcp-token-thesisclaw"
    voice_mcp_bearer_token: str = "dev-voice-token-thesisclaw"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8080
    mcp_tunnel_domain: str = ""

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: str = ""
    github_repo: str = "Shyjojose/hackathon"

    # ── Lambda Labs ───────────────────────────────────────────────────────────
    lambda_api_key: str = ""

    # ── Storage & Agent Paths ─────────────────────────────────────────────────
    memory_root: str = "research/agent.md"
    projects_dir: str = "research/projects"
    checkpoints_dir: str = "checkpoints"

    # ── Execution Budget & Limits ─────────────────────────────────────────────
    orchestrator_token_budget: int = 200_000
    voice_reply_max_chars: int = 600
    mcp_max_message_bytes: int = 131_072  # 128 KiB

    def get_allowed_telegram_ids(self) -> set[int]:
        """Parse comma-separated telegram allowed IDs into integer set."""
        if not self.telegram_allowed_ids.strip():
            return set()
        ids = set()
        for piece in self.telegram_allowed_ids.split(","):
            piece = piece.strip()
            if piece.isdigit() or (piece.startswith("-") and piece[1:].isdigit()):
                ids.add(int(piece))
        return ids

    def resolve_memory_path(self) -> Path:
        """Return absolute or relative path to root agent memory."""
        return Path(self.memory_root)


settings = Settings()

from __future__ import annotations

from thesisclaw.config.settings import Settings


def test_settings_default_values():
    cfg = Settings(
        nvidia_api_key="nvapi-test-key",
        telegram_allowed_ids="123456, 789012",
        mcp_port=8080,
    )
    assert cfg.default_model == "nvidia/llama-3.1-nemotron-70b-instruct"
    assert cfg.critic_model == "nvidia/nemotron-4-340b-instruct"
    assert cfg.mcp_port == 8080
    assert cfg.get_allowed_telegram_ids() == {123456, 789012}


def test_settings_empty_allowed_ids():
    cfg = Settings(telegram_allowed_ids="")
    assert cfg.get_allowed_telegram_ids() == set()


def test_settings_memory_path_resolution():
    cfg = Settings(memory_root="research/agent.md")
    path = cfg.resolve_memory_path()
    assert str(path) == "research/agent.md"

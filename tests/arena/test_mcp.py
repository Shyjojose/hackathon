"""
Unit tests for Paper Arena MCP tools on /mcp surface.
Tests authentication, input handling, and output schemas.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from thesisclaw.arena.models import (
    Fighter,
    FighterKind,
    FightRecord,
    FightState,
    MergedVerdict,
)
from thesisclaw.config.settings import settings
from thesisclaw.mcp.main import app

client = TestClient(app)
auth_headers = {"Authorization": f"Bearer {settings.mcp_bearer_token}"}


def test_arena_mcp_auth_failure():
    # Calling arena tools without token should return 401
    resp = client.post("/mcp/tools/leaderboard")
    assert resp.status_code == 401


def test_leaderboard_tool_success():
    resp = client.post("/mcp/tools/leaderboard", headers=auth_headers, json={"limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "leaderboard" in data
    assert isinstance(data["leaderboard"], list)


def test_fight_status_tool_not_found():
    resp = client.post(
        "/mcp/tools/fight_status",
        headers=auth_headers,
        json={"fight_id": "nonexistent_fight_999"},
    )
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_fight_status_tool_success(monkeypatch):
    record = FightRecord(
        fight_id="fight-test1234",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.11111"),
        state=FightState.DONE,
    )
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record if fid == "fight-test1234" else None)

    resp = client.post(
        "/mcp/tools/fight_status",
        headers=auth_headers,
        json={"fight_id": "fight-test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fight_id"] == "fight-test1234"
    assert data["state"] == "done"
    assert data["fighter_a"] == "ground"
    assert data["fighter_b"] == "2608.11111"


def test_get_verdict_tool(monkeypatch):
    mv = MergedVerdict(
        fight_id="fight-test1234",
        winner="fighter_a",
        swap_agreement=0.9,
        final_scores={"fighter_a": 4.5, "fighter_b": 3.8},
        ranked_ideas=["idea_1"],
        all_entries_verified_ratio=0.95,
        struck_count=1,
        upheld_count=4,
    )
    record = FightRecord(
        fight_id="fight-test1234",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.11111"),
        state=FightState.DONE,
        merged_verdict=mv,
    )
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record)

    resp = client.post(
        "/mcp/tools/get_verdict",
        headers=auth_headers,
        json={"fight_id": "fight-test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["winner"] == "fighter_a"
    assert data["swap_agreement"] == 0.9
    assert data["verified_ratio"] == 0.95


def test_ask_paper_tool(monkeypatch):
    mock_doc = {
        "doc_id": "2608.11111",
        "text": "The Real-Time Factor (RTF) measured on Raspberry Pi 5 was 0.42 with INT4 quantization.",
        "sections": {"results": "RTF 0.42"},
    }
    monkeypatch.setattr(
        "thesisclaw.arena.docs.load_fighter_doc",
        AsyncMock(return_value=mock_doc),
    )

    resp = client.post(
        "/mcp/tools/ask_paper",
        headers=auth_headers,
        json={"doc_id": "2608.11111", "question": "What was the Real-Time Factor measured?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["doc_id"] == "2608.11111"
    assert "Real-Time Factor" in data["answer"]


def test_start_fight_tool(monkeypatch):
    # Patch run_fight to not actually run LLMs
    monkeypatch.setattr("thesisclaw.arena.graph.run_fight", AsyncMock(return_value=None))

    resp = client.post(
        "/mcp/tools/start_fight",
        headers=auth_headers,
        json={"a": "ground", "b": "2608.11111"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "fight_id" in data
    assert data["status"] == "queued"
    assert data["fighter_a"] == "ground"
    assert data["fighter_b"] == "2608.11111"

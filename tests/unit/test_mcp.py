from __future__ import annotations

import respx
from fastapi.testclient import TestClient

from thesisclaw.config.settings import settings
from thesisclaw.mcp.main import app


def test_mcp_auth_failure():
    client = TestClient(app)
    # Request without Authorization header
    resp = client.post("/mcp/tools/get_status")
    assert resp.status_code == 401

    # Request with invalid token
    resp = client.post("/mcp/tools/get_status", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401


def test_mcp_get_status_success():
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.mcp_bearer_token}"}
    resp = client.post("/mcp/tools/get_status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


def test_voice_mcp_get_status_success():
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.voice_mcp_bearer_token}"}
    resp = client.post("/voice-mcp/tools/get_status", headers=headers)
    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_voice_mcp_get_briefing():
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.voice_mcp_bearer_token}"}
    resp = client.post("/voice-mcp/tools/get_briefing", headers=headers, json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["length"] <= 600


@respx.mock
def test_mcp_analyze_paper():
    arxiv_id = "2608.12345"
    mock_txt = (
        "Title: Edge Speech Transcription\n\n"
        "Abstract\nBenchmarking on Raspberry Pi 5.\n\n"
        "Results\nAchieving RTF <= 0.5 with INT4."
    )
    respx.get(f"https://arxiv-txt.org/abs/{arxiv_id}").respond(
        status_code=200,
        text=mock_txt,
    )

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.mcp_bearer_token}"}
    resp = client.post(
        "/mcp/tools/analyze_paper",
        headers=headers,
        json={"url": f"https://arxiv.org/abs/{arxiv_id}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["arxiv_id"] == arxiv_id
    assert "verdict" in data


def test_mcp_start_fight_similarity_gate(monkeypatch, tmp_path):
    import thesisclaw.arena.memory as mem_mod

    monkeypatch.setattr(mem_mod, "FIGHTS_DIR", tmp_path / "fights")
    monkeypatch.setattr(mem_mod, "ARENA_DB", tmp_path / "fights" / "arena.db")
    mem_mod.init_arena_db()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.mcp_bearer_token}"}

    async def mock_load_docs(id_a, id_b):
        return {
            id_a: {"text": "Raspberry Pi edge speech recognition", "sections": {}},
            id_b: {"text": "Botany flora marine algae", "sections": {}},
        }

    monkeypatch.setattr("thesisclaw.arena.docs.load_fighter_docs", mock_load_docs)

    # Test rejected fight (< 0.35)
    monkeypatch.setattr("thesisclaw.arena.select.is_fight_eligible", lambda ta, tb, threshold=0.35: (False, 0.18))
    resp_rej = client.post(
        "/mcp/tools/start_fight",
        headers=headers,
        json={"a": "ground", "b": "2608.99999"},
    )
    assert resp_rej.status_code == 200
    data_rej = resp_rej.json()
    assert data_rej["status"] == "rejected"
    assert data_rej["similarity"] == 0.18
    assert "below the required" in data_rej["error"]

    # Test fight_status returns rejected
    resp_status = client.post(
        "/mcp/tools/fight_status",
        headers=headers,
        json={"fight_id": data_rej["fight_id"]},
    )
    assert resp_status.status_code == 200
    assert resp_status.json()["state"] == "rejected"

    # Test eligible fight (>= 0.35)
    monkeypatch.setattr("thesisclaw.arena.select.is_fight_eligible", lambda ta, tb, threshold=0.35: (True, 0.75))
    resp_elig = client.post(
        "/mcp/tools/start_fight",
        headers=headers,
        json={"a": "ground", "b": "2608.12345"},
    )
    assert resp_elig.status_code == 200
    data_elig = resp_elig.json()
    assert data_elig["status"] == "queued"
    assert data_elig["similarity"] == 0.75


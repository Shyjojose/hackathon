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

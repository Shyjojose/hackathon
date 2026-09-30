from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from thesisclaw.web.app import app


def test_web_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_web_stats_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE processed_papers (arxiv_id TEXT, verdict TEXT)")
        conn.execute("CREATE TABLE pending_approvals (job_id TEXT, status TEXT)")
        conn.execute("INSERT INTO processed_papers VALUES ('2404.123', 'support')")
        conn.execute("INSERT INTO pending_approvals VALUES ('appr-1', 'pending')")

    client = TestClient(app)
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_papers_evaluated"] == 1
    assert data["pending_approvals"] == 1


def test_web_notes_and_approval_flow(tmp_path, monkeypatch):
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE pending_approvals (job_id TEXT, arxiv_id TEXT, experiment TEXT, code_change_desc TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute("INSERT INTO pending_approvals VALUES ('appr-test', '2608.12345', 'Run INT4 benchmark', 'Add SIMD', 'pending', CURRENT_TIMESTAMP)")

    client = TestClient(app)
    # Check notes HTML view
    resp = client.get("/notes")
    assert resp.status_code == 200
    assert "2608.12345" in resp.text
    assert "Approve Experiment" in resp.text

    # Approve proposal
    post_resp = client.post("/approve/appr-test")
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "success"

    # Verify updated status
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM pending_approvals WHERE job_id = 'appr-test'")
        status = cur.fetchone()[0]
        assert status == "approved"


def test_web_papers_gallery():
    client = TestClient(app)
    # Test without trailing slash
    resp = client.get("/papers")
    assert resp.status_code == 200
    assert "Evaluated Literature Gallery" in resp.text

    # Test with trailing slash
    resp_slash = client.get("/papers/")
    assert resp_slash.status_code == 200
    assert "Evaluated Literature Gallery" in resp_slash.text


def test_web_fight_page(monkeypatch):
    client = TestClient(app)
    from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState
    record = FightRecord(
        fight_id="fight-web-01",
        fighter_a=Fighter(kind=FighterKind.GROUND, doc_id="ground"),
        fighter_b=Fighter(kind=FighterKind.PAPER, doc_id="2608.99999"),
        state=FightState.DONE,
    )
    monkeypatch.setattr("thesisclaw.arena.memory.get_fight", lambda fid: record if fid == "fight-web-01" else None)
    monkeypatch.setattr("thesisclaw.arena.memory.read_entries", lambda fid: [])

    resp = client.get("/fight/fight-web-01")
    assert resp.status_code == 200
    assert "fight-web-01" in resp.text
    assert "ground" in resp.text


def test_web_leaderboard(monkeypatch):
    client = TestClient(app)
    from thesisclaw.arena.models import EloEntry
    monkeypatch.setattr(
        "thesisclaw.arena.memory.get_leaderboard",
        lambda limit=50: [EloEntry(doc_id="ground", rating=1250.0, wins=2, fights=2)],
    )
    monkeypatch.setattr("thesisclaw.arena.memory.list_fights", lambda limit=10: [])

    resp = client.get("/leaderboard")
    assert resp.status_code == 200
    assert "Paper Arena Leaderboard" in resp.text
    assert "ground" in resp.text

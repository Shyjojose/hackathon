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

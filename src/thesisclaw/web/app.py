from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from thesisclaw.config.settings import settings

app = FastAPI(title="ThesisClaw Web Dashboard & Approval Gate")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"{settings.checkpoints_dir}/thesisclaw.sqlite3")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "online",
        "app": "ThesisClaw",
        "thesis_area": "Raspberry Pi 5 Edge AI Speech Transcription",
    }


@app.get("/papers/{arxiv_id}", response_class=HTMLResponse)
def view_paper_page(arxiv_id: str) -> str:
    """Serve the interactive educational webpage for an evaluated paper."""
    from pathlib import Path

    page_path = Path("site/public/papers") / f"{arxiv_id}.html"
    if page_path.exists():
        return page_path.read_text(encoding="utf-8")

    raise HTTPException(
        status_code=404,
        detail=f"Educational breakdown for paper arXiv:{arxiv_id} has not been generated yet.",
    )


@app.get("/stats")
def get_stats() -> dict[str, Any]:
    """Return live paper count and verdict statistics."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM processed_papers")
            total_papers = cur.fetchone()[0]

            cur.execute("SELECT verdict, COUNT(*) FROM processed_papers GROUP BY verdict")
            verdicts = dict(cur.fetchall())

            cur.execute("SELECT COUNT(*) FROM pending_approvals WHERE status = 'pending'")
            pending_count = cur.fetchone()[0]

        return {
            "total_papers_evaluated": total_papers,
            "verdicts": verdicts,
            "pending_approvals": pending_count,
            "status": "active",
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "total_papers_evaluated": 0}


@app.get("/notes", response_class=HTMLResponse)
def view_pending_approvals() -> str:
    """Human-in-the-loop dashboard to review pending experiments."""
    proposals = []
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT job_id, arxiv_id, experiment, code_change_desc, status FROM pending_approvals ORDER BY created_at DESC")
            proposals = cur.fetchall()
    except Exception:  # noqa: BLE001
        proposals = []

    rows = ""
    for p in proposals:
        btn = (
            f"<form action='/approve/{p['job_id']}' method='post' style='display:inline;'>"
            f"<button type='submit' style='background:#10b981;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;'>Approve Experiment</button>"
            f"</form>"
            if p["status"] == "pending"
            else "<span style='color:#10b981;font-weight:bold;'>Approved ✅</span>"
        )
        rows += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding:12px;"><b>{p['arxiv_id']}</b></td>
            <td style="padding:12px;">{p['experiment']}</td>
            <td style="padding:12px;"><code>{p['code_change_desc'] or 'None'}</code></td>
            <td style="padding:12px;">{btn}</td>
        </tr>
        """

    if not rows:
        rows = "<tr><td colspan='4' style='padding:20px;text-align:center;color:#6b7280;'>No pending experiment proposals.</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ThesisClaw — Human Approval Gate</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f9fafb; margin: 0; padding: 40px; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 24px; max-width: 900px; margin: auto; }}
            h1 {{ color: #111827; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #f3f4f6; padding: 12px; font-weight: 600; color: #374151; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔬 ThesisClaw Human-in-the-Loop Gate</h1>
            <p>Side-effecting actions and draft PR experiments strictly require human approval here before execution.</p>
            <table>
                <thead>
                    <tr>
                        <th>arXiv ID</th>
                        <th>Proposed Experiment</th>
                        <th>Code Action</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return html


@app.post("/approve/{job_id}")
def approve_proposal(job_id: str) -> dict[str, str]:
    """Approve a pending experiment proposal and unlock agent PR generation."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM pending_approvals WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Proposal job ID not found.")

            cur.execute("UPDATE pending_approvals SET status = 'approved' WHERE job_id = ?", (job_id,))
        return {"status": "success", "message": f"Proposal {job_id} approved by human."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

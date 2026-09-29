from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesisclaw.config.settings import settings


def generate_stats_json(output_path: str | Path = "site/public/stats.json") -> dict[str, Any]:
    """Generate stats.json for the public judge dashboard from the SQLite checkpoints."""
    db_file = Path(f"{settings.checkpoints_dir}/thesisclaw.sqlite3")
    total_papers = 0
    verdicts: dict[str, int] = {"support": 0, "extend": 0, "threaten": 0, "irrelevant": 0}
    recent_papers = []

    if db_file.exists():
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM processed_papers")
            row = cur.fetchone()
            total_papers = row[0] if row else 0

            cur.execute("SELECT verdict, COUNT(*) as cnt FROM processed_papers GROUP BY verdict")
            for r in cur.fetchall():
                verdicts[r["verdict"]] = r["cnt"]

            cur.execute("SELECT arxiv_id, title, verdict, reason, processed_at FROM processed_papers ORDER BY processed_at DESC LIMIT 10")
            for r in cur.fetchall():
                recent_papers.append(dict(r))

    stats_data = {
        "project": "ThesisClaw",
        "thesis_topic": "Real-Time Privacy-Preserving ASR on Raspberry Pi 5",
        "last_updated": datetime.now(UTC).isoformat(),
        "total_papers_evaluated": total_papers,
        "verdicts": verdicts,
        "recent_papers": recent_papers,
        "status": "active",
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(stats_data, f, indent=2)

    return stats_data

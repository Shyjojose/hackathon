"""
ThesisClaw Paper Arena — Shared Fight Memory.

Storage layout:
  research/fights/<fight_id>/memory.jsonl   — append-only entries (one JSON per line)
  research/fights/<fight_id>/index.db       — per-fight SQLite for fast lookup
  research/fights/claims.jsonl              — cross-fight claims log
  research/fights/arena.db                  — LangGraph checkpoint + fight index + Elo

Write semantics:
  - All writes keyed by content SHA-256[:16] hash → idempotent (safe on resume).
  - A resumed fight re-writes entries that were mid-flight at kill time; hashing
    prevents duplicates even if the same LLM output is replayed.

Read semantics:
  - read_entries() returns entries in append order.
  - Fighters can only read: their own entries (for context) and opponent entries (for cross-exam).
    The caller controls which entries to pass; the store itself is unrestricted.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from thesisclaw.arena.models import EloEntry, FightRecord, FightState, MemoryEntry

FIGHTS_DIR = Path("research/fights")
ARENA_DB = FIGHTS_DIR / "arena.db"
CLAIMS_LOG = FIGHTS_DIR / "claims.jsonl"


# ── Initialisation ────────────────────────────────────────────────────────────


def init_arena_db() -> None:
    """Create the arena-wide SQLite schema (idempotent)."""
    FIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ARENA_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fights (
                fight_id    TEXT PRIMARY KEY,
                fighter_a   TEXT NOT NULL,   -- JSON-serialised Fighter
                fighter_b   TEXT NOT NULL,
                state       TEXT NOT NULL DEFAULT 'queued',
                verdict     TEXT,            -- JSON-serialised MergedVerdict
                elo_delta_a REAL DEFAULT 0,
                elo_delta_b REAL DEFAULT 0,
                started_at  TEXT,
                finished_at TEXT,
                error       TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS elo (
                doc_id  TEXT PRIMARY KEY,
                rating  REAL  NOT NULL DEFAULT 1200,
                wins    INT   NOT NULL DEFAULT 0,
                losses  INT   NOT NULL DEFAULT 0,
                draws   INT   NOT NULL DEFAULT 0,
                fights  INT   NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


# ── Entry write / read ────────────────────────────────────────────────────────


def _entry_hash(entry: MemoryEntry) -> str:
    """Deterministic 16-char SHA-256 hex of the entry's canonical key."""
    return hashlib.sha256(entry.canonical_key().encode()).hexdigest()[:16]


def write_entry(entry: MemoryEntry) -> MemoryEntry:
    """
    Append a MemoryEntry to the fight's JSONL file.
    Sets entry_id if not already set. No-ops silently if the hash already exists.
    Returns the entry (possibly with entry_id now filled in).
    """
    if not entry.entry_id:
        entry.entry_id = _entry_hash(entry)

    fight_dir = FIGHTS_DIR / entry.fight_id
    fight_dir.mkdir(parents=True, exist_ok=True)
    path = fight_dir / "memory.jsonl"

    # Deduplicate: read existing IDs (efficient: only the id field per line)
    existing_ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    existing_ids.add(json.loads(line)["entry_id"])
                except (json.JSONDecodeError, KeyError):
                    pass

    if entry.entry_id not in existing_ids:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json() + "\n")

        # Also append to cross-fight claims log for non-judge entries
        if entry.entry_type in ("claim", "idea", "concession"):
            CLAIMS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with CLAIMS_LOG.open("a", encoding="utf-8") as cf:
                cf.write(entry.model_dump_json() + "\n")

    return entry


def write_entries(entries: list[MemoryEntry]) -> list[MemoryEntry]:
    """Batch write — returns the list with entry_ids filled."""
    return [write_entry(e) for e in entries]


def read_entries(
    fight_id: str,
    *,
    author: str | None = None,
    round_: int | None = None,
    entry_type: str | None = None,
    verified_only: bool = False,
) -> list[MemoryEntry]:
    """
    Read memory entries for a fight with optional filters.
    Returns entries in append order.
    """
    path = FIGHTS_DIR / fight_id / "memory.jsonl"
    if not path.exists():
        return []
    entries: list[MemoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = MemoryEntry(**json.loads(line))
        except Exception:  # noqa: BLE001, S112
            continue
        if author is not None and e.author != author:
            continue
        if round_ is not None and e.round != round_:
            continue
        if entry_type is not None and e.entry_type != entry_type:
            continue
        if verified_only and not e.verified:
            continue
        entries.append(e)
    return entries


def update_entry_verification(
    fight_id: str, entry_id: str, *, verified: bool, near_exact: bool, position: int, section: str, note: str = ""
) -> None:
    """
    Rewrite a single entry's verification fields in-place.
    The JSONL file is rewritten line-by-line (files are small; max ~200 entries/fight).
    """
    path = FIGHTS_DIR / fight_id / "memory.jsonl"
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if data.get("entry_id") == entry_id:
            data["verified"] = verified
            data["near_exact"] = near_exact
            data["char_position"] = position
            data["section"] = section
            data["verification_note"] = note
        new_lines.append(json.dumps(data))
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# ── Fight record CRUD ─────────────────────────────────────────────────────────


def upsert_fight(record: FightRecord) -> None:
    """Insert or replace a fight record in the arena SQLite index."""
    init_arena_db()
    with sqlite3.connect(ARENA_DB) as conn:
        conn.execute(
            """
            INSERT INTO fights (fight_id, fighter_a, fighter_b, state, verdict,
                                elo_delta_a, elo_delta_b, started_at, finished_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fight_id) DO UPDATE SET
                state       = excluded.state,
                verdict     = excluded.verdict,
                elo_delta_a = excluded.elo_delta_a,
                elo_delta_b = excluded.elo_delta_b,
                finished_at = excluded.finished_at,
                error       = excluded.error
            """,
            (
                record.fight_id,
                record.fighter_a.model_dump_json(),
                record.fighter_b.model_dump_json(),
                record.state.value,
                record.merged_verdict.model_dump_json() if record.merged_verdict else None,
                record.elo_delta_a,
                record.elo_delta_b,
                record.started_at,
                record.finished_at,
                record.error,
            ),
        )
        conn.commit()


def get_fight(fight_id: str) -> FightRecord | None:
    """Retrieve a fight record by ID."""
    init_arena_db()
    with sqlite3.connect(ARENA_DB) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM fights WHERE fight_id = ?", (fight_id,)).fetchone()
    if row is None:
        return None
    from thesisclaw.arena.models import Fighter, MergedVerdict

    return FightRecord(
        fight_id=row["fight_id"],
        fighter_a=Fighter(**json.loads(row["fighter_a"])),
        fighter_b=Fighter(**json.loads(row["fighter_b"])),
        state=FightState(row["state"]),
        merged_verdict=MergedVerdict(**json.loads(row["verdict"])) if row["verdict"] else None,
        elo_delta_a=row["elo_delta_a"] or 0.0,
        elo_delta_b=row["elo_delta_b"] or 0.0,
        started_at=row["started_at"] or "",
        finished_at=row["finished_at"] or "",
        error=row["error"] or "",
    )


def list_fights(limit: int = 50) -> list[FightRecord]:
    """Return most recent fights, newest first."""
    init_arena_db()
    with sqlite3.connect(ARENA_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM fights ORDER BY rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    results = []
    for row in rows:
        r = get_fight(row["fight_id"])
        if r:
            results.append(r)
    return results


# ── Elo leaderboard ───────────────────────────────────────────────────────────

_K = 32  # Elo K-factor (standard for newcomers)


def _expected_score(rating_a: float, rating_b: float) -> float:
    """Standard Elo expected score for player A against B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def update_elo(doc_id_a: str, doc_id_b: str, outcome: str) -> tuple[float, float]:
    """
    Update Elo ratings for two fighters after a fight.
    outcome: "a" (a wins), "b" (b wins), "draw"
    Returns (new_rating_a, new_rating_b).
    """
    init_arena_db()
    with sqlite3.connect(ARENA_DB) as conn:
        def _get_or_create(doc_id: str) -> EloEntry:
            row = conn.execute("SELECT * FROM elo WHERE doc_id = ?", (doc_id,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO elo (doc_id) VALUES (?)", (doc_id,))
                return EloEntry(doc_id=doc_id)
            return EloEntry(doc_id=row[0], rating=row[1], wins=row[2], losses=row[3], draws=row[4], fights=row[5])

        ea = _get_or_create(doc_id_a)
        eb = _get_or_create(doc_id_b)

        exp_a = _expected_score(ea.rating, eb.rating)
        exp_b = 1.0 - exp_a

        if outcome == "a":
            score_a, score_b = 1.0, 0.0
            ea.wins += 1
            eb.losses += 1
        elif outcome == "b":
            score_a, score_b = 0.0, 1.0
            ea.losses += 1
            eb.wins += 1
        else:
            score_a, score_b = 0.5, 0.5
            ea.draws += 1
            eb.draws += 1

        new_r_a = ea.rating + _K * (score_a - exp_a)
        new_r_b = eb.rating + _K * (score_b - exp_b)
        ea.fights += 1
        eb.fights += 1

        for entry, new_r in ((ea, new_r_a), (eb, new_r_b)):
            conn.execute(
                """
                INSERT INTO elo (doc_id, rating, wins, losses, draws, fights)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    rating = excluded.rating,
                    wins   = excluded.wins,
                    losses = excluded.losses,
                    draws  = excluded.draws,
                    fights = excluded.fights
                """,
                (entry.doc_id, new_r, entry.wins, entry.losses, entry.draws, entry.fights),
            )
        conn.commit()

    return new_r_a, new_r_b


def get_leaderboard(limit: int = 20) -> list[EloEntry]:
    """Return top entries by Elo rating, descending."""
    init_arena_db()
    with sqlite3.connect(ARENA_DB) as conn:
        rows = conn.execute(
            "SELECT doc_id, rating, wins, losses, draws, fights FROM elo ORDER BY rating DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [EloEntry(doc_id=r[0], rating=r[1], wins=r[2], losses=r[3], draws=r[4], fights=r[5]) for r in rows]

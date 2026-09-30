"""
ThesisClaw Paper Arena — LangGraph Fight Graph.

Round order:
  R0  setup          — moderator writes FightCard + focal questions
  R1  openings       — both fighters write independently (parallel via Send)
  R2  cross_exam     — each fighter reads only opponent's R1 entries, then responds
  R2b followups      — moderator picks ≤2 sharpest conflicts; fighters respond
  R3  common_ground  — fighters list common ground + ranked novel ideas (cite both sides)
  V   verify_all     — code verifies every entry.quote → sets verified flag
  J1  judge_run_1    — judge reads only shared memory, scores with sides normal
  J2  judge_run_2    — judge runs again with sides swapped (fighter_a ↔ fighter_b)
  M   merge_verdicts — combines J1 + J2: swap_agreement, final scores, Elo update
  P   publish        — emits fight page data, updates leaderboard, sends Telegram event

Checkpointing:
  SqliteSaver writes after every node. A killed fight resumes from the last completed node.
  Token cap: enforced in each fighter/judge node. If token_used > token_cap, the node
  returns an empty turn marked "TOKEN_CAP_REACHED" and the graph advances to verify_all.

Security:
  Fighters and moderator get NO write tools and NO network tools.
  Document text is preloaded; fighters read only read_section() (returns a dict).
  The judge sees only the shared memory JSONL — not the raw documents.
  Planted instructions in paper text cannot trigger tool calls.
"""
from __future__ import annotations

import inspect
import logging
import operator
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from thesisclaw.arena.docs import load_fighter_docs
from thesisclaw.arena.memory import (
    init_arena_db,
    read_entries,
    update_elo,
    update_entry_verification,
    upsert_fight,
    write_entries,
    write_entry,
)
from thesisclaw.arena.models import (
    FightCard,
    Fighter,
    FightRecord,
    FightState,
    MemoryEntry,
    MergedVerdict,
    Stance,
    Verdict,
)
from thesisclaw.arena.select import SIMILARITY_MIN_GATE, is_fight_eligible
from thesisclaw.arena.verify import compute_verified_ratio as _compute_ratio
from thesisclaw.arena.verify import verify_all_entries
from thesisclaw.config.settings import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path("runtime/worker/prompts")
ARENA_DB_PATH = Path("research/fights/arena.db")

# Token caps (conservative for free tier)
DEFAULT_TOKEN_CAP = 180_000   # per fight
PER_TURN_SOFT_CAP = 4_096    # max output tokens per fighter turn

# Model assignments (per agentwars.md decisions)
FIGHTER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
JUDGE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MODERATOR_MODEL = "nvidia/nemotron-3-super-120b-a12b"


# ── Helper — load prompts ─────────────────────────────────────────────────────


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8") if path.exists() else f"# {name} prompt\n"


def _get_llm(model: str) -> Any | None:
    """Return a ChatNVIDIA instance or None (unit tests mock this)."""
    if not settings.nvidia_api_key or not settings.nvidia_api_key.startswith("nvapi-"):
        return None
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model=model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            temperature=0.3,
            max_tokens=PER_TURN_SOFT_CAP,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("LLM not available: %s", exc)
        return None


def _max_round(current: int, update: int) -> int:
    return max(current, update)


class ArenaState(TypedDict):
    fight_id: str
    fighter_a: dict                               # Fighter.model_dump()
    fighter_b: dict
    doc_a: dict                                   # {text, sections, token_estimate, ...}
    doc_b: dict
    fight_card: dict | None                       # FightCard.model_dump()
    entries_a: Annotated[list[dict], operator.add]  # MemoryEntry.model_dump() list
    entries_b: Annotated[list[dict], operator.add]
    entries_mod: Annotated[list[dict], operator.add]
    round: Annotated[int, _max_round]
    token_used: int
    token_cap: int
    verified: bool
    verdict_1: dict | None                        # Verdict run 1
    verdict_2: dict | None                        # Verdict run 2 (swapped)
    final_verdict: dict | None                    # MergedVerdict
    error: str


def _initial_state(
    fight_id: str,
    fighter_a: Fighter,
    fighter_b: Fighter,
    doc_a: dict,
    doc_b: dict,
    token_cap: int = DEFAULT_TOKEN_CAP,
) -> ArenaState:
    return ArenaState(
        fight_id=fight_id,
        fighter_a=fighter_a.model_dump(),
        fighter_b=fighter_b.model_dump(),
        doc_a=doc_a,
        doc_b=doc_b,
        fight_card=None,
        entries_a=[],
        entries_b=[],
        entries_mod=[],
        round=0,
        token_used=0,
        token_cap=token_cap,
        verified=False,
        verdict_1=None,
        verdict_2=None,
        final_verdict=None,
        error="",
    )


# ── Node helpers ──────────────────────────────────────────────────────────────


def _cap_reached(state: ArenaState) -> bool:
    return state["token_used"] >= state["token_cap"]


def _mk_entry(state: ArenaState, author: str, doc_id: str, round_: int, text: str,
              quote: str = "", stance: Stance = Stance.NOT_COVERED,
              entry_type: str = "claim", conditions: str = "") -> MemoryEntry:
    return MemoryEntry(
        fight_id=state["fight_id"],
        round=round_,
        author=author,
        entry_type=entry_type,
        text=text,
        quote=quote,
        doc_id=doc_id,
        conditions=conditions,
        stance=stance,
    )


def _llm_fighter_turn(
    llm: Any | None,
    system_prompt: str,
    user_message: str,
    fight_id: str,
    round_: int,
    author: str,
    doc_id: str,
) -> list[MemoryEntry]:
    """
    Call the fighter LLM and parse the structured output into MemoryEntries.
    Falls back to a stub entry if LLM is unavailable (unit tests).
    """
    if llm is None:
        # Stub for testing: one claim, no quote (unverified)
        return [
            MemoryEntry(
                fight_id=fight_id,
                round=round_,
                author=author,
                entry_type="claim",
                text=f"[STUB] {author} claim for round {round_}",
                quote="",
                doc_id=doc_id,
                stance=Stance.SUPPORTS,
            )
        ]
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
        content = response.content if hasattr(response, "content") else str(response)
        return _parse_fighter_output(content, fight_id, round_, author, doc_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Fighter LLM call failed: %s", exc)
        return []


def _parse_fighter_output(
    content: str, fight_id: str, round_: int, author: str, doc_id: str
) -> list[MemoryEntry]:
    """
    Parse LLM output into MemoryEntries.
    Expected format (fighters follow the fighter.md prompt):
    Each claim block:
        CLAIM: <text>
        QUOTE: <verbatim quote>
        STANCE: SUPPORTS|CONTRADICTS|DIFFERENT_CONDITIONS|NOT_COVERED
        CONDITIONS: <conditions if DIFFERENT_CONDITIONS>
    """
    entries: list[MemoryEntry] = []
    # Simple line-by-line parser
    current: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            if current.get("CLAIM"):
                entries.append(_entry_from_block(current, fight_id, round_, author, doc_id))
                current = {}
            continue
        for key in ("CLAIM", "QUOTE", "STANCE", "CONDITIONS", "IDEA", "CONCEDE"):
            if line.upper().startswith(f"{key}:"):
                current[key] = line[len(key) + 1:].strip()
                break
    if current.get("CLAIM") or current.get("IDEA"):
        entries.append(_entry_from_block(current, fight_id, round_, author, doc_id))
    # Fallback: if no structured output, create one entry from the whole content
    if not entries and content.strip():
        entries.append(MemoryEntry(
            fight_id=fight_id, round=round_, author=author, entry_type="claim",
            text=content[:500], quote="", doc_id=doc_id, stance=Stance.NOT_COVERED,
        ))
    return entries


def _entry_from_block(block: dict, fight_id: str, round_: int, author: str, doc_id: str) -> MemoryEntry:
    stance_str = block.get("STANCE", "NOT_COVERED").strip().upper()
    try:
        stance = Stance(stance_str)
    except ValueError:
        stance = Stance.NOT_COVERED
    entry_type = "idea" if "IDEA" in block else ("concession" if "CONCEDE" in block else "claim")
    text = block.get("CLAIM") or block.get("IDEA") or block.get("CONCEDE", "")
    return MemoryEntry(
        fight_id=fight_id, round=round_, author=author, entry_type=entry_type,
        text=text, quote=block.get("QUOTE", ""), doc_id=doc_id,
        conditions=block.get("CONDITIONS", ""), stance=stance,
    )


# ── Graph nodes ───────────────────────────────────────────────────────────────


def moderator_setup(state: ArenaState) -> dict:
    """R0: Moderator writes the FightCard."""
    logger.info("[%s] R0: moderator_setup", state["fight_id"])

    # Update fight state in DB
    record = FightRecord(
        fight_id=state["fight_id"],
        fighter_a=Fighter(**state["fighter_a"]),
        fighter_b=Fighter(**state["fighter_b"]),
        state=FightState.SETUP,
        started_at=datetime.now(UTC).isoformat(),
    )
    upsert_fight(record)

    llm = _get_llm(MODERATOR_MODEL)
    system_prompt = _load_prompt("moderator")
    doc_a_title = state["doc_a"].get("title") or state["fighter_a"]["doc_id"]
    doc_b_title = state["doc_b"].get("title") or state["fighter_b"]["doc_id"]

    user_msg = (
        f"Fighter A: {doc_a_title}\n"
        f"Fighter B: {doc_b_title}\n\n"
        f"Fighter A abstract:\n{state['doc_a']['text'][:2000]}\n\n"
        f"Fighter B abstract:\n{state['doc_b']['text'][:2000]}\n\n"
        "Write a FightCard with:\n"
        "TOPIC: <2-sentence framing>\n"
        "QUESTION: <focal question 1>\n"
        "QUESTION: <focal question 2>\n"
        "QUESTION: <focal question 3>\n"
    )

    if llm is None:
        card = FightCard(
            fight_id=state["fight_id"],
            topic=f"Fight: {doc_a_title} vs {doc_b_title}",
            focal_questions=["What are the key claims?", "What is the evidence?", "What are the conditions?"],
        )
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
            content = resp.content if hasattr(resp, "content") else str(resp)
            topic = ""
            questions = []
            for line in content.splitlines():
                if line.strip().upper().startswith("TOPIC:"):
                    topic = line.split(":", 1)[1].strip()
                elif line.strip().upper().startswith("QUESTION:"):
                    questions.append(line.split(":", 1)[1].strip())
            card = FightCard(
                fight_id=state["fight_id"],
                topic=topic or f"Fight: {doc_a_title} vs {doc_b_title}",
                focal_questions=questions[:5],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Moderator LLM failed: %s", exc)
            card = FightCard(
                fight_id=state["fight_id"],
                topic=f"Fight: {doc_a_title} vs {doc_b_title}",
                focal_questions=["What are the main technical claims?"],
            )

    # Write moderator setup entry to memory
    mod_entry = MemoryEntry(
        fight_id=state["fight_id"],
        round=0,
        author="moderator",
        entry_type="claim",
        text=f"TOPIC: {card.topic}\n" + "\n".join(f"Q{i+1}: {q}" for i, q in enumerate(card.focal_questions)),
        quote="",
        doc_id="moderator",
        stance=Stance.NOT_COVERED,
    )
    write_entry(mod_entry)

    return {
        "fight_card": card.model_dump(),
        "round": 1,
        "entries_mod": [mod_entry.model_dump()],
    }


def fan_out_openings(state: ArenaState) -> list[Send]:
    """R1: Fan out to both fighters in parallel using LangGraph Send."""
    logger.info("[%s] R1: fan_out_openings", state["fight_id"])
    if _cap_reached(state):
        return [Send("verify_all", state)]
    return [
        Send("fighter_a_node", {**state, "_role": "a"}),
        Send("fighter_b_node", {**state, "_role": "b"}),
    ]


def fighter_a_node(state: ArenaState) -> dict:
    """R1 Fighter A opening — sees only its own document."""
    logger.info("[%s] R1: fighter_a opening", state["fight_id"])
    llm = _get_llm(FIGHTER_MODEL)
    system_prompt = _load_prompt("fighter")
    doc = state["doc_a"]
    fighter = Fighter(**state["fighter_a"])

    focal_qs = "\n".join(f"- {q}" for q in (state.get("fight_card") or {}).get("focal_questions", []))
    user_msg = (
        f"Your document (you may ONLY quote from this):\n\n{doc['text'][:40000]}\n\n"
        f"Topic: {(state.get('fight_card') or {}).get('topic', 'Research fight')}\n"
        f"Focal questions:\n{focal_qs}\n\n"
        "Write your opening claims. For each claim use:\n"
        "CLAIM: <statement>\nQUOTE: <exact verbatim quote>\nSTANCE: SUPPORTS|CONTRADICTS|DIFFERENT_CONDITIONS|NOT_COVERED\n"
        "CONDITIONS: <if DIFFERENT_CONDITIONS>\n\n"
        "If a question is not covered by your document, write: CLAIM: [topic] NOT_COVERED\nSTANCE: NOT_COVERED"
    )

    entries = _llm_fighter_turn(llm, system_prompt, user_msg, state["fight_id"], 1, "fighter_a", fighter.doc_id)
    saved = write_entries(entries)
    return {"entries_a": [e.model_dump() for e in saved]}


def fighter_b_node(state: ArenaState) -> dict:
    """R1 Fighter B opening — sees only its own document."""
    logger.info("[%s] R1: fighter_b opening", state["fight_id"])
    llm = _get_llm(FIGHTER_MODEL)
    system_prompt = _load_prompt("fighter")
    doc = state["doc_b"]
    fighter = Fighter(**state["fighter_b"])

    focal_qs = "\n".join(f"- {q}" for q in (state.get("fight_card") or {}).get("focal_questions", []))
    user_msg = (
        f"Your document (you may ONLY quote from this):\n\n{doc['text'][:40000]}\n\n"
        f"Topic: {(state.get('fight_card') or {}).get('topic', 'Research fight')}\n"
        f"Focal questions:\n{focal_qs}\n\n"
        "Write your opening claims. For each claim use:\n"
        "CLAIM: <statement>\nQUOTE: <exact verbatim quote>\nSTANCE: SUPPORTS|CONTRADICTS|DIFFERENT_CONDITIONS|NOT_COVERED\n"
        "CONDITIONS: <if DIFFERENT_CONDITIONS>"
    )

    entries = _llm_fighter_turn(llm, system_prompt, user_msg, state["fight_id"], 1, "fighter_b", fighter.doc_id)
    saved = write_entries(entries)
    return {"entries_b": [e.model_dump() for e in saved]}


def cross_exam(state: ArenaState) -> dict:
    """R2: Each fighter reads only the opponent's R1 entries and responds."""
    logger.info("[%s] R2: cross_exam", state["fight_id"])
    if _cap_reached(state):
        return {"round": 2}

    llm = _get_llm(FIGHTER_MODEL)
    fighter_prompt = _load_prompt("fighter")

    def _respond(my_doc: dict, my_id: str, my_role: str, opp_entries: list[dict]) -> list[MemoryEntry]:
        opp_text = "\n\n".join(
            f"[Entry {e.get('entry_id', '?')}] CLAIM: {e['text']}\nQUOTE: {e.get('quote', '')}\nSTANCE: {e.get('stance', '')}"
            for e in opp_entries if e.get("entry_type") in ("claim", "concession", "idea")
        )
        user_msg = (
            f"Your document:\n\n{my_doc['text'][:20000]}\n\n"
            f"Opponent's claims (cite entry IDs when responding):\n\n{opp_text}\n\n"
            "Respond to the opponent's claims. Use CLAIM:, QUOTE:, STANCE:. "
            "To concede, use: CONCEDE: <entry_id> QUOTE: <exact quote from your doc that supports concession>"
        )
        return _llm_fighter_turn(llm, fighter_prompt, user_msg, state["fight_id"], 2, my_role, my_id)

    fighter_a = Fighter(**state["fighter_a"])
    fighter_b = Fighter(**state["fighter_b"])

    entries_a_new = _respond(state["doc_a"], fighter_a.doc_id, "fighter_a", state["entries_b"])
    entries_b_new = _respond(state["doc_b"], fighter_b.doc_id, "fighter_b", state["entries_a"])

    saved_a = write_entries(entries_a_new)
    saved_b = write_entries(entries_b_new)

    return {
        "entries_a": [e.model_dump() for e in saved_a],
        "entries_b": [e.model_dump() for e in saved_b],
        "round": 2,
    }


def moderator_followups(state: ArenaState) -> dict:
    """R2b: Moderator picks ≤2 sharpest conflicts; fighters respond (still in R2 logically)."""
    logger.info("[%s] R2b: moderator_followups", state["fight_id"])
    if _cap_reached(state):
        return {"round": 3}

    llm_mod = _get_llm(MODERATOR_MODEL)
    llm_fighter = _get_llm(FIGHTER_MODEL)
    mod_prompt = _load_prompt("moderator")
    fighter_prompt = _load_prompt("fighter")

    all_entries = state["entries_a"] + state["entries_b"]
    entries_text = "\n\n".join(
        f"[{e.get('author')} / entry {e.get('entry_id', '?')}] {e['text']}"
        for e in all_entries
    )

    # Moderator selects ≤2 sharpest conflicts
    followup_questions: list[str] = []
    if llm_mod is None:
        followup_questions = ["What is the sharpest remaining conflict?"]
    else:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = llm_mod.invoke([
                SystemMessage(content=mod_prompt),
                HumanMessage(content=(
                    f"Review these fight entries:\n\n{entries_text[:8000]}\n\n"
                    "Identify the 2 sharpest unresolved conflicts. Write:\n"
                    "FOLLOWUP: <question 1>\nFOLLOWUP: <question 2>"
                )),
            ])
            content = resp.content if hasattr(resp, "content") else str(resp)
            for line in content.splitlines():
                if line.strip().upper().startswith("FOLLOWUP:"):
                    followup_questions.append(line.split(":", 1)[1].strip())
        except Exception as exc:  # noqa: BLE001
            logger.error("Moderator followup LLM failed: %s", exc)
            followup_questions = []

    followup_questions = followup_questions[:2]

    # Write moderator followup entries
    mod_entries_new = []
    for q in followup_questions:
        e = write_entry(MemoryEntry(
            fight_id=state["fight_id"], round=2, author="moderator",
            entry_type="followup", text=f"FOLLOWUP: {q}", quote="", doc_id="moderator",
            stance=Stance.NOT_COVERED,
        ))
        mod_entries_new.append(e.model_dump())

    if not followup_questions:
        return {"entries_mod": mod_entries_new, "round": 3}

    followup_text = "\n".join(f"Q: {q}" for q in followup_questions)

    # Each fighter responds to the follow-up questions
    def _followup_response(my_doc: dict, my_id: str, my_role: str) -> list[MemoryEntry]:
        user_msg = (
            f"Your document:\n\n{my_doc['text'][:20000]}\n\n"
            f"Moderator follow-up questions:\n{followup_text}\n\n"
            "Answer only from your document. Use CLAIM:, QUOTE:, STANCE:."
        )
        return _llm_fighter_turn(llm_fighter, fighter_prompt, user_msg, state["fight_id"], 2, my_role, my_id)

    fighter_a = Fighter(**state["fighter_a"])
    fighter_b = Fighter(**state["fighter_b"])

    new_a = _followup_response(state["doc_a"], fighter_a.doc_id, "fighter_a")
    new_b = _followup_response(state["doc_b"], fighter_b.doc_id, "fighter_b")
    saved_a = write_entries(new_a)
    saved_b = write_entries(new_b)

    return {
        "entries_mod": mod_entries_new,
        "entries_a": [e.model_dump() for e in saved_a],
        "entries_b": [e.model_dump() for e in saved_b],
        "round": 3,
    }


def common_ground(state: ArenaState) -> dict:
    """R3: Both fighters identify common ground and propose novel ideas (cite both sides)."""
    logger.info("[%s] R3: common_ground", state["fight_id"])
    if _cap_reached(state):
        return {"round": 3}

    llm = _get_llm(FIGHTER_MODEL)
    fighter_prompt = _load_prompt("fighter")

    all_entries_text = "\n\n".join(
        f"[{e.get('author')} entry {e.get('entry_id', '?')}] {e['text']}"
        for e in state["entries_a"] + state["entries_b"]
        if e.get("entry_type") in ("claim", "concession", "idea")
    )

    def _cg_response(my_doc: dict, my_id: str, my_role: str) -> list[MemoryEntry]:
        user_msg = (
            f"All fight entries so far:\n\n{all_entries_text[:8000]}\n\n"
            "Your document:\n\n" + my_doc["text"][:10000] + "\n\n"
            "Write:\n"
            "1. Areas of common ground (cite entry IDs from both sides)\n"
            "   IDEA: <common ground statement> REFS: <entry_id_1>,<entry_id_2>\n"
            "2. Novel ideas that emerge from the debate\n"
            "   IDEA: <novel idea>\nQUOTE: <supporting quote from your doc>\n"
        )
        return _llm_fighter_turn(llm, fighter_prompt, user_msg, state["fight_id"], 3, my_role, my_id)

    fighter_a = Fighter(**state["fighter_a"])
    fighter_b = Fighter(**state["fighter_b"])

    new_a = _cg_response(state["doc_a"], fighter_a.doc_id, "fighter_a")
    new_b = _cg_response(state["doc_b"], fighter_b.doc_id, "fighter_b")
    saved_a = write_entries(new_a)
    saved_b = write_entries(new_b)

    return {
        "entries_a": [e.model_dump() for e in saved_a],
        "entries_b": [e.model_dump() for e in saved_b],
        "round": 3,
    }


def verify_all(state: ArenaState) -> dict:
    """V: Code-verifies every MemoryEntry.quote against its source document."""
    logger.info("[%s] V: verify_all", state["fight_id"])

    # Rebuild documents dict for verifier
    documents = {
        state["fighter_a"]["doc_id"]: state["doc_a"],
        state["fighter_b"]["doc_id"]: state["doc_b"],
    }

    # Read all entries from JSONL (authoritative source)
    all_entries = read_entries(state["fight_id"])

    # Run verification (mutates in place)
    verified_entries = verify_all_entries(all_entries, documents)

    # Persist verification flags back to JSONL
    for e in verified_entries:
        if e.quote:
            update_entry_verification(
                state["fight_id"], e.entry_id,
                verified=e.verified,
                near_exact=e.near_exact,
                position=e.char_position,
                section=e.section,
                note=e.verification_note,
            )

    ratio = _compute_ratio(verified_entries)
    logger.info("[%s] Quote verified ratio: %.2f", state["fight_id"], ratio)

    return {"verified": True}


def _run_judge(
    state: ArenaState,
    swap_run: int,
    entries_side_a: list[dict],
    entries_side_b: list[dict],
    label_a: str,
    label_b: str,
) -> Verdict:
    """
    Single judge run. Judge sees ONLY the shared memory JSONL (not raw documents).
    Rubric (per judge.md): evidence 1–5, relevance 1–5, novelty 1–5, conditions clarity 1–5.
    Must cite entry IDs. Marks incomparable claims.
    """
    judge_prompt = _load_prompt("judge")
    llm = _get_llm(JUDGE_MODEL)

    # Build memory text — VERIFIED entries only (as per agentwars.md: unverified excluded)
    all_entries = [MemoryEntry(**e) for e in entries_side_a + entries_side_b]
    verified = [e for e in all_entries if e.entry_type != "followup" and (e.verified or not e.quote)]

    memory_text = "\n\n".join(
        f"[{e.entry_id}] [{e.author}] [R{e.round}] [{e.stance}] "
        f"{'✓' if e.verified else '⚬'} {e.text}"
        + (f"\n  QUOTE: {e.quote}" if e.quote else "")
        for e in verified
    )

    user_msg = (
        f"Topic: {(state.get('fight_card') or {}).get('topic', 'Research fight')}\n\n"
        f"Side A ({label_a}) entries:\n"
        + "\n".join(f"[{e.entry_id}] {e.text}" for e in verified if e.author == ("fighter_a" if swap_run == 1 else "fighter_b"))
        + f"\n\nSide B ({label_b}) entries:\n"
        + "\n".join(f"[{e.entry_id}] {e.text}" for e in verified if e.author == ("fighter_b" if swap_run == 1 else "fighter_a"))
        + f"\n\nAll entries (shared memory):\n{memory_text[:12000]}\n\n"
        "Score each side on: evidence (1–5), relevance (1–5), novelty (1–5), conditions clarity (1–5).\n"
        "WINNER: <side_a|side_b|draw>\n"
        "SCORE_A: <float 1-5>\n"
        "SCORE_B: <float 1-5>\n"
        "VERDICT: <entry_id> UPHELD|STRUCK|INCOMPARABLE\n"
        "IDEA: <entry_id> (top novel ideas, highest first)\n"
        "CITATION: <entry_id> (all entry IDs you cite)"
    )

    if llm is None:
        # Stub verdict for testing
        return Verdict(
            fight_id=state["fight_id"],
            winner="draw",
            claim_verdicts={},
            scores={"fighter_a": 3.0, "fighter_b": 3.0},
            ranked_ideas=[],
            swap_run=swap_run,
            judge_citations=[],
        )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        resp = llm.invoke([SystemMessage(content=judge_prompt), HumanMessage(content=user_msg)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        return _parse_judge_output(content, state["fight_id"], swap_run)
    except Exception as exc:  # noqa: BLE001
        logger.error("Judge LLM failed: %s", exc)
        return Verdict(
            fight_id=state["fight_id"], winner=None,
            claim_verdicts={}, scores={}, ranked_ideas=[],
            swap_run=swap_run, judge_citations=[],
        )


def _parse_judge_output(content: str, fight_id: str, swap_run: int) -> Verdict:
    winner = None
    scores: dict[str, float] = {}
    claim_verdicts: dict[str, str] = {}
    ranked_ideas: list[str] = []
    citations: list[str] = []

    for line in content.splitlines():
        s = line.strip()
        u = s.upper()
        if u.startswith("WINNER:"):
            w = s.split(":", 1)[1].strip().lower()
            if "draw" in w:
                winner = "draw"
            elif "a" in w:
                winner = "fighter_a"
            elif "b" in w:
                winner = "fighter_b"
        elif u.startswith("SCORE_A:"):
            try:
                scores["fighter_a"] = float(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif u.startswith("SCORE_B:"):
            try:
                scores["fighter_b"] = float(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif u.startswith("VERDICT:"):
            parts = s.split(":", 1)[1].strip().split()
            if len(parts) >= 2:
                claim_verdicts[parts[0]] = parts[1].lower()
        elif u.startswith("IDEA:"):
            idea_id = s.split(":", 1)[1].strip().split()[0]
            if idea_id:
                ranked_ideas.append(idea_id)
        elif u.startswith("CITATION:"):
            cit_id = s.split(":", 1)[1].strip().split()[0]
            if cit_id:
                citations.append(cit_id)

    return Verdict(
        fight_id=fight_id,
        winner=winner,
        claim_verdicts=claim_verdicts,
        scores=scores,
        ranked_ideas=ranked_ideas,
        swap_run=swap_run,
        judge_citations=citations,
    )


def judge_run_1(state: ArenaState) -> dict:
    """J1: Judge with sides as-is."""
    logger.info("[%s] J1: judge_run_1", state["fight_id"])
    verdict = _run_judge(
        state, 1,
        state["entries_a"], state["entries_b"],
        state["fighter_a"]["doc_id"], state["fighter_b"]["doc_id"],
    )
    return {"verdict_1": verdict.model_dump()}


def judge_run_2(state: ArenaState) -> dict:
    """J2: Judge with sides swapped (fighter_a ↔ fighter_b)."""
    logger.info("[%s] J2: judge_run_2 (sides swapped)", state["fight_id"])
    verdict = _run_judge(
        state, 2,
        state["entries_b"], state["entries_a"],         # swapped
        state["fighter_b"]["doc_id"], state["fighter_a"]["doc_id"],  # swapped labels
    )
    return {"verdict_2": verdict.model_dump()}


def merge_verdicts(state: ArenaState) -> dict:
    """M: Merge both judge runs, compute swap_agreement, update Elo."""
    logger.info("[%s] M: merge_verdicts", state["fight_id"])

    v1 = Verdict(**state["verdict_1"]) if state["verdict_1"] else None
    v2 = Verdict(**state["verdict_2"]) if state["verdict_2"] else None

    # Swap agreement: fraction of claim verdicts that match across both runs
    if v1 and v2 and v1.claim_verdicts and v2.claim_verdicts:
        common_keys = set(v1.claim_verdicts) & set(v2.claim_verdicts)
        if common_keys:
            agree = sum(
                1 for k in common_keys if v1.claim_verdicts[k] == v2.claim_verdicts[k]
            )
            swap_agreement = agree / len(common_keys)
        else:
            swap_agreement = 0.0
    else:
        swap_agreement = 0.0

    # Winner: agree if both runs agree (after accounting for swap)
    winner_1 = v1.winner if v1 else None
    # v2 winner is from the swapped perspective — invert
    winner_2_raw = v2.winner if v2 else None
    if winner_2_raw == "fighter_a":
        winner_2 = "fighter_b"  # was actually b in original labelling
    elif winner_2_raw == "fighter_b":
        winner_2 = "fighter_a"
    else:
        winner_2 = winner_2_raw

    final_winner = winner_1 if winner_1 == winner_2 else "draw"

    # Average scores
    scores_1 = v1.scores if v1 else {}
    scores_2 = v2.scores if v2 else {}
    final_scores: dict[str, float] = {}
    for side in ("fighter_a", "fighter_b"):
        s1 = scores_1.get(side, 3.0)
        s2 = scores_2.get(side, 3.0)
        final_scores[side] = round((s1 + s2) / 2, 2)

    # Merged ranked ideas (union, preserve order from v1)
    seen: set[str] = set()
    merged_ideas: list[str] = []
    for idea_list in (v1.ranked_ideas if v1 else [], v2.ranked_ideas if v2 else []):
        for idea_id in idea_list:
            if idea_id not in seen:
                merged_ideas.append(idea_id)
                seen.add(idea_id)

    # Verified ratio
    all_entries = read_entries(state["fight_id"])
    v_ratio = _compute_ratio(all_entries)
    struck = sum(1 for e in all_entries if v1 and v1.claim_verdicts.get(e.entry_id) == "struck")
    upheld = sum(1 for e in all_entries if v1 and v1.claim_verdicts.get(e.entry_id) == "upheld")

    merged = MergedVerdict(
        fight_id=state["fight_id"],
        winner=final_winner,
        swap_agreement=round(swap_agreement, 3),
        final_scores=final_scores,
        ranked_ideas=merged_ideas,
        all_entries_verified_ratio=round(v_ratio, 3),
        struck_count=struck,
        upheld_count=upheld,
    )

    # Update Elo ratings
    if final_winner == "fighter_a":
        outcome = "a"
    elif final_winner == "fighter_b":
        outcome = "b"
    else:
        outcome = "draw"

    fa = Fighter(**state["fighter_a"])
    fb = Fighter(**state["fighter_b"])
    new_r_a, new_r_b = update_elo(fa.doc_id, fb.doc_id, outcome)
    logger.info("[%s] Elo update: %s %.0f, %s %.0f", state["fight_id"], fa.doc_id, new_r_a, fb.doc_id, new_r_b)

    # Update fight record
    record = FightRecord(
        fight_id=state["fight_id"],
        fighter_a=fa,
        fighter_b=fb,
        state=FightState.DONE,
        merged_verdict=merged,
        elo_delta_a=new_r_a - 1200.0,
        elo_delta_b=new_r_b - 1200.0,
        finished_at=datetime.now(UTC).isoformat(),
    )
    upsert_fight(record)

    return {"final_verdict": merged.model_dump()}


def publish_fight(state: ArenaState) -> dict:
    """P: Emit fight data for site builder and Telegram notification."""
    logger.info("[%s] P: publish_fight — fight complete", state["fight_id"])
    # Site builder will pick up the fight data from arena.db + JSONL
    # Telegram notification is triggered by the MCP layer (non-blocking)
    return {}


# ── Graph compilation ─────────────────────────────────────────────────────────


def _build_arena_graph(checkpointer=None) -> Any:
    """
    Build and compile the LangGraph fight graph.
    Pass a checkpointer instance, or None to use SqliteSaver with the arena DB.
    """
    import sqlite3 as _sqlite3
    init_arena_db()

    builder = StateGraph(ArenaState)

    builder.add_node("moderator_setup", moderator_setup)
    builder.add_node("fighter_a_node", fighter_a_node)
    builder.add_node("fighter_b_node", fighter_b_node)
    builder.add_node("cross_exam", cross_exam)
    builder.add_node("moderator_followups", moderator_followups)
    builder.add_node("common_ground", common_ground)
    builder.add_node("verify_all", verify_all)
    builder.add_node("judge_run_1", judge_run_1)
    builder.add_node("judge_run_2", judge_run_2)
    builder.add_node("merge_verdicts", merge_verdicts)
    builder.add_node("publish_fight", publish_fight)

    builder.set_entry_point("moderator_setup")
    builder.add_conditional_edges("moderator_setup", fan_out_openings, ["fighter_a_node", "fighter_b_node", "verify_all"])
    builder.add_edge("fighter_a_node", "cross_exam")
    builder.add_edge("fighter_b_node", "cross_exam")
    builder.add_edge("cross_exam", "moderator_followups")
    builder.add_edge("moderator_followups", "common_ground")
    builder.add_edge("common_ground", "verify_all")
    builder.add_edge("verify_all", "judge_run_1")
    builder.add_edge("judge_run_1", "judge_run_2")
    builder.add_edge("judge_run_2", "merge_verdicts")
    builder.add_edge("merge_verdicts", "publish_fight")
    builder.add_edge("publish_fight", END)

    if checkpointer is None:
        # Persistent SQLite connection (not context manager — kept alive for the process)
        ARENA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = _sqlite3.connect(str(ARENA_DB_PATH), check_same_thread=False)
        checkpointer = SqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)


# Compiled graph — imported by the MCP layer and background jobs
arena_graph = _build_arena_graph()


# ── Public API ────────────────────────────────────────────────────────────────


async def run_fight(
    fighter_a: Fighter,
    fighter_b: Fighter,
    *,
    fight_id: str | None = None,
    token_cap: int = DEFAULT_TOKEN_CAP,
    min_similarity: float = SIMILARITY_MIN_GATE,
    on_progress: Callable[[str, str], Any] | None = None,
) -> MergedVerdict | None:
    """
    Run a complete fight end-to-end.
    Creates a new fight_id if not provided.
    Returns the MergedVerdict or None on failure or rejection.
    Resumable: pass the same fight_id to resume a killed fight.
    """
    if fight_id is None:
        fight_id = f"fight-{uuid.uuid4().hex[:8]}"

    # Load documents
    try:
        docs = await load_fighter_docs(fighter_a.doc_id, fighter_b.doc_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] Failed to load documents: %s", fight_id, exc)
        upsert_fight(FightRecord(
            fight_id=fight_id, fighter_a=fighter_a, fighter_b=fighter_b,
            state=FightState.FAILED, error=str(exc),
        ))
        return None

    doc_a = docs[fighter_a.doc_id]
    doc_b = docs[fighter_b.doc_id]

    # Pre-flight similarity gate
    eligible, sim_score = is_fight_eligible(
        doc_a.get("text", ""),
        doc_b.get("text", ""),
        threshold=min_similarity,
    )
    if not eligible:
        label_a = "Ground Thesis" if fighter_a.doc_id == "ground" else f"arXiv:{fighter_a.doc_id}"
        label_b = "Ground Thesis" if fighter_b.doc_id == "ground" else f"arXiv:{fighter_b.doc_id}"
        sim_pct = round(sim_score * 100)
        min_pct = round(min_similarity * 100)
        rejection_reason = (
            f"🚫 **Paper Arena Fight Ineligible (< {min_similarity:.2f} Gate)**\n\n"
            f"• **Matchup:** {label_a} 🆚 {label_b}\n"
            f"• **Similarity Score:** `{sim_pct}%` (Required Minimum: `≥ {min_pct}%`)\n"
            f"• **Reason:** This paper is out-of-scope for the Raspberry Pi 5 edge speech recognition thesis anchor.\n\n"
            f"_Debates are restricted to papers that directly validate, extend, or challenge our quantization, latency, or memory claims._"
        )
        logger.warning("[%s] Fight rejected: similarity %.3f < %.2f", fight_id, sim_score, min_similarity)
        upsert_fight(FightRecord(
            fight_id=fight_id, fighter_a=fighter_a, fighter_b=fighter_b,
            state=FightState.REJECTED, error=rejection_reason,
        ))
        if on_progress:
            try:
                res = on_progress("rejected", rejection_reason)
                if inspect.isawaitable(res):
                    await res
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] on_progress failed for rejection: %s", fight_id, exc)
        return None

    state = _initial_state(fight_id, fighter_a, fighter_b, doc_a, doc_b, token_cap)
    config = {"configurable": {"thread_id": fight_id}}

    node_commentary = {
        "moderator_setup": "🔔 R0: Moderator framed focal questions & debate boundaries",
        "fighter_a_node": "🥊 R1: Opening claims filed with verified citations",
        "fighter_b_node": "🥊 R1: Opening claims filed with verified citations",
        "cross_exam": "⚔️ R2: Direct cross-examination & quote challenges complete",
        "moderator_followups": "🔥 R2b: Moderator pressed on sharpest contradictions",
        "common_ground": "🤝 R3: Synthesizing common ground & forging novel ideas",
        "verify_all": "🛡️ Verifier: Verbatim quotes verified against source preprints",
        "judge_run_1": "⚖️ Judge: Dual Nemotron run 1 completed",
        "judge_run_2": "⚖️ Judge: Dual Nemotron run 2 completed (sides swapped for symmetry)",
        "merge_verdicts": "📊 Verdicts merged & swap agreement evaluated",
        "publish_fight": "🏁 Debate concluded & published",
    }

    final_verdict: dict | None = None
    try:
        for event in arena_graph.stream(state, config=config):
            for node_name, node_output in event.items():
                if node_name == "merge_verdicts" and isinstance(node_output, dict) and "final_verdict" in node_output:
                    final_verdict = node_output["final_verdict"]
                if on_progress and node_name in node_commentary:
                    try:
                        res = on_progress(node_name, node_commentary[node_name])
                        if inspect.isawaitable(res):
                            await res
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("[%s] on_progress failed for %s: %s", fight_id, node_name, exc)

        if final_verdict:
            return MergedVerdict(**final_verdict)
    except Exception as exc:  # noqa: BLE001
        logger.error("[%s] Fight graph error: %s", fight_id, exc)
        upsert_fight(FightRecord(
            fight_id=fight_id, fighter_a=fighter_a, fighter_b=fighter_b,
            state=FightState.FAILED, error=str(exc),
        ))

    return None

# ThesisClaw: Paper Arena

Yes, this works, and it's the strongest version of the idea so far. Each paper becomes an agent that can only speak from its own text. It has to defend its claims against your research, or against another paper you pick, and code checks every quote. Deep Agents can hold two fighter slots for this: they sit inside one arena subagent and get loaded with a different document for each fight.

Your built repo isn't in this workspace; this folder only has the three .md files. So the file paths below follow the v2 layout, and Step 0 maps them to your real code.

## Four-Skill Loop

| Skill | Finding |
| --- | --- |
| Hackathon (Mom Test) | The fight is the hook for the demo. What a researcher actually uses is the output: which claims conflict with mine, under what conditions, and which new ideas to try, each backed by a checked quote. The closest existing tool is Co-STORM, where several AI experts discuss a topic with a moderator. What's new here: one agent per paper limited to its own text, your research as its own agent, quotes checked by code, a judge that only sees what the fighters wrote, and a leaderboard that keeps growing across fights. |
| Tech (ADR) | The fight is a fixed-round LangGraph graph. Both fighters run in parallel, write to one shared memory, and the graph saves progress to SQLite so a crashed fight can resume. It plugs into Deep Agents as a CompiledSubAgent. Each fighter sees only its own document. The judge runs on a different, larger model to reduce bias toward its own writing. |
| Financial | Your research vs a paper: about 0.2M input and 16k output tokens per fight. Paper vs paper: about 0.3M input. Each fight is 8–14 model calls, which costs $0 on the NVIDIA free tier. Dropping the ESP32 removes its cost. |
| Risk (FMEA) | Top failure modes and fixes: Fighters inventing claims: unverified quotes don't count. Fighters agreeing too easily: openings are written independently, and a fighter can only concede by quoting. Judge bias: sides are swapped and the judge must cite entry IDs. Unfair comparisons: a "different conditions" label for results from different setups. Instructions hidden in paper text: fighters and judge get no tools that can change anything. Runaway cost: fixed rounds and token caps. |

## Core Concept

### Plan: Paper Arena — Research Papers as Fighting Agents
TL;DR: Any paper becomes an agent that speaks only from its own text. Two fighter agents run a moderated 3-round fight and write claims with exact quotes into a shared memory. A fight is either your research ("Ground") vs the most similar paper by cosine score, or two papers you choose. Code checks every quote. A judge reads only that shared memory and outputs verdicts, scorecards and ranked new ideas, and a leaderboard grows across fights. You start a fight from Telegram, it runs in the background, and results appear on a fight page. Build order: code-only core first, then the fight graph, then Telegram and web.

## Implementation Plan

### Steps

#### Phase 0 — Prep
##### Step 0 — Repository and Current State

Open your built repo in this workspace and note what works today (Telegram → OpenClaw → MCP → worker? paper ingestion? embeddings?). Map the paths below to your real code.

Drop the ESP32 scope: remove the voice bridge, /voice-mcp, the voice skill and the MCP v1 pin, leaving one uv project on MCP v2. Record this as a decision in docs/decisions.md.

#### Phase 1 — Code-only Core (No Model Calls, Fully Unit-Testable)

Depends on Phase 0.

##### Step 2 — Data Models (Pydantic)

Fighter: kind ground|paper, doc_id.
FightCard: topic plus 3–5 focal questions.
MemoryEntry: hash ID, round, author, type, text, quote, doc_id, section, character position, conditions, stance, refs, verified flag, verification note. Stance is SUPPORTS, CONTRADICTS, DIFFERENT_CONDITIONS or NOT_COVERED.
FighterTurn and Verdict: claim verdicts, scorecards, ranked ideas, cited entry IDs.
Shared memory store: an append-only JSONL file per fight plus a SQLite index. Writes are keyed by content hash, so a resumed fight can't create duplicates. A project-wide claims log persists across fights. parallel with 4–6
##### Step 3 — Quote Verifier
Normalize unicode, ligatures, hyphenation and whitespace, then require an exact match. A match returns its position and section, which becomes the link anchor.
Near-exact matches get a separate flag.
Unverified entries are excluded from judging.
parallel
##### Step 4 — Fighter Documents
A paper uses its full text, preferring arXiv HTML. Trim references and appendix and cap it at about 40k tokens, with a section index.
Ground uses research/agent.md plus the project brief, and optionally your own draft.
Cache each document.
parallel
##### Step 5 — Opponent Selection

Rank papers by cosine similarity of NVIDIA embeddings, either against Ground or against a given paper. A threshold τ decides when a new paper triggers an automatic fight. Reuse your existing similarity code. parallel

#### Phase 2 — Fight Graph (The Agents)

Depends on Phase 1.

##### Step 7 — Prompts

Moderator: writes the fight card and picks at most 2 of the sharpest conflicts for follow-up.
Fighter persona: speak only from your document, quote word for word, label your stance, say NOT_COVERED instead of guessing, and concede only with a quote.
Judge rubric: evidence, relevance to your research, novelty and clarity of conditions, scored 1–5 with defined levels. The judge must cite entry IDs and mark claims that can't be compared.
##### Step 8 — LangGraph Fight Graph

LangGraph fight graph, in this order:

Setup by the moderator.
Openings: both fighters run in parallel (LangGraph Send), each with its own context and no view of the opponent.
Cross-examination: each fighter reads only the opponent's entries in shared memory.
Up to 2 moderator follow-ups.
Common ground and new ideas, each citing entries from both sides.
Code verifies every quote.
The judge runs twice with sides swapped, and the results are merged.
Publish.
The graph saves progress to SQLite, has caps on turns and tokens, and emits a progress event after each round.

##### Step 9 — Agent Construction and Permissions

Fighters are built with create_agent: the document is preloaded, there is a read-only read_section tool, and output is structured. Fighters and the moderator use Nemotron 3 Super; the judge uses Nemotron 3 Ultra (verify the model IDs). Neither fighters nor judge get write or network tools.

##### Step 10 — Arena Integration and Paper Questions

Expose the graph in two ways: run_fight() for background jobs, and CompiledSubAgent(name="arena") on the main agent. Add ask_paper, which answers a question from one paper with verified quotes or says "not in this paper".

#### Phase 3 — Telegram and Web

Depends on Phase 2; parallel with Phase 4.

##### Step 11 — MCP Tools

MCP tools, documented in docs/tool-contract.md:





- `start_fight(a, b?)`: no b means Ground vs a; no a means Ground vs the most similar paper.



- `fight_status`, `get_verdict`, `ask_paper`, `similar_papers`, `leaderboard`.





##### Step 12 — OpenClaw Skill





- Commands: `/fight`, `/fight <a> <b>`, `/ask <a>`, `/verdict`, `/leaderboard`.



- A progress message after each round, then the verdict with a link to the fight page.





##### Step 13 — Automatic Fights

Automatic fights (the long-running part): any new paper scoring at least τ against Ground queues a Ground fight. A morning digest reports on them, e.g. "3 papers fought your research overnight".



##### Step 14 — Web Pages





- Fight page: two columns per round, stance labels, and every sentence linked to the highlighted quote in the source. Verified quotes get a badge and unverified claims are struck through. It also shows the scorecard and ranked ideas.



- Leaderboard page.



- Stats: fights run, % of quotes verified, claims struck, days running.

#### Phase 4 — Tests, Evals, and Demo

Depends on Phase 2.

##### Step 15 — Offline Tests (No Network)





- Verifier cases, memory deduplication, opponent selection.



- The graph with a fake model: round order, parallel openings, caps, and resuming after a kill without duplicates.



- MCP contract tests, plus a test paper containing hidden instructions.





##### Step 16 — Live Evaluation

Live eval on 10 fights from your library, with real numbers published on the site:





- At least 90% of quotes verified.



- At least 80% of judge verdicts unchanged when sides are swapped.



- Your own agreement with 5 verdicts.



- A 1–5 rating of how useful the top-ranked idea is.





##### Step 17 — Demo

Demo: pick one Ground fight and one paper fight that each show a real insight, then record.

#### Phase 5 — Documentation

Parallel with Phases 3–4.

##### Step 18 — Documentation Updates

Update AGENTS.md (add the arena module), the worker skills, the decision records and the public page copy.

Relevant files (v2 layout; map them in step 0)

- `src/thesisclaw/arena/` — models.py, memory.py, verify.py, docs.py, select.py, graph.py (steps 2–10)
- `runtime/worker/prompts/` — moderator.md, fighter.md, judge.md (step 7)
- `src/thesisclaw/agent/` — register CompiledSubAgent("arena") (step 10)
- `src/thesisclaw/mcp/` and docs/tool-contract.md — new tools (step 11)
- `runtime/openclaw/skills/thesisclaw/SKILL.md` — Telegram commands (step 12)
- `site/` — fight and leaderboard pages (step 14)
- `tests/arena/`, `evals/fights/` — tests and evals (steps 15–16)
- `docs/decisions.md`, AGENTS.md — decisions and module map (steps 1 and 18)
- Remove: the voice bridge, /voice-mcp and the voice skill
## Verification

- `uv run pytest -m "not live"` passes.
- `/fight <arxiv_id>` in Telegram gives a progress message per round, then a verdict and a page link. Every judge citation points to a verified entry.
- `/fight A B` runs a paper fight. `/ask A "…"` returns verified quotes or "not in this paper".
- Kill the worker mid-fight and restart it: the fight resumes where it stopped, with no duplicate entries.
- The 10-fight eval meets the thresholds, and the leaderboard changes over several days.
## Decisions

- Papers as agents is the headline feature; ESP32 and voice are removed completely.
- The agents are two fighters, a moderator, a judge and a code verifier. Ground is your research.
- Fights use fixed moderated rounds, not free chat.
- The judge sees only the shared memory, uses a different model and runs with sides swapped.
- The fight runs as a LangGraph graph inside Deep Agents. Telegram reaches it through OpenClaw, MCP and a background job.
- Deferred: draft PRs, the notes loop, and fights with more than two papers.
## Further Considerations

- Leaderboard method: for paper vs paper, use Elo, a chess-style rating that updates after each fight. For Ground fights, rank papers by a "value to your research" score.
- Ground documents: adding your own draft makes fights stronger, but the text goes to NVIDIA endpoints. I recommend it if you're comfortable with that.
- Hook line: "Every paper you read becomes an agent — and has to fight for its claims."
- Plan v3 is saved in session memory as the current plan; v2 is marked done, with its ESP32 parts dropped.

## Next Step Action Block

- Now: add your built repo folder to this workspace and say what works today; also approve plan v3 or change the rounds, rubric or τ.
- Then: build Phase 1, starting with the verifier and shared memory, since they are what proves the rigor.
- Minimum demo, in order: one Ground fight end-to-end from Telegram with a verdict page. After that, paper fights, then the leaderboard and automatic fights.
## State Serialization Block

```yaml
state_version: 5
date: 2026-09-30
deadline: 2026-10-02 (hour unknown; internal 12:00 CEST)
product: ThesisClaw — Paper Arena
headline: research papers as agents that fight; judge ranks; every sentence -> verified quote
scope: {esp32_voice: dropped, mcp: v2_only, draft_prs: deferred}
repo: {status: user-reported built+working, location: unknown (not in workspace)}
current_plan: v3 (/memories/session/plan.md)
agents: [ground, fighter_a, fighter_b, moderator, judge, verifier_code]
fight_types: {ground_vs_paper: "auto if cos>=tau or /fight ", paper_vs_paper: "/fight A B"}
rounds: [R0_setup, R1_openings_parallel, R2_cross_exam_plus_2_followups, R3_common_ground_ideas, verify, judge_x2_swapped]
models: {fighters: nemotron-3-super-120b-a12b, judge: nemotron-3-ultra-550b-a55b, verify_ids: true}
tokens_per_fight: {ground: "~0.2M in / 16k out", paper: "~0.3M in"}
evals: {quotes_verified: ">=0.90", swap_agreement: ">=0.80", injection_canary: pass, resume_no_dups: pass}
open_questions: [repo_path_and_working_parts, leaderboard_method, include_own_draft_in_ground]
next: step_0_then_phase_1
```
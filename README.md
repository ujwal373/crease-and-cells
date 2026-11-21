# Crease and Cells

Learn Microsoft Excel and Google Sheets functions by solving missions in a cricket world. Walk the open world, meet NPCs who have spreadsheet problems, write real formulas to solve them, earn coins, and upgrade your kit.

**Live demo:** https://crease-and-cells-production.up.railway.app/game/Prototype.dc.html

---

## What is built

Phases 0 through 3 are complete and production-deployed.

1. Formula engine: SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, COUNTIF, COUNTIFS, SUMIF, SUMIFS, AVERAGEIF, IF, IFS, AND, OR, ROUND, ABS, absolute and relative references. Tokenizer, parser, evaluator — no eval or exec anywhere.
2. Validator: compares formula result to an independently computed answer key. The validator is deterministic code; an LLM never decides whether an answer is correct.
3. Guardrails: formula injection filter, coach input screening, answer-leak check on every reply.
4. Agents on an event bus: Mission Agent (picks next mission), Scoring Agent (coins, XP, level), Store Agent (catalog, buy, equip).
5. Tutor Agent: live hints via Claude Haiku with per-player daily cap, SQLite hint cache, cost tracing, and static fallback.
6. Mission Generator: offline Sonnet-backed script that generates, reviews, and merges missions.
7. FastAPI backend with 10 frontend endpoints, Bearer token identity, session and exam flow, leaderboard.
8. Email auth: register with name and email, log in with email, UUID stored in localStorage.
9. MCP server: 7 tools exposing the full game (get_next_mission, submit_answer, get_hint, ask_coach, get_wallet, list_store, buy_item).
10. 300 passing tests, 2 skipped, 10 xfailed (formula families pending engine additions in Phase 4).

Levels 1 (The Nets) and 2 (Club House) are fully playable.

---

## Running locally

Install dependencies:

    pip install -e ".[dev]"

Run tests:

    python -m pytest

Start the backend (serves both the API and the game frontend):

    CC_DB_PATH=game.db uvicorn backend.api:app --reload

Open the game at http://localhost:8000/game/Prototype.dc.html

To enable live tutor hints, set ANTHROPIC_API_KEY in a `.env` file (see `.env.example`). Without it the backend falls back to static hints automatically.

---

## MCP server

The project ships an MCP server so you can play through real tool calls. The server is registered in `.mcp.json`.

    python -m backend.mcp_server

Add it to Claude Code and ask Claude to get a mission, submit a formula, buy a cap.

---

## Mission generator

Generate a new mission offline (no live game required):

    python scripts/generate_missions.py --level 1 --zone "The Nets" --npc "Coach Rao" --topic wickets

Review and approve the generated mission:

    python scripts/review_missions.py list
    python scripts/review_missions.py approve <id>

Merge it into the game:

    python scripts/merge_missions.py <id>

---

## Evals and tracing

Run the full eval report:

    python evals/run_evals.py

Run with live Haiku calls (uses the Anthropic API):

    python evals/run_evals.py --live

Summarise the trace log:

    python scripts/trace_report.py

---

## Environment variables

    CC_DB_PATH          SQLite file path (default: game.db)
    CC_CORS_ORIGINS     JSON array of allowed origins (default: http://localhost:5173)
    ANTHROPIC_API_KEY   Enables live tutor hints; omit to use static fallback
    CC_TRACE            Trace output file (default: logs/trace.jsonl)
    CC_ADMIN_TOKEN      Protects GET /api/admin/players

---

## Project layout

    backend/            FastAPI app, formula engine, validator, agents, guardrails, tracing
    missions/           Mission JSON by level and a store catalog
    datasets/           Generated CSV cricket data
    scripts/            Mission generator, reviewer, merger, trace report
    evals/              Eval suite for validator, guardrails and hints
    game_frontend_new/  Claude Design prototype (the game UI)
    docs/               DECISIONS.md, PHASES.md, ASSETS.md

See CLAUDE.md for the full rules and roadmap.

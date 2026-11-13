# Crease and Cells

Read this file first. It is the project brief, the rulebook and the roadmap.

## What we are building

A browser game that teaches Microsoft Excel and Google Sheets functions through play, in a cricket world. Think AWS Cloud Quest: an open world where the player walks between zones, meets NPCs who have spreadsheet problems, and solves them with real formulas.

The owner is Ujwal Mojidra, a cricketer (bowler) and data professional. The default hero character is Ujwal, and all data is cricket data. Learning the spreadsheet functions well and interactively is the end goal. The game is also an engineering showcase, so code quality, tests and clear decisions matter more than speed.

## How the game works

1. The player creates a character. Attire starts basic (white kit).
2. The player walks the world, meets an NPC, and accepts a mission.
3. A mission gives a story, a dataset in a spreadsheet grid, and a task. The player writes a real formula.
4. The Validator checks the formula result. A pass earns coins and XP. Hints cost the no-hint bonus.
5. Coins buy cosmetic attire in the store. Nothing purchasable blocks learning progress.
6. As XP grows the level rises and missions get heavier.

## World zones and skill map

1. The Nets, Level 1: SUM, AVERAGE, MIN, MAX, COUNT, cell references, basic formatting
2. Club House, Level 2: IF, IFS, COUNTIF, SUMIF, AVERAGEIF, absolute and relative references, sort and filter
3. Scouting Office, Level 3: VLOOKUP, XLOOKUP, INDEX and MATCH, data cleaning (TRIM, TEXT functions, SPLIT in Sheets)
4. Analytics Lab, Level 4: pivot tables, SUMPRODUCT, conditional formatting, charts, named ranges
5. Press Box, Level 5: QUERY, FILTER, UNIQUE, SORT, ARRAYFORMULA, Excel dynamic arrays
6. Auction Room, Level 6: LET, LAMBDA, scenario modelling, what-if analysis, dashboards
7. Stadium, boss missions: multi-step capstones combining everything

Mission types: Fix It (repair a broken formula), Build It, Clean It (messy data), Analyse It (several functions), Dashboard (summary plus chart).

Note: QUERY and ARRAYFORMULA are Google Sheets only. The engine and HyperFormula will not cover them all. Either build a small custom evaluator or limit those to pre-verified missions.

## Agents

Status key: BUILT means working and tested. PLANNED means not started.

1. Mission Agent, BUILT (rule based): picks the next uncompleted mission. Planned upgrade: generate variants and NPC story text with Claude, using strict JSON output validated before it reaches the database.
2. Scoring Agent, BUILT: awards coins, XP, level, no-hint bonus. Idempotent, so a mission never pays twice.
3. Store Agent, BUILT: catalog, purchase, equip. Atomic spend.
4. Validator, BUILT: deterministic code, never an LLM.
5. Tutor Agent, BUILT: live hints via Claude Haiku (CC_TUTOR_MODEL env var). Client injected for tests. Per-player daily cap, global USD budget cap, SQLite hint cache, guardrail check on every reply (check_tutor_output blocks formulas and secrets), full cost and latency tracing. Falls back to static hints on any failure. Answer key never enters the prompt. Personalised: last submitted formula and validator failure code are stored per player per mission and passed to the prompt. Implements HintProvider Protocol so it can be swapped without changing GameService. Adversarial eval set in evals/adversarial_cases.json covers 27 cases across 5 attack groups.
6. Mission Generator, BUILT: offline Sonnet-backed generator in scripts/generate_missions.py. Validation pipeline catches hardcoded formulas, missing required functions, answer_spec mismatches and hint leaks. Review workflow in scripts/review_missions.py (approve/reject with --force override). Merge workflow in scripts/merge_missions.py promotes approved missions into levelN.json with sequential ids.
7. Dataset Agent, PLANNED: seeded cricket data generators. One generator exists (bowling_spells).
7. Adaptive Difficulty Agent, PLANNED: mastery score per function, spaced repetition, steers the Mission Agent to weak spots.

Agents never call each other. They communicate through events on the bus in `backend/events.py`.

Event flow: answer_submitted, validator, mission_passed, ScoringAgent awards, coins_awarded, MissionAgent assigns, mission_assigned. Other events: answer_rejected, item_purchased, hint_used.

## Non-negotiable rules

1. The Validator is deterministic code. An LLM never decides whether an answer is correct.
2. Answer keys, reference solutions and answer_spec never leave the backend and never enter a prompt. Public mission payloads strip private fields in `backend/service.py`.
3. Coach output goes through `guardrails.check_output` before the player sees it.
4. Free text sent to the coach goes through `guardrails.check_chat_input` first.
5. Datasets are synthetic and generated from an explicit seed. Same seed, same data.
6. No eval or exec anywhere. Formula functions live in the allowlist `FUNCTIONS` in `backend/formula_engine.py`.
7. Cosmetic items only in the store.
8. Every validator, engine or guardrail change needs a test. Keep the suite green.
9. Never put an API key in frontend code. Keys live in backend environment variables only.
10. Do not call an LLM live for every player action. Pre-generate, cache, cap and fall back (see AI cost rules).

## Layout

```
backend/formula_engine.py   tokenizer, parser, evaluator, allowlisted functions
backend/validator.py        compares the formula result to the expected value
backend/keys.py             answer keys computed independently from the engine
backend/guardrails.py       input filter, injection screening, output leak check
backend/tracing.py          JSONL traces with latency (CC_TRACE sets the file; request_id context var set by API middleware)
backend/api.py              FastAPI app wrapping GameService (CC_DB_PATH, CC_CORS_ORIGINS, ANTHROPIC_API_KEY)
backend/events.py           event bus and event names
backend/service.py          GameService plus Mission, Scoring and Store agents
backend/state.py            SQLite state: wallet, completed missions, inventory, hint cache, caps
backend/ai_config.py        model names, pricing and daily limit constants
backend/tutor.py            TutorAgent: live hints via Haiku with caching, caps and fallback
backend/mcp_server.py       MCP server exposing the game as 7 tools
backend/cricket_data.py     seeded synthetic datasets
backend/tests/              pytest suite
missions/                   mission JSON and store catalog
datasets/                   generated CSVs
evals/run_evals.py          quality report for validator, guardrails, hints
docs/DECISIONS.md           technology recommendations and reasoning
```

## Commands

```
pip install -e ".[dev]"
python -m pytest
python evals/run_evals.py
python evals/run_evals.py --live
python scripts/trace_report.py
python scripts/generate_missions.py --level 1 --zone "The Nets" --npc "Coach Rao" --topic wickets
python scripts/review_missions.py list
python scripts/review_missions.py approve <id>
python scripts/review_missions.py approve <id> --force
python scripts/merge_missions.py <id>
python -m backend.cricket_data
python -m backend.mcp_server
uvicorn backend.api:app --reload
CC_DB_PATH=game.db CC_CORS_ORIGINS='["http://localhost:5173"]' uvicorn backend.api:app --reload
```

Environment variables for the API:
CC_DB_PATH        SQLite file path (default: game.db)
CC_CORS_ORIGINS   JSON array or comma-separated allowed origins (default: http://localhost:5173)
ANTHROPIC_API_KEY Enables live Tutor hints; omit to disable
CC_TRACE          Trace output file (default: logs/trace.jsonl)

The project MCP server is registered in `.mcp.json`. Use it to play missions through real tool calls: get_next_mission, submit_answer, get_hint, ask_coach, get_wallet, list_store, buy_item.

## Engine functions supported today

SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, COUNTIF, COUNTIFS, SUMIF, SUMIFS, AVERAGEIF, IF, IFS, AND, OR, ROUND, ABS. Operators: + - * / ^ & and comparisons. ROUND follows Excel (half away from zero). Absolute references ($G$2, $G$2:$G$61) are handled. Next to add for Level 3: VLOOKUP, XLOOKUP, INDEX, MATCH, TRIM.

## Adding a mission

1. Add an entry to a `missions/levelN.json` file: id, level, zone, npc, title, story, task, dataset, answer_spec, reference_solution, required_any or required_all, three progressive hints, reward.
2. If the answer kind is new, add it to `backend/keys.py`.
3. If it needs a function the engine lacks, add it to `FUNCTIONS` with tests.
4. Hints must not contain the answer value or the formula. `tests/test_guardrails.py` enforces this.
5. Run `python -m pytest` and `python evals/run_evals.py`.

## Cricket datasets

Planned schemas, all synthetic and seeded:
1. players: player_id, name, role, batting_hand, bowling_style, team, age
2. matches: match_id, date, venue, format, team_a, team_b, winner
3. deliveries: match_id, over, ball, bowler, batter, runs, extras, wicket_type, dismissed_player
4. bowling_spells: match_id, bowler, overs, maidens, runs, wickets, economy (BUILT)
5. nets_sessions: date, bowler, balls_bowled, speed_kmh, line_length_score, pitch_zone
6. fitness_log: date, player, sprint_time, workload, sleep_hours
7. auction: player, base_price, sold_price, team

Cleaning missions need deliberate mess: extra spaces, mixed date formats, duplicate rows, numbers stored as text. Real data from Cricsheet is optional; check its licence first. Synthetic stays the default.

## Economy and attire

Coins come from missions: base reward plus a no-hint bonus of 10, with streak and speed bonuses planned. Item tiers: common, club, state, national, legendary. Slots: jersey, cap, shoes, sleeve, ball skin, kit bag. Planned extras: daily practice mission, weekly tournament, badges (First Wicket for first pass, Hat Trick for three passes in a row, Maiden Over for a no-hint pass).

## Planned tech stack

1. Frontend: TypeScript, Phaser 3 for the open world, a spreadsheet grid panel as an overlay when talking to an NPC. HyperFormula for instant in-browser feedback. On submit the server recomputes and checks, so the answer key never reaches the browser.
2. Backend: FastAPI wrapping GameService. Stateless, so it scales by adding instances.
3. Database: SQLite now, Postgres (Supabase or Neon) later. Redis (Upstash) for caching, rate limits, leaderboards.
4. Auth: Supabase Auth, Clerk or Firebase Auth, with Google login.
5. Hosting: static frontend on a CDN (Cloudflare Pages or Vercel). Backend on Cloud Run, Fly.io or Railway. Infrastructure as code with Terraform or Pulumi.
6. Analytics and errors: PostHog and Sentry.

## AI cost rules

1. Claude API is separate from the Claude subscription. Keys come from the Claude Console with prepaid credits and a monthly spend limit.
2. Models: Haiku for live hints (CC_TUTOR_MODEL, default claude-haiku-5-5), Sonnet for offline mission generation (GENERATOR_MODEL), Opus only offline for authoring boss missions. All model names and prices live in backend/ai_config.py. Haiku prices are listed as "from" prices on the official page and should be treated as a floor.
3. Validator is pure code, zero cost.
4. Pre-generate mission variants offline in batches using scripts/generate_missions.py, review with scripts/review_missions.py, and merge into the game with scripts/merge_missions.py.
5. Tutor hints are the only live LLM call. Cap per player per day (CC_DAILY_PLAYER_CAP, default 5). Cache hints by mission id, failure code and hint level when message is None and failure_code is non-empty. Fall back to static hints on any failure, API error, or cap hit.
6. Hard daily AI budget in code (CC_DAILY_BUDGET_USD, default $1.00). The live eval mode uses a separate $0.05 ceiling and a temporary database.
7. Personalised hints (last formula and failure code) are cached only for cacheable requests. Chat replies are never cached so one player's session never reaches another player.

## Traffic readiness

CDN for static assets, stateless backend, queue for slow work (reward processing, generation), rate limits per player and per IP, DB indexes on player_id and mission_id, connection pooling, load test with k6 before any launch push. Do not over-engineer early: build Phases 0 to 2 simply, with a design that scales without a rewrite.

## Open world feature backlog

Camera easing, chunked tile maps, spreadsheet overlay without scene change, mobile joystick, day and night cycle, weather events, NPC routines, quest markers and minimap, fast travel by auto rickshaw or team bus, zones that visibly improve with level, a nets bowling mini game that boosts coins, match day scheduled missions, an Auction Room mission chain, live wardrobe preview with set bonuses, streaks, leaderboards, badges, sound and commentary. Later: ghost players via WebSockets. Single player first.

## Build phases

1. Phase 0, done: design, schemas, mission JSON.
2. Phase 1, done: engine, validator, 3 Level 1 missions, agents on the bus, guardrails, tracing, MCP server.
3. Phase 2, in progress: IFS, AND, OR added to engine, absolute references tested, 4 Level 2 missions added. Remaining: FastAPI layer, character creator, simple web grid UI, world map with 2 zones.
4. Phase 3, done. Stage 3A: Tutor Agent live with Haiku, ai_config.py for model names and pricing, state.py extended with hint cache and daily caps, full tracing. Stage 3B: scripts/generate_missions.py (offline Sonnet generation with validation pipeline), scripts/review_missions.py (approve or reject workflow), scripts/merge_missions.py (promote to levelN.json), missions/generated/ pending directory. Stage 3C: adversarial eval set (evals/adversarial_cases.json, 27 cases), offline tutor evals and live eval mode in run_evals.py, scripts/trace_report.py for log summaries, HintProvider Protocol in tutor.py, DECISIONS.md entry for agent framework choice, CLAUDE.md updated.
5. Phase 2 (FastAPI layer), Stage 2A done. backend/api.py wraps GameService: 10 frontend endpoints (world, player, encounter, answer, begin, lesson, facility, store/buy, avatar/equip, clubs, leaderboard), Bearer token player identity, NPC encounter service (EncounterService), question generator (question_gen.py), NPC config (npc_config.py), game config constants (game_config.py), new DB tables (skill_xp, encounters, sessions, checkpoints, facility_visits, leaderboard), player snapshot helper, appearance validation with hex colours. Frontend (game_frontend_new/project/Prototype.dc.html) wired to real backend via HttpAdapter; character creator, NPC encounters, formula answers, coins/XP, store and equip all persist to SQLite. Test suite: 289 passed, 2 skipped, 10 xfailed. Stage 2B: deeper frontend features (session/exam flow, club progression UI) pending.
6. Phase 4: Dataset and Adaptive Difficulty agents, Levels 3 to 5.
6. Phase 5: Levels 6 and 7, polish, sound, playtest, Terraform deployment.

## Engineering showcase goals

Keep these visible and demonstrable: MCP server, guardrails with a growing injection regression set, evals and observability (traces now carry latency, extend with model, tokens, cost), agent orchestration through events, AI coding agent configuration (this file, `.mcp.json`, `.cursor/rules`, `.github/copilot-instructions.md`), and infrastructure as code. Record each technology choice in `docs/DECISIONS.md` with what was evaluated, the recommendation and when to revisit.

## Conventions

Python 3.11+, type hints on public functions, stdlib first, small single purpose modules. Tests for every behaviour change. Prefer editing existing files to adding new ones. Do not claim a feature works until a test or a run proves it. Commit messages are short and imperative.

## How to work with the owner

1. Before big choices (framework, cloud, schema changes), give two or three options with a recommendation and ask.
2. Small, clear tasks: just do them, run the tests, and report in a few lines.
3. Be honest about what is built versus planned. Update the status markers in this file when that changes.
4. Formatting for anything written for the owner to read or paste into Google Docs: no ** bold markers, no dash bullets, no em dashes. Use plain sentences and numbered lists.
5. Be direct about problems. If a request would break one of the rules above, say so and propose an alternative.

## Open decisions

1. Hosting provider for frontend and backend
2. Auth provider
3. How to evaluate Sheets-only functions (custom evaluator versus pre-verified missions)
4. Agent framework for the Claude-backed agents (plain SDK versus Claude Agent SDK versus LangGraph)
5. Multiplayer in first public version (recommendation: no, single player first)

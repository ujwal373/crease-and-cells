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
5. Tutor Agent, PLANNED: progressive hints today are static text. Planned: Claude Haiku generates hints from the player's formula and error, but never receives the answer key.
6. Dataset Agent, PLANNED: seeded cricket data generators. One generator exists (bowling_spells).
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
backend/tracing.py          JSONL traces with latency (CC_TRACE sets the file)
backend/events.py           event bus and event names
backend/service.py          GameService plus Mission, Scoring and Store agents
backend/state.py            SQLite state: wallet, completed missions, inventory
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
python -m backend.cricket_data
python -m backend.mcp_server
```

The project MCP server is registered in `.mcp.json`. Use it to play missions through real tool calls: get_next_mission, submit_answer, get_hint, ask_coach, get_wallet, list_store, buy_item.

## Engine functions supported today

SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, COUNTIF, COUNTIFS, SUMIF, SUMIFS, AVERAGEIF, IF, ROUND, ABS. Operators: + - * / ^ & and comparisons. ROUND follows Excel (half away from zero). Next to add for Level 2 and 3: IFS, AND, OR, VLOOKUP, XLOOKUP, INDEX, MATCH, TRIM, plus absolute reference handling tests.

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
2. Models: Haiku for hints and NPC chatter, Sonnet for mission generation and explanations, Opus only offline for authoring boss missions. Check current pricing before budgeting.
3. Validator is pure code, zero cost.
4. Pre-generate mission variants offline in batches, store them, and serve from the database.
5. Tutor hints are the only live LLM call: cap per player per day, cache common hints by mission and error type, and fall back to static hints if the API is slow or down.
6. Enforce a hard daily AI budget in code.

## Traffic readiness

CDN for static assets, stateless backend, queue for slow work (reward processing, generation), rate limits per player and per IP, DB indexes on player_id and mission_id, connection pooling, load test with k6 before any launch push. Do not over-engineer early: build Phases 0 to 2 simply, with a design that scales without a rewrite.

## Open world feature backlog

Camera easing, chunked tile maps, spreadsheet overlay without scene change, mobile joystick, day and night cycle, weather events, NPC routines, quest markers and minimap, fast travel by auto rickshaw or team bus, zones that visibly improve with level, a nets bowling mini game that boosts coins, match day scheduled missions, an Auction Room mission chain, live wardrobe preview with set bonuses, streaks, leaderboards, badges, sound and commentary. Later: ghost players via WebSockets. Single player first.

## Build phases

1. Phase 0, done: design, schemas, mission JSON.
2. Phase 1, done: engine, validator, 3 Level 1 missions, agents on the bus, guardrails, tracing, MCP server.
3. Phase 2, next: more Level 1 and 2 missions and functions, FastAPI layer, character creator, simple web grid UI, world map with 2 zones.
4. Phase 3: Claude-backed Mission and Tutor agents behind the guardrails, with evals and token and cost tracing.
5. Phase 4: Dataset and Adaptive Difficulty agents, Levels 3 to 5.
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

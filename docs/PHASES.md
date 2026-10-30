# Build phase notes

This file records the full task text for each build phase so it survives context compression.

---

## Stage 3C

Read CLAUDE.md first. Stages 3A and 3B and the follow-up fixes are done. Do only this stage, then show me a summary.

Context: the live Tutor is backend/tutor.py (TutorAgent, Haiku, injected client, cache, daily caps, budget cap). Replies pass guardrails.check_tutor_output. Tests use a fake client, so no network or API key is needed. Traces go to logs/trace.jsonl through backend/tracing.py.

1. Adversarial eval set. Create evals/adversarial_cases.json with at least 25 cases in these groups: formulas and chat messages that try to extract the answer, role play requests, delimiter breakouts (for example closing the player_formula or player_message tags and adding new instructions), requests in other languages, and requests to spell the answer in words. Each case has an id, a group, the input, and what must happen (blocked before the model, or reply replaced by the static hint).

2. Offline tutor evals in evals/run_evals.py using the fake client. Fake replies should include deliberately bad ones: a reply with the answer number, a reply with the exact formula, an equivalent formula with a different range, a function call with no equals sign, and a clean reply. Report three rates: leak rate (must be 0 percent), block rate for adversarial inputs, and fallback rate. Also include the personalised inputs (last formula and failure code reaching the prompt) and the new formula guard in these checks. Exit non-zero if the leak rate is not 0 or any adversarial case that must be blocked is not blocked.

3. Live eval mode: add a --live flag. It must refuse to run without ANTHROPIC_API_KEY, use a temporary database, run at most 8 cases, enforce a hard cost ceiling of 0.05 dollars using the existing cost_usd, and check each reply for length (3 sentences or fewer), leaks, and formula-shaped text. Print total input tokens, output tokens, cost and latency per case. It never runs in the normal test suite.

4. Trace summary: add scripts/trace_report.py that reads logs/trace.jsonl and prints a plain table with total calls, cache hit rate, fallback rate with reasons, average and 95th percentile latency, total input and output tokens, and total cost, grouped by model. Handle a missing or empty file politely. Add a test with a small sample trace file.

5. Agent interface and decision record: define a small Protocol in backend/tutor.py (for example HintProvider with one get_hint method) that TutorAgent implements, and have GameService depend on the Protocol, so the tutor can be swapped later. Add an entry to docs/DECISIONS.md comparing the plain Anthropic SDK, the Claude Agent SDK and LangGraph for the Claude-backed agents. Recommend the plain SDK for now, explain why (small fixed workflow, full control of guardrails, caching and cost, fewer dependencies), and say when to revisit (multi-step tool-using agents, long running tasks, or human approval flows).

6. Update CLAUDE.md: mark the Tutor Agent and offline Mission generation as BUILT, update the AI cost rules to match the real caps and models, add the new commands (evals, live eval, trace report, generate, review, merge missions), and update the build phases section.

7. Run python -m pytest and python evals/run_evals.py. Both must pass.

Formatting for anything you write for me to read: no ** bold markers, no dash bullets, no em dashes.

---

## Phase 2

Save this whole task text into docs/PHASES.md under the heading Phase 2 before coding. Read CLAUDE.md fully before doing anything. Then do the rest of Phase 2 in two stages. After each stage, run python -m pytest and python evals/run_evals.py, show me a short summary, and STOP and wait for my go ahead. Do not start the next stage early.

Rules: the answer key, answer_spec and reference_solution never leave the backend. No API key in any frontend file. GameService stays the single source of truth, so do not copy game logic into the API layer or the frontend.

Stage 2A: FastAPI layer

1. Add fastapi, uvicorn and httpx (for tests) to pyproject.toml dependencies.

2. Create backend/api.py. It wraps GameService in a FastAPI app. Endpoints: next_mission, submit_answer, hint, ask_coach, wallet, store_list, buy_item.

3. Define a Pydantic response model for every endpoint that lists only the allowed public fields. Use extra=ignore so a new private field can never leak by accident. Add a test that walks the generated OpenAPI schema and fails if any field named answer_spec, reference_solution, hints, required_all or required_any appears in a response model.

4. Add a preview endpoint. It evaluates a formula against the mission sheet with the existing formula engine and returns only the resulting value or an error code. It must not return pass or fail, rewards, or anything about the answer. Apply a stricter per-player rate limit on this endpoint.

5. Validate player IDs as UUID v4. Add a comment marking where auth will plug in later.

6. Add request size limits (reject bodies larger than 10 KB), CORS restricted to origins listed in the CC_CORS_ORIGINS env var (default localhost:5173), and simple in-memory per-player and per-IP rate limiting. Document in code that the in-memory limiter needs Redis for multi-instance deployments.

7. The API must build GameService with the tutor client when ANTHROPIC_API_KEY is set, the same way backend/mcp_server.py does, and run without it otherwise.

8. GameState currently uses one shared SQLite connection. Make it safe for concurrent requests (a lock, or a connection per call with WAL mode). Write a concurrency test showing that many simultaneous purchases or submissions never overspend coins or double-award a mission.

9. Return clear error shapes (never raw exception text). Return 404 for unknown mission IDs. Return 429 for rate-limit violations.

10. Tests in backend/tests/test_api.py using FastAPI TestClient. Cover: no private fields in any response, preview endpoint reveals nothing about correctness, oversized body is rejected, rate limit triggers 429, invalid player ID is rejected, a blocked injection to the coach returns a safe reply.

11. Add an entry to docs/DECISIONS.md on the preview endpoint decision: server-side preview with the existing formula engine versus HyperFormula running in the browser.

12. Update CLAUDE.md: add the uvicorn run command and any new env vars (CC_CORS_ORIGINS, CC_DB_PATH).

Stage 2B: first playable web page

Do not start Stage 2B until Stage 2A is reviewed and approved.

1. Create a frontend/ directory. Use Vite with TypeScript in strict mode. No framework (plain TypeScript), unless Phaser is already a dependency from CLAUDE.md, in which case add it now but do not start the full open world yet.

2. Build one page with three panels: a mission panel (NPC name, title, story, task), a spreadsheet grid, and a formula bar with a Submit button and a Hint button. Add a coach chat input below the grid. Add a wallet display (coins, xp, level) in the corner, and a Store button that opens a simple overlay list of items.

3. Store the player ID in localStorage (with try/catch, fall back to a freshly generated UUID v4 if localStorage is unavailable or empty).

4. Wire the preview call to the formula bar with a short debounce (300 ms). Show the preview result in a small status line. Preview must never show pass or fail, only the computed value or an error code.

5. On submit, show a clear pass or fail message. On a pass, show the coins and xp awarded. On a fail, show the reason. The Submit button must be disabled while a request is in flight.

6. Friendly messages for error states: rate limit hit, server down, invalid formula. Mobile-friendly layout (the grid scrolls horizontally on small screens).

7. Add a brief README section on how to run both processes together (uvicorn and vite dev server), and what CORS origins to set.

Formatting for anything you write for me to read: no ** bold markers, no dash bullets, no em dashes.

---

## Phase 2 part 2

Save this whole task text into docs/PHASES.md under the heading Phase 2 part 2 before coding. Read CLAUDE.md and docs/PHASES.md first. Do two stages. After each stage run python -m pytest, python evals/run_evals.py and the frontend type check and build, show me a short summary, and STOP and wait for my go ahead.

Rules: the server decides which mission a player gets and what they earn. The world is only a way to reach missions, never a place where rewards or progress are calculated. No game logic copied into the frontend. No copyrighted art or characters: draw placeholder art in code, or use CC0 assets and record each one with its licence in docs/ASSETS.md.

STAGE 2C: Character creator

Backend: add an appearance table (player_id, display_name, body_type, skin_tone, hair_style, hair_colour). Serve GET /api/appearance and POST /api/appearance. Validate every field server-side against an allowlist. Filter display_name through the existing guardrails.check_chat_input and cap it at 30 characters. Include the appearance object in the wallet response. Tests: validation rejects bad values, injection name blocked, no cross-player access, wallet includes appearance.

Frontend: character creator screen shown on first visit (no cc_creator_done in localStorage) and reachable from a Customize button in the wallet bar. Form fields: display_name (default Ujwal Mojidra), body_type, skin_tone, hair_style, hair_colour. Live canvas preview updates on every change. Save calls POST /api/appearance. On success set cc_creator_done in localStorage and update the wallet display.

Character renderer module frontend/src/character.ts: exports drawCharacter(ctx, width, height, appearance, outfit). Draws a layered cricket player using Canvas 2D geometric shapes only, no external images. Layers in order: trousers, jersey body, arms with optional sleeve bands, shoes, neck, head, hair, cap. Scales uniformly from a 200x300 design space. Reusable for the world sprite in Stage 2D.

STAGE 2D: Open world with Phaser 3

npm install phaser (lazily imported so the mission UI does not wait for it). Two zones on a single tilemap: The Nets (always open) and Club House (visually locked, door blocked until level 2). Tile-based maps with collision layers, drawn procedurally in code (no Tiled files or external tileset images). Movement: WASD and arrow keys, plus a virtual on-screen joystick for touch. NPCs standing at fixed positions with a quest-marker sprite above them. Clicking or walking into range of an NPC opens the mission panel as an overlay without a scene change. Club House door shows a locked padlock and a level-2 tooltip when the player is below level 2. Player sprite generated from the character renderer at 48x72, cached as a Phaser texture. vitest unit tests for pure logic only (tile collision checks, zone unlock predicate). README: add Phaser note and how to start the world. Commit separately from Stage 2C.

Formatting for anything you write for me to read: no ** bold markers, no dash bullets, no em dashes.

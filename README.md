# Crease and Cells

Learn Excel and Google Sheets by helping people in a cricket world. Solve missions with real formulas, earn coins, upgrade your kit.

## Status

Built and tested (Phase 0 and 1 vertical slice):

- Deterministic formula engine (SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, COUNTIF, COUNTIFS, SUMIF, SUMIFS, AVERAGEIF, IF, ROUND, ABS)
- Validator with independent answer keys, hardcode detection and required-function checks
- Seeded synthetic cricket datasets
- Mission, Scoring and Store agents on an event bus
- Guardrails: formula input filter, injection screening for the coach, output leak check
- JSONL tracing with latency on every call
- MCP server exposing the game as tools
- 84 tests and an eval report

Phase 2 complete: FastAPI layer, character creator, Phaser 3 open world (two zones, procedural tile map, WASD and touch joystick, NPC interaction). Planned: Adaptive Difficulty agent, Levels 3 to 7, Terraform deployment.

## Quick start

    pip install -e ".[dev]"
    python -m pytest
    python evals/run_evals.py
    python -m backend.mcp_server

Add the server to Claude Code with the `.mcp.json` in this repo, then ask Claude to play: get a mission, submit a formula, check the wallet, buy a cap.

## Running locally

Start both processes from the project root.

Backend (port 8000):

    CC_DB_PATH=game.db CC_CORS_ORIGINS='["http://localhost:5173"]' uvicorn backend.api:app --reload

The default CC_CORS_ORIGINS already allows localhost:5173, so the env var above is only needed if you change the frontend port.

Frontend (port 5173):

    cd frontend
    npm install
    npm run dev

The Vite dev server proxies all /api/* requests to localhost:8000, so no CORS configuration is required during development. Open http://localhost:5173 in a browser.

For a production build:

    cd frontend && npm run build

The output is in frontend/dist. Serve it from any static host and set VITE_API_URL to the backend's public URL at build time:

    VITE_API_URL=https://your-backend.example.com npm run build

## Open world (Phaser 3)

The frontend includes a Phaser 3 open world behind the "Open World" button. Phaser is lazily
imported so the mission UI loads instantly without waiting for the 1.4 MB game engine.

Two zones are on the map: The Nets (always open) and Club House (door locked until level 2).
All tile graphics are drawn procedurally in code with Phaser GameObjects.Graphics. No external
tileset images or Tiled files are used. The player sprite comes from the character renderer at
48x72. Movement: WASD, arrow keys, and a virtual on-screen joystick for touch devices.

Walking into range of an NPC or clicking on them opens the mission panel as a side overlay
without stopping or restarting the Phaser scene. The "Back to World" button dismisses the panel
and returns focus to the world.

To run the frontend tests:

    cd frontend && npm test

## Design notes

See CLAUDE.md for the rules and layout, and docs/DECISIONS.md for the technology recommendations.

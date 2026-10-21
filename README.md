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

Planned: Phaser 3 world and spreadsheet panel, FastAPI layer, LLM-backed Tutor and Mission generation, Adaptive Difficulty agent, character creator, Terraform deployment, Levels 2 to 7.

## Quick start

    pip install -e ".[dev]"
    python -m pytest
    python evals/run_evals.py
    python -m backend.mcp_server

Add the server to Claude Code with the `.mcp.json` in this repo, then ask Claude to play: get a mission, submit a formula, check the wallet, buy a cap.

## Design notes

See CLAUDE.md for the rules and layout, and docs/DECISIONS.md for the technology recommendations.

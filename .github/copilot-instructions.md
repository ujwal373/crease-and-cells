Read CLAUDE.md at the repo root before changing code. Key rules:

- The validator is deterministic code. Never use an LLM to judge answers.
- Answer keys and reference solutions never go into prompts or public payloads.
- No eval or exec. Formula functions live in an allowlist in backend/formula_engine.py.
- Agents communicate only through the event bus in backend/events.py.
- Every validator or guardrail change needs a test. Run `python -m pytest` before finishing.

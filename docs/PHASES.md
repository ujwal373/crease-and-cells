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

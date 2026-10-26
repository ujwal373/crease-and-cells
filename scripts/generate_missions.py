"""Offline mission generator using Claude Sonnet.

This script is an offline tool; it is never called at request time.
Run it in a batch to produce mission candidates for human review.

Usage:
  python scripts/generate_missions.py \\
      --level 1 --zone "The Nets" --npc "Coach Rao" --topic wickets

Rules that must always hold:
  1. The model is never given answer keys, reference solutions, or expected
     values for existing missions.
  2. The model generates the formula and answer_spec as output; the validator
     then independently evaluates the formula on real data and compares.
  3. Generated missions land in missions/generated/ with status=pending_review
     until a human runs review_missions.py to approve or reject them.
  4. No generated mission is ever loaded by the game engine until it has been
     manually moved into a levelN.json file.
"""
from __future__ import annotations

import json
import math
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.ai_config import GENERATOR_MODEL
from backend.cricket_data import GENERATORS, to_grid
from backend.formula_engine import FormulaError, Grid, evaluate
from backend.guardrails import check_output
from backend.keys import compute_answer

GENERATED_DIR = ROOT / "missions" / "generated"


# ---------------------------------------------------------------------------
# Column metadata exposed to the model (no actual data values)
# ---------------------------------------------------------------------------
_DATASET_SCHEMA = {
    "bowling_spells": {
        "columns": [
            ("A", "match_id",  "text",   "e.g. M001"),
            ("B", "bowler",    "text",   "player name, e.g. Ujwal Mojidra (the hero)"),
            ("C", "overs",     "int",    "overs bowled: 2, 3 or 4"),
            ("D", "maidens",   "int",    "maiden overs: 0 or 1"),
            ("E", "runs",      "int",    "runs conceded"),
            ("F", "wickets",   "int",    "wickets taken: 0, 1, 2 or 3"),
            ("G", "economy",   "float",  "runs per over, e.g. 7.50"),
        ]
    }
}

_ANSWER_SPEC_GUIDE = """
Valid answer_spec kinds (use exactly one):

count_gt     Count rows where one numeric field exceeds a threshold.
             {"kind":"count_gt","field":"economy","value":8}

sum_where    Sum one field only for rows where another field equals a value.
             {"kind":"sum_where","where_field":"bowler","where_value":"Ujwal Mojidra","sum_field":"wickets"}

avg_where_round  Average one field filtered by another, rounded.
             {"kind":"avg_where_round","where_field":"bowler","where_value":"Ujwal Mojidra","avg_field":"economy","digits":2}

count_multi  Count rows satisfying all conditions.
             {"kind":"count_multi","conditions":[{"field":"wickets","op":">=","value":2},{"field":"economy","op":"<","value":8}]}

sum_multi    Sum a field across rows satisfying all conditions.
             {"kind":"sum_multi","sum_field":"runs","conditions":[{"field":"bowler","op":"=","value":"Ujwal Mojidra"},{"field":"wickets","op":">=","value":1}]}
"""

_FUNCTIONS_BY_LEVEL = {
    1: ["SUM", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTA", "COUNTIF", "SUMIF", "AVERAGEIF", "ROUND"],
    2: ["COUNTIFS", "SUMIFS", "IF", "IFS", "AND", "OR"],
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class GenerateResult:
    mission: dict | None
    status: str                      # "verified" | "needs_review" | "invalid"
    validation_errors: list[str] = field(default_factory=list)
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class MissionGenerator:
    """Offline Sonnet-backed mission generator. Inject client for tests."""

    def __init__(self, client=None) -> None:
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client
        import anthropic  # noqa: PLC0415
        return anthropic.Anthropic()

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a mission designer for Crease and Cells, a cricket-themed game that "
            "teaches spreadsheet formulas. Your output must be a single valid JSON object "
            "and nothing else: no preamble, no explanation, no markdown fences."
        )

    @staticmethod
    def _user_prompt(
        level: int, zone: str, npc: str, topic: str, seed: int, rows: int
    ) -> str:
        col_lines = "\n".join(
            f"  {col} ({letter}): {kind} — {note}"
            for letter, col, kind, note in _DATASET_SCHEMA["bowling_spells"]["columns"]
        )
        all_funcs = list(_FUNCTIONS_BY_LEVEL[1])
        if level >= 2:
            all_funcs += list(_FUNCTIONS_BY_LEVEL[2])
        fn_str = ", ".join(all_funcs)

        return (
            f"Generate one Level {level} mission for the \"{zone}\" zone.\n\n"
            f"Dataset: bowling_spells (seed {seed}, {rows} data rows, header row 1, data rows 2 to {rows + 1})\n"
            f"Columns:\n{col_lines}\n\n"
            f"Functions available: {fn_str}\n"
            f"NPC: {npc}\n"
            f"Topic: {topic}\n\n"
            "Return a JSON object with exactly these keys:\n"
            "{\n"
            '  "title": "short catchy title",\n'
            '  "story": "2-3 sentences of cricket narrative from the NPC",\n'
            '  "task": "clear task stating which columns to use by letter and name, which rows, and what formula to write",\n'
            f'  "npc": "{npc}",\n'
            '  "reference_solution": "=FORMULA(...)",\n'
            '  "answer_spec": { ... },\n'
            '  "hints": ["hint 1", "hint 2", "hint 3"],\n'
            '  "required_any": ["FUNCTION_NAME"] or [],\n'
            '  "required_all": ["FUNCTION_NAME"] or []\n'
            "}\n\n"
            + _ANSWER_SPEC_GUIDE
            + "\nHint rules (the game enforces these, so follow them carefully):\n"
            "1. Hint 1: a conceptual nudge with no formula syntax.\n"
            "2. Hint 2: structural guidance on how the formula is shaped.\n"
            "3. Hint 3: near-complete structure described in words, with column letters as references.\n"
            "4. NEVER write the complete formula in any hint.\n"
            "5. NEVER write a specific number that is the final answer in any hint.\n"
        )

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    def _call_model(self, level: int, zone: str, npc: str, topic: str, seed: int, rows: int) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=GENERATOR_MODEL,
            max_tokens=1024,
            system=self._system_prompt(),
            messages=[{"role": "user", "content": self._user_prompt(level, zone, npc, topic, seed, rows)}],
        )
        return response.content[0].text

    # ------------------------------------------------------------------
    # Validation pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(raw: str, level: int, zone: str, npc: str, seed: int, rows: int) -> GenerateResult:
        errors: list[str] = []

        # Step 1: JSON parse
        raw_stripped = raw.strip()
        # Strip any accidental markdown fences
        if raw_stripped.startswith("```"):
            raw_stripped = re.sub(r"^```[a-z]*\n?", "", raw_stripped)
            raw_stripped = re.sub(r"\n?```$", "", raw_stripped.strip())
        try:
            doc = json.loads(raw_stripped)
        except json.JSONDecodeError as exc:
            return GenerateResult(None, "invalid", [f"json_parse: {exc}"], raw)

        # Step 2: Required fields
        required = {"title", "story", "task", "npc", "reference_solution", "answer_spec", "hints",
                    "required_any", "required_all"}
        missing = required - doc.keys()
        if missing:
            return GenerateResult(doc, "invalid", [f"missing_fields: {sorted(missing)}"], raw)

        ref_sol = doc["reference_solution"]
        if not isinstance(ref_sol, str) or not ref_sol.startswith("="):
            return GenerateResult(doc, "invalid", [f"bad_reference_solution: must start with ="], raw)

        hints = doc.get("hints", [])
        if not isinstance(hints, list) or len(hints) != 3:
            return GenerateResult(doc, "invalid", [f"hints must be a list of 3 strings"], raw)

        # Step 3: Load dataset
        gen, cols = GENERATORS["bowling_spells"]
        dataset_rows = gen(seed, rows)
        grid = Grid(to_grid(cols, dataset_rows))

        # Step 4: Evaluate the formula
        try:
            eval_result = evaluate(ref_sol, grid)
            formula_value = eval_result.value
        except FormulaError as exc:
            return GenerateResult(doc, "invalid", [f"formula_error: {exc}"], raw)

        # Step 5: Compute answer from answer_spec
        try:
            spec_value = compute_answer(doc["answer_spec"], dataset_rows)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"answer_spec_error: {exc}")
            spec_value = None

        # Step 6: Compare formula result vs answer_spec result
        if spec_value is not None:
            def _close(a, b) -> bool:
                if isinstance(a, float) and isinstance(b, float):
                    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
                return a == b

            if not _close(formula_value, spec_value):
                errors.append(
                    f"answer_mismatch: formula={formula_value!r} answer_spec={spec_value!r}"
                )

        # Step 7: Hint guardrail check
        from backend.service import _fmt_secret  # avoid circular at module load
        secrets = _fmt_secret(formula_value) + [ref_sol]
        for i, hint in enumerate(hints, 1):
            if not isinstance(hint, str) or not hint.strip():
                errors.append(f"hint_{i}_empty")
                continue
            guard = check_output(hint, secrets)
            if not guard.allowed:
                errors.append(f"hint_{i}_leaks: {guard.reason}")

        # Assemble the full mission dict
        mission = {
            "id": f"GEN-{uuid.uuid4().hex[:8].upper()}",
            "level": level,
            "zone": zone,
            "npc": doc["npc"],
            "title": doc["title"],
            "story": doc["story"],
            "task": doc["task"],
            "dataset": {"generator": "bowling_spells", "seed": seed, "rows": rows},
            "answer_spec": doc["answer_spec"],
            "reference_solution": ref_sol,
            "required_all": doc.get("required_all", []),
            "required_any": doc.get("required_any", []),
            "hints": hints,
            "reward": {"coins": 50 + level * 10, "xp": 100 + level * 10},
            "status": "verified" if not errors else "needs_review",
        }

        status = "verified" if not errors else "needs_review"
        return GenerateResult(mission, status, errors, raw)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        level: int = 1,
        zone: str = "The Nets",
        npc: str = "Coach Rao",
        topic: str = "wickets",
        seed: int = 101,
        rows: int = 60,
    ) -> GenerateResult:
        try:
            raw = self._call_model(level, zone, npc, topic, seed, rows)
        except Exception as exc:
            return GenerateResult(None, "invalid", [f"api_error: {type(exc).__name__}: {exc}"], "")
        return self._validate(raw, level, zone, npc, seed, rows)


def save_result(result: GenerateResult, out_dir: Path = GENERATED_DIR) -> Path | None:
    """Write the generated mission JSON to missions/generated/. Returns the path or None."""
    if result.mission is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = result.mission["id"].lower()
    path = out_dir / f"{slug}.json"
    path.write_text(json.dumps(result.mission, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate a mission offline using Claude Sonnet.")
    parser.add_argument("--level",  type=int, default=1)
    parser.add_argument("--zone",   default="The Nets")
    parser.add_argument("--npc",    default="Coach Rao")
    parser.add_argument("--topic",  default="wickets")
    parser.add_argument("--seed",   type=int, default=101)
    parser.add_argument("--rows",   type=int, default=60)
    parser.add_argument("--dry-run", action="store_true", help="print but do not save")
    args = parser.parse_args(argv)

    print(f"Generating Level {args.level} mission via {GENERATOR_MODEL}...")
    gen = MissionGenerator()
    result = gen.generate(
        level=args.level, zone=args.zone, npc=args.npc,
        topic=args.topic, seed=args.seed, rows=args.rows,
    )

    print(f"Status: {result.status}")
    if result.validation_errors:
        print("Validation errors:")
        for e in result.validation_errors:
            print(f"  {e}")

    if result.mission:
        print(json.dumps(result.mission, indent=2))

    if not args.dry_run and result.mission is not None:
        path = save_result(result)
        print(f"Saved to {path}")


if __name__ == "__main__":
    main()

"""Mission answer validator. Deterministic code only, never an LLM.

Failure reasons are deliberately vague about the expected value so a wrong
answer never leaks the answer key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .formula_engine import FormulaError, Grid, evaluate


@dataclass
class ValidationResult:
    passed: bool
    reason: str
    player_value: Any = None


def validate(
    formula: str,
    grid: Grid,
    expected: Any,
    required_all: Iterable[str] = (),
    required_any: Iterable[str] = (),
    tol: float = 1e-6,
) -> ValidationResult:
    try:
        res = evaluate(formula, grid)
    except FormulaError as err:
        return ValidationResult(False, f"formula_error: {err.code} {err.detail}".strip())

    if res.reference_count == 0:
        return ValidationResult(False, "hardcoded_value: use cells from the sheet, not typed-in numbers", res.value)

    missing = [f for f in required_all if f.upper() not in res.functions]
    if missing:
        return ValidationResult(False, "missing_function: this mission needs " + ", ".join(missing), res.value)

    any_of = [f.upper() for f in required_any]
    if any_of and not (set(any_of) & res.functions):
        return ValidationResult(False, "missing_function: use one of " + ", ".join(any_of), res.value)

    got = res.value
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        ok = isinstance(got, (int, float)) and not isinstance(got, bool) and abs(float(got) - float(expected)) <= tol
    else:
        ok = str(got).strip().lower() == str(expected).strip().lower()
    return ValidationResult(ok, "correct" if ok else "wrong_value", got)

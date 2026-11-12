"""Tests for the deterministic question generator (question_gen.py)."""
from __future__ import annotations

import pytest

from backend.formula_engine import Grid, evaluate
from backend.game_config import FAMILY_IDS
from backend.question_gen import build_question, reward_for

# Families whose model formulas use only functions currently in the engine.
# text/date/lookup/stats/arrays use UPPER, LEFT, TRIM, DAYS, DATE, MONTH,
# VLOOKUP, INDEX, MATCH, XLOOKUP, MEDIAN, LARGE, SUMPRODUCT, COUNTUNIQUE —
# none of which are in the engine yet.  Add families here as functions land.
_ENGINE_FAMILIES = ["maths", "logic"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_seed_same_question():
    q1 = build_question("maths", 1, 42)
    q2 = build_question("maths", 1, 42)
    assert q1 == q2


def test_different_seeds_different_questions():
    q1 = build_question("maths", 1, 1)
    q2 = build_question("maths", 1, 2)
    assert q1["story"] != q2["story"] or q1["rows"] != q2["rows"]


def test_difficulty_affects_reward():
    c1, x1 = reward_for(1, 0)
    c3, x3 = reward_for(3, 0)
    assert c3 > c1 and x3 > x1


# ---------------------------------------------------------------------------
# Shape: all families return valid structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family", FAMILY_IDS)
def test_all_families_return_valid_shape(family):
    if family not in _ENGINE_FAMILIES:
        pytest.xfail(f"'{family}' templates use functions not yet in the engine")
    q = build_question(family, 2, 7)
    assert isinstance(q["rows"], list) and len(q["rows"]) >= 2
    assert isinstance(q["tr"], int)
    assert isinstance(q["tc"], int)
    assert isinstance(q["model"], str) and q["model"].startswith("=")
    assert isinstance(q["must_use"], list)  # may be empty for some templates
    assert isinstance(q["story"], str) and len(q["story"]) > 10
    assert isinstance(q["task"], str) and len(q["task"]) > 5
    assert isinstance(q["hint"], str)
    assert isinstance(q["explain"], str)
    assert q["expected"] is not None


@pytest.mark.parametrize("family", FAMILY_IDS)
def test_all_families_target_cell_in_bounds(family):
    if family not in _ENGINE_FAMILIES:
        pytest.xfail(f"'{family}' templates use functions not yet in the engine")
    q = build_question(family, 2, 13)
    assert 0 <= q["tr"] < len(q["rows"])
    assert 0 <= q["tc"] < len(q["rows"][q["tr"]])


# ---------------------------------------------------------------------------
# Correctness: model formula evaluates to expected value
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family", _ENGINE_FAMILIES)
@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_model_evaluates_to_expected(family, difficulty):
    q = build_question(family, difficulty, 55)
    grid = Grid(q["rows"])
    result = evaluate(q["model"], grid)
    got = result.value if hasattr(result, "value") else result
    expected = q["expected"]
    if isinstance(expected, bool) or isinstance(got, bool):
        assert got == expected
    else:
        try:
            gf, ef = float(got), float(expected)
            if ef == 0:
                assert abs(gf) < 1e-6
            else:
                assert abs(gf - ef) / max(abs(ef), 1e-9) < 1e-5, (
                    f"{family} diff={difficulty}: got {got}, expected {expected}"
                )
        except (TypeError, ValueError):
            assert str(got).strip().lower() == str(expected).strip().lower()


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------

def test_reward_for_increases_with_difficulty():
    c1, x1 = reward_for(1, 0)
    c2, x2 = reward_for(2, 0)
    c3, x3 = reward_for(3, 0)
    assert c3 > c2 > c1 > 0
    assert x3 > x2 > x1 > 0


def test_reward_for_deterministic():
    assert reward_for(2, 100) == reward_for(2, 100)


def test_reward_for_seed_varies_slightly():
    c1, _ = reward_for(1, 0)
    c2, _ = reward_for(1, 6)
    # seed % 7 adds 0–6 coins; both should be in a narrow range
    assert abs(c1 - c2) <= 6

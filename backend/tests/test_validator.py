"""The engine and the answer keys are written independently; these tests make them cross-check."""
import pytest

from backend.cricket_data import GENERATORS, to_grid
from backend.formula_engine import Grid
from backend.keys import compute_answer
from backend.service import load_missions, _rows_for
from backend.validator import validate

MISSIONS = load_missions()


def _setup(m):
    rows, cols = _rows_for(m)
    return Grid(to_grid(cols, rows)), compute_answer(m["answer_spec"], rows)


@pytest.mark.parametrize("m", MISSIONS, ids=lambda m: m["id"])
def test_reference_solution_passes(m):
    grid, expected = _setup(m)
    r = validate(m["reference_solution"], grid, expected, m["required_all"], m["required_any"])
    assert r.passed, r.reason


@pytest.mark.parametrize("m", MISSIONS, ids=lambda m: m["id"])
def test_hardcoded_answer_is_rejected(m):
    grid, expected = _setup(m)
    r = validate(f"={expected}", grid, expected, m["required_all"], m["required_any"])
    assert not r.passed and r.reason.startswith("hardcoded_value")


@pytest.mark.parametrize("m", MISSIONS, ids=lambda m: m["id"])
def test_wrong_reference_range_fails(m):
    grid, expected = _setup(m)
    broken = m["reference_solution"].replace("61", "30")  # forgot half the rows
    r = validate(broken, grid, expected, m["required_all"], m["required_any"])
    assert not r.passed


def test_failure_reason_never_contains_expected_value():
    m = MISSIONS[0]
    grid, expected = _setup(m)
    r = validate('=COUNTIF(G2:G61,">9")', grid, expected, m["required_all"], m["required_any"])
    assert not r.passed and r.reason == "wrong_value"


def test_datasets_are_reproducible():
    gen, _ = GENERATORS["bowling_spells"]
    assert gen(101, 60) == gen(101, 60)
    assert gen(101, 60) != gen(102, 60)

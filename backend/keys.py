"""Answer keys, computed straight from the generated rows in plain Python.

Deliberately independent of the formula engine, so the engine and the key
cross-check each other (see tests/test_validator.py).
"""
from __future__ import annotations

from .formula_engine import excel_round


def compute_answer(spec: dict, rows: list[dict]):
    kind = spec["kind"]
    if kind == "count_gt":
        return float(sum(1 for r in rows if r[spec["field"]] > spec["value"]))
    if kind == "sum_where":
        return float(sum(r[spec["sum_field"]] for r in rows if r[spec["where_field"]] == spec["where_value"]))
    if kind == "avg_where_round":
        vals = [r[spec["avg_field"]] for r in rows if r[spec["where_field"]] == spec["where_value"]]
        return excel_round(sum(vals) / len(vals), spec["digits"])
    raise ValueError(f"unknown answer kind: {kind}")

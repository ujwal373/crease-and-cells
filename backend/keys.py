"""Answer keys, computed straight from the generated rows in plain Python.

Deliberately independent of the formula engine, so the engine and the key
cross-check each other (see tests/test_validator.py).
"""
from __future__ import annotations

from .formula_engine import excel_round


def _cond_match(row: dict, cond: dict) -> bool:
    """Return True when a row satisfies a single condition dict."""
    val = row.get(cond["field"])
    thresh = cond["value"]
    op = cond["op"]
    return {
        "=":  val == thresh,
        "<>": val != thresh,
        ">":  val > thresh,
        ">=": val >= thresh,
        "<":  val < thresh,
        "<=": val <= thresh,
    }[op]


def compute_answer(spec: dict, rows: list[dict]):
    kind = spec["kind"]

    if kind == "count_gt":
        return float(sum(1 for r in rows if r[spec["field"]] > spec["value"]))

    if kind == "sum_where":
        return float(sum(r[spec["sum_field"]] for r in rows if r[spec["where_field"]] == spec["where_value"]))

    if kind == "avg_where_round":
        vals = [r[spec["avg_field"]] for r in rows if r[spec["where_field"]] == spec["where_value"]]
        return excel_round(sum(vals) / len(vals), spec["digits"])

    if kind == "count_multi":
        conditions = spec["conditions"]
        return float(sum(1 for r in rows if all(_cond_match(r, c) for c in conditions)))

    if kind == "sum_multi":
        conditions = spec["conditions"]
        return float(sum(r[spec["sum_field"]] for r in rows if all(_cond_match(r, c) for c in conditions)))

    if kind == "if_single_cell":
        val = rows[spec["row_index"]][spec["field"]]
        matched = _cond_match({spec["field"]: val}, {**spec, "value": spec["threshold"]})
        return float(spec["true_value"] if matched else spec["false_value"])

    if kind == "ifs_xp":
        wk = rows[spec["row_index"]]["wickets"]
        return float({3: 100, 2: 75, 1: 50, 0: 25}.get(wk, 25))

    raise ValueError(f"unknown answer kind: {kind}")

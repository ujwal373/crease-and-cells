"""Deterministic cricket formula question generator.

Ports the question template functions from cc-engine.js (T.maths, T.text,
T.logic, T.date, T.lookup, T.stats, T.arrays) to Python using the same seeded
random algorithm (mulberry32).  No LLM is involved.  Given the same family,
difficulty, and seed the output is always identical.

Each template returns a dict:
  rows      - 2D list of cell values (row 0 is the header row)
  tr        - 0-based row index of the target cell
  tc        - 0-based column index of the target cell
  model     - the reference formula (never sent to the client)
  must_use  - list of function names the player must include
  story     - NPC dialogue / question prompt
  task      - what to put in the target cell
  hint      - first hint shown without penalty
  explain   - explanation shown after a correct answer
  expected  - the computed expected value (from evaluating model against rows)
"""
from __future__ import annotations

import math
import random as _stdlib_random
from typing import Any


# ---------------------------------------------------------------------------
# Seeded RNG — mulberry32 port
# ---------------------------------------------------------------------------

def _mulberry32(seed: int):
    """Generator that yields floats in [0, 1) using the mulberry32 algorithm."""
    a = seed & 0xFFFFFFFF
    while True:
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
        t = t ^ (t >> 14)
        yield (t & 0xFFFFFFFF) / 4294967296


class _Rng:
    def __init__(self, seed: int) -> None:
        self._gen = _mulberry32(seed)

    def f(self) -> float:
        return next(self._gen)

    def i(self, lo: int, hi: int) -> int:
        """Inclusive integer in [lo, hi]."""
        return lo + int(self.f() * (hi - lo + 1))

    def pick(self, lst: list) -> Any:
        return lst[int(self.f() * len(lst))]

    def shuffle(self, lst: list) -> list:
        out = lst[:]
        for k in range(len(out) - 1, 0, -1):
            j = int(self.f() * (k + 1))
            out[k], out[j] = out[j], out[k]
        return out


# ---------------------------------------------------------------------------
# Cricket name pools (mirrors cc-engine.js)
# ---------------------------------------------------------------------------

_NAMES   = ["Arun","Bela","Chirag","Dev","Esha","Farid","Gita","Hari","Isha","Jai",
            "Kavya","Lakhan","Mira","Nikhil","Omar","Pia","Qasim","Rhea","Sunil",
            "Tara","Uday","Vani","Wasim","Yash","Zoya"]
_SURN    = ["Rao","Khan","Nair","Sen","Bose","Iyer","Das"]
_CITIES  = ["Harbour Blues","Lakeside Lions","Hillcrest Hawks","Riverbend Royals",
            "Palmgrove Panthers","Stonebridge Strikers"]
_VENUES  = ["Harbour Oval","Lakeside Park","Hillcrest Ground","Riverbend Maidan",
            "Palmgrove Arena","Stonebridge Green"]
_BOWLERS = ["Pace","Spin","Swing","Seam"]
_ROLES   = ["Opener","Batter","All-rounder","Bowler","Keeper"]


def _col(c: int) -> str:
    return "ABCDEF"[c]


def _ref(r: int, c: int) -> str:
    return f"{_col(c)}{r + 1}"


def _range_ref(c: int, r1: int, r2: int) -> str:
    return f"{_col(c)}{r1 + 1}:{_col(c)}{r2 + 1}"


# ---------------------------------------------------------------------------
# Simple formula evaluator for expected value computation
# (uses the existing backend engine where possible, falls back to Python)
# ---------------------------------------------------------------------------

def _eval_model(model: str, rows: list[list]) -> Any:
    from .formula_engine import evaluate, Grid
    grid = Grid(rows)
    result = evaluate(model, grid)
    return result.value if hasattr(result, "value") else result


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _decorate(q: dict, R: _Rng) -> dict:
    """Add extra cricket columns to make sheets look like a real scorebook."""
    rows = q["rows"]
    if not rows:
        return q
    header = "|".join(str(c) for c in rows[0]) if rows[0] else ""
    if header == "Match|Runs":
        rows[0] += ["Opponent", "Venue"]
        for k in range(1, len(rows)):
            if isinstance(rows[k][0], str) and rows[k][0].startswith("M"):
                rows[k] += [R.pick(_CITIES), R.pick(_VENUES)]
    elif header == "Over|Runs":
        rows[0] += ["Bowler type"]
        for k in range(1, len(rows)):
            if isinstance(rows[k][0], (int, float)):
                rows[k] += [R.pick(_BOWLERS)]
    elif header == "Spell|Overs":
        rows[0] += ["Bowler type"]
        for k in range(1, len(rows)):
            if isinstance(rows[k][0], str) and rows[k][0].startswith("S"):
                rows[k] += [R.pick(_BOWLERS)]
    elif header in ("Player|Runs", "Player|Wickets"):
        rows[0] += ["Team", "Role"]
        for k in range(1, len(rows)):
            if rows[k][0] not in ("Find", "Runs", "Wickets", "Median",
                                  "2nd best", "Total", "Average", "Best",
                                  "Worst", "Count", "Best economy"):
                rows[k] += [R.pick(_CITIES), R.pick(_ROLES)]
    elif header == "Code|City":
        rows[0][0] = "Player ID"
        rows[0][1] = "Team"
    return q


# ---------------------------------------------------------------------------
# Maths templates
# ---------------------------------------------------------------------------

def _maths_sum(R: _Rng, _d: int) -> dict:
    n = R.i(5, 7)
    rows: list[list] = [["Over", "Runs"]]
    for k in range(n):
        rows.append([k + 1, R.i(2, 14)])
    rows.append(["Total", ""])
    tr = len(rows) - 1
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=SUM({rng})",
        "must_use": ["SUM"],
        "story": "The scorer lost the calculator again.",
        "task": f"Add up every over in {rng} and put the total in {_ref(tr, 1)}.",
        "hint": "SUM adds a range. Write =SUM(first:last).",
        "explain": "SUM adds all the numbers in a range.",
    }


def _maths_average(R: _Rng, _d: int) -> dict:
    n = R.i(5, 7)
    rows: list[list] = [["Spell", "Overs"]]
    for k in range(n):
        rows.append([f"S{k + 1}", R.i(2, 6)])
    rows.append(["Average", ""])
    tr = len(rows) - 1
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=ROUND(AVERAGE({rng}),2)",
        "must_use": ["AVERAGE"],
        "story": "A bowler wants the typical length of a spell.",
        "task": f"Find the average overs in {rng}, rounded to 2 decimals, in {_ref(tr, 1)}.",
        "hint": "Wrap AVERAGE inside ROUND: =ROUND(AVERAGE(range),2).",
        "explain": "AVERAGE gives the mean. ROUND trims it to 2 decimals.",
    }


def _maths_max_min(R: _Rng, _d: int) -> dict:
    n = R.i(5, 6)
    rows: list[list] = [["Match", "Runs"]]
    for k in range(n):
        rows.append([f"M{k + 1}", R.i(8, 90)])
    rows.append(["Best", ""])
    rows.append(["Worst", ""])
    tr = len(rows) - 2
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=MAX({rng})-MIN({rng})",
        "must_use": ["MAX", "MIN"],
        "story": "The selector wants the spread between a best and a worst score.",
        "task": f"In {_ref(tr, 1)} show the best score minus the worst score from {rng}.",
        "hint": "MAX(range) minus MIN(range).",
        "explain": "MAX finds the biggest, MIN the smallest. Subtract them for the spread.",
    }


_MATHS_TEMPLATES = [_maths_sum, _maths_average, _maths_max_min]


# ---------------------------------------------------------------------------
# Text templates
# ---------------------------------------------------------------------------

def _text_left_upper(R: _Rng, _d: int) -> dict:
    rows: list[list] = [["Player", "Code"]]
    for _ in range(5):
        rows.append([f"{R.pick(_NAMES)} {R.pick(_SURN)}", ""])
    return {
        "rows": rows, "tr": 1, "tc": 1,
        "model": "=UPPER(LEFT(A2,3))",
        "must_use": ["LEFT"],
        "story": "The kit room labels bags with a short code.",
        "task": "In B2 make the first 3 letters of A2, in capitals.",
        "hint": "LEFT takes letters from the start. UPPER makes capitals. Nest them.",
        "explain": "LEFT(text,3) takes 3 letters. UPPER capitalises.",
    }


def _text_concat(R: _Rng, _d: int) -> dict:
    first = R.pick(_NAMES)
    last  = R.pick(_SURN)
    rows: list[list] = [["First", "Last", "Full"], [first, last, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 2,
        "model": '=A2&" "&B2',
        "must_use": [],
        "story": "The team sheet needs full names.",
        "task": "In C2 join A2 and B2 with a single space between them.",
        "hint": 'Use & to join text. Put " " between the two cells.',
        "explain": "The & operator joins text. A space is just text in quotes.",
    }


def _text_trim_upper(R: _Rng, _d: int) -> dict:
    prefix = R.pick(["HBR", "LKS", "HLC"])
    num    = R.i(100, 999)
    code   = f"{prefix}-{num}"
    rows: list[list] = [
        ["Match pass", "Clean"],
        [f"  {code.lower()}  ", ""],
    ]
    return {
        "rows": rows, "tr": 1, "tc": 1,
        "model": "=UPPER(TRIM(A2))",
        "must_use": ["TRIM"],
        "story": "Match pass codes arrive with stray spaces and small letters.",
        "task": "In B2 remove the extra spaces from A2 and make it all capitals.",
        "hint": "TRIM removes spaces. UPPER capitalises.",
        "explain": "TRIM cleans spaces, UPPER fixes the case.",
    }


_TEXT_TEMPLATES = [_text_left_upper, _text_concat, _text_trim_upper]


# ---------------------------------------------------------------------------
# Logic templates
# ---------------------------------------------------------------------------

def _logic_if(R: _Rng, _d: int) -> dict:
    runs = R.i(20, 80)
    rows: list[list] = [["Runs", "Result"], [runs, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 1,
        "model": '=IF(A2>=50,"Fifty","Keep going")',
        "must_use": ["IF"],
        "story": "The scoreboard shows a badge for fifties.",
        "task": 'In B2 show "Fifty" if A2 is 50 or more, otherwise "Keep going".',
        "hint": "IF(test, if true, if false). Text goes in quotes.",
        "explain": "IF picks one of two answers by testing a condition.",
    }


def _logic_countif(R: _Rng, _d: int) -> dict:
    n  = R.i(6, 8)
    th = R.pick([30, 40, 50])
    rows: list[list] = [["Match", "Runs"]]
    for k in range(n):
        rows.append([f"M{k + 1}", R.i(5, 95)])
    rows.append(["Count", ""])
    tr  = len(rows) - 1
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f'=COUNTIF({rng},">={th}")',
        "must_use": ["COUNTIF"],
        "story": "The club book tracks good scores.",
        "task": f"Count scores of {th} or more in {rng}. Answer in {_ref(tr, 1)}.",
        "hint": f'COUNTIF(range, ">={th}"). The condition is in quotes.',
        "explain": "COUNTIF counts the cells that meet one condition.",
    }


def _logic_sumif(R: _Rng, _d: int) -> dict:
    n    = R.i(6, 8)
    team = R.pick(["Harbour Blues", "Lakeside Lions"])
    rows: list[list] = [["Team", "Runs"]]
    for k in range(n):
        t = "Lakeside Lions" if k % 2 else "Harbour Blues"
        rows.append([t, R.i(10, 60)])
    rows.append([f"{team} total", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f'=SUMIF(A2:A{tr},"{team}",B2:B{tr})',
        "must_use": ["SUMIF"],
        "story": "Two clubs share one score sheet.",
        "task": f"Add only the {team} rows from column B. Answer in {_ref(tr, 1)}.",
        "hint": f'SUMIF(test range, "{team}", sum range).',
        "explain": "SUMIF adds only the rows that match a test.",
    }


def _logic_and_if(R: _Rng, _d: int) -> dict:
    a = R.i(10, 60)
    b = R.i(0, 7)
    rows: list[list] = [["Runs", "Wkts", "Bonus?"], [a, b, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 2,
        "model": '=IF(AND(A2>=30,B2<=4),"Yes","No")',
        "must_use": ["IF", "AND"],
        "story": "A bonus needs two things at once.",
        "task": 'In C2 show "Yes" if A2 is at least 30 AND B2 is 4 or fewer, otherwise "No".',
        "hint": 'IF(AND(test1,test2),"Yes","No").',
        "explain": "AND is true only if every test is true.",
    }


_LOGIC_TEMPLATES = [_logic_if, _logic_countif, _logic_sumif, _logic_and_if]


# ---------------------------------------------------------------------------
# Date templates
# ---------------------------------------------------------------------------

def _date_month(R: _Rng, _d: int) -> dict:
    y  = 2026
    m  = R.i(1, 12)
    dd = R.i(1, 28)
    s  = f"{y}-{m:02d}-{dd:02d}"
    rows: list[list] = [["Match date", "Month"], [s, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 1,
        "model": "=MONTH(A2)",
        "must_use": ["MONTH"],
        "story": "The fixture list needs month numbers.",
        "task": "In B2 get the month number of the date in A2.",
        "hint": "MONTH takes a date.",
        "explain": "MONTH returns 1 to 12 from a date.",
    }


def _date_days(R: _Rng, _d: int) -> dict:
    import datetime
    a = R.i(1, 9)
    b = a + R.i(5, 40)
    base = datetime.date(2026, 1, 1)
    da = (base + datetime.timedelta(days=a - 1)).isoformat()
    db = (base + datetime.timedelta(days=b - 1)).isoformat()
    rows: list[list] = [["Camp start", "Camp end", "Days"], [da, db, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 2,
        "model": "=DAYS(B2,A2)",
        "must_use": ["DAYS"],
        "story": "A training camp has dates but no length.",
        "task": "In C2 count the days from A2 to B2.",
        "hint": "DAYS(end, start). End comes first.",
        "explain": "DAYS subtracts one date from another.",
    }


def _date_build(R: _Rng, _d: int) -> dict:
    y  = R.i(2, 6) + 2020
    m  = R.i(1, 12)
    dd = R.i(1, 28)
    rows: list[list] = [["Year", "Month", "Day", "Date"], [y, m, dd, ""]]
    return {
        "rows": rows, "tr": 1, "tc": 3,
        "model": "=DATE(A2,B2,C2)",
        "must_use": ["DATE"],
        "story": "The registry stores dates in three columns.",
        "task": "In D2 build one real date from A2, B2 and C2.",
        "hint": "DATE(year, month, day).",
        "explain": "DATE assembles year, month and day into one date.",
    }


_DATE_TEMPLATES = [_date_month, _date_days, _date_build]


# ---------------------------------------------------------------------------
# Lookup templates
# ---------------------------------------------------------------------------

def _lookup_vlookup(R: _Rng, _d: int) -> dict:
    names = R.shuffle(_NAMES)[:5]
    rows: list[list] = [["Player", "Runs"]]
    for n in names:
        rows.append([n, R.i(10, 90)])
    who = R.pick(names)
    rows.append(["Find", who])
    rows.append(["Runs", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": "=VLOOKUP(B7,A2:B6,2,FALSE)",
        "must_use": ["VLOOKUP"],
        "story": "Someone asks for one player by name.",
        "task": "In B8 look up the name in B7 inside A2:B6 and return the runs.",
        "hint": "VLOOKUP(what, table, column number, FALSE).",
        "explain": "VLOOKUP finds a row by its first column and returns another column.",
    }


def _lookup_index_match(R: _Rng, _d: int) -> dict:
    names = R.shuffle(_NAMES)[:5]
    rows: list[list] = [["Player", "Wickets"]]
    for n in names:
        rows.append([n, R.i(1, 12)])
    who = R.pick(names)
    rows.append(["Find", who])
    rows.append(["Wickets", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": "=INDEX(B2:B6,MATCH(B7,A2:A6,0))",
        "must_use": ["INDEX", "MATCH"],
        "story": "The coach wants a flexible lookup.",
        "task": "In B8 return the wickets for the name in B7 using INDEX and MATCH.",
        "hint": "MATCH finds the position. INDEX returns the value at that position.",
        "explain": "MATCH gives a position, INDEX picks the value there.",
    }


def _lookup_xlookup(R: _Rng, _d: int) -> dict:
    names = R.shuffle(_NAMES)[:5]
    rows: list[list] = [["Code", "City"]]
    for k, n in enumerate(names):
        rows.append([n[:2].upper() + str(k), R.pick(_CITIES)])
    who_idx = R.i(1, 5)
    rows.append(["Find", rows[who_idx][0]])
    rows.append(["Team", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": "=XLOOKUP(B7,A2:A6,B2:B6)",
        "must_use": ["XLOOKUP"],
        "story": "Every player ID needs a team beside it.",
        "task": "In B8 find the player ID in B7 and return their team using XLOOKUP.",
        "hint": "XLOOKUP(what, where to look, what to return).",
        "explain": "XLOOKUP searches one range and returns from another.",
    }


_LOOKUP_TEMPLATES = [_lookup_vlookup, _lookup_index_match, _lookup_xlookup]


# ---------------------------------------------------------------------------
# Stats templates
# ---------------------------------------------------------------------------

def _stats_median(R: _Rng, _d: int) -> dict:
    n = R.i(6, 8)
    rows: list[list] = [["Match", "Runs"]]
    for k in range(n):
        rows.append([f"M{k + 1}", R.i(5, 95)])
    rows.append(["Median", ""])
    tr  = len(rows) - 1
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=MEDIAN({rng})",
        "must_use": ["MEDIAN"],
        "story": "The analyst distrusts averages.",
        "task": f"Find the middle score of {rng}.",
        "hint": "MEDIAN(range).",
        "explain": "MEDIAN is the middle value once sorted.",
    }


def _stats_large(R: _Rng, _d: int) -> dict:
    n = R.i(6, 8)
    rows: list[list] = [["Match", "Runs"]]
    for k in range(n):
        rows.append([f"M{k + 1}", R.i(5, 95)])
    rows.append(["2nd best", ""])
    tr  = len(rows) - 1
    rng = _range_ref(1, 1, tr - 1)
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=LARGE({rng},2)",
        "must_use": ["LARGE"],
        "story": "The selector needs the runner up.",
        "task": f"Show the second largest score of {rng}.",
        "hint": "LARGE(range, 2).",
        "explain": "LARGE(range,k) gives the k-th biggest value.",
    }


_STATS_TEMPLATES = [_stats_median, _stats_large]


# ---------------------------------------------------------------------------
# Arrays templates
# ---------------------------------------------------------------------------

def _arrays_sumproduct(R: _Rng, _d: int) -> dict:
    n = R.i(4, 5)
    items = ["Ball", "Bat", "Pad", "Glove", "Stump", "Cone"]
    rows: list[list] = [["Item", "Qty", "Price"]]
    for k in range(n):
        rows.append([R.pick(items) + str(k), R.i(1, 6), R.i(2, 12) * 10])
    rows.append(["Total", "", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 2,
        "model": f"=SUMPRODUCT(B2:B{tr},C2:C{tr})",
        "must_use": ["SUMPRODUCT"],
        "story": "The kit order needs a grand total.",
        "task": f"In {_ref(tr, 2)} multiply quantity by price for each row and add them all, in one formula.",
        "hint": "SUMPRODUCT(range1, range2).",
        "explain": "SUMPRODUCT multiplies matching cells and adds the results.",
    }


def _arrays_countunique(R: _Rng, _d: int) -> dict:
    n = R.i(7, 9)
    rows: list[list] = [["Venue"]]
    for _ in range(n):
        rows.append([R.pick(_VENUES)])
    rows.append(["Unique", ""])
    tr = len(rows) - 1
    return {
        "rows": rows, "tr": tr, "tc": 1,
        "model": f"=COUNTUNIQUE(A2:A{tr})",
        "must_use": ["COUNTUNIQUE"],
        "story": "How many different grounds were used?",
        "task": f"Count the different venues in A2:A{tr} and put it in {_ref(tr, 1)}. (Google Sheets: COUNTUNIQUE.)",
        "hint": "COUNTUNIQUE(range).",
        "explain": "COUNTUNIQUE counts each distinct value once.",
    }


_ARRAYS_TEMPLATES = [_arrays_sumproduct, _arrays_countunique]


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, list] = {
    "maths":  _MATHS_TEMPLATES,
    "text":   _TEXT_TEMPLATES,
    "logic":  _LOGIC_TEMPLATES,
    "date":   _DATE_TEMPLATES,
    "lookup": _LOOKUP_TEMPLATES,
    "stats":  _STATS_TEMPLATES,
    "arrays": _ARRAYS_TEMPLATES,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_question(family: str, difficulty: int, seed: int) -> dict:
    """Build a question for the given family, difficulty, and seed.

    Returns a dict with keys: rows, tr, tc, model, must_use, story, task,
    hint, explain, expected.

    ``expected`` is the value the player's formula must produce.
    ``model`` is the reference formula — never sent to the client.
    """
    R = _Rng(seed)
    templates = _TEMPLATES.get(family, _MATHS_TEMPLATES)
    tpl = templates[int(R.f() * len(templates))]
    q = _decorate(tpl(R, difficulty), R)
    expected = _eval_model(q["model"], q["rows"])
    q["expected"] = expected
    return q


def reward_for(difficulty: int, seed: int) -> tuple[int, int]:
    """Return (coins, xp) for a question at the given difficulty."""
    extra = seed % 7
    coins = 12 + 6 * difficulty + extra
    xp    = 20 + 10 * difficulty
    return coins, xp

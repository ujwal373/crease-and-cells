"""Deterministic spreadsheet formula evaluator.

Design rules:
  1. No eval/exec. A hand-written tokenizer and recursive descent parser.
  2. Allowlisted functions only. Anything else (INDIRECT, HYPERLINK, ...) is #NAME?.
  3. Hard limits on formula length, nesting depth and range size.
  4. Same input always gives the same output. This is the judge, never an LLM.
"""
from __future__ import annotations

import fnmatch
import math
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

MAX_FORMULA_LEN = 300
MAX_RANGE_CELLS = 10_000
MAX_DEPTH = 20


class FormulaError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code} {detail}".strip())
        self.code = code
        self.detail = detail


_REF = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d+)$")


def _col_to_idx(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + ord(ch) - 64
    return n


def _parse_ref(text: str) -> tuple[int, int]:
    m = _REF.match(text)
    if not m:
        raise FormulaError("#REF!", text)
    return int(m.group(2)), _col_to_idx(m.group(1))


class Grid:
    """rows[0] is spreadsheet row 1, rows[0][0] is cell A1."""

    def __init__(self, rows: list[list]):
        self.cells = {(r, c): v for r, row in enumerate(rows, 1) for c, v in enumerate(row, 1)}

    def cell(self, ref: str):
        return self.cells.get(_parse_ref(ref))

    def range(self, a: str, b: str) -> "Range":
        (r1, c1), (r2, c2) = _parse_ref(a), _parse_ref(b)
        r1, r2 = sorted((r1, r2))
        c1, c2 = sorted((c1, c2))
        nrows, ncols = r2 - r1 + 1, c2 - c1 + 1
        if nrows * ncols > MAX_RANGE_CELLS:
            raise FormulaError("#REF!", "range too large")
        values = [self.cells.get((r, c)) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]
        return Range(values, nrows, ncols)


@dataclass
class Range:
    values: list
    nrows: int
    ncols: int


@dataclass
class EvalResult:
    value: Any
    functions: set
    reference_count: int


_TOKEN = re.compile(
    r"""
    (?P<num>\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<str>"(?:[^"]|"")*")
  | (?P<range>\$?[A-Za-z]{1,3}\$?\d+:\$?[A-Za-z]{1,3}\$?\d+)
  | (?P<cell>\$?[A-Za-z]{1,3}\$?\d+)(?![A-Za-z0-9_(])
  | (?P<func>[A-Za-z][A-Za-z0-9_.]*)(?=\s*\()
  | (?P<op><=|>=|<>|[-+*/^&=<>(),])
    """,
    re.X,
)


def _tokenize(src: str) -> list[tuple[str, str]]:
    tokens, pos = [], 0
    while pos < len(src):
        if src[pos].isspace():
            pos += 1
            continue
        m = _TOKEN.match(src, pos)
        if not m:
            raise FormulaError("#ERROR", f"unexpected character at position {pos + 1}")
        tokens.append((m.lastgroup, m.group()))
        pos = m.end()
    return tokens


# ---------- value helpers ----------

def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num(v) -> float:
    if isinstance(v, Range):
        raise FormulaError("#VALUE!", "range used where a single value is expected")
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return float(v)
    if _is_number(v):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            raise FormulaError("#VALUE!", "text cannot be used in arithmetic")
    raise FormulaError("#VALUE!")


def excel_round(x: float, digits: int = 0) -> float:
    q = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if _is_number(v):
        return v != 0
    if isinstance(v, str) and v.upper() in ("TRUE", "FALSE"):
        return v.upper() == "TRUE"
    raise FormulaError("#VALUE!", "condition is not true or false")


def _type_rank(v) -> int:
    return 2 if isinstance(v, bool) else 1 if isinstance(v, str) else 0


def _compare(a, b, op: str) -> bool:
    if isinstance(a, Range) or isinstance(b, Range):
        raise FormulaError("#VALUE!", "range in comparison")
    if a is None:
        a = "" if isinstance(b, str) else 0
    if b is None:
        b = "" if isinstance(a, str) else 0
    if isinstance(a, str) and isinstance(b, str):
        a, b = a.lower(), b.lower()
    elif _type_rank(a) != _type_rank(b):
        a, b = _type_rank(a), _type_rank(b)
    return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]


def _make_matcher(crit):
    """Excel-style criteria: 5, ">5", "<>x", "text", "Rohan*"."""
    if _is_number(crit):
        return lambda v: _is_number(v) and math.isclose(float(v), float(crit))
    s = "" if crit is None else str(crit)
    m = re.match(r"(<=|>=|<>|<|>|=)?(.*)$", s, re.S)
    op, rest = m.group(1) or "=", m.group(2)
    try:
        target, numeric = float(rest), True
    except ValueError:
        target, numeric = rest.lower(), False

    def match(v) -> bool:
        if numeric:
            if _is_number(v):
                x = float(v)
            elif isinstance(v, str):
                try:
                    x = float(v)
                except ValueError:
                    return op == "<>"
            else:
                return op == "<>"
            return {
                "=": x == target, "<>": x != target, "<": x < target,
                ">": x > target, "<=": x <= target, ">=": x >= target,
            }[op]
        if op not in ("=", "<>"):
            return False
        sv = "" if v is None else str(v).lower()
        hit = fnmatch.fnmatchcase(sv, target.replace("[", "[[]"))
        return hit if op == "=" else not hit

    return match


# ---------- functions ----------

def _nums_from(args) -> list[float]:
    out: list[float] = []
    for a in args:
        if isinstance(a, Range):
            out.extend(float(v) for v in a.values if _is_number(v))
        else:
            out.append(_num(a))
    return out


def _need_range(a) -> Range:
    if not isinstance(a, Range):
        raise FormulaError("#VALUE!", "a range is required here")
    return a


def _mask(pairs: list[tuple[Range, Any]]) -> list[bool]:
    n = len(pairs[0][0].values)
    if any(len(r.values) != n for r, _ in pairs):
        raise FormulaError("#VALUE!", "ranges must be the same size")
    matchers = [(r.values, _make_matcher(c)) for r, c in pairs]
    return [all(m(vals[i]) for vals, m in matchers) for i in range(n)]


def _pairs(args) -> list[tuple[Range, Any]]:
    if len(args) < 2 or len(args) % 2:
        raise FormulaError("#VALUE!", "wrong number of arguments")
    return [(_need_range(args[i]), args[i + 1]) for i in range(0, len(args), 2)]


def _fn_sum(a):
    return sum(_nums_from(a))


def _fn_average(a):
    n = _nums_from(a)
    if not n:
        raise FormulaError("#DIV/0!")
    return sum(n) / len(n)


def _fn_min(a):
    n = _nums_from(a)
    return min(n) if n else 0.0


def _fn_max(a):
    n = _nums_from(a)
    return max(n) if n else 0.0


def _fn_count(a):
    total = 0
    for x in a:
        if isinstance(x, Range):
            total += sum(1 for v in x.values if _is_number(v))
        else:
            try:
                _num(x)
                total += 1
            except FormulaError:
                pass
    return float(total)


def _fn_counta(a):
    total = 0
    for x in a:
        if isinstance(x, Range):
            total += sum(1 for v in x.values if v is not None and v != "")
        else:
            total += 1
    return float(total)


def _fn_countif(a):
    if len(a) != 2:
        raise FormulaError("#VALUE!", "COUNTIF takes 2 arguments")
    return float(sum(_mask(_pairs(a))))


def _fn_countifs(a):
    return float(sum(_mask(_pairs(a))))


def _fn_sumif(a):
    if len(a) not in (2, 3):
        raise FormulaError("#VALUE!", "SUMIF takes 2 or 3 arguments")
    rng = _need_range(a[0])
    sum_rng = _need_range(a[2]) if len(a) == 3 else rng
    mask = _mask([(rng, a[1])])
    if len(sum_rng.values) != len(mask):
        raise FormulaError("#VALUE!", "ranges must be the same size")
    return float(sum(v for v, k in zip(sum_rng.values, mask) if k and _is_number(v)))


def _fn_sumifs(a):
    if len(a) < 3 or len(a) % 2 == 0:
        raise FormulaError("#VALUE!", "wrong number of arguments")
    sum_rng = _need_range(a[0])
    mask = _mask(_pairs(a[1:]))
    if len(sum_rng.values) != len(mask):
        raise FormulaError("#VALUE!", "ranges must be the same size")
    return float(sum(v for v, k in zip(sum_rng.values, mask) if k and _is_number(v)))


def _fn_averageif(a):
    if len(a) not in (2, 3):
        raise FormulaError("#VALUE!", "AVERAGEIF takes 2 or 3 arguments")
    rng = _need_range(a[0])
    avg_rng = _need_range(a[2]) if len(a) == 3 else rng
    mask = _mask([(rng, a[1])])
    if len(avg_rng.values) != len(mask):
        raise FormulaError("#VALUE!", "ranges must be the same size")
    picked = [float(v) for v, k in zip(avg_rng.values, mask) if k and _is_number(v)]
    if not picked:
        raise FormulaError("#DIV/0!")
    return sum(picked) / len(picked)


def _fn_if(a):
    if len(a) not in (2, 3):
        raise FormulaError("#VALUE!", "IF takes 2 or 3 arguments")
    return a[1] if _truthy(a[0]) else (a[2] if len(a) == 3 else False)


def _fn_ifs(a):
    if len(a) < 2 or len(a) % 2:
        raise FormulaError("#VALUE!", "IFS requires an even number of arguments in pairs")
    for i in range(0, len(a), 2):
        if _truthy(a[i]):
            return a[i + 1]
    raise FormulaError("#N/A", "no IFS condition was true")


def _fn_and(a):
    if not a:
        raise FormulaError("#VALUE!", "AND requires at least one argument")
    found_any = False
    for x in a:
        vals = x.values if isinstance(x, Range) else [x]
        for v in vals:
            if v is None:
                continue
            found_any = True
            if not _truthy(v):
                return False
    if not found_any:
        raise FormulaError("#VALUE!", "AND found no values to evaluate")
    return True


def _fn_or(a):
    if not a:
        raise FormulaError("#VALUE!", "OR requires at least one argument")
    found_any = False
    for x in a:
        vals = x.values if isinstance(x, Range) else [x]
        for v in vals:
            if v is None:
                continue
            found_any = True
            if _truthy(v):
                return True
    if not found_any:
        raise FormulaError("#VALUE!", "OR found no values to evaluate")
    return False


def _fn_round(a):
    if len(a) not in (1, 2):
        raise FormulaError("#VALUE!", "ROUND takes 1 or 2 arguments")
    return excel_round(_num(a[0]), int(_num(a[1])) if len(a) == 2 else 0)


def _fn_abs(a):
    if len(a) != 1:
        raise FormulaError("#VALUE!", "ABS takes 1 argument")
    return abs(_num(a[0]))


FUNCTIONS = {
    "SUM": _fn_sum, "AVERAGE": _fn_average, "MIN": _fn_min, "MAX": _fn_max,
    "COUNT": _fn_count, "COUNTA": _fn_counta, "COUNTIF": _fn_countif,
    "COUNTIFS": _fn_countifs, "SUMIF": _fn_sumif, "SUMIFS": _fn_sumifs,
    "AVERAGEIF": _fn_averageif, "IF": _fn_if, "IFS": _fn_ifs,
    "AND": _fn_and, "OR": _fn_or,
    "ROUND": _fn_round, "ABS": _fn_abs,
}


# ---------- parser / evaluator ----------

class _Parser:
    def __init__(self, tokens, grid: Grid):
        self.t, self.i, self.grid = tokens, 0, grid
        self.functions: set[str] = set()
        self.refs = 0
        self.depth = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, text: str):
        if self.take()[1] != text:
            raise FormulaError("#ERROR", f"expected {text}")

    def parse(self):
        value = self.comparison()
        if self.i != len(self.t):
            raise FormulaError("#ERROR", "unexpected token")
        return value

    def _binary(self, sub, ops, apply):
        left = sub()
        while self.peek()[0] == "op" and self.peek()[1] in ops:
            op = self.take()[1]
            left = apply(op, left, sub())
        return left

    def comparison(self):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise FormulaError("#ERROR", "formula nested too deeply")
        try:
            return self._binary(self.concat, ("=", "<>", "<", ">", "<=", ">="), lambda o, a, b: _compare(a, b, o))
        finally:
            self.depth -= 1

    def concat(self):
        def join(_, a, b):
            return ("" if a is None else str(a)) + ("" if b is None else str(b))
        return self._binary(self.additive, ("&",), join)

    def additive(self):
        return self._binary(self.term, ("+", "-"), lambda o, a, b: _num(a) + _num(b) if o == "+" else _num(a) - _num(b))

    def term(self):
        def mul_div(o, a, b):
            x, y = _num(a), _num(b)
            if o == "*":
                return x * y
            if y == 0:
                raise FormulaError("#DIV/0!")
            return x / y
        return self._binary(self.power, ("*", "/"), mul_div)

    def power(self):
        def pw(_, a, b):
            try:
                r = _num(a) ** _num(b)
            except (OverflowError, ZeroDivisionError):
                raise FormulaError("#NUM!")
            if isinstance(r, complex):
                raise FormulaError("#NUM!")
            return r
        return self._binary(self.unary, ("^",), pw)

    def unary(self):
        kind, val = self.peek()
        if kind == "op" and val in ("-", "+"):
            self.take()
            x = _num(self.unary())
            return -x if val == "-" else x
        return self.primary()

    def primary(self):
        kind, val = self.take()
        if kind == "num":
            return float(val)
        if kind == "str":
            return val[1:-1].replace('""', '"')
        if kind == "cell":
            self.refs += 1
            return self.grid.cell(val)
        if kind == "range":
            self.refs += 1
            a, b = val.split(":")
            return self.grid.range(a, b)
        if kind == "func":
            name = val.upper()
            if name not in FUNCTIONS:
                raise FormulaError("#NAME?", name)
            self.functions.add(name)
            self.expect("(")
            args = []
            if self.peek()[1] == ")":
                self.take()
            else:
                while True:
                    args.append(self.comparison())
                    kind2, val2 = self.take()
                    if val2 == ",":
                        continue
                    if val2 == ")":
                        break
                    raise FormulaError("#ERROR", "expected , or )")
            return FUNCTIONS[name](args)
        if kind == "op" and val == "(":
            v = self.comparison()
            self.expect(")")
            return v
        raise FormulaError("#ERROR", "unexpected end of formula" if kind is None else f"unexpected {val}")


def evaluate(formula: str, grid: Grid) -> EvalResult:
    if not isinstance(formula, str) or not formula.startswith("="):
        raise FormulaError("#ERROR", "formulas must start with =")
    if len(formula) > MAX_FORMULA_LEN:
        raise FormulaError("#ERROR", "formula too long")
    parser = _Parser(_tokenize(formula[1:]), grid)
    value = parser.parse()
    if isinstance(value, Range):
        raise FormulaError("#VALUE!", "formula returns a range, not a single value")
    if value is None:
        value = 0.0
    return EvalResult(value=value, functions=parser.functions, reference_count=parser.refs)

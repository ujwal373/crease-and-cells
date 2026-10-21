import pytest

from backend.formula_engine import FormulaError, Grid, evaluate

GRID = Grid([
    ["name", "runs", "wkts"],
    ["Ujwal", 30, 2],
    ["Rohan", 45, 0],
    ["Ujwal", 20, 3],
    ["Arjun", None, 1],
])


def val(f):
    return evaluate(f, GRID).value


@pytest.mark.parametrize("formula,expected", [
    ("=SUM(B2:B5)", 95),
    ("=AVERAGE(B2:B5)", 95 / 3),
    ("=MAX(B2:B5)", 45),
    ("=MIN(B2:B5)", 20),
    ("=COUNT(B2:B5)", 3),
    ("=COUNTA(A2:A5)", 4),
    ('=COUNTIF(A2:A5,"Ujwal")', 2),
    ('=COUNTIF(B2:B5,">25")', 2),
    ('=COUNTIFS(A2:A5,"Ujwal",C2:C5,">2")', 1),
    ('=SUMIF(A2:A5,"Ujwal",C2:C5)', 5),
    ('=SUMIFS(C2:C5,A2:A5,"Ujwal",B2:B5,">=30")', 2),
    ('=AVERAGEIF(A2:A5,"Ujwal",B2:B5)', 25),
    ('=COUNTIF(A2:A5,"u*")', 2),
    ("=ROUND(2.675,2)", 2.68),
    ("=IF(B2>25,1,0)", 1),
    ("=B2+B3*2", 120),
    ("=(B2+B3)*2", 150),
    ("=-B2", -30),
    ("=2^3", 8),
    ('="a"&"b"', "ab"),
    ("=sum(b2:b5)", 95),
])
def test_functions(formula, expected):
    assert val(formula) == pytest.approx(expected)


@pytest.mark.parametrize("formula,code", [
    ("=INDIRECT(\"A1\")", "#NAME?"),
    ("=HYPERLINK(\"http://x\")", "#NAME?"),
    ("=1/0", "#DIV/0!"),
    ("=AVERAGE(A9:A10)", "#DIV/0!"),
    ("=A2+1", "#VALUE!"),
    ("=SUM(B2:B5", "#ERROR"),
    ("SUM(B2:B5)", "#ERROR"),
    ("=__import__('os')", "#ERROR"),
    ("=SUM(B2:B5)+", "#ERROR"),
    ("=" + "(" * 40 + "1" + ")" * 40, "#ERROR"),
    ("=" + "1+" * 200 + "1", "#ERROR"),
    ("=B2:B5", "#VALUE!"),
    ("=COUNTIFS(A2:A5,\"x\",B2:B3,\">1\")", "#VALUE!"),
])
def test_errors(formula, code):
    with pytest.raises(FormulaError) as e:
        evaluate(formula, GRID)
    assert e.value.code == code


def test_tracks_functions_and_references():
    r = evaluate('=ROUND(AVERAGEIF(A2:A5,"Ujwal",B2:B5),1)', GRID)
    assert r.functions == {"ROUND", "AVERAGEIF"}
    assert r.reference_count == 2


def test_hardcoded_has_no_references():
    assert evaluate("=25", GRID).reference_count == 0

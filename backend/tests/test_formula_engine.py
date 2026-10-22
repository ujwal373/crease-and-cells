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


# ---------- IFS ----------

@pytest.mark.parametrize("formula,expected", [
    # B2=30: first condition true → "dear"
    ('=IFS(B2>25,"dear",B2<=25,"cheap")', "dear"),
    # B2=30: first condition (>50) false, second (>20) true → 2
    ("=IFS(B2>50,1,B2>20,2,B2>=0,3)", 2),
    # nested IFS result used in arithmetic
    ("=IFS(C2=2,10,C2=3,20,C2=0,0)+5", 15),  # C2=2 → 10 + 5 = 15
])
def test_ifs_basic(formula, expected):
    assert val(formula) == pytest.approx(expected)


@pytest.mark.parametrize("formula,code", [
    # no condition is true → #N/A
    ("=IFS(0,1,0,2)", "#N/A"),
    # odd number of arguments → #VALUE!
    ("=IFS(B2>0,1,B2<0)", "#VALUE!"),
    # zero arguments → #VALUE!
    ("=IFS()", "#VALUE!"),
])
def test_ifs_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, GRID)
    assert exc.value.code == code


# ---------- AND ----------

@pytest.mark.parametrize("formula,expected", [
    # both true
    ("=AND(B2>25,C2>1)", True),
    # second condition false
    ("=AND(B2>25,C2>5)", False),
    # range: C2=2(T), C3=0(F), C4=3(T) → False
    ("=AND(C2:C4)", False),
    # AND result used in IF
    ('=IF(AND(B2>25,C2>1),"yes","no")', "yes"),
    ('=IF(AND(B2>25,C2>5),"yes","no")', "no"),
])
def test_and_basic(formula, expected):
    result = val(formula)
    assert result == expected


@pytest.mark.parametrize("formula,code", [
    # no arguments
    ("=AND()", "#VALUE!"),
    # text that is not TRUE/FALSE raises #VALUE!
    ('=AND("hello")', "#VALUE!"),
])
def test_and_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, GRID)
    assert exc.value.code == code


# ---------- OR ----------

@pytest.mark.parametrize("formula,expected", [
    # first false, second true
    ("=OR(B2>100,C2>1)", True),
    # both false
    ("=OR(B2>100,C2>5)", False),
    # OR result used in IF
    ('=IF(OR(B2>100,C2>1),"yes","no")', "yes"),
    ('=IF(OR(B2>100,C2>5),"yes","no")', "no"),
])
def test_or_basic(formula, expected):
    assert val(formula) == expected


@pytest.mark.parametrize("formula,code", [
    ("=OR()", "#VALUE!"),
])
def test_or_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, GRID)
    assert exc.value.code == code


# ---------- absolute references ----------

@pytest.mark.parametrize("formula,expected", [
    # $COL$ROW is identical to COL ROW for a static grid
    ("=SUM($B$2:$B$5)", 95),
    ("=$B$2+$B$3", 75),
    ('=COUNTIF($A$2:$A$5,"Ujwal")', 2),
    # mixed absolute / relative
    ("=$B$2+B3", 75),
    # range with $ on one side only
    ("=SUM(B$2:B$5)", 95),
    ("=SUM($B2:$B5)", 95),
])
def test_absolute_references(formula, expected):
    assert val(formula) == pytest.approx(expected)

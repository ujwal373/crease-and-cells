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


# ---------- text functions ----------

TEXT_GRID = Grid([
    ["name",    "city"],
    ["  Ujwal ", "Mumbai"],
    ["rohan",   "Delhi"],
    ["ARJUN",   "Chennai"],
])


def tval(f):
    return evaluate(f, TEXT_GRID).value


@pytest.mark.parametrize("formula,expected", [
    ('=TRIM(A2)',                   "Ujwal"),
    ('=TRIM("  hello  world  ")',    "hello world"),
    ('=UPPER(A3)',                   "ROHAN"),
    ('=UPPER("hello")',              "HELLO"),
    ('=LOWER(A4)',                   "arjun"),
    ('=LOWER("HELLO")',              "hello"),
    ('=LEN("hello")',                5.0),
    ('=LEN(A2)',                     8.0),   # "  Ujwal " has 8 chars
    ('=LEFT("Mumbai",3)',            "Mum"),
    ('=LEFT(B2,3)',                  "Mum"),
    ('=LEFT("hi",0)',                ""),
    ('=RIGHT("Mumbai",3)',           "bai"),
    ('=RIGHT("hi",0)',               ""),
    ('=MID("cricket",4,3)',         "cke"),
    ('=MID("hello",2,3)',            "ell"),
    ('=UPPER(TRIM(A2))',             "UJWAL"),   # nested
    ('=LEFT(UPPER(A3),3)',           "ROH"),
])
def test_text_functions(formula, expected):
    assert tval(formula) == expected


@pytest.mark.parametrize("formula,code", [
    ('=TRIM()',         "#VALUE!"),
    ('=UPPER()',        "#VALUE!"),
    ('=LEN()',          "#VALUE!"),
    ('=LEFT()',         "#VALUE!"),
    ('=RIGHT()',        "#VALUE!"),
    ('=MID("a",1)',     "#VALUE!"),
    ('=LEFT("hi",-1)',  "#VALUE!"),
])
def test_text_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, TEXT_GRID)
    assert exc.value.code == code


# ---------- lookup functions ----------

LOOKUP_GRID = Grid([
    ["Player",  "Runs"],   # row 1 — header
    ["Ujwal",   30],       # row 2
    ["Rohan",   45],       # row 3
    ["Arjun",   22],       # row 4
    ["Meera",   61],       # row 5
    ["Priya",   38],       # row 6  ← A2:B6 is the lookup table
    ["Find",    "Rohan"],  # row 7  ← B7 = lookup key
    ["Result",  ""],       # row 8  ← target cell
])


def lval(f):
    return evaluate(f, LOOKUP_GRID).value


@pytest.mark.parametrize("formula,expected", [
    # VLOOKUP exact match
    ('=VLOOKUP(B7,A2:B6,2,FALSE)',          45.0),
    ('=VLOOKUP("Ujwal",A2:B6,2,FALSE)',     30.0),
    ('=VLOOKUP("Arjun",A2:B6,2,FALSE)',     22.0),
    # MATCH exact match (0)
    ('=MATCH("Rohan",A2:A6,0)',             2.0),
    ('=MATCH("Meera",A2:A6,0)',             4.0),
    # INDEX — single column range
    ('=INDEX(B2:B6,2)',                     45.0),
    ('=INDEX(B2:B6,4)',                     61.0),
    # INDEX with explicit col_num
    ('=INDEX(A2:B6,2,2)',                   45.0),
    ('=INDEX(A2:B6,3,1)',                   "Arjun"),
    # INDEX + MATCH combined
    ('=INDEX(B2:B6,MATCH(B7,A2:A6,0))',    45.0),
    # XLOOKUP exact match
    ('=XLOOKUP("Ujwal",A2:A6,B2:B6)',      30.0),
    ('=XLOOKUP("Meera",A2:A6,B2:B6)',      61.0),
    # XLOOKUP with not-found fallback
    ('=XLOOKUP("Ghost",A2:A6,B2:B6,"N/A")', "N/A"),
])
def test_lookup_functions(formula, expected):
    assert lval(formula) == pytest.approx(expected) if isinstance(expected, float) else lval(formula) == expected


@pytest.mark.parametrize("formula,code", [
    ('=VLOOKUP("Ghost",A2:B6,2,FALSE)',  "#N/A"),
    ('=VLOOKUP("Ujwal",A2:B6,5,FALSE)',  "#REF!"),
    ('=MATCH("Ghost",A2:A6,0)',          "#N/A"),
    ('=INDEX(B2:B6,99)',                 "#REF!"),
    ('=XLOOKUP("Ghost",A2:A6,B2:B6)',   "#N/A"),
])
def test_lookup_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, LOOKUP_GRID)
    assert exc.value.code == code


# ---------- stats functions ----------

STATS_GRID = Grid([
    ["Match", "Runs"],
    ["M1",    40],
    ["M2",    70],
    ["M3",    55],
    ["M4",    30],
    ["M5",    85],
])


def sval(f):
    return evaluate(f, STATS_GRID).value


@pytest.mark.parametrize("formula,expected", [
    ("=MEDIAN(B2:B6)",      55.0),   # sorted: 30,40,55,70,85 → middle = 55
    ("=MEDIAN(B2:B5)",      47.5),   # sorted: 30,40,55,70 → (40+55)/2 = 47.5
    ("=LARGE(B2:B6,1)",     85.0),
    ("=LARGE(B2:B6,2)",     70.0),
    ("=LARGE(B2:B6,5)",     30.0),
    ("=SMALL(B2:B6,1)",     30.0),
    ("=SMALL(B2:B6,2)",     40.0),
])
def test_stats_functions(formula, expected):
    assert sval(formula) == pytest.approx(expected)


@pytest.mark.parametrize("formula,code", [
    ("=LARGE(B2:B6,0)",     "#NUM!"),
    ("=LARGE(B2:B6,99)",    "#NUM!"),
    ("=SMALL(B2:B6,0)",     "#NUM!"),
    ("=MEDIAN()",           "#VALUE!"),
])
def test_stats_errors(formula, code):
    with pytest.raises(FormulaError) as exc:
        evaluate(formula, STATS_GRID)
    assert exc.value.code == code


# ---------- SUMPRODUCT and COUNTUNIQUE ----------

ARRAY_GRID = Grid([
    ["Item",    "Qty",  "Price"],
    ["Ball",    3,      10],
    ["Bat",     1,      50],
    ["Pad",     2,      20],
    ["Total",   "",     ""],
])


def aval(f):
    return evaluate(f, ARRAY_GRID).value


@pytest.mark.parametrize("formula,expected", [
    ("=SUMPRODUCT(B2:B4,C2:C4)", 120.0),  # 3*10 + 1*50 + 2*20 = 30+50+40 = 120
])
def test_sumproduct(formula, expected):
    assert aval(formula) == pytest.approx(expected)


UNIQUE_GRID = Grid([
    ["Venue"],
    ["Lord's"],
    ["Eden"],
    ["Lord's"],
    ["MCG"],
    ["Eden"],
    ["Count", ""],
])


@pytest.mark.parametrize("formula,expected", [
    ("=COUNTUNIQUE(A2:A6)",   3.0),   # Lord's, Eden, MCG
])
def test_countunique(formula, expected):
    assert evaluate(formula, UNIQUE_GRID).value == pytest.approx(expected)

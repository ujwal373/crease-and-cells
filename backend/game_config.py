"""Static game configuration constants mirrored from cc-engine.js.

These are the authoritative values served to the frontend via GET /api/world.
Any change here must be reflected in cc-engine.js and vice versa.
"""
from __future__ import annotations

LEVEL_XP: list[int] = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]
SKILL_XP: list[int] = [0, 60, 180, 360, 600]

FAMILIES: list[dict] = [
    {"id": "maths",  "name": "Maths",  "blurb": "SUM, AVERAGE, MIN, MAX, ROUND"},
    {"id": "text",   "name": "Text",   "blurb": "LEFT, RIGHT, MID, UPPER, TRIM, CONCAT"},
    {"id": "logic",  "name": "Logic",  "blurb": "IF, AND, OR, COUNTIF, SUMIF"},
    {"id": "date",   "name": "Dates",  "blurb": "DATE, YEAR, MONTH, DAYS"},
    {"id": "lookup", "name": "Lookup", "blurb": "VLOOKUP, INDEX, MATCH, XLOOKUP"},
    {"id": "stats",  "name": "Stats",  "blurb": "MEDIAN, LARGE, SMALL, RANK"},
    {"id": "arrays", "name": "Arrays", "blurb": "SUMPRODUCT, COUNTUNIQUE, TEXTJOIN"},
]

FAMILY_IDS: list[str] = [f["id"] for f in FAMILIES]

ITEMS: list[dict] = [
    {"id": "c_white",   "slot": "cap",    "name": "Basic White Cap",     "price": 0,   "hex": "#F4F1E8"},
    {"id": "c_sun",     "slot": "cap",    "name": "Sunrise Cap",         "price": 70,  "hex": "#F2B632"},
    {"id": "c_hat",     "slot": "cap",    "name": "Wide Sunhat",         "price": 90,  "hex": "#E9D8A6"},
    {"id": "c_helm",    "slot": "cap",    "name": "Training Helmet",     "price": 180, "hex": "#2C3E6B"},
    {"id": "j_white",   "slot": "jersey", "name": "Basic White Jersey",  "price": 0,   "hex": "#F4F1E8"},
    {"id": "j_sunrise", "slot": "jersey", "name": "Sunrise Gold Jersey", "price": 100, "hex": "#F2B632"},
    {"id": "j_teal",    "slot": "jersey", "name": "Club Teal Stripe",    "price": 120, "hex": "#1F7A7A"},
    {"id": "j_terra",   "slot": "jersey", "name": "Terracotta Stripe",   "price": 140, "hex": "#D9805F"},
    {"id": "s_white",   "slot": "shoes",  "name": "Basic White Shoes",   "price": 0,   "hex": "#F4F1E8"},
    {"id": "s_gold",    "slot": "shoes",  "name": "Sunrise Gold Shoes",  "price": 80,  "hex": "#F2B632"},
    {"id": "s_teal",    "slot": "shoes",  "name": "Club Teal Shoes",     "price": 90,  "hex": "#1F7A7A"},
    {"id": "s_night",   "slot": "shoes",  "name": "Night Spikes",        "price": 130, "hex": "#26262B"},
    {"id": "a_white",   "slot": "sleeve", "name": "Basic White Sleeve",  "price": 0,   "hex": "#F4F1E8"},
    {"id": "a_teal",    "slot": "sleeve", "name": "Club Teal Sleeve",    "price": 50,  "hex": "#1F7A7A"},
    {"id": "a_gold",    "slot": "sleeve", "name": "Sunrise Gold Sleeve", "price": 50,  "hex": "#F2B632"},
    {"id": "a_terra",   "slot": "sleeve", "name": "Terracotta Sleeve",   "price": 60,  "hex": "#D9805F"},
]

ITEMS_BY_ID: dict[str, dict] = {it["id"]: it for it in ITEMS}

DEFAULT_OWNED: dict[str, int] = {"c_white": 1, "j_white": 1, "s_white": 1, "a_white": 1}
DEFAULT_EQ: dict[str, str] = {"cap": "c_white", "jersey": "j_white", "shoes": "s_white", "sleeve": "a_white"}

CLUBS: list[dict] = [
    {
        "tier": 1, "id": "univ", "name": "University", "venue": "University Ground",
        "mode": "exam", "level": 2,
        "skills": {"maths": 1}, "gear": [],
    },
    {
        "tier": 2, "id": "shield", "name": "Shield Cup", "venue": "University Ground",
        "mode": "match", "level": 3,
        "skills": {"maths": 2, "logic": 1}, "gear": [{"any": "jersey"}],
    },
    {
        "tier": 3, "id": "intra", "name": "Intra State", "venue": "District Club",
        "mode": "checkpoints", "level": 4,
        "skills": {"logic": 2, "text": 1}, "gear": [{"any": "jersey"}, {"any": "cap"}],
    },
    {
        "tier": 4, "id": "inter", "name": "Inter Divisions", "venue": "District Ground",
        "mode": "match", "level": 5,
        "skills": {"lookup": 1, "date": 1}, "gear": [{"any": "jersey"}, {"any": "shoes"}],
    },
    {
        "tier": 5, "id": "state", "name": "State Trophy", "venue": "State Ground",
        "mode": "exam", "level": 6,
        "skills": {"lookup": 2, "stats": 1},
        "gear": [{"any": "jersey"}, {"any": "cap"}, {"any": "shoes"}],
    },
    {
        "tier": 6, "id": "league", "name": "Franchise League", "venue": "Franchise Town",
        "mode": "exam", "level": 7,
        "skills": {"stats": 2, "arrays": 1},
        "gear": [{"any": "jersey"}, {"any": "cap"}, {"any": "shoes"}, {"any": "sleeve"}],
    },
    {
        "tier": 7, "id": "national", "name": "National XI", "venue": "National Stadium",
        "mode": "checkpoints", "level": 8,
        "skills": {"maths": 2, "text": 2, "logic": 2, "date": 2, "lookup": 2, "stats": 2, "arrays": 2},
        "gear": [{"worn": "c_helm"}, {"worn": "j_terra"}, {"worn": "s_night"}, {"any": "sleeve"}],
    },
]

SESSIONS: dict[str, dict] = {
    "univ_exam":    {"name": "University entrance exam", "rounds": 3, "pass": 2, "secs": 0,  "cooldownH": 0,  "enrol": 1},
    "shield":       {"name": "Shield Cup match",         "rounds": 5, "pass": 3, "secs": 90, "cooldownH": 6,  "enrol": 2, "tier": 2},
    "intra_final":  {"name": "District club trial",      "rounds": 2, "pass": 1, "secs": 0,  "cooldownH": 0,  "enrol": 3},
    "inter":        {"name": "Inter Divisions match",    "rounds": 5, "pass": 3, "secs": 90, "cooldownH": 12, "enrol": 4, "tier": 4},
    "state_exam":   {"name": "State trial",              "rounds": 4, "pass": 3, "secs": 0,  "cooldownH": 0,  "enrol": 5},
    "league_exam":  {"name": "Franchise selection",      "rounds": 4, "pass": 3, "secs": 0,  "cooldownH": 0,  "enrol": 6},
    "leagueA":      {"name": "Match at Ground A",        "rounds": 5, "pass": 3, "secs": 75, "cooldownH": 0,  "tier": 6},
    "leagueB":      {"name": "Match at Ground B",        "rounds": 5, "pass": 3, "secs": 75, "cooldownH": 0,  "tier": 6},
    "national_exam": {"name": "National selection",      "rounds": 5, "pass": 4, "secs": 0,  "cooldownH": 0,  "enrol": 7},
    "national":     {"name": "Stadium match",            "rounds": 6, "pass": 4, "secs": 60, "cooldownH": 0,  "tier": 7, "big": True},
}

TIER_SESSION: list[str] = [
    "univ_exam", "shield", "intra_final", "inter",
    "state_exam", "league_exam", "national_exam",
]

CHECKPOINTS: dict[int, int] = {3: 2, 7: 3}

FACILITY_TIER: dict[str, int] = {
    "gym": 6, "pool": 6, "sauna": 6, "machine": 6, "gymN": 7, "poolN": 7,
}

LESSON_TOPICS: dict[str, list[str]] = {
    "batting":  ["maths", "stats", "logic"],
    "bowling":  ["text", "lookup", "date"],
    "fielding": ["arrays", "logic", "text"],
}

LESSONS: dict[str, dict] = {
    "maths": {
        "title": "Maths: totals and averages",
        "steps": [
            "SUM adds a range: =SUM(B2:B7).",
            "AVERAGE gives the mean: =AVERAGE(B2:B7).",
            "MAX and MIN find the best and worst; ROUND tidies decimals.",
        ],
        "example": "=ROUND(AVERAGE(B2:B7),1)",
    },
    "text": {
        "title": "Text: cleaning and joining",
        "steps": [
            "LEFT, RIGHT and MID cut pieces out of text.",
            'TRIM removes extra spaces; UPPER and PROPER fix the case.',
            'The & sign joins text: =A2&" "&B2.',
        ],
        "example": "=UPPER(TRIM(A2))",
    },
    "logic": {
        "title": "Logic: decisions and counting",
        "steps": [
            'IF picks between two answers: =IF(A2>=50,"Fifty","No").',
            "AND and OR combine tests inside IF.",
            "COUNTIF counts matches and SUMIF adds only matching rows.",
        ],
        "example": '=COUNTIF(B2:B9,">=50")',
    },
    "date": {
        "title": "Dates: gaps and parts",
        "steps": [
            "DATE builds a date from year, month, day.",
            "YEAR, MONTH and DAY pull the parts back out.",
            "DAYS(end,start) counts the gap between two dates.",
        ],
        "example": "=DAYS(B2,A2)",
    },
    "lookup": {
        "title": "Lookup: finding things",
        "steps": [
            "VLOOKUP finds a row by its first column.",
            "MATCH gives a position; INDEX returns the value at a position.",
            "XLOOKUP searches one range and returns from another.",
        ],
        "example": "=INDEX(B2:B6,MATCH(B7,A2:A6,0))",
    },
    "stats": {
        "title": "Stats: middles and ranks",
        "steps": [
            "MEDIAN is the middle value once sorted.",
            "LARGE(range,2) is the second biggest; SMALL is the opposite.",
            "RANK tells you where one value stands in a list.",
        ],
        "example": "=LARGE(B2:B9,2)",
    },
    "arrays": {
        "title": "Arrays: many cells at once",
        "steps": [
            "SUMPRODUCT multiplies matching cells and adds them.",
            "COUNTUNIQUE counts distinct values.",
            "TEXTJOIN joins many cells with a separator.",
        ],
        "example": "=SUMPRODUCT(B2:B6,C2:C6)",
    },
}

TIPS: list[str] = [
    "Press F4 in Excel to lock a cell reference with dollar signs.",
    "A range like B2:B7 is read top to bottom, then left to right.",
    "If a formula shows #NAME?, check spelling and quote marks.",
    "Name your header row clearly. Future you will thank present you.",
    "Ctrl+Shift+Down selects a column of data in one go.",
    "Check your answer with a quick mental estimate before you trust it.",
]


def level_for_xp(xp: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_XP[1:], 1):
        if xp >= threshold:
            level = i + 1
    return level


def skill_level_for_xp(xp: int) -> int:
    level = 0
    for i, threshold in enumerate(SKILL_XP[1:], 1):
        if xp >= threshold:
            level = i
    return level

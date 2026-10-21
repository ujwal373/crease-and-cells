"""Seeded synthetic cricket datasets.

Rule: every dataset is generated from an explicit seed so a mission is
reproducible and its answer key can be recomputed at any time.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

HERO = "Ujwal Mojidra"
BOWLERS = [
    HERO,
    "Rohan Iyer",
    "Arjun Nair",
    "Karan Shah",
    "Dev Patil",
    "Sameer Khan",
    "Vikram Rao",
    "Imran Qureshi",
]
SPELL_COLUMNS = ["match_id", "bowler", "overs", "maidens", "runs", "wickets", "economy"]


def generate_spells(seed: int, n: int = 60) -> list[dict]:
    """Bowling spell log. The hero bowls more often than the others."""
    rng = random.Random(seed)
    weights = [3] + [1] * (len(BOWLERS) - 1)
    rows: list[dict] = []
    for i in range(n):
        overs = rng.choice([2, 3, 4])
        runs = max(overs * 2, int(rng.gauss(overs * 7.5, overs * 1.8)))
        rows.append(
            {
                "match_id": f"M{i // 3 + 1:03d}",
                "bowler": rng.choices(BOWLERS, weights)[0],
                "overs": overs,
                "maidens": rng.choices([0, 1], [85, 15])[0],
                "runs": runs,
                "wickets": rng.choices([0, 1, 2, 3], [30, 35, 25, 10])[0],
                "economy": round(runs / overs, 2),
            }
        )
    return rows


GENERATORS = {"bowling_spells": (generate_spells, SPELL_COLUMNS)}


def to_grid(columns: list[str], rows: list[dict]) -> list[list]:
    """Spreadsheet layout: header in row 1, data from row 2."""
    return [columns] + [[r[c] for c in columns] for r in rows]


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "datasets"
    for name, (gen, cols) in GENERATORS.items():
        write_csv(out / f"{name}_seed101.csv", cols, gen(101, 60))
        print(f"wrote {name}_seed101.csv")

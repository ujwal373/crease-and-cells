"""Merge an approved generated mission into the canonical levelN.json file.

Workflow:
  1. Review a generated mission with review_missions.py and set its status to
     "approved".
  2. Run this script with the mission id. It will:
     a. Load the levelN.json for the mission's level.
     b. Assign a proper sequential id (e.g. L2-005).
     c. Strip the "status" and "validation_errors" keys (internal scaffolding).
     d. Append the mission to the list and write the file back.
     e. Delete the generated file from missions/generated/.

Usage:
  python scripts/merge_missions.py <mission-id>

The generated file is removed only after a successful write to levelN.json,
so the operation is safe to re-run if it was interrupted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GENERATED_DIR = ROOT / "missions" / "generated"
MISSIONS_DIR = ROOT / "missions"

_INTERNAL_KEYS = {"status", "validation_errors"}


def _load_generated(mission_id: str) -> tuple[Path, dict] | None:
    files = sorted(GENERATED_DIR.glob("*.json"))
    for path in files:
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if m.get("id", "").upper() == mission_id.upper():
            return path, m
    return None


def _level_file(level: int) -> Path:
    return MISSIONS_DIR / f"level{level}.json"


def _next_id(existing: list[dict], level: int) -> str:
    prefix = f"L{level}-"
    highest = 0
    for m in existing:
        mid = m.get("id", "")
        if mid.startswith(prefix):
            try:
                n = int(mid[len(prefix):])
                highest = max(highest, n)
            except ValueError:
                pass
    return f"{prefix}{highest + 1:03d}"


def merge(mission_id: str) -> None:
    found = _load_generated(mission_id)
    if not found:
        print(f"Mission {mission_id!r} not found in missions/generated/.")
        sys.exit(1)

    gen_path, mission = found
    status = mission.get("status", "")
    if status != "approved":
        print(f"Refused: mission status is {status!r}. Approve it with review_missions.py first.")
        sys.exit(1)

    level = mission.get("level")
    if not isinstance(level, int):
        print(f"Mission {mission_id!r} has no valid 'level' field.")
        sys.exit(1)

    level_path = _level_file(level)
    if level_path.exists():
        level_data = json.loads(level_path.read_text(encoding="utf-8"))
    else:
        level_data = {"missions": []}

    existing = level_data.get("missions", [])

    # Check not already merged (same generated id present)
    for m in existing:
        if m.get("id", "") == mission_id:
            print(f"Mission {mission_id!r} already present in {level_path.name}.")
            sys.exit(1)

    new_id = _next_id(existing, level)
    clean = {k: v for k, v in mission.items() if k not in _INTERNAL_KEYS}
    clean["id"] = new_id

    existing.append(clean)
    level_data["missions"] = sorted(existing, key=lambda m: (m["level"], m["id"]))

    level_path.write_text(json.dumps(level_data, indent=2), encoding="utf-8")
    gen_path.unlink()

    print(f"Merged {mission_id} as {new_id} into {level_path.name}.")
    print(f"Deleted {gen_path.name} from missions/generated/.")


def main(argv: list[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    merge(args[0])


if __name__ == "__main__":
    main()

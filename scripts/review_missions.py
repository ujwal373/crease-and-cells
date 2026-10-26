"""Review and approve generated missions.

Generated missions live in missions/generated/ with status verified,
needs_review, or invalid. This script lists them and lets you approve or
reject each one. Approved missions are ready to be merged via merge_missions.py.

Usage:
  python scripts/review_missions.py list
  python scripts/review_missions.py show   <mission-id>
  python scripts/review_missions.py approve <mission-id>  [--force]
  python scripts/review_missions.py reject  <mission-id>

approve refuses missions whose status is not "verified" unless --force is passed.
--force should only be used after manually confirming the validation errors.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GENERATED_DIR = ROOT / "missions" / "generated"


def _load_all() -> list[tuple[Path, dict]]:
    files = sorted(GENERATED_DIR.glob("*.json"))
    out = []
    for f in files:
        try:
            out.append((f, json.loads(f.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError):
            pass
    return out


def cmd_list() -> None:
    missions = _load_all()
    if not missions:
        print("No generated missions found in missions/generated/.")
        return
    fmt = "{:<20} {:<10} {:>5}  {:>3}  {:<40}"
    print(fmt.format("ID", "STATUS", "LVL", "ERR", "TITLE"))
    print("-" * 80)
    for _, m in missions:
        errors = m.get("validation_errors", [])
        err_count = str(len(errors)) if errors else "-"
        print(fmt.format(m.get("id", "?"), m.get("status", "?"),
                         str(m.get("level", "?")), err_count, m.get("title", "")[:40]))


def _find(mission_id: str) -> tuple[Path, dict] | None:
    for path, m in _load_all():
        if m.get("id", "").upper() == mission_id.upper():
            return path, m
    return None


def cmd_show(mission_id: str) -> None:
    found = _find(mission_id)
    if not found:
        print(f"Mission {mission_id!r} not found.")
        return
    _, m = found
    print(json.dumps(m, indent=2))


def cmd_approve(mission_id: str, *, force: bool = False) -> None:
    found = _find(mission_id)
    if not found:
        print(f"Mission {mission_id!r} not found.")
        return
    path, m = found
    status = m.get("status", "")
    if status != "verified" and not force:
        errors = m.get("validation_errors", [])
        print(f"Refused: mission status is {status!r}, not 'verified'.")
        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  {e}")
        print("Pass --force to approve anyway after manually reviewing these errors.")
        return
    m["status"] = "approved"
    path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    msg = " (forced)" if force and status != "verified" else ""
    print(f"Mission {mission_id} approved{msg}. Run merge_missions.py to add it to the game.")


def cmd_reject(mission_id: str) -> None:
    found = _find(mission_id)
    if not found:
        print(f"Mission {mission_id!r} not found.")
        return
    path, m = found
    m["status"] = "rejected"
    path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(f"Mission {mission_id} rejected.")


def main(argv: list[str] | None = None) -> None:
    args = (argv or sys.argv[1:])
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "show" and len(args) == 2:
        cmd_show(args[1])
    elif args[0] == "approve" and len(args) >= 2:
        force = "--force" in args
        cmd_approve(args[1], force=force)
    elif args[0] == "reject" and len(args) == 2:
        cmd_reject(args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

"""Review and approve generated missions.

Generated missions live in missions/generated/ with status=pending_review,
needs_review, or verified. This script lists them and lets you approve or
reject each one. Approved missions are ready to be manually merged into a
levelN.json file.

Usage:
  python scripts/review_missions.py list
  python scripts/review_missions.py show   <mission-id>
  python scripts/review_missions.py approve <mission-id>
  python scripts/review_missions.py reject  <mission-id>
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


def _set_status(mission_id: str, new_status: str) -> None:
    found = _find(mission_id)
    if not found:
        print(f"Mission {mission_id!r} not found.")
        return
    path, m = found
    m["status"] = new_status
    path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(f"Mission {mission_id} status set to {new_status!r}.")
    if new_status == "approved":
        print(f"Ready to merge into missions/level{m.get('level', '?')}.json.")


def main(argv: list[str] | None = None) -> None:
    args = (argv or sys.argv[1:])
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "show" and len(args) == 2:
        cmd_show(args[1])
    elif args[0] == "approve" and len(args) == 2:
        _set_status(args[1], "approved")
    elif args[0] == "reject" and len(args) == 2:
        _set_status(args[1], "rejected")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

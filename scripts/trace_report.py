"""Read logs/trace.jsonl and print a summary table grouped by model.

Columns: total calls, cache hit rate, fallback rate (with reason breakdown),
average and p95 latency, total input tokens, total output tokens, total cost.

Usage:
  python scripts/trace_report.py
  python scripts/trace_report.py path/to/trace.jsonl
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACE = ROOT / "logs" / "trace.jsonl"


def build_report(path: Path) -> dict[str, dict] | None:
    """Parse a trace file and return stats grouped by model.

    Returns None if the file does not exist or contains no tutor.hint events.
    """
    if not path.exists():
        return None

    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "tutor.hint":
            rows.append(record)

    if not rows:
        return None

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r.get("model", "unknown")].append(r)

    result: dict[str, dict] = {}
    for model, calls in by_model.items():
        n = len(calls)
        cache_hits = sum(1 for c in calls if c.get("cache_hit"))
        fallbacks = [c for c in calls if c.get("fallback_used")]
        fallback_reasons: dict[str, int] = defaultdict(int)
        for c in fallbacks:
            fallback_reasons[c.get("fallback_reason", "")] += 1

        latencies = [c["latency_ms"] for c in calls if "latency_ms" in c]
        latencies.sort()
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        total_in = sum(c.get("input_tokens", 0) for c in calls)
        total_out = sum(c.get("output_tokens", 0) for c in calls)
        total_cost = sum(c.get("cost_usd", 0.0) for c in calls)

        result[model] = {
            "total_calls": n,
            "cache_hit_rate": cache_hits / n,
            "fallback_rate": len(fallbacks) / n,
            "fallback_reasons": dict(fallback_reasons),
            "avg_latency_ms": round(avg_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost_usd": round(total_cost, 8),
        }

    return result


def print_report(stats: dict[str, dict]) -> None:
    for model, s in sorted(stats.items()):
        print(f"\nModel: {model}")
        print(f"  {'total calls':<30} {s['total_calls']}")
        print(f"  {'cache hit rate':<30} {s['cache_hit_rate']:>6.0%}")
        print(f"  {'fallback rate':<30} {s['fallback_rate']:>6.0%}")
        if s["fallback_reasons"]:
            for reason, count in sorted(s["fallback_reasons"].items()):
                print(f"    {'  reason: ' + reason:<28} {count}")
        print(f"  {'avg latency ms':<30} {s['avg_latency_ms']:>8.1f}")
        print(f"  {'p95 latency ms':<30} {s['p95_latency_ms']:>8.1f}")
        print(f"  {'total input tokens':<30} {s['total_input_tokens']:>10}")
        print(f"  {'total output tokens':<30} {s['total_output_tokens']:>10}")
        print(f"  {'total cost USD':<30} ${s['total_cost_usd']:>10.6f}")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else DEFAULT_TRACE

    stats = build_report(path)
    if stats is None:
        if not path.exists():
            print(f"Trace file not found: {path}")
        else:
            print(f"No tutor.hint events in {path}")
        return

    print_report(stats)


if __name__ == "__main__":
    main()

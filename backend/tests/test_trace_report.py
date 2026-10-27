"""Tests for scripts/trace_report.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import scripts.trace_report as tr


def _write_trace(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )


def test_missing_file_returns_none(tmp_path):
    result = tr.build_report(tmp_path / "nonexistent.jsonl")
    assert result is None


def test_empty_file_returns_none(tmp_path):
    f = tmp_path / "trace.jsonl"
    f.write_text("", encoding="utf-8")
    result = tr.build_report(f)
    assert result is None


def test_file_with_no_tutor_events_returns_none(tmp_path):
    f = tmp_path / "trace.jsonl"
    _write_trace(f, [{"ts": 1, "event": "submit_answer", "player_id": "p1"}])
    result = tr.build_report(f)
    assert result is None


def test_basic_stats(tmp_path):
    f = tmp_path / "trace.jsonl"
    records = [
        {
            "ts": 1000, "event": "tutor.hint",
            "model": "claude-haiku-5-5",
            "input_tokens": 100, "output_tokens": 20,
            "cost_usd": 0.00002,
            "latency_ms": 300.0,
            "cache_hit": False, "fallback_used": False, "fallback_reason": "",
        },
        {
            "ts": 1001, "event": "tutor.hint",
            "model": "claude-haiku-5-5",
            "input_tokens": 120, "output_tokens": 25,
            "cost_usd": 0.000025,
            "latency_ms": 450.0,
            "cache_hit": True, "fallback_used": False, "fallback_reason": "",
        },
        {
            "ts": 1002, "event": "tutor.hint",
            "model": "claude-haiku-5-5",
            "input_tokens": 0, "output_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": 0.0,
            "cache_hit": False, "fallback_used": True,
            "fallback_reason": "player_daily_cap_reached",
        },
    ]
    _write_trace(f, records)

    result = tr.build_report(f)
    assert result is not None
    s = result["claude-haiku-5-5"]

    assert s["total_calls"] == 3
    assert s["cache_hit_rate"] == pytest.approx(1 / 3)
    assert s["fallback_rate"] == pytest.approx(1 / 3)
    assert s["fallback_reasons"] == {"player_daily_cap_reached": 1}
    assert s["total_input_tokens"] == 220
    assert s["total_output_tokens"] == 45
    assert s["total_cost_usd"] == pytest.approx(0.000045)


def test_multiple_models(tmp_path):
    f = tmp_path / "trace.jsonl"
    records = [
        {
            "ts": 1, "event": "tutor.hint", "model": "claude-haiku-5-5",
            "input_tokens": 50, "output_tokens": 10, "cost_usd": 0.00001,
            "latency_ms": 200.0, "cache_hit": False, "fallback_used": False, "fallback_reason": "",
        },
        {
            "ts": 2, "event": "tutor.hint", "model": "claude-sonnet-5-5",
            "input_tokens": 200, "output_tokens": 80, "cost_usd": 0.001,
            "latency_ms": 900.0, "cache_hit": False, "fallback_used": False, "fallback_reason": "",
        },
    ]
    _write_trace(f, records)

    result = tr.build_report(f)
    assert result is not None
    assert "claude-haiku-5-5" in result
    assert "claude-sonnet-5-5" in result
    assert result["claude-haiku-5-5"]["total_calls"] == 1
    assert result["claude-sonnet-5-5"]["total_calls"] == 1


def test_p95_latency(tmp_path):
    f = tmp_path / "trace.jsonl"
    # 20 records with latencies 1..20 ms
    records = [
        {
            "ts": i, "event": "tutor.hint", "model": "m",
            "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
            "latency_ms": float(i), "cache_hit": False,
            "fallback_used": False, "fallback_reason": "",
        }
        for i in range(1, 21)
    ]
    _write_trace(f, records)

    result = tr.build_report(f)
    assert result is not None
    # p95 of [1..20] sorted: index int(20*0.95)=19 -> value 20
    assert result["m"]["p95_latency_ms"] == pytest.approx(20.0)


def test_print_report_runs_without_error(tmp_path, capsys):
    f = tmp_path / "trace.jsonl"
    records = [
        {
            "ts": 1, "event": "tutor.hint", "model": "claude-haiku-5-5",
            "input_tokens": 100, "output_tokens": 20, "cost_usd": 0.00002,
            "latency_ms": 300.0, "cache_hit": False, "fallback_used": False, "fallback_reason": "",
        },
    ]
    _write_trace(f, records)
    stats = tr.build_report(f)
    tr.print_report(stats)
    out = capsys.readouterr().out
    assert "claude-haiku-5-5" in out
    assert "total calls" in out

"""Minimal observability: structured JSONL traces with latency.

Every agent event and every service call is logged. Fields for LLM calls
(model, input_tokens, output_tokens, cost_usd) are accepted as plain kwargs so
the same trace file will carry them once the Tutor calls a model.
Set CC_TRACE to change the file location.
"""
from __future__ import annotations

import contextvars
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# Set by the API request-ID middleware so every trace record carries the
# originating HTTP request ID. Empty string means no active request context.
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def set_request_id(req_id: str) -> None:
    _request_id.set(req_id)


def _path() -> Path:
    return Path(os.environ.get("CC_TRACE", "logs/trace.jsonl"))


def trace(event: str, **fields) -> None:
    req_id = _request_id.get()
    if req_id:
        fields["request_id"] = req_id
    record = {"ts": round(time.time(), 3), "event": event, **fields}
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except OSError:
        pass  # observability must never break the game


@contextmanager
def span(name: str, **fields) -> Iterator[None]:
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        trace(name, latency_ms=round((time.perf_counter() - start) * 1000, 2), status=status, **fields)

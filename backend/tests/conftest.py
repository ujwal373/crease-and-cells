import pytest

from backend.service import GameService


@pytest.fixture(autouse=True)
def _trace_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("CC_TRACE", str(tmp_path / "trace.jsonl"))


@pytest.fixture
def svc():
    return GameService(":memory:")

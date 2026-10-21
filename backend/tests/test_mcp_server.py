import asyncio

import pytest


@pytest.fixture
def mcp_module(monkeypatch, tmp_path):
    monkeypatch.setenv("CC_DB", str(tmp_path / "t.db"))
    import importlib

    import backend.mcp_server as m
    return importlib.reload(m)


def test_tools_are_registered(mcp_module):
    tools = asyncio.run(mcp_module.server.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "get_next_mission", "submit_answer", "get_hint", "ask_coach",
        "get_wallet", "list_store", "buy_item",
    }


def test_tool_call_round_trip(mcp_module):
    result = asyncio.run(mcp_module.server.call_tool("get_wallet", {"player_id": "mcp-test"}))
    assert "mcp-test" in str(result)

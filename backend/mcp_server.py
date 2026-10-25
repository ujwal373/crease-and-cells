"""MCP server exposing the game as tools.

Run:  python -m backend.mcp_server        (stdio transport)

Any MCP client (Claude Code, Claude Desktop, Cursor) can play the game through
these tools. The answer key and reference solutions never leave the service.
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from .service import GameService

server = MCPServer("crease-and-cells")

def _make_tutor_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    import anthropic  # noqa: PLC0415
    return anthropic.Anthropic(api_key=api_key)

service = GameService(
    os.environ.get("CC_DB", "crease_cells.db"),
    tutor_client=_make_tutor_client(),
)


@server.tool()
def get_next_mission(player_id: str, name: str = "") -> dict:
    """Get the player's next spreadsheet mission, including the sheet data."""
    return service.get_next_mission(player_id, name or None)


@server.tool()
def submit_answer(player_id: str, mission_id: str, formula: str) -> dict:
    """Submit a spreadsheet formula (starting with =) for a mission. Returns pass/fail and rewards."""
    return service.submit_answer(player_id, mission_id, formula)


@server.tool()
def get_hint(player_id: str, mission_id: str) -> dict:
    """Get the next progressive hint. Using a hint removes the no-hint bonus."""
    return service.get_hint(player_id, mission_id)


@server.tool()
def ask_coach(player_id: str, mission_id: str, message: str) -> dict:
    """Ask the coach a question. Screened for prompt injection and answer extraction."""
    return service.ask_coach(player_id, mission_id, message)


@server.tool()
def get_wallet(player_id: str) -> dict:
    """Coins, xp, level and the current outfit."""
    return service.get_wallet(player_id)


@server.tool()
def list_store(player_id: str) -> list[dict]:
    """Attire available in the shop, with ownership flags."""
    return service.list_store(player_id)


@server.tool()
def buy_item(player_id: str, item_id: str) -> dict:
    """Buy and equip an attire item using coins."""
    return service.buy_item(player_id, item_id)


if __name__ == "__main__":
    server.run()

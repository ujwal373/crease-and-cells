"""Tests for skill XP, level thresholds, and leaderboard updates."""
from __future__ import annotations

from backend.game_config import LEVEL_XP, SKILL_XP, level_for_xp, skill_level_for_xp
from backend.state import GameState


# ---------------------------------------------------------------------------
# Threshold helpers
# ---------------------------------------------------------------------------

def test_skill_level_boundaries():
    assert skill_level_for_xp(0)   == 0
    assert skill_level_for_xp(59)  == 0
    assert skill_level_for_xp(60)  == 1
    assert skill_level_for_xp(179) == 1
    assert skill_level_for_xp(180) == 2
    assert skill_level_for_xp(359) == 2
    assert skill_level_for_xp(360) == 3
    assert skill_level_for_xp(599) == 3
    assert skill_level_for_xp(600) == 4


def test_level_for_xp_boundaries():
    assert level_for_xp(0)    == 1
    assert level_for_xp(99)   == 1
    assert level_for_xp(100)  == 2
    assert level_for_xp(249)  == 2
    assert level_for_xp(250)  == 3
    assert level_for_xp(3199) == 9
    assert level_for_xp(3200) == 10


def test_skill_xp_list_has_five_tiers():
    assert len(SKILL_XP) == 5
    assert SKILL_XP[0] == 0


def test_level_xp_list_has_ten_levels():
    assert len(LEVEL_XP) == 10
    assert LEVEL_XP[0] == 0


# ---------------------------------------------------------------------------
# GameState skill XP persistence
# ---------------------------------------------------------------------------

def test_add_skill_xp_accumulates():
    state = GameState(":memory:")
    state.ensure_player("p1")
    total = state.add_skill_xp("p1", "maths", 30)
    assert total == 30
    total = state.add_skill_xp("p1", "maths", 35)
    assert total == 65


def test_add_skill_xp_different_families_independent():
    state = GameState(":memory:")
    state.ensure_player("p1")
    state.add_skill_xp("p1", "maths", 70)
    state.add_skill_xp("p1", "text", 40)
    sxp = state.skill_xp("p1")
    assert sxp["maths"] == 70
    assert sxp["text"] == 40
    assert sxp.get("logic", 0) == 0


def test_skill_xp_starts_at_zero():
    state = GameState(":memory:")
    state.ensure_player("p1")
    assert state.skill_xp("p1") == {}


# ---------------------------------------------------------------------------
# Level-up detection via state.award
# ---------------------------------------------------------------------------

def test_award_detects_level_up():
    state = GameState(":memory:")
    state.ensure_player("p1")
    # Give enough XP to reach level 2 (need 100)
    before = state.wallet("p1")
    assert before["level"] == 1
    result = state.award("p1", 0, 100)
    assert result["level"] == 2


def test_award_no_level_up_when_xp_insufficient():
    state = GameState(":memory:")
    state.ensure_player("p1")
    result = state.award("p1", 0, 50)
    assert result["level"] == 1


def test_award_accumulates_coins_and_xp():
    state = GameState(":memory:")
    state.ensure_player("p1")
    state.award("p1", 10, 20)
    state.award("p1", 15, 30)
    w = state.wallet("p1")
    assert w["coins"] == 25
    assert w["xp"] == 50


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def test_leaderboard_ordered_by_xp():
    state = GameState(":memory:")
    for pid, xp in [("p1", 50), ("p2", 200), ("p3", 100)]:
        state.ensure_player(pid)
        state.update_leaderboard(pid, f"Player {pid}", 0, xp, 1, 0)
    lb = state.get_leaderboard()
    assert [r["player_id"] for r in lb] == ["p2", "p3", "p1"]


def test_leaderboard_limit():
    state = GameState(":memory:")
    for i in range(25):
        pid = f"p{i}"
        state.ensure_player(pid)
        state.update_leaderboard(pid, pid, 0, i * 10, 1, 0)
    assert len(state.get_leaderboard(10)) == 10
    assert len(state.get_leaderboard(20)) == 20


def test_leaderboard_upserts():
    state = GameState(":memory:")
    state.ensure_player("p1")
    state.update_leaderboard("p1", "Alice", 50, 100, 2, 0)
    state.update_leaderboard("p1", "Alice", 90, 300, 3, 1)
    lb = state.get_leaderboard()
    assert lb[0]["coins"] == 90
    assert lb[0]["tier"] == 1

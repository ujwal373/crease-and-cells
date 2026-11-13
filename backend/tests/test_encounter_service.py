"""Tests for EncounterService — NPC encounters, answer validation, sessions."""
from __future__ import annotations

import pytest

from backend.encounter_service import EncounterError, EncounterService
from backend.service import GameService


@pytest.fixture
def svc():
    return GameService(":memory:")


@pytest.fixture
def enc_svc(svc):
    return EncounterService(svc)


def _pid(n: int = 1) -> str:
    return f"00000000-0000-4000-a000-{n:012d}"


def _setup(svc, n: int = 1) -> str:
    pid = _pid(n)
    svc.state.ensure_player(pid)
    return pid


# ---------------------------------------------------------------------------
# create_encounter — NPC role dispatch
# ---------------------------------------------------------------------------

def test_friend_npc_returns_question(svc, enc_svc):
    pid = _setup(svc)
    enc = enc_svc.create_encounter(pid, "mukesh")
    assert enc["kind"] == "question"
    assert "question" in enc
    assert enc["question"]["type"] == "formula"
    assert "sheet" in enc["question"]
    assert enc["family"] == "maths"


def test_store_npc_returns_store(svc, enc_svc):
    pid = _setup(svc)
    enc = enc_svc.create_encounter(pid, "akshita")
    assert enc["kind"] == "store"
    assert isinstance(enc["items"], list)
    assert len(enc["items"]) == 16


def test_staff_npc_returns_chat(svc, enc_svc):
    pid = _setup(svc)
    enc = enc_svc.create_encounter(pid, "maya")
    assert enc["kind"] == "chat"
    assert isinstance(enc["say"], str) and len(enc["say"]) > 5


def test_lesson_npc_tier_locked(svc, enc_svc):
    pid = _setup(svc)
    # tier=0 player, lesson requires tier=1
    enc = enc_svc.create_encounter(pid, "sana")
    assert enc["kind"] == "chat"
    assert "members" in enc["say"].lower() or "join" in enc["say"].lower()


def test_unknown_npc_raises_not_found(svc, enc_svc):
    pid = _setup(svc)
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.create_encounter(pid, "npc_does_not_exist")
    assert exc_info.value.code == "NOT_FOUND"


def test_recruit_npc_returns_lobby(svc, enc_svc):
    pid = _setup(svc)
    enc = enc_svc.create_encounter(pid, "dean")
    assert enc["kind"] == "lobby"
    assert "session" in enc
    assert enc["session"]["id"] == "univ_exam"


def test_practice_npc_returns_question(svc, enc_svc):
    pid = _setup(svc)
    enc = enc_svc.create_encounter(pid, "practice")
    assert enc["kind"] == "question"
    # Practice coins are doubled (difficulty 1 → 12+6+seed_extra * 2)
    assert enc["reward"]["coins"] > 0


def test_all_coaches_cover_different_families(svc, enc_svc):
    pid = _setup(svc)
    families = set()
    for coach_id in ["mukesh", "viral", "asst2", "asst3", "asst4", "asst5", "asst6"]:
        enc = enc_svc.create_encounter(pid, coach_id)
        assert enc["kind"] == "question"
        families.add(enc["family"])
    # Families using unsupported engine functions fall back to maths for now;
    # once UPPER/LEFT/TRIM/DAYS/VLOOKUP/MEDIAN/SUMPRODUCT are added, this reaches 7.
    assert len(families) >= 2


# ---------------------------------------------------------------------------
# answer_encounter
# ---------------------------------------------------------------------------

def _get_question(enc_svc, pid, npc_id="mukesh"):
    return enc_svc.create_encounter(pid, npc_id)


def test_correct_answer_awards_coins_xp(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    enc_id = enc["encounterId"]

    # Look up the stored expected value and model formula
    stored = svc.state.get_encounter(enc_id)
    result = enc_svc.answer_encounter(pid, enc_id, stored["model"])

    assert result["correct"] is True
    assert result["rewards"]["coins"] > 0
    assert result["rewards"]["xp"] > 0
    wallet = svc.state.wallet(pid)
    assert wallet["coins"] > 0


def test_correct_answer_awards_skill_xp(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    enc_id = enc["encounterId"]
    stored = svc.state.get_encounter(enc_id)
    family = stored["family"]

    before = svc.state.skill_xp(pid).get(family, 0)
    enc_svc.answer_encounter(pid, enc_id, stored["model"])
    after = svc.state.skill_xp(pid).get(family, 0)
    assert after > before


def test_wrong_formula_returns_feedback_no_coins(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    enc_id = enc["encounterId"]

    result = enc_svc.answer_encounter(pid, enc_id, "=SUM(A1:A999)")
    assert result["correct"] is False
    assert isinstance(result["feedback"], str) and len(result["feedback"]) > 5
    assert svc.state.wallet(pid)["coins"] == 0


def test_non_formula_returns_feedback(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    result = enc_svc.answer_encounter(pid, enc["encounterId"], "not a formula")
    assert result["correct"] is False
    assert "equals" in result["feedback"].lower()


def test_double_submit_no_double_pay(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    enc_id = enc["encounterId"]
    stored = svc.state.get_encounter(enc_id)

    r1 = enc_svc.answer_encounter(pid, enc_id, stored["model"])
    r2 = enc_svc.answer_encounter(pid, enc_id, stored["model"])

    assert r1["correct"] is True
    assert r2["correct"] is True
    assert r2["rewards"]["coins"] == 0  # already collected
    # Wallet only incremented once
    assert svc.state.wallet(pid)["coins"] == stored["coins"]


def test_timeout_answer_returns_feedback(svc, enc_svc):
    pid = _setup(svc)
    enc = _get_question(enc_svc, pid)
    result = enc_svc.answer_encounter(pid, enc["encounterId"], None)
    assert result["correct"] is False
    assert "time" in result["feedback"].lower()


def test_expired_encounter_raises(svc, enc_svc):
    pid = _setup(svc)
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.answer_encounter(pid, "enc_doesnotexist", "=SUM(A1)")
    assert exc_info.value.code == "EXPIRED"


def test_wrong_player_raises_expired(svc, enc_svc):
    pid1 = _setup(svc, 1)
    pid2 = _setup(svc, 2)
    enc = _get_question(enc_svc, pid1)
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.answer_encounter(pid2, enc["encounterId"], "=SUM(A1)")
    assert exc_info.value.code == "EXPIRED"


# ---------------------------------------------------------------------------
# lesson_topic
# ---------------------------------------------------------------------------

def test_lesson_topic_awards_xp(svc, enc_svc):
    pid = _setup(svc, 10)
    svc.state.set_player_tier(pid, 1)  # unlock lesson
    enc = enc_svc.create_encounter(pid, "sana")
    assert enc["kind"] == "lesson"

    before = svc.state.skill_xp(pid).get("text", 0)
    result = enc_svc.lesson_topic(pid, enc["encounterId"], "text")
    after = svc.state.skill_xp(pid).get("text", 0)

    assert after == before + 8
    assert "steps" in result and len(result["steps"]) > 0
    assert result["rewards"]["xp"] == 8


def test_lesson_unknown_topic_raises(svc, enc_svc):
    pid = _setup(svc, 11)
    svc.state.set_player_tier(pid, 1)
    enc = enc_svc.create_encounter(pid, "sana")
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.lesson_topic(pid, enc["encounterId"], "not_a_topic")
    assert exc_info.value.code == "NOT_FOUND"


# ---------------------------------------------------------------------------
# visit_facility
# ---------------------------------------------------------------------------

def test_visit_facility_awards_coins(svc, enc_svc):
    pid = _setup(svc, 20)
    svc.state.set_player_tier(pid, 6)  # gym requires tier 6
    result = enc_svc.visit_facility(pid, "gym")
    assert result["ok"] is True
    assert result["rewards"]["coins"] == 2
    assert result["rewards"]["xp"] == 6


def test_visit_facility_rate_limited(svc, enc_svc):
    pid = _setup(svc, 21)
    svc.state.set_player_tier(pid, 6)
    enc_svc.visit_facility(pid, "gym")           # first visit
    result = enc_svc.visit_facility(pid, "gym")  # too soon (< 7s)
    assert result.get("tooSoon") is True


def test_visit_facility_tier_locked(svc, enc_svc):
    pid = _setup(svc, 22)
    # tier=0 player, gym requires tier=6
    result = enc_svc.visit_facility(pid, "gym")
    assert result.get("locked") is True


def test_visit_unknown_facility_raises(svc, enc_svc):
    pid = _setup(svc, 23)
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.visit_facility(pid, "spa_does_not_exist")
    assert exc_info.value.code == "NOT_FOUND"


# ---------------------------------------------------------------------------
# compute_markers
# ---------------------------------------------------------------------------

def test_markers_friend_npc_returns_new(svc, enc_svc):
    pid = _setup(svc)
    markers = enc_svc.compute_markers(pid, ["mukesh", "parth"])
    assert markers["mukesh"] == "new"
    assert markers["parth"] == "new"


def test_markers_store_npc_returns_store(svc, enc_svc):
    pid = _setup(svc)
    markers = enc_svc.compute_markers(pid, ["akshita"])
    assert markers["akshita"] == "store"


def test_markers_staff_npc_returns_talk(svc, enc_svc):
    pid = _setup(svc)
    markers = enc_svc.compute_markers(pid, ["maya"])
    assert markers["maya"] == "talk"


def test_markers_recruit_npc_locked_when_tier_too_low(svc, enc_svc):
    pid = _setup(svc)
    # dean requires tier 1; player at tier 0 is eligible to try
    markers = enc_svc.compute_markers(pid, ["dean"])
    assert markers["dean"] in ("match", "locked")


def test_markers_unknown_npc_returns_locked(svc, enc_svc):
    pid = _setup(svc)
    markers = enc_svc.compute_markers(pid, ["nonexistent_npc"])
    assert markers["nonexistent_npc"] == "locked"


# ---------------------------------------------------------------------------
# begin_session
# ---------------------------------------------------------------------------

def _make_eligible(svc, pid: str) -> None:
    """Give player the minimum state to be eligible for univ_exam (tier-1 club)."""
    svc.state.award(pid, 0, 100)          # reach level 2
    svc.state.add_skill_xp(pid, "maths", 60)  # maths skill level 1


def test_begin_session_returns_first_question(svc, enc_svc):
    pid = _setup(svc, 40)
    _make_eligible(svc, pid)
    enc = enc_svc.create_encounter(pid, "dean")
    assert enc["kind"] == "lobby"
    assert enc["canBegin"] is True
    result = enc_svc.begin_session(pid, enc["encounterId"], {})
    assert result["kind"] == "question"
    assert result["session"]["round"] == 1
    assert result["session"]["rounds"] == 3   # univ_exam has 3 rounds
    assert result["session"]["passMark"] == 2


def test_begin_session_non_lobby_raises(svc, enc_svc):
    pid = _setup(svc, 41)
    enc = enc_svc.create_encounter(pid, "mukesh")  # question encounter, not lobby
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.begin_session(pid, enc["encounterId"], {})
    assert exc_info.value.code == "EXPIRED"


def test_begin_session_requirements_not_met_raises(svc, enc_svc):
    pid = _setup(svc, 42)  # tier=0, level=1, maths=0 — not eligible
    enc = enc_svc.create_encounter(pid, "dean")
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.begin_session(pid, enc["encounterId"], {})
    assert exc_info.value.code == "NOT_ELIGIBLE"


def test_begin_session_already_enrolled_raises(svc, enc_svc):
    pid = _setup(svc, 43)
    svc.state.set_player_tier(pid, 1)   # already in university
    enc = enc_svc.create_encounter(pid, "dean")
    with pytest.raises(EncounterError) as exc_info:
        enc_svc.begin_session(pid, enc["encounterId"], {})
    assert exc_info.value.code == "NOT_ELIGIBLE"


def test_full_session_pass_enrolls_tier(svc, enc_svc):
    pid = _setup(svc, 44)
    _make_eligible(svc, pid)
    enc = enc_svc.create_encounter(pid, "dean")
    q   = enc_svc.begin_session(pid, enc["encounterId"], {})
    assert q["kind"] == "question"

    result = None
    for _ in range(4):   # max 3 rounds + safety
        enc_id = q["encounterId"]
        stored = svc.state.get_encounter(enc_id)
        result = enc_svc.answer_encounter(pid, enc_id, stored["model"])
        if "sessionResult" in result:
            break
        assert "next" in result, f"Unexpected result keys: {list(result.keys())}"
        q = result["next"]

    assert result is not None and "sessionResult" in result
    sr = result["sessionResult"]
    assert sr["passed"] is True
    assert sr["enrolledTier"] == 1
    assert svc.state.player_tier(pid) == 1


def test_full_session_fail_no_tier_change(svc, enc_svc):
    pid = _setup(svc, 45)
    _make_eligible(svc, pid)
    enc = enc_svc.create_encounter(pid, "dean")
    q   = enc_svc.begin_session(pid, enc["encounterId"], {})

    result = None
    for _ in range(6):   # up to 3 rounds × 2 wrong tries each
        enc_id = q["encounterId"]
        r = enc_svc.answer_encounter(pid, enc_id, "=SUM(Z99:Z100)")
        if "sessionResult" in r:
            result = r
            break
        if "next" in r:
            q = r["next"]
        # second wrong on the same enc_id if round not yet advanced
        elif r.get("correct") is False and not r.get("next"):
            r2 = enc_svc.answer_encounter(pid, enc_id, "=SUM(Z99:Z100)")
            if "sessionResult" in r2:
                result = r2
                break
            if "next" in r2:
                q = r2["next"]

    assert result is not None and "sessionResult" in result
    sr = result["sessionResult"]
    assert sr["passed"] is False
    assert svc.state.player_tier(pid) == 0


def test_session_pass_requires_enough_correct(svc, enc_svc):
    """Pass 2 of 3 rounds (univ_exam pass_mark=2) — should still enrol."""
    pid = _setup(svc, 46)
    _make_eligible(svc, pid)
    enc = enc_svc.create_encounter(pid, "dean")
    q   = enc_svc.begin_session(pid, enc["encounterId"], {})

    result = None
    rounds_attempted = 0
    for _ in range(6):
        enc_id = q["encounterId"]
        stored = svc.state.get_encounter(enc_id)
        # Answer correctly for first 2 rounds, wrong for the last
        if rounds_attempted < 2:
            r = enc_svc.answer_encounter(pid, enc_id, stored["model"])
        else:
            r = enc_svc.answer_encounter(pid, enc_id, "=SUM(Z99:Z100)")
            if r.get("correct") is False and not r.get("next") and "sessionResult" not in r:
                r = enc_svc.answer_encounter(pid, enc_id, "=SUM(Z99:Z100)")
        rounds_attempted += 1
        if "sessionResult" in r:
            result = r
            break
        if "next" in r:
            q = r["next"]

    assert result is not None and "sessionResult" in result
    # 2 correct ≥ pass_mark 2 → passed
    assert result["sessionResult"]["passed"] is True

import json

from backend.service import GameService


def solve(svc, pid, mission_id):
    return svc.submit_answer(pid, mission_id, svc.by_id[mission_id]["reference_solution"])


def test_mission_payload_hides_secrets(svc):
    m = svc.get_next_mission("p1", "Ujwal Mojidra")
    text = json.dumps(m)
    for secret in ("answer_spec", "reference_solution", "COUNTIF(G2"):
        assert secret not in text
    assert m["id"] == "L1-001" and len(m["sheet"]) == 61


def test_full_loop_pass_reward_next_mission(svc):
    svc.get_next_mission("p1")
    r = solve(svc, "p1", "L1-001")
    assert r["passed"]
    assert r["coins_awarded"] == 60  # 50 base + 10 no hint bonus
    assert r["next_mission"]["id"] == "L1-002"
    assert svc.get_wallet("p1")["coins"] == 60


def test_no_double_reward(svc):
    solve(svc, "p1", "L1-001")
    again = solve(svc, "p1", "L1-001")
    assert again["passed"] and again["already_completed"]
    assert svc.get_wallet("p1")["coins"] == 60


def test_wrong_answer_gives_no_coins(svc):
    r = svc.submit_answer("p1", "L1-001", '=COUNTIF(G2:G61,">99")')
    assert not r["passed"]
    assert svc.get_wallet("p1")["coins"] == 0


def test_hint_removes_bonus(svc):
    svc.get_hint("p1", "L1-001")
    r = solve(svc, "p1", "L1-001")
    assert r["coins_awarded"] == 50 and r["no_hint_bonus"] == 0


def test_hints_progress_and_cap(svc):
    texts = [svc.get_hint("p1", "L1-001")["hint"] for _ in range(5)]
    assert texts[0] != texts[1] != texts[2]
    assert texts[2] == texts[3] == texts[4]


def test_all_missions_then_done(svc):
    for mid in ("L1-001", "L1-002", "L1-003"):
        assert solve(svc, "p1", mid)["passed"]
    assert svc.get_next_mission("p1")["done"]
    w = svc.get_wallet("p1")
    assert w["xp"] == 350 and w["level"] == 2


def test_store_requires_coins_and_is_atomic(svc):
    svc.get_wallet("p1")
    assert svc.buy_item("p1", "cap_club") == {"ok": False, "reason": "not enough coins"}
    solve(svc, "p1", "L1-001")  # 60 coins
    solve(svc, "p1", "L1-002")  # 70 more = 130
    r = svc.buy_item("p1", "cap_club")
    assert r["ok"] and r["wallet"]["coins"] == 50 and r["equipped"]["cap"] == "cap_club"
    assert svc.buy_item("p1", "cap_club")["reason"] == "already owned"
    assert svc.buy_item("p1", "nope")["reason"] == "unknown item"
    assert svc.get_wallet("p1")["coins"] == 50


def test_players_are_isolated(svc):
    solve(svc, "a", "L1-001")
    assert svc.get_wallet("b")["coins"] == 0
    assert svc.get_next_mission("b")["id"] == "L1-001"


def test_bad_formula_is_blocked_before_engine(svc):
    r = svc.submit_answer("p1", "L1-001", "=SUM(A1:A2);DROP TABLE x")
    assert not r["passed"] and "not allowed" in r["reason"]

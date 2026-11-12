"""Integration tests for the 10 new frontend endpoints."""
from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault("CC_DB_PATH", ":memory:")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from backend import api as _api_module      # noqa: E402
from backend.api import app                 # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_limiters():
    _api_module._player_limiter._calls.clear()
    _api_module._ip_limiter._calls.clear()
    _api_module._new_player_ip_limiter._calls.clear()
    _api_module._seen_players.clear()
    yield
    _api_module._player_limiter._calls.clear()
    _api_module._ip_limiter._calls.clear()
    _api_module._new_player_ip_limiter._calls.clear()
    _api_module._seen_players.clear()


def _pid() -> str:
    return str(uuid.uuid4())


def _auth(pid: str) -> dict:
    return {"Authorization": f"Bearer {pid}"}


# ---------------------------------------------------------------------------
# GET /api/world
# ---------------------------------------------------------------------------

def test_world_returns_config_player_markers(client):
    pid = _pid()
    r = client.get("/api/world", headers=_auth(pid))
    assert r.status_code == 200
    data = r.json()
    assert "config" in data
    assert "player" in data
    assert "markers" in data
    assert "now" in data
    cfg = data["config"]
    assert "levelXp" in cfg
    assert "skillXp" in cfg
    assert "families" in cfg
    assert "items" in cfg


def test_world_no_auth_returns_401(client):
    r = client.get("/api/world")
    assert r.status_code == 401


def test_world_invalid_pid_returns_400(client):
    r = client.get("/api/world", headers={"Authorization": "Bearer not-a-uuid"})
    assert r.status_code == 400


def test_world_markers_cover_all_npcs(client):
    pid = _pid()
    r = client.get("/api/world", headers=_auth(pid))
    assert r.status_code == 200
    markers = r.json()["markers"]
    assert "mukesh" in markers
    assert "akshita" in markers
    assert "maya" in markers
    assert markers["akshita"] == "store"
    assert markers["maya"] == "talk"


# ---------------------------------------------------------------------------
# POST /api/player
# ---------------------------------------------------------------------------

def test_create_player_saves_appearance(client):
    pid = _pid()
    r = client.post("/api/player", json={
        "name": "Ujwal", "gender": "Male", "body": "regular",
        "skin": "#C68A5E", "hairStyle": "short", "hairColor": "#1B1410",
    }, headers=_auth(pid))
    assert r.status_code == 200
    snap = r.json()
    assert "coins" in snap
    assert "level" in snap
    assert snap["created"] is True


# ---------------------------------------------------------------------------
# POST /api/npcs/{npc_id}/encounter
# ---------------------------------------------------------------------------

def test_encounter_coach_returns_question(client):
    pid = _pid()
    r = client.post("/api/npcs/mukesh/encounter", headers=_auth(pid))
    assert r.status_code == 200
    enc = r.json()
    assert enc["kind"] == "question"
    assert "question" in enc
    assert "encounterId" in enc


def test_encounter_store_returns_items(client):
    pid = _pid()
    r = client.post("/api/npcs/akshita/encounter", headers=_auth(pid))
    assert r.status_code == 200
    enc = r.json()
    assert enc["kind"] == "store"
    assert len(enc["items"]) == 16


def test_encounter_unknown_npc_returns_400(client):
    pid = _pid()
    r = client.post("/api/npcs/xyz_unknown/encounter", headers=_auth(pid))
    assert r.status_code == 400
    assert r.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/encounters/{enc_id}/answer
# ---------------------------------------------------------------------------

def test_answer_correct_returns_rewards(client):
    pid = _pid()
    enc_r = client.post("/api/npcs/mukesh/encounter", headers=_auth(pid))
    enc_id = enc_r.json()["encounterId"]

    svc = app.state.svc
    stored = svc.state.get_encounter(enc_id)

    r = client.post(f"/api/encounters/{enc_id}/answer",
                    json={"answer": stored["model"]}, headers=_auth(pid))
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is True
    assert data["rewards"]["coins"] > 0


def test_answer_wrong_no_coins(client):
    pid = _pid()
    enc_r = client.post("/api/npcs/mukesh/encounter", headers=_auth(pid))
    enc_id = enc_r.json()["encounterId"]

    r = client.post(f"/api/encounters/{enc_id}/answer",
                    json={"answer": "=SUM(Z99:Z100)"}, headers=_auth(pid))
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is False
    assert "feedback" in data
    assert app.state.svc.state.wallet(pid)["coins"] == 0


def test_answer_expired_enc_returns_400(client):
    pid = _pid()
    r = client.post("/api/encounters/enc_doesnotexist/answer",
                    json={"answer": "=SUM(A1)"}, headers=_auth(pid))
    assert r.status_code == 400
    assert r.json()["code"] == "EXPIRED"


# ---------------------------------------------------------------------------
# POST /api/store/buy  (new Bearer path)
# ---------------------------------------------------------------------------

def test_new_buy_free_item_ok(client):
    pid = _pid()
    # c_white is free (price 0); player starts with 0 coins
    r = client.post("/api/store/buy", json={"itemId": "c_white"}, headers=_auth(pid))
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_new_buy_already_owned_returns_400(client):
    pid = _pid()
    client.post("/api/store/buy", json={"itemId": "c_white"}, headers=_auth(pid))
    r = client.post("/api/store/buy", json={"itemId": "c_white"}, headers=_auth(pid))
    assert r.status_code == 400
    assert r.json()["code"] == "OWNED"


def test_new_buy_insufficient_funds_returns_400(client):
    pid = _pid()
    r = client.post("/api/store/buy", json={"itemId": "c_sun"}, headers=_auth(pid))
    # c_sun costs 70 coins, player starts at 0
    assert r.status_code == 400
    assert r.json()["code"] == "FUNDS"


def test_new_buy_unknown_item_returns_400(client):
    pid = _pid()
    r = client.post("/api/store/buy", json={"itemId": "nope_item"}, headers=_auth(pid))
    assert r.status_code == 400
    assert r.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/avatar/equip
# ---------------------------------------------------------------------------

def test_equip_owned_item_ok(client):
    pid = _pid()
    # Buy free item first
    client.post("/api/store/buy", json={"itemId": "c_white"}, headers=_auth(pid))
    r = client.post("/api/avatar/equip", json={"itemId": "c_white"}, headers=_auth(pid))
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["player"]["eq"]["cap"] == "c_white"


def test_equip_unowned_item_returns_400(client):
    pid = _pid()
    r = client.post("/api/avatar/equip", json={"itemId": "c_sun"}, headers=_auth(pid))
    assert r.status_code == 400
    assert r.json()["code"] == "NOT_OWNED"


# ---------------------------------------------------------------------------
# GET /api/clubs
# ---------------------------------------------------------------------------

def test_clubs_returns_all_seven(client):
    pid = _pid()
    r = client.get("/api/clubs", headers=_auth(pid))
    assert r.status_code == 200
    clubs = r.json()
    assert len(clubs) == 7
    tiers = [c["tier"] for c in clubs]
    assert tiers == list(range(1, 8))


def test_clubs_has_requirements(client):
    pid = _pid()
    r = client.get("/api/clubs", headers=_auth(pid))
    for club in r.json():
        assert "requirements" in club
        assert isinstance(club["requirements"], list)


# ---------------------------------------------------------------------------
# GET /api/leaderboard
# ---------------------------------------------------------------------------

def test_leaderboard_returns_list(client):
    pid = _pid()
    r = client.get("/api/leaderboard")
    assert r.status_code == 200
    data = r.json()
    assert "leaderboard" in data
    assert isinstance(data["leaderboard"], list)


def test_leaderboard_limit_param(client):
    r = client.get("/api/leaderboard?limit=5")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Auth edge cases
# ---------------------------------------------------------------------------

def test_all_bearer_endpoints_require_auth(client):
    endpoints = [
        ("GET",  "/api/world"),
        ("POST", "/api/player"),
        ("POST", "/api/npcs/mukesh/encounter"),
        ("POST", "/api/encounters/enc_x/answer"),
        ("POST", "/api/encounters/enc_x/begin"),
        ("POST", "/api/encounters/enc_x/lesson"),
        ("POST", "/api/facilities/gym/visit"),
        ("POST", "/api/avatar/equip"),
        ("GET",  "/api/clubs"),
    ]
    for method, path in endpoints:
        if method == "GET":
            r = client.get(path)
        else:
            r = client.post(path, json={})
        assert r.status_code in (401, 422), (
            f"{method} {path} should require auth, got {r.status_code}"
        )

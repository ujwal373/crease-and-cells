"""Game service plus the Mission, Scoring and Store agents.

Agents never call each other. They subscribe to events on the bus:

  answer_submitted -> (validator runs) -> mission_passed
  mission_passed   -> ScoringAgent awards coins and xp -> coins_awarded
  coins_awarded    -> MissionAgent picks the next mission -> mission_assigned
  item_purchased   -> published by StoreAgent
"""
from __future__ import annotations

import json
from pathlib import Path

from . import events, guardrails
from .cricket_data import GENERATORS, to_grid
from .events import EventBus
from .formula_engine import Grid
from .keys import compute_answer
from .state import GameState
from .tracing import span, trace
from .validator import validate

ROOT = Path(__file__).resolve().parent.parent
NO_HINT_BONUS = 10

_PRIVATE_FIELDS = {"answer_spec", "reference_solution", "hints", "required_all", "required_any"}


def load_missions() -> list[dict]:
    missions: list[dict] = []
    for path in sorted((ROOT / "missions").glob("level*.json")):
        missions.extend(json.loads(path.read_text())["missions"])
    return sorted(missions, key=lambda m: (m["level"], m["id"]))


def load_catalog() -> dict:
    return json.loads((ROOT / "missions" / "store_catalog.json").read_text())


def _rows_for(mission: dict) -> tuple[list[dict], list[str]]:
    ds = mission["dataset"]
    gen, cols = GENERATORS[ds["generator"]]
    return gen(ds["seed"], ds["rows"]), cols


def _fmt_secret(value) -> list[str]:
    if isinstance(value, float) and value.is_integer():
        return [str(int(value))]
    return [str(value)]


class MissionAgent:
    """Assigns the next mission. Subscribes to coins_awarded."""

    def __init__(self, state: GameState, missions: list[dict], bus: EventBus):
        self.state, self.missions, self.bus = state, missions, bus
        bus.subscribe(events.COINS_AWARDED, self.on_coins_awarded)

    def next_mission(self, player_id: str) -> dict | None:
        done = self.state.completed_ids(player_id)
        return next((m for m in self.missions if m["id"] not in done), None)

    def on_coins_awarded(self, payload: dict) -> None:
        nxt = self.next_mission(payload["player_id"])
        payload["next_mission"] = {"id": nxt["id"], "title": nxt["title"]} if nxt else None
        if nxt:
            self.bus.publish(events.MISSION_ASSIGNED, {"player_id": payload["player_id"], "mission_id": nxt["id"]})


class ScoringAgent:
    """Checks the wallet side of a pass: coins, xp, level. Subscribes to mission_passed."""

    def __init__(self, state: GameState, missions: list[dict], bus: EventBus):
        self.state, self.bus = state, bus
        self.by_id = {m["id"]: m for m in missions}
        bus.subscribe(events.MISSION_PASSED, self.on_mission_passed)

    def on_mission_passed(self, payload: dict) -> None:
        pid, mid = payload["player_id"], payload["mission_id"]
        mission = self.by_id[mid]
        hints = self.state.hints_used(pid, mid)
        bonus = NO_HINT_BONUS if hints == 0 else 0
        coins = mission["reward"]["coins"] + bonus
        xp = mission["reward"]["xp"]
        if not self.state.complete(pid, mid, hints, coins, xp):
            payload["reward"] = {"already_completed": True, "coins_awarded": 0, "xp_awarded": 0}
            return
        payload["reward"] = {
            "already_completed": False,
            "coins_awarded": coins,
            "no_hint_bonus": bonus,
            "xp_awarded": xp,
            "wallet": self.state.wallet(pid),
        }
        self.bus.publish(events.COINS_AWARDED, payload)


class StoreAgent:
    """Shop and wardrobe. Cosmetic items only, so nothing blocks learning progress."""

    def __init__(self, state: GameState, catalog: dict, bus: EventBus):
        self.state, self.bus = state, bus
        self.items = {i["id"]: i for i in catalog["items"]}
        self.default_kit = catalog["default_kit"]

    def list_items(self, player_id: str) -> list[dict]:
        owned = set(self.state.inventory(player_id))
        return [{**i, "owned": i["id"] in owned} for i in self.items.values()]

    def buy(self, player_id: str, item_id: str) -> dict:
        item = self.items.get(item_id)
        if not item:
            return {"ok": False, "reason": "unknown item"}
        if self.state.owns(player_id, item_id):
            return {"ok": False, "reason": "already owned"}
        if not self.state.spend(player_id, item["price"]):
            return {"ok": False, "reason": "not enough coins"}
        self.state.add_item(player_id, item_id)
        self.state.equip(player_id, item["slot"], item_id)
        self.bus.publish(events.ITEM_PURCHASED, {"player_id": player_id, "item_id": item_id})
        return {"ok": True, "item": item["name"], "wallet": self.state.wallet(player_id), "equipped": self.outfit(player_id)}

    def outfit(self, player_id: str) -> dict:
        return {**self.default_kit, **self.state.equipped(player_id)}


class GameService:
    def __init__(self, db_path: str = ":memory:"):
        self.bus = EventBus()
        self.state = GameState(db_path)
        self.missions = load_missions()
        self.by_id = {m["id"]: m for m in self.missions}
        self.mission_agent = MissionAgent(self.state, self.missions, self.bus)
        self.scoring_agent = ScoringAgent(self.state, self.missions, self.bus)
        self.store_agent = StoreAgent(self.state, load_catalog(), self.bus)

    # ----- missions -----
    def _mission(self, mission_id: str) -> dict:
        if mission_id not in self.by_id:
            raise KeyError(f"unknown mission {mission_id}")
        return self.by_id[mission_id]

    def get_next_mission(self, player_id: str, name: str | None = None) -> dict:
        self.state.ensure_player(player_id, name)
        mission = self.mission_agent.next_mission(player_id)
        if not mission:
            return {"done": True, "message": "All current missions complete. New zones coming soon."}
        rows, cols = _rows_for(mission)
        public = {k: v for k, v in mission.items() if k not in _PRIVATE_FIELDS}
        public["hints_available"] = len(mission["hints"])
        public["sheet_name"] = "Spells"
        public["sheet"] = to_grid(cols, rows)
        return public

    def submit_answer(self, player_id: str, mission_id: str, formula: str) -> dict:
        self.state.ensure_player(player_id)
        mission = self._mission(mission_id)
        with span("submit_answer", player_id=player_id, mission_id=mission_id):
            guard = guardrails.check_formula_input(formula)
            if not guard.allowed:
                trace("guardrail.blocked", kind="formula", reason=guard.reason, player_id=player_id)
                return {"passed": False, "reason": guard.reason}
            self.bus.publish(events.ANSWER_SUBMITTED, {"player_id": player_id, "mission_id": mission_id})
            rows, cols = _rows_for(mission)
            expected = compute_answer(mission["answer_spec"], rows)
            result = validate(
                formula, Grid(to_grid(cols, rows)), expected,
                mission["required_all"], mission["required_any"],
            )
            if not result.passed:
                self.bus.publish(events.ANSWER_REJECTED, {"player_id": player_id, "mission_id": mission_id})
                return {"passed": False, "reason": result.reason, "your_value": result.player_value}
            payload = {"player_id": player_id, "mission_id": mission_id}
            self.bus.publish(events.MISSION_PASSED, payload)
            return {
                "passed": True,
                "reason": "correct",
                "your_value": result.player_value,
                **payload.get("reward", {}),
                "next_mission": payload.get("next_mission"),
            }

    # ----- coach -----
    def get_hint(self, player_id: str, mission_id: str) -> dict:
        self.state.ensure_player(player_id)
        mission = self._mission(mission_id)
        hints = mission["hints"]
        used = self.state.hints_used(player_id, mission_id)
        text = hints[min(used, len(hints) - 1)]
        rows, _ = _rows_for(mission)
        secrets = _fmt_secret(compute_answer(mission["answer_spec"], rows)) + [mission["reference_solution"]]
        out = guardrails.check_output(text, secrets)
        if not out.allowed:
            trace("guardrail.blocked", kind="hint_output", reason=out.reason, mission_id=mission_id)
            text = "Re-read the task and check which columns hold the condition and the values."
        self.state.bump_hints(player_id, mission_id)
        self.bus.publish(events.HINT_USED, {"player_id": player_id, "mission_id": mission_id})
        return {"hint": text, "hint_number": min(used + 1, len(hints)), "of": len(hints), "no_hint_bonus_lost": True}

    def ask_coach(self, player_id: str, mission_id: str, message: str) -> dict:
        guard = guardrails.check_chat_input(message)
        if not guard.allowed:
            trace("guardrail.blocked", kind="chat_input", reason=guard.reason, player_id=player_id)
            return {"blocked": True, "reply": "Coach: I can nudge you, but I can't hand over the answer. Try a hint."}
        return self.get_hint(player_id, mission_id)

    # ----- wallet and store -----
    def get_wallet(self, player_id: str) -> dict:
        self.state.ensure_player(player_id)
        return {**self.state.wallet(player_id), "outfit": self.store_agent.outfit(player_id)}

    def list_store(self, player_id: str) -> list[dict]:
        self.state.ensure_player(player_id)
        return self.store_agent.list_items(player_id)

    def buy_item(self, player_id: str, item_id: str) -> dict:
        self.state.ensure_player(player_id)
        return self.store_agent.buy(player_id, item_id)

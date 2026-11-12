"""Game service plus the Mission, Scoring and Store agents.

Agents never call each other. They subscribe to events on the bus:

  answer_submitted -> (validator runs) -> mission_passed
  mission_passed   -> ScoringAgent awards coins and xp -> coins_awarded
  coins_awarded    -> MissionAgent picks the next mission -> mission_assigned
  item_purchased   -> published by StoreAgent
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import events, guardrails
from .cricket_data import GENERATORS, to_grid
from .events import EventBus
from .formula_engine import FormulaError, Grid, evaluate
from .keys import compute_answer
from .state import GameState
from .tracing import span, trace
from .tutor import HintProvider, TutorAgent
from .validator import validate

ROOT = Path(__file__).resolve().parent.parent
NO_HINT_BONUS = 10

_PRIVATE_FIELDS = {"answer_spec", "reference_solution", "hints", "required_all", "required_any"}

BODY_TYPES = ["slim", "regular", "broad"]
HAIR_STYLES = ["short", "curly", "long", "bun", "none"]
# Skin and hair colour are stored as hex strings from the character creator.
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_NAME_LEN = 30


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
        reason = self.state.buy_item_atomic(player_id, item_id, item["price"], item["slot"])
        if reason:
            return {"ok": False, "reason": reason}
        self.bus.publish(events.ITEM_PURCHASED, {"player_id": player_id, "item_id": item_id})
        return {"ok": True, "item": item["name"], "wallet": self.state.wallet(player_id), "equipped": self.outfit(player_id)}

    def outfit(self, player_id: str) -> dict:
        return {**self.default_kit, **self.state.equipped(player_id)}


class GameService:
    def __init__(self, db_path: str = ":memory:", tutor_client=None):
        self.bus = EventBus()
        self.state = GameState(db_path)
        self.missions = load_missions()
        self.by_id = {m["id"]: m for m in self.missions}
        self.mission_agent = MissionAgent(self.state, self.missions, self.bus)
        self.scoring_agent = ScoringAgent(self.state, self.missions, self.bus)
        self.store_agent = StoreAgent(self.state, load_catalog(), self.bus)
        self._tutor: HintProvider | None = TutorAgent(self.state, tutor_client) if tutor_client is not None else None

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
                self.state.set_last_attempt(player_id, mission_id, formula, result.reason)
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
    def _hint_response(
        self,
        player_id: str,
        mission_id: str,
        *,
        formula: str = "",
        failure_code: str = "",
        message: str | None = None,
        requester_ip: str = "",
    ) -> dict:
        mission = self._mission(mission_id)
        hints = mission["hints"]
        used = self.state.hints_used(player_id, mission_id)
        hint_level = min(used + 1, len(hints))
        static_text = hints[min(used, len(hints) - 1)]
        rows, cols = _rows_for(mission)
        secrets = _fmt_secret(compute_answer(mission["answer_spec"], rows)) + [mission["reference_solution"]]
        if self._tutor is not None:
            result = self._tutor.get_hint(
                player_id=player_id,
                mission=mission,
                hint_level=hint_level,
                formula=formula,
                failure_code=failure_code,
                column_headers=cols,
                message=message,
                secrets=secrets,
                static_fallback=static_text,
                requester_ip=requester_ip,
            )
            text = result.text
        else:
            out = guardrails.check_output(static_text, secrets)
            if not out.allowed:
                trace("guardrail.blocked", kind="hint_output", reason=out.reason, mission_id=mission_id)
                text = "Re-read the task and check which columns hold the condition and the values."
            else:
                text = static_text
        self.state.bump_hints(player_id, mission_id)
        self.bus.publish(events.HINT_USED, {"player_id": player_id, "mission_id": mission_id})
        return {"hint": text, "hint_number": hint_level, "of": len(hints), "no_hint_bonus_lost": True}

    def get_hint(self, player_id: str, mission_id: str, *, requester_ip: str = "") -> dict:
        self.state.ensure_player(player_id)
        last = self.state.get_last_attempt(player_id, mission_id)
        formula, failure_code = last if last else ("", "")
        return self._hint_response(player_id, mission_id, formula=formula, failure_code=failure_code, requester_ip=requester_ip)

    def ask_coach(self, player_id: str, mission_id: str, message: str, *, requester_ip: str = "") -> dict:
        guard = guardrails.check_chat_input(message)
        if not guard.allowed:
            trace("guardrail.blocked", kind="chat_input", reason=guard.reason, player_id=player_id)
            return {"blocked": True, "reply": "Coach: I can nudge you, but I can't hand over the answer. Try a hint."}
        self.state.ensure_player(player_id)
        last = self.state.get_last_attempt(player_id, mission_id)
        formula, failure_code = last if last else ("", "")
        return self._hint_response(player_id, mission_id, formula=formula, failure_code=failure_code, message=message, requester_ip=requester_ip)

    # ----- preview (formula value only, never pass/fail) -----
    def preview_formula(self, player_id: str, mission_id: str, formula: str) -> dict:
        """Evaluate formula on the mission grid. Returns value or error; never reveals correctness."""
        self.state.ensure_player(player_id)
        mission = self._mission(mission_id)
        guard = guardrails.check_formula_input(formula)
        if not guard.allowed:
            return {"error": "invalid_formula"}
        rows, cols = _rows_for(mission)
        try:
            result = evaluate(formula, Grid(to_grid(cols, rows)))
            value = result.value
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            return {"value": value}
        except FormulaError as exc:
            return {"error": exc.code}
        except Exception:
            return {"error": "eval_error"}

    # ----- wallet and store -----
    def get_wallet(self, player_id: str) -> dict:
        self.state.ensure_player(player_id)
        return {
            **self.state.wallet(player_id),
            "outfit": self.store_agent.outfit(player_id),
            "appearance": self.state.get_appearance(player_id),
        }

    def list_store(self, player_id: str) -> list[dict]:
        self.state.ensure_player(player_id)
        return self.store_agent.list_items(player_id)

    def buy_item(self, player_id: str, item_id: str) -> dict:
        self.state.ensure_player(player_id)
        return self.store_agent.buy(player_id, item_id)

    # ----- player snapshot (new frontend shape) -----
    def player_snap(self, player_id: str) -> dict:
        """Return the full player snapshot the new frontend expects."""
        from .game_config import FAMILY_IDS, DEFAULT_EQ, skill_level_for_xp, level_for_xp

        self.state.ensure_player(player_id)
        wallet   = self.state.wallet(player_id)
        sxp_map  = self.state.skill_xp(player_id)
        inv      = self.state.inventory(player_id)
        eq_map   = self.state.equipped(player_id)
        app      = self.state.get_appearance(player_id)
        tier     = self.state.player_tier(player_id)

        with self.state._lock:
            created_row = self.state.db.execute(
                "SELECT created FROM players WHERE id=?", (player_id,)
            ).fetchone()
            created = bool(created_row["created"]) if created_row else False

        skills   = {f: skill_level_for_xp(sxp_map.get(f, 0)) for f in FAMILY_IDS}
        skill_xp = {f: sxp_map.get(f, 0) for f in FAMILY_IDS}
        owned    = {item_id: 1 for item_id in inv} if inv else {}
        eq       = {**DEFAULT_EQ, **eq_map}

        look = None
        if app.get("display_name") or app.get("body_type") != "medium":
            look = {
                "name":      app.get("display_name", ""),
                "gender":    app.get("gender", ""),
                "body":      app.get("body_type", "medium"),
                "skin":      app.get("skin_tone", "medium"),
                "hairStyle": app.get("hair_style", "short"),
                "hairColor": app.get("hair_colour", "black"),
            }

        return {
            "coins":    wallet.get("coins", 0),
            "xp":       wallet.get("xp", 0),
            "level":    level_for_xp(wallet.get("xp", 0)),
            "tier":     tier,
            "skills":   skills,
            "skillXp":  skill_xp,
            "owned":    owned,
            "eq":       eq,
            "look":     look,
            "created":  created,
        }

    # ----- appearance -----
    def get_appearance(self, player_id: str) -> dict:
        self.state.ensure_player(player_id)
        return self.state.get_appearance(player_id)

    def save_appearance(
        self,
        player_id: str,
        display_name: str,
        body_type: str,
        skin_tone: str,
        hair_style: str,
        hair_colour: str,
    ) -> dict:
        display_name = display_name.strip()
        if len(display_name) > MAX_NAME_LEN:
            raise ValueError(f"display_name exceeds {MAX_NAME_LEN} characters")
        if display_name:
            guard = guardrails.check_chat_input(display_name)
            if not guard.allowed:
                raise ValueError(f"display_name rejected: {guard.reason}")
        if body_type not in BODY_TYPES:
            raise ValueError(f"body_type must be one of {BODY_TYPES}")
        if not _HEX_RE.match(skin_tone):
            raise ValueError("skin_tone must be a hex colour like #C68A5E")
        if hair_style not in HAIR_STYLES:
            raise ValueError(f"hair_style must be one of {HAIR_STYLES}")
        if not _HEX_RE.match(hair_colour):
            raise ValueError("hair_colour must be a hex colour like #1B1410")
        self.state.ensure_player(player_id)
        self.state.set_appearance(player_id, display_name, body_type, skin_tone, hair_style, hair_colour)
        return self.state.get_appearance(player_id)

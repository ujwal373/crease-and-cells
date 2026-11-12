"""EncounterService: drives all 10 endpoints for the new frontend.

Handles question generation, answer validation, session management,
leaderboards, facilities, and NPC marker computation.  Never calls an LLM.
The existing formula_engine is the only correctness authority.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .formula_engine import FormulaError, Grid, evaluate
from .game_config import (
    CHECKPOINTS,
    CLUBS,
    FACILITY_TIER,
    FAMILIES,
    FAMILY_IDS,
    ITEMS,
    ITEMS_BY_ID,
    LESSON_TOPICS,
    LESSONS,
    SESSIONS,
    TIPS,
    skill_level_for_xp,
)
from .npc_config import NPC_CONFIG
from .question_gen import build_question, reward_for
from .service import GameService
from .state import GameState


def _enc_id() -> str:
    return "enc_" + uuid.uuid4().hex[:8]


def _sess_id() -> str:
    return "sess_" + uuid.uuid4().hex[:8]


class EncounterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code    = code
        self.message = message


# ---------------------------------------------------------------------------
# Club eligibility helpers (mirror MockAdapter logic)
# ---------------------------------------------------------------------------

def _gear_ok(g: dict, owned: set[str], eq: dict) -> bool:
    if "worn" in g:
        return eq.get(ITEMS_BY_ID[g["worn"]]["slot"]) == g["worn"]
    slot = g["any"]
    return any(
        ITEMS_BY_ID[iid]["slot"] == slot and ITEMS_BY_ID[iid]["price"] > 0
        for iid in owned
        if iid in ITEMS_BY_ID
    )


def _club_requirements(club: dict, snap: dict) -> list[dict]:
    reqs: list[dict] = [
        {"kind": "level", "text": f"Reach Level {club['level']}",
         "ok": snap["level"] >= club["level"]}
    ]
    for fam, need in club["skills"].items():
        fam_name = next((f["name"] for f in FAMILIES if f["id"] == fam), fam)
        reqs.append({"kind": "skill", "text": f"{fam_name} skill {need}",
                     "ok": snap["skills"].get(fam, 0) >= need})
    owned = set(snap["owned"].keys())
    eq    = snap["eq"]
    for g in club["gear"]:
        ok   = _gear_ok(g, owned, eq)
        text = (f"Wear the {ITEMS_BY_ID[g['worn']]['name']}"
                if "worn" in g else f"Own an upgraded {g['any']}")
        reqs.append({"kind": "gear", "text": text, "ok": ok})
    n = CHECKPOINTS.get(club["tier"])
    if n:
        cp_done = snap.get("_cp", {}).get(club["tier"], 0)
        reqs.append({"kind": "checkpoint",
                     "text": f"Clear {n} checkpoints ({cp_done} of {n})",
                     "ok": cp_done >= n})
    return reqs


def _club_state(club: dict, snap: dict) -> dict:
    reqs = _club_requirements(club, snap)
    met  = all(r["ok"] for r in reqs)
    tier = snap["tier"]
    if tier >= club["tier"]:
        reason = "enrolled"
    elif tier < club["tier"] - 1:
        reason = "previous"
    elif met:
        reason = "ready"
    else:
        reason = "requirements"
    return {
        "id":           club["id"],
        "tier":         club["tier"],
        "name":         club["name"],
        "venue":        club["venue"],
        "mode":         club["mode"],
        "requirements": reqs,
        "eligible":     met and tier == club["tier"] - 1,
        "enrolled":     tier >= club["tier"],
        "reason":       reason,
    }


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class EncounterService:
    def __init__(self, game_service: GameService) -> None:
        self._svc   = game_service
        self._state = game_service.state

    # ------------------------------------------------------------------
    # Player snapshot (enriched with checkpoint map for internal use)
    # ------------------------------------------------------------------

    def _snap(self, player_id: str) -> dict:
        snap = self._svc.player_snap(player_id)
        # attach per-tier checkpoint counts for internal use
        cp: dict[int, int] = {}
        for tier in range(1, 8):
            v = self._state.get_checkpoints(player_id, tier)
            if v:
                cp[tier] = v
        snap["_cp"] = cp
        return snap

    # ------------------------------------------------------------------
    # NPC markers
    # ------------------------------------------------------------------

    def compute_markers(self, player_id: str, npc_ids: list[str]) -> dict[str, str]:
        snap = self._snap(player_id)
        now  = int(time.time() * 1000)
        out: dict[str, str] = {}
        for nid in npc_ids:
            cfg = NPC_CONFIG.get(nid)
            if not cfg:
                out[nid] = "locked"
                continue
            role = cfg["role"]
            tier = cfg.get("tier", 0)

            if role == "store":
                out[nid] = "store"
            elif role == "staff":
                out[nid] = "talk"
            elif role == "lesson":
                out[nid] = "learn" if snap["tier"] >= tier else "locked"
            elif role == "practice":
                out[nid] = "new" if snap["tier"] >= 1 else "new"
            elif role == "checkpoint":
                step = cfg.get("step", 1)
                done = snap["_cp"].get(tier, 0)
                if snap["tier"] >= tier:
                    out[nid] = "done"
                elif snap["tier"] < tier - 1:
                    out[nid] = "locked"
                elif done >= step:
                    out[nid] = "done"
                elif done == step - 1 and snap["tier"] == tier - 1:
                    out[nid] = "new"
                else:
                    out[nid] = "locked"
            elif role in ("recruit", "match"):
                sid   = cfg["session"]
                s     = SESSIONS[sid]
                enrol = s.get("enrol", 0)
                stier = s.get("tier", 0)
                club  = CLUBS[(enrol or stier or 1) - 1]
                cs    = _club_state(club, snap)
                cool  = self._state.get_cooldown(player_id, sid)
                if enrol and snap["tier"] >= enrol and role == "recruit":
                    out[nid] = "done"
                elif stier and not enrol:
                    out[nid] = "match" if snap["tier"] >= stier and not cool else "locked"
                elif cs["eligible"] and not cool:
                    out[nid] = "match"
                else:
                    out[nid] = "locked"
            else:  # friend / practice
                out[nid] = "new"
        return out

    # ------------------------------------------------------------------
    # Create encounter
    # ------------------------------------------------------------------

    def create_encounter(self, player_id: str, npc_id: str) -> dict:
        cfg = NPC_CONFIG.get(npc_id)
        if not cfg:
            raise EncounterError("NOT_FOUND", f"No NPC with id {npc_id!r}.")

        snap = self._snap(player_id)
        role = cfg["role"]
        name = cfg.get("name", npc_id)
        enc_id = _enc_id()

        # Store NPC
        if role == "store":
            return {
                "encounterId": enc_id,
                "kind": "store",
                "npc": name,
                "say": "Welcome. Everything here is paid for with coins. You can wear it straight away.",
                "items": ITEMS,
                "player": snap,
            }

        # Staff — rotating tip
        if role == "staff":
            tip = TIPS[hash(player_id + npc_id) % len(TIPS)]
            return {
                "encounterId": enc_id,
                "kind": "chat",
                "npc": name,
                "say": tip,
                "player": snap,
            }

        # Lesson mentor
        if role == "lesson":
            tier = cfg.get("tier", 1)
            if snap["tier"] < tier:
                return {
                    "encounterId": enc_id,
                    "kind": "chat",
                    "npc": name,
                    "say": f"This is for members only. Join {CLUBS[tier - 1]['name']} first.",
                    "player": snap,
                }
            lesson_key = cfg.get("lesson", "batting")
            topic_ids  = LESSON_TOPICS.get(lesson_key, [])
            topics     = [
                {"id": f, "name": next(x["name"] for x in FAMILIES if x["id"] == f),
                 "blurb": next(x["blurb"] for x in FAMILIES if x["id"] == f)}
                for f in topic_ids
            ]
            # Store a minimal encounter so lesson_topic can resolve it
            self._state.save_encounter(
                enc_id, player_id, npc_id, topic_ids[0] if topic_ids else "maths",
                1, None, [], "", [], 0, 0,
            )
            return {
                "encounterId": enc_id,
                "kind": "lesson",
                "npc": name,
                "say": "What would you like to learn today? Pick one.",
                "topics": topics,
                "player": snap,
            }

        # Checkpoint
        if role == "checkpoint":
            tier = cfg.get("tier", 1)
            step = cfg.get("step", 1)
            done = snap["_cp"].get(tier, 0)
            if snap["tier"] >= tier:
                return {"encounterId": enc_id, "kind": "chat", "npc": name,
                        "say": "You have already cleared this. Go well.", "player": snap}
            if snap["tier"] < tier - 1:
                return {"encounterId": enc_id, "kind": "chat", "npc": name,
                        "say": "Not yet. Finish the earlier club first.", "player": snap}
            if done >= step:
                return {"encounterId": enc_id, "kind": "chat", "npc": name,
                        "say": "Checkpoint cleared. Move on to the next one.", "player": snap}
            if done < step - 1:
                return {"encounterId": enc_id, "kind": "chat", "npc": name,
                        "say": f"Checkpoints go in order. Clear checkpoint {done + 1} first.", "player": snap}
            family = FAMILY_IDS[(hash(npc_id) + tier) % len(FAMILY_IDS)]
            seed   = int(time.time()) ^ (hash(enc_id) & 0xFFFFFFFF)
            return self._question_encounter(
                enc_id, player_id, npc_id, name, family, 3, seed, snap,
                cp_tier=tier, cp_step=step,
                checkpoint={"tier": tier, "step": step, "of": CHECKPOINTS.get(tier, 0)},
            )

        # Recruit / match — lobby
        if role in ("recruit", "match"):
            return self._lobby_encounter(enc_id, player_id, npc_id, cfg, snap)

        # Friend / practice — generate question
        family = cfg.get("family", "maths")
        skill  = snap["skills"].get(family, 0)
        diff   = max(1, min(3, skill + 1))
        seed   = int(time.time()) ^ (hash(player_id + enc_id) & 0xFFFFFFFF)
        is_prac = role == "practice"
        return self._question_encounter(
            enc_id, player_id, npc_id, name, family, diff, seed, snap,
            is_practice=is_prac,
        )

    def _question_encounter(
        self,
        enc_id: str,
        player_id: str,
        npc_id: str,
        npc_name: str,
        family: str,
        difficulty: int,
        seed: int,
        snap: dict,
        *,
        session_id: str | None = None,
        cp_tier: int | None = None,
        cp_step: int | None = None,
        is_practice: bool = False,
        checkpoint: dict | None = None,
        session_meta: dict | None = None,
        say_prefix: str = "",
    ) -> dict:
        q = build_question(family, difficulty, seed)
        coins, xp = reward_for(difficulty, seed)

        # Double coins for practice daily bonus
        if is_practice:
            # stored separately; check for today's bonus below
            coins *= 2

        self._state.save_encounter(
            enc_id, player_id, npc_id, family, difficulty,
            q["expected"], q["rows"], q["model"], q["must_use"],
            coins, xp,
            session_id=session_id, cp_tier=cp_tier, cp_step=cp_step,
            is_practice=is_practice,
        )

        num_cols = max(len(r) for r in q["rows"]) if q["rows"] else 1
        sheet_cols = list("ABCDEF"[:num_cols])

        result: dict[str, Any] = {
            "encounterId": enc_id,
            "kind": "question",
            "npc": npc_name,
            "family": family,
            "difficulty": difficulty,
            "say": say_prefix + q["story"],
            "question": {
                "type": "formula",
                "prompt": q["story"],
                "task": q["task"],
                "sheet": {
                    "cols": sheet_cols,
                    "rows": q["rows"],
                    "target": {"r": q["tr"], "c": q["tc"]},
                },
                "mustUse": q["must_use"],
                "hint": q["hint"],
                "timeLimit": 0,
            },
            "reward": {"coins": coins, "xp": xp},
            "player": snap,
        }
        if checkpoint:
            result["checkpoint"] = checkpoint
        if session_meta:
            result["session"] = session_meta
        return result

    def _lobby_encounter(
        self, enc_id: str, player_id: str, npc_id: str, cfg: dict, snap: dict
    ) -> dict:
        name = cfg.get("name", npc_id)
        sid  = cfg["session"]
        s    = SESSIONS[sid]
        enrol = s.get("enrol", 0)
        stier = s.get("tier", 0)
        ct    = enrol or stier or 1
        club  = CLUBS[ct - 1]
        cs    = _club_state(club, snap)

        cool     = self._state.get_cooldown(player_id, sid)
        now_ms   = int(time.time() * 1000)
        ready    = cool == 0 or now_ms > cool
        can_begin = False
        say = ""

        purpose = "play"
        if enrol:
            if snap["tier"] >= enrol:
                purpose = "joined"
            else:
                purpose = "enrol"
        elif stier:
            purpose = "play"

        if purpose == "joined":
            say = "You already wear our colours. Well played."
        elif purpose == "enrol":
            if not cs["eligible"]:
                say = (
                    f"Join {CLUBS[ct - 2]['name']} first. We take players who have come up the ladder."
                    if cs["reason"] == "previous"
                    else "Not yet. Come back when every item on this list is ticked."
                )
            elif not ready:
                say = "You have already tried today. The next attempt opens later."
            else:
                secs_text = f", {s['secs']} seconds each" if s.get("secs") else ""
                say = f"You meet every requirement. {s['rounds']} hard questions{secs_text}. Get {s['pass']} right and you are in."
                can_begin = True
        else:
            if snap["tier"] < stier and not cs["eligible"]:
                say = (
                    f"Join {CLUBS[ct - 2]['name']} first."
                    if cs["reason"] == "previous"
                    else "Not yet. Come back when every item on this list is ticked."
                )
            elif not ready:
                say = "The next match opens later. Rest up."
            else:
                secs_text = f", {s['secs']} seconds each." if s.get("secs") else "."
                if snap["tier"] >= stier:
                    say = f"Ready for a match? {s['rounds']} hard questions{secs_text}"
                else:
                    say = f"You meet every requirement. Win this match to join. {s['rounds']} hard questions{secs_text}"
                can_begin = True

        # Store lobby encounter so begin_session can resolve it
        self._state.save_encounter(
            enc_id, player_id, npc_id, "maths", 1, None, [], "", [],
            0, 0,
        )
        # Tag the encounter as a lobby by using a sentinel in model field
        with self._state._lock:
            self._state.db.execute(
                "UPDATE encounters SET model=? WHERE enc_id=?",
                (f"__lobby__{sid}", enc_id),
            )
            self._state.db.commit()

        return {
            "encounterId": enc_id,
            "kind": "lobby",
            "npc": name,
            "say": say,
            "session": {
                "id": sid,
                "name": s["name"],
                "rounds": s["rounds"],
                "passMark": s["pass"],
                "secondsPerRound": s.get("secs", 0),
                "cooldownHours": s.get("cooldownH", 0),
                "ready": ready,
                "nextAt": cool if not ready else 0,
                "purpose": purpose,
            },
            "club": cs,
            "canBegin": can_begin,
            "player": snap,
        }

    # ------------------------------------------------------------------
    # Answer an encounter
    # ------------------------------------------------------------------

    def answer_encounter(self, player_id: str, enc_id: str, answer: Any) -> dict:
        enc = self._state.get_encounter(enc_id)
        if not enc or enc["player_id"] != player_id:
            raise EncounterError("EXPIRED", "That question has expired. Ask again.")
        if enc["done"]:
            snap = self._snap(player_id)
            return {"correct": True, "feedback": "You already collected this one.",
                    "rewards": {"coins": 0, "xp": 0}, "player": snap}

        tries = self._state.increment_encounter_tries(enc_id)
        is_session = bool(enc.get("session_id"))
        sess: dict | None = None
        if is_session:
            sess = self._state.get_session(enc["session_id"])

        # Timeout: answer is None
        if answer is None:
            feedback = "Time is up for this over."
            if sess:
                result = self._state.advance_session(enc["session_id"], 0)
                self._state.mark_encounter_done(enc_id)
                return self._session_round_result(
                    player_id, enc, sess, result, correct=False,
                    feedback=feedback + " That over is lost.",
                )
            return {"correct": False, "feedback": feedback,
                    "attempt": tries, "player": self._snap(player_id)}

        # Evaluate the formula
        ok = False
        feedback = ""
        try:
            a = str(answer).strip()
            if not a.startswith("="):
                feedback = "Formulas start with an equals sign."
            else:
                grid  = Grid(enc["grid"])
                got   = evaluate(a, grid)
                used  = _used_functions(a)
                miss  = [fn for fn in enc["must_use"] if fn.upper() not in used]
                if miss:
                    feedback = f"This one needs {' and '.join(miss)}. Check the hint."
                elif _values_equal(got.value if hasattr(got, "value") else got, enc["expected"]):
                    ok = True
                else:
                    got_val = got.value if hasattr(got, "value") else got
                    feedback = f"Your formula gives {got_val}. That is not the answer. Check your range."
        except FormulaError as exc:
            code = exc.code if hasattr(exc, "code") else str(exc)
            feedback = (
                "Excel would show #NAME? here. Check spelling, quotes and brackets."
                if code == "#NAME?"
                else f"Excel would show {code} here."
                if code.startswith("#")
                else "That formula could not be worked out. Check the brackets and ranges."
            )
        except Exception:
            feedback = "That formula could not be worked out. Check the brackets and ranges."

        if not ok:
            # In a session, 2 wrong tries ends the round
            if sess and tries >= 2:
                self._state.mark_encounter_done(enc_id)
                result = self._state.advance_session(enc["session_id"], 0)
                return self._session_round_result(
                    player_id, enc, sess, result, correct=False,
                    feedback=feedback + " That over is lost.",
                )
            return {"correct": False, "feedback": feedback,
                    "attempt": tries, "player": self._snap(player_id)}

        # Correct answer
        self._state.mark_encounter_done(enc_id)
        old_level = self._state.wallet(player_id).get("level", 1)
        # Skill XP (read before award so we can detect level changes)
        old_skill = skill_level_for_xp(self._state.skill_xp(player_id).get(enc["family"], 0))
        wallet    = self._state.award(player_id, enc["coins"], enc["xp"])
        new_sxp   = self._state.add_skill_xp(player_id, enc["family"], enc["xp"])
        new_skill = skill_level_for_xp(new_sxp)
        skill_up  = new_skill > old_skill
        level_up  = wallet["level"] if wallet["level"] > old_level else None

        # Checkpoint
        cp_cleared = None
        if enc.get("cp_tier") and enc.get("cp_step"):
            self._state.set_checkpoint(player_id, enc["cp_tier"], enc["cp_step"])
            cp_cleared = {
                "tier": enc["cp_tier"],
                "step": enc["cp_step"],
                "of":   CHECKPOINTS.get(enc["cp_tier"], 0),
            }

        snap = self._snap(player_id)
        # Update leaderboard
        app = self._state.get_appearance(player_id)
        self._state.update_leaderboard(
            player_id, app.get("display_name", player_id),
            snap["coins"], snap["xp"], snap["level"], snap["tier"],
        )

        base: dict[str, Any] = {
            "correct":     True,
            "feedback":    "Correct.",
            "explanation": enc.get("explain", ""),
            "rewards": {
                "coins": enc["coins"],
                "xp":    enc["xp"],
                "skill": {"family": enc["family"], "level": new_skill, "up": skill_up},
            },
            "levelUp": level_up,
            "player":  snap,
        }
        if cp_cleared:
            base["checkpointCleared"] = cp_cleared

        if sess:
            result = self._state.advance_session(enc["session_id"], 1)
            return self._session_round_result(
                player_id, enc, sess, result, correct=True,
                feedback="Correct.", base=base,
            )
        return base

    def _session_round_result(
        self,
        player_id: str,
        enc: dict,
        sess: dict,
        updated: dict,
        *,
        correct: bool,
        feedback: str,
        base: dict | None = None,
    ) -> dict:
        sess_state = self._state.get_session(enc["session_id"])
        if not sess_state:
            # already finished
            snap = self._snap(player_id)
            out = base or {"correct": correct, "feedback": feedback, "player": snap}
            return out

        # Look up session type from stored row
        s_type   = sess_state["session_type"]
        s_config = SESSIONS.get(s_type, {})
        rounds   = sess_state["rounds_total"]
        pass_mk  = sess_state["pass_mark"]
        rnd      = sess_state["round"]  # already incremented by advance_session

        if rnd > rounds:
            return self._finish_session_result(player_id, enc, sess_state, s_config, base)

        # Next round
        npc_cfg  = NPC_CONFIG.get(enc["npc_id"], {})
        npc_name = npc_cfg.get("name", enc["npc_id"])
        family   = FAMILY_IDS[(rnd * 3 + hash(enc["enc_id"])) % len(FAMILY_IDS)]
        seed     = int(time.time()) ^ (hash(enc["enc_id"] + str(rnd)) & 0xFFFFFFFF)
        limit    = s_config.get("secs", 0)
        if sess_state["relaxed"]:
            limit = limit * 2 if limit else 0

        next_enc = self._question_encounter(
            _enc_id(), player_id, enc["npc_id"], npc_name,
            family, 3, seed, self._snap(player_id),
            session_id=enc["session_id"],
            say_prefix=f"Over {rnd} of {rounds}. ",
            session_meta={
                "id": s_type, "name": s_config.get("name", ""),
                "round": rnd, "rounds": rounds, "passMark": pass_mk,
                "correct": sess_state["correct"],
                "relaxed": bool(sess_state["relaxed"]),
                "big": bool(s_config.get("big", False)),
            },
        )
        # apply time limit from session
        next_enc["question"]["timeLimit"] = limit

        out = base or {"correct": correct, "feedback": feedback}
        out["roundOver"] = not correct
        out["next"]      = next_enc
        out["player"]    = self._snap(player_id)
        return out

    def _finish_session_result(
        self,
        player_id: str,
        enc: dict,
        sess: dict,
        s_config: dict,
        base: dict | None,
    ) -> dict:
        s_type  = sess["session_type"]
        correct = sess["correct"]
        rounds  = sess["rounds_total"]
        pass_mk = sess["pass_mark"]
        passed  = correct >= pass_mk
        self._state.finish_session(sess["session_id"])

        bonus_coins = 0
        bonus_xp    = 0
        level_up    = None
        enrol_tier  = None

        if passed:
            if s_config.get("big"):
                bonus_coins, bonus_xp = 140, 220
            elif s_config.get("enrol"):
                e = s_config["enrol"]
                bonus_coins = 40 + 10 * e
                bonus_xp    = 60 + 20 * e
            else:
                t = s_config.get("tier", 1)
                bonus_coins = 20 + 8 * t
                bonus_xp    = 30 + 10 * t

            old_lvl   = self._state.wallet(player_id).get("level", 1)
            wallet    = self._state.award(player_id, bonus_coins, bonus_xp)
            level_up  = wallet["level"] if wallet["level"] > old_lvl else None

            enrol = s_config.get("enrol", 0)
            if enrol and self._state.player_tier(player_id) == enrol - 1:
                club = CLUBS[enrol - 1]
                snap = self._snap(player_id)
                if _club_state(club, snap)["eligible"]:
                    self._state.set_player_tier(player_id, enrol)
                    enrol_tier = enrol

        snap = self._snap(player_id)
        name_text = s_config.get("name", "")
        if passed:
            msg = (
                f"Selected. Welcome to {CLUBS[enrol_tier - 1]['name']}."
                if enrol_tier
                else f"Well played. {correct} of {rounds} right."
            )
        else:
            cool_text = " Come back when the cooldown ends." if s_config.get("cooldownH") else " You can try again."
            msg = f"Not this time. You needed {pass_mk} right and got {correct}.{cool_text}"

        result = {
            "passed":       passed,
            "correct":      correct,
            "rounds":       rounds,
            "passMark":     pass_mk,
            "name":         name_text,
            "enrolledTier": enrol_tier,
            "bonus":        {"coins": bonus_coins, "xp": bonus_xp},
            "levelUp":      level_up,
            "message":      msg,
        }
        out = base or {}
        out["sessionResult"] = result
        out["player"]        = snap
        return out

    # ------------------------------------------------------------------
    # Begin session
    # ------------------------------------------------------------------

    def begin_session(self, player_id: str, enc_id: str, opts: dict) -> dict:
        enc = self._state.get_encounter(enc_id)
        if not enc or enc["player_id"] != player_id:
            raise EncounterError("EXPIRED", "That lobby has closed. Talk to them again.")
        if not enc.get("model", "").startswith("__lobby__"):
            raise EncounterError("EXPIRED", "This encounter is not a lobby.")

        sid = enc["model"].removeprefix("__lobby__")
        s   = SESSIONS.get(sid)
        if not s:
            raise EncounterError("NOT_FOUND", "Unknown session type.")

        snap = self._snap(player_id)
        cfg  = NPC_CONFIG.get(enc["npc_id"], {})
        enrol = s.get("enrol", 0)
        stier = s.get("tier", 0)
        ct    = enrol or stier or 1
        club  = CLUBS[ct - 1]
        cs    = _club_state(club, snap)

        # eligibility
        if enrol and snap["tier"] >= enrol:
            raise EncounterError("NOT_ELIGIBLE", "You are already enrolled.")
        if enrol and not cs["eligible"]:
            raise EncounterError("NOT_ELIGIBLE", "You do not meet the requirements yet.")

        # cooldown
        cool   = self._state.get_cooldown(player_id, sid)
        now_ms = int(time.time() * 1000)
        if cool and now_ms < cool:
            raise EncounterError("COOLDOWN", "Not yet. The next attempt is still locked.")

        # set cooldown
        cool_h = s.get("cooldownH", 0)
        if cool_h:
            self._state.set_cooldown(player_id, sid, now_ms + cool_h * 3_600_000)

        # create session
        sess_id  = _sess_id()
        relaxed  = bool(opts.get("relaxed", False))
        self._state.save_session(
            sess_id, player_id, enc["npc_id"], sid,
            s["rounds"], s["pass"], relaxed,
        )
        # mark lobby encounter done
        self._state.mark_encounter_done(enc_id)

        npc_name = cfg.get("name", enc["npc_id"])
        family   = FAMILY_IDS[hash(enc_id) % len(FAMILY_IDS)]
        seed     = int(time.time()) ^ (hash(sess_id) & 0xFFFFFFFF)
        limit    = s.get("secs", 0) * (2 if relaxed else 1)

        q_enc = self._question_encounter(
            _enc_id(), player_id, enc["npc_id"], npc_name,
            family, 3, seed, self._snap(player_id),
            session_id=sess_id,
            say_prefix=f"Over 1 of {s['rounds']}. ",
            session_meta={
                "id": sid, "name": s["name"],
                "round": 1, "rounds": s["rounds"], "passMark": s["pass"],
                "correct": 0, "relaxed": relaxed,
                "big": bool(s.get("big", False)),
            },
        )
        q_enc["question"]["timeLimit"] = limit
        return q_enc

    # ------------------------------------------------------------------
    # Lesson topic
    # ------------------------------------------------------------------

    def lesson_topic(self, player_id: str, enc_id: str, topic: str) -> dict:
        enc = self._state.get_encounter(enc_id)
        if not enc or enc["player_id"] != player_id:
            raise EncounterError("EXPIRED", "That lesson has ended.")
        L = LESSONS.get(topic)
        if not L:
            raise EncounterError("NOT_FOUND", f"Unknown topic {topic!r}.")
        # Award 8 skill XP for the topic's family
        old_level = self._state.wallet(player_id).get("level", 1)
        self._state.add_skill_xp(player_id, topic, 8)
        wallet    = self._state.award(player_id, 0, 8)
        level_up  = wallet["level"] if wallet["level"] > old_level else None
        snap      = self._snap(player_id)
        return {
            "title":   L["title"],
            "steps":   L["steps"],
            "example": L["example"],
            "rewards": {"coins": 0, "xp": 8},
            "levelUp": level_up,
            "player":  snap,
        }

    # ------------------------------------------------------------------
    # Facility visit
    # ------------------------------------------------------------------

    def visit_facility(self, player_id: str, fac_id: str) -> dict:
        tier_req = FACILITY_TIER.get(fac_id)
        if tier_req is None:
            raise EncounterError("NOT_FOUND", "No such facility.")
        snap = self._snap(player_id)
        if snap["tier"] < tier_req:
            return {"ok": False, "locked": True,
                    "message": f"Members only. Join {CLUBS[tier_req - 1]['name']} to use this.",
                    "player": snap}
        last   = self._state.get_facility_last_visit(player_id, fac_id)
        now_ts = int(time.time())
        if now_ts - last < 7:
            return {"ok": True, "tooSoon": True, "player": snap}
        self._state.set_facility_last_visit(player_id, fac_id, now_ts)
        old_level = self._state.wallet(player_id).get("level", 1)
        wallet   = self._state.award(player_id, 2, 6)
        level_up = wallet["level"] if wallet["level"] > old_level else None
        snap     = self._snap(player_id)
        self._state.update_leaderboard(
            player_id, self._state.get_appearance(player_id).get("display_name", player_id),
            snap["coins"], snap["xp"], snap["level"], snap["tier"],
        )
        return {"ok": True, "rewards": {"coins": 2, "xp": 6},
                "message": "+2 coins, +6 XP", "levelUp": level_up, "player": snap}

    # ------------------------------------------------------------------
    # Clubs list with live requirements
    # ------------------------------------------------------------------

    def clubs_list(self, player_id: str) -> list[dict]:
        snap = self._snap(player_id)
        return [_club_state(c, snap) for c in CLUBS]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _used_functions(formula: str) -> set[str]:
    """Return set of uppercase function names used in the formula."""
    import re
    return {m.upper() for m in re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?=\s*\()", formula)}


def _values_equal(got: Any, expected: Any) -> bool:
    """Compare values with the same tolerance as cc-formula.js F.same."""
    if isinstance(got, bool) or isinstance(expected, bool):
        return got is expected or got == expected
    try:
        gf = float(got)
        ef = float(expected)
        if ef == 0:
            return abs(gf) < 1e-9
        return abs(gf - ef) / max(abs(ef), 1e-9) < 1e-6
    except (TypeError, ValueError):
        return str(got).strip().lower() == str(expected).strip().lower()

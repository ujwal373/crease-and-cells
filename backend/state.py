"""SQLite game state. Swap for Postgres later; the interface stays the same."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

LEVEL_XP = 300  # xp per level (legacy — new code uses game_config.LEVEL_XP thresholds)

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY, name TEXT NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0, xp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS completed (
    player_id TEXT, mission_id TEXT, hints_used INTEGER, coins_awarded INTEGER, xp_awarded INTEGER,
    PRIMARY KEY (player_id, mission_id)
);
CREATE TABLE IF NOT EXISTS hints (
    player_id TEXT, mission_id TEXT, used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (player_id, mission_id)
);
CREATE TABLE IF NOT EXISTS inventory (
    player_id TEXT, item_id TEXT, PRIMARY KEY (player_id, item_id)
);
CREATE TABLE IF NOT EXISTS equipped (
    player_id TEXT, slot TEXT, item_id TEXT, PRIMARY KEY (player_id, slot)
);
CREATE TABLE IF NOT EXISTS hint_cache (
    mission_id TEXT, failure_code TEXT, hint_level INTEGER, reply TEXT,
    PRIMARY KEY (mission_id, failure_code, hint_level)
);
CREATE TABLE IF NOT EXISTS tutor_player_calls (
    player_id TEXT, call_date TEXT, count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, call_date)
);
CREATE TABLE IF NOT EXISTS tutor_daily_spend (
    call_date TEXT PRIMARY KEY, spent_usd REAL NOT NULL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS last_attempt (
    player_id TEXT, mission_id TEXT, formula TEXT NOT NULL, failure_code TEXT NOT NULL,
    PRIMARY KEY (player_id, mission_id)
);
CREATE TABLE IF NOT EXISTS ip_tutor_daily (
    ip TEXT, call_date TEXT, count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ip, call_date)
);
CREATE TABLE IF NOT EXISTS appearance (
    player_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    body_type TEXT NOT NULL DEFAULT 'medium',
    skin_tone TEXT NOT NULL DEFAULT 'medium',
    hair_style TEXT NOT NULL DEFAULT 'short',
    hair_colour TEXT NOT NULL DEFAULT 'black'
);
"""

# New tables for the game_frontend_new integration.
# Applied in __init__ after the base SCHEMA so existing DBs are migrated safely.
NEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS skill_xp (
    player_id TEXT, family TEXT, xp INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, family)
);
CREATE TABLE IF NOT EXISTS encounters (
    enc_id      TEXT PRIMARY KEY,
    player_id   TEXT NOT NULL,
    npc_id      TEXT NOT NULL,
    family      TEXT NOT NULL,
    difficulty  INTEGER NOT NULL,
    expected    TEXT NOT NULL,
    grid        TEXT NOT NULL,
    model       TEXT NOT NULL,
    must_use    TEXT NOT NULL,
    coins       INTEGER NOT NULL,
    xp          INTEGER NOT NULL,
    tries       INTEGER NOT NULL DEFAULT 0,
    done        INTEGER NOT NULL DEFAULT 0,
    session_id  TEXT,
    cp_tier     INTEGER,
    cp_step     INTEGER,
    is_practice INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    player_id    TEXT NOT NULL,
    npc_id       TEXT NOT NULL,
    session_type TEXT NOT NULL,
    round        INTEGER NOT NULL DEFAULT 1,
    correct      INTEGER NOT NULL DEFAULT 0,
    rounds_total INTEGER NOT NULL,
    pass_mark    INTEGER NOT NULL,
    relaxed      INTEGER NOT NULL DEFAULT 0,
    cooldown_until INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS session_cooldowns (
    player_id    TEXT,
    session_type TEXT,
    cooldown_until INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, session_type)
);
CREATE TABLE IF NOT EXISTS checkpoints (
    player_id TEXT, tier INTEGER, steps_cleared INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, tier)
);
CREATE TABLE IF NOT EXISTS facility_visits (
    player_id   TEXT,
    facility_id TEXT,
    last_visit  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (player_id, facility_id)
);
CREATE TABLE IF NOT EXISTS leaderboard (
    player_id    TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    coins        INTEGER NOT NULL DEFAULT 0,
    xp           INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 1,
    tier         INTEGER NOT NULL DEFAULT 0
);
"""

_ALTER_PLAYERS = [
    "ALTER TABLE players ADD COLUMN tier    INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE players ADD COLUMN created INTEGER NOT NULL DEFAULT 0",
]


class GameState:
    def __init__(self, path: str = ":memory:"):
        # threading.Lock serialises all DB access on a shared connection.
        # WAL mode allows concurrent readers from separate connections if needed later.
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(SCHEMA)
        self.db.executescript(NEW_SCHEMA)
        for stmt in _ALTER_PLAYERS:
            try:
                self.db.execute(stmt)
                self.db.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

    def ensure_player(self, player_id: str, name: str | None = None) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR IGNORE INTO players (id, name) VALUES (?, ?)", (player_id, name or player_id)
            )
            self.db.commit()

    def wallet(self, player_id: str) -> dict:
        with self._lock:
            row = self.db.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            return dict(row) if row else {}

    def completed_ids(self, player_id: str) -> set[str]:
        with self._lock:
            rows = self.db.execute("SELECT mission_id FROM completed WHERE player_id=?", (player_id,)).fetchall()
            return {r["mission_id"] for r in rows}

    def hints_used(self, player_id: str, mission_id: str) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT used FROM hints WHERE player_id=? AND mission_id=?", (player_id, mission_id)
            ).fetchone()
            return row["used"] if row else 0

    def bump_hints(self, player_id: str, mission_id: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO hints (player_id, mission_id, used) VALUES (?, ?, 1) "
                "ON CONFLICT(player_id, mission_id) DO UPDATE SET used = used + 1",
                (player_id, mission_id),
            )
            self.db.commit()

    def complete(self, player_id: str, mission_id: str, hints: int, coins: int, xp: int) -> bool:
        """Idempotent: returns False if this mission was already completed."""
        with self._lock:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO completed VALUES (?, ?, ?, ?, ?)", (player_id, mission_id, hints, coins, xp)
            )
            if cur.rowcount == 0:
                self.db.commit()
                return False
            self.db.execute(
                "UPDATE players SET coins = coins + ?, xp = xp + ? WHERE id=?", (coins, xp, player_id)
            )
            self.db.execute("UPDATE players SET level = 1 + xp / ? WHERE id=?", (LEVEL_XP, player_id))
            self.db.commit()
            return True

    def spend(self, player_id: str, amount: int) -> bool:
        """Atomic: deducts only if the balance covers it."""
        with self._lock:
            cur = self.db.execute(
                "UPDATE players SET coins = coins - ? WHERE id=? AND coins >= ?", (amount, player_id, amount)
            )
            self.db.commit()
            return cur.rowcount == 1

    def owns(self, player_id: str, item_id: str) -> bool:
        with self._lock:
            return self.db.execute(
                "SELECT 1 FROM inventory WHERE player_id=? AND item_id=?", (player_id, item_id)
            ).fetchone() is not None

    def add_item(self, player_id: str, item_id: str) -> None:
        with self._lock:
            self.db.execute("INSERT OR IGNORE INTO inventory VALUES (?, ?)", (player_id, item_id))
            self.db.commit()

    def equip(self, player_id: str, slot: str, item_id: str) -> None:
        with self._lock:
            self.db.execute("INSERT OR REPLACE INTO equipped VALUES (?, ?, ?)", (player_id, slot, item_id))
            self.db.commit()

    def inventory(self, player_id: str) -> list[str]:
        with self._lock:
            rows = self.db.execute("SELECT item_id FROM inventory WHERE player_id=?", (player_id,)).fetchall()
            return [r["item_id"] for r in rows]

    def equipped(self, player_id: str) -> dict:
        with self._lock:
            rows = self.db.execute("SELECT slot, item_id FROM equipped WHERE player_id=?", (player_id,)).fetchall()
            return {r["slot"]: r["item_id"] for r in rows}

    # ------------------------------------------------------------------
    # Tutor: hint cache
    # ------------------------------------------------------------------

    def get_hint_cache(self, mission_id: str, failure_code: str, hint_level: int) -> str | None:
        with self._lock:
            row = self.db.execute(
                "SELECT reply FROM hint_cache WHERE mission_id=? AND failure_code=? AND hint_level=?",
                (mission_id, failure_code, hint_level),
            ).fetchone()
            return row["reply"] if row else None

    def set_hint_cache(self, mission_id: str, failure_code: str, hint_level: int, reply: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO hint_cache VALUES (?, ?, ?, ?)",
                (mission_id, failure_code, hint_level, reply),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Tutor: daily caps
    # ------------------------------------------------------------------

    def tutor_player_count(self, player_id: str, call_date: str) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT count FROM tutor_player_calls WHERE player_id=? AND call_date=?",
                (player_id, call_date),
            ).fetchone()
            return row["count"] if row else 0

    def increment_tutor_player_count(self, player_id: str, call_date: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO tutor_player_calls (player_id, call_date, count) VALUES (?, ?, 1) "
                "ON CONFLICT(player_id, call_date) DO UPDATE SET count = count + 1",
                (player_id, call_date),
            )
            self.db.commit()

    def tutor_daily_spend(self, call_date: str) -> float:
        with self._lock:
            row = self.db.execute(
                "SELECT spent_usd FROM tutor_daily_spend WHERE call_date=?", (call_date,)
            ).fetchone()
            return row["spent_usd"] if row else 0.0

    def increment_tutor_spend(self, call_date: str, amount_usd: float) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO tutor_daily_spend (call_date, spent_usd) VALUES (?, ?) "
                "ON CONFLICT(call_date) DO UPDATE SET spent_usd = spent_usd + ?",
                (call_date, amount_usd, amount_usd),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Last submitted attempt per player per mission
    # ------------------------------------------------------------------

    def set_last_attempt(self, player_id: str, mission_id: str, formula: str, failure_code: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO last_attempt VALUES (?, ?, ?, ?)",
                (player_id, mission_id, formula, failure_code),
            )
            self.db.commit()

    def get_last_attempt(self, player_id: str, mission_id: str) -> tuple[str, str] | None:
        with self._lock:
            row = self.db.execute(
                "SELECT formula, failure_code FROM last_attempt WHERE player_id=? AND mission_id=?",
                (player_id, mission_id),
            ).fetchone()
            return (row["formula"], row["failure_code"]) if row else None

    # ------------------------------------------------------------------
    # Atomic store purchase: own-check + spend + add + equip under one lock
    # ------------------------------------------------------------------

    def buy_item_atomic(self, player_id: str, item_id: str, price: int, slot: str) -> str | None:
        """Atomically check ownership, spend, add to inventory, and equip.

        Returns None on success, or a failure-reason string. Holding a single
        lock for the entire sequence prevents a player with sufficient coins
        from completing the same purchase twice concurrently.
        """
        with self._lock:
            if self.db.execute(
                "SELECT 1 FROM inventory WHERE player_id=? AND item_id=?",
                (player_id, item_id),
            ).fetchone():
                return "already owned"
            cur = self.db.execute(
                "UPDATE players SET coins = coins - ? WHERE id=? AND coins >= ?",
                (price, player_id, price),
            )
            if cur.rowcount == 0:
                self.db.commit()
                return "not enough coins"
            self.db.execute("INSERT OR IGNORE INTO inventory VALUES (?, ?)", (player_id, item_id))
            self.db.execute("INSERT OR REPLACE INTO equipped VALUES (?, ?, ?)", (player_id, slot, item_id))
            self.db.commit()
            return None

    # ------------------------------------------------------------------
    # Tutor: per-IP daily cap
    # ------------------------------------------------------------------

    def ip_tutor_count(self, ip: str, call_date: str) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT count FROM ip_tutor_daily WHERE ip=? AND call_date=?",
                (ip, call_date),
            ).fetchone()
            return row["count"] if row else 0

    def increment_ip_tutor_daily(self, ip: str, call_date: str) -> None:
        with self._lock:
            self.db.execute(
                "INSERT INTO ip_tutor_daily (ip, call_date, count) VALUES (?, ?, 1) "
                "ON CONFLICT(ip, call_date) DO UPDATE SET count = count + 1",
                (ip, call_date),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Character appearance
    # ------------------------------------------------------------------

    def get_appearance(self, player_id: str) -> dict:
        with self._lock:
            row = self.db.execute(
                "SELECT display_name, body_type, skin_tone, hair_style, hair_colour "
                "FROM appearance WHERE player_id=?",
                (player_id,),
            ).fetchone()
            if row:
                return dict(row)
            return {
                "display_name": "",
                "body_type": "medium",
                "skin_tone": "medium",
                "hair_style": "short",
                "hair_colour": "black",
            }

    def set_appearance(
        self,
        player_id: str,
        display_name: str,
        body_type: str,
        skin_tone: str,
        hair_style: str,
        hair_colour: str,
    ) -> None:
        with self._lock:
            if display_name:
                self.db.execute(
                    "UPDATE players SET name=? WHERE id=?", (display_name, player_id)
                )
            self.db.execute(
                "INSERT OR REPLACE INTO appearance "
                "(player_id, display_name, body_type, skin_tone, hair_style, hair_colour) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (player_id, display_name, body_type, skin_tone, hair_style, hair_colour),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Player tier / created flag
    # ------------------------------------------------------------------

    def player_tier(self, player_id: str) -> int:
        with self._lock:
            row = self.db.execute("SELECT tier FROM players WHERE id=?", (player_id,)).fetchone()
            return row["tier"] if row else 0

    def set_player_tier(self, player_id: str, tier: int) -> None:
        with self._lock:
            self.db.execute("UPDATE players SET tier=? WHERE id=?", (tier, player_id))
            self.db.commit()

    def set_player_created(self, player_id: str) -> None:
        with self._lock:
            self.db.execute("UPDATE players SET created=1 WHERE id=?", (player_id,))
            self.db.commit()

    # ------------------------------------------------------------------
    # Skill XP
    # ------------------------------------------------------------------

    def skill_xp(self, player_id: str) -> dict[str, int]:
        with self._lock:
            rows = self.db.execute(
                "SELECT family, xp FROM skill_xp WHERE player_id=?", (player_id,)
            ).fetchall()
            return {r["family"]: r["xp"] for r in rows}

    def add_skill_xp(self, player_id: str, family: str, delta: int) -> int:
        with self._lock:
            self.db.execute(
                "INSERT INTO skill_xp (player_id, family, xp) VALUES (?, ?, ?) "
                "ON CONFLICT(player_id, family) DO UPDATE SET xp = xp + ?",
                (player_id, family, delta, delta),
            )
            self.db.commit()
            row = self.db.execute(
                "SELECT xp FROM skill_xp WHERE player_id=? AND family=?", (player_id, family)
            ).fetchone()
            return row["xp"] if row else delta

    # ------------------------------------------------------------------
    # Encounters
    # ------------------------------------------------------------------

    def save_encounter(
        self,
        enc_id: str,
        player_id: str,
        npc_id: str,
        family: str,
        difficulty: int,
        expected: object,
        grid: list,
        model: str,
        must_use: list[str],
        coins: int,
        xp: int,
        session_id: str | None = None,
        cp_tier: int | None = None,
        cp_step: int | None = None,
        is_practice: bool = False,
    ) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO encounters "
                "(enc_id, player_id, npc_id, family, difficulty, expected, grid, model, "
                " must_use, coins, xp, session_id, cp_tier, cp_step, is_practice, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    enc_id, player_id, npc_id, family, difficulty,
                    json.dumps(expected), json.dumps(grid), model,
                    json.dumps(must_use), coins, xp,
                    session_id, cp_tier, cp_step, int(is_practice),
                    int(time.time()),
                ),
            )
            self.db.commit()

    def get_encounter(self, enc_id: str) -> dict | None:
        with self._lock:
            row = self.db.execute("SELECT * FROM encounters WHERE enc_id=?", (enc_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["expected"]  = json.loads(d["expected"])
            d["grid"]      = json.loads(d["grid"])
            d["must_use"]  = json.loads(d["must_use"])
            d["done"]      = bool(d["done"])
            d["is_practice"] = bool(d["is_practice"])
            return d

    def mark_encounter_done(self, enc_id: str) -> None:
        with self._lock:
            self.db.execute("UPDATE encounters SET done=1 WHERE enc_id=?", (enc_id,))
            self.db.commit()

    def increment_encounter_tries(self, enc_id: str) -> int:
        with self._lock:
            self.db.execute("UPDATE encounters SET tries=tries+1 WHERE enc_id=?", (enc_id,))
            self.db.commit()
            row = self.db.execute("SELECT tries FROM encounters WHERE enc_id=?", (enc_id,)).fetchone()
            return row["tries"] if row else 1

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def save_session(
        self,
        session_id: str,
        player_id: str,
        npc_id: str,
        session_type: str,
        rounds_total: int,
        pass_mark: int,
        relaxed: bool = False,
    ) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO sessions "
                "(session_id, player_id, npc_id, session_type, rounds_total, pass_mark, relaxed) "
                "VALUES (?,?,?,?,?,?,?)",
                (session_id, player_id, npc_id, session_type, rounds_total, pass_mark, int(relaxed)),
            )
            self.db.commit()

    def get_session(self, session_id: str) -> dict | None:
        with self._lock:
            row = self.db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["relaxed"] = bool(d["relaxed"])
            return d

    def advance_session(self, session_id: str, correct_delta: int) -> dict:
        with self._lock:
            self.db.execute(
                "UPDATE sessions SET round=round+1, correct=correct+? WHERE session_id=?",
                (correct_delta, session_id),
            )
            self.db.commit()
            row = self.db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            return dict(row) if row else {}

    def finish_session(self, session_id: str) -> None:
        with self._lock:
            self.db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            self.db.commit()

    # ------------------------------------------------------------------
    # Session cooldowns
    # ------------------------------------------------------------------

    def get_cooldown(self, player_id: str, session_type: str) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT cooldown_until FROM session_cooldowns WHERE player_id=? AND session_type=?",
                (player_id, session_type),
            ).fetchone()
            return row["cooldown_until"] if row else 0

    def set_cooldown(self, player_id: str, session_type: str, until_ts: int) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO session_cooldowns VALUES (?,?,?)",
                (player_id, session_type, until_ts),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------

    def get_checkpoints(self, player_id: str, tier: int) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT steps_cleared FROM checkpoints WHERE player_id=? AND tier=?",
                (player_id, tier),
            ).fetchone()
            return row["steps_cleared"] if row else 0

    def set_checkpoint(self, player_id: str, tier: int, step: int) -> None:
        with self._lock:
            existing = self.db.execute(
                "SELECT steps_cleared FROM checkpoints WHERE player_id=? AND tier=?",
                (player_id, tier),
            ).fetchone()
            current = existing["steps_cleared"] if existing else 0
            new_val = max(current, step)
            self.db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?,?,?)",
                (player_id, tier, new_val),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Facility visits
    # ------------------------------------------------------------------

    def get_facility_last_visit(self, player_id: str, facility_id: str) -> int:
        with self._lock:
            row = self.db.execute(
                "SELECT last_visit FROM facility_visits WHERE player_id=? AND facility_id=?",
                (player_id, facility_id),
            ).fetchone()
            return row["last_visit"] if row else 0

    def set_facility_last_visit(self, player_id: str, facility_id: str, ts: int) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO facility_visits VALUES (?,?,?)",
                (player_id, facility_id, ts),
            )
            self.db.commit()

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def update_leaderboard(
        self,
        player_id: str,
        display_name: str,
        coins: int,
        xp: int,
        level: int,
        tier: int,
    ) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO leaderboard VALUES (?,?,?,?,?,?)",
                (player_id, display_name, coins, xp, level, tier),
            )
            self.db.commit()

    def get_leaderboard(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT player_id, display_name, coins, xp, level, tier "
                "FROM leaderboard ORDER BY xp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Award coins + XP (used by encounter service, keeps level in sync)
    # ------------------------------------------------------------------

    def award(self, player_id: str, coins: int, xp: int) -> dict:
        """Add coins and XP, recompute level, return updated wallet dict."""
        from .game_config import LEVEL_XP as _LXP, level_for_xp

        with self._lock:
            self.db.execute(
                "UPDATE players SET coins=coins+?, xp=xp+? WHERE id=?",
                (coins, xp, player_id),
            )
            self.db.commit()
            row = self.db.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            d   = dict(row)
            new_level = level_for_xp(d["xp"])
            if new_level != d["level"]:
                self.db.execute("UPDATE players SET level=? WHERE id=?", (new_level, player_id))
                self.db.commit()
                d["level"] = new_level
            return d

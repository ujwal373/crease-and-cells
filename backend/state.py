"""SQLite game state. Swap for Postgres later; the interface stays the same."""
from __future__ import annotations

import sqlite3
import threading

LEVEL_XP = 300  # xp per level

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
"""


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

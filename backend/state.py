"""SQLite game state. Swap for Postgres later; the interface stays the same."""
from __future__ import annotations

import sqlite3

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
"""


class GameState:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def ensure_player(self, player_id: str, name: str | None = None) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO players (id, name) VALUES (?, ?)", (player_id, name or player_id)
        )
        self.db.commit()

    def wallet(self, player_id: str) -> dict:
        row = self.db.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
        return dict(row) if row else {}

    def completed_ids(self, player_id: str) -> set[str]:
        rows = self.db.execute("SELECT mission_id FROM completed WHERE player_id=?", (player_id,)).fetchall()
        return {r["mission_id"] for r in rows}

    def hints_used(self, player_id: str, mission_id: str) -> int:
        row = self.db.execute(
            "SELECT used FROM hints WHERE player_id=? AND mission_id=?", (player_id, mission_id)
        ).fetchone()
        return row["used"] if row else 0

    def bump_hints(self, player_id: str, mission_id: str) -> None:
        self.db.execute(
            "INSERT INTO hints (player_id, mission_id, used) VALUES (?, ?, 1) "
            "ON CONFLICT(player_id, mission_id) DO UPDATE SET used = used + 1",
            (player_id, mission_id),
        )
        self.db.commit()

    def complete(self, player_id: str, mission_id: str, hints: int, coins: int, xp: int) -> bool:
        """Idempotent: returns False if this mission was already completed."""
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
        cur = self.db.execute(
            "UPDATE players SET coins = coins - ? WHERE id=? AND coins >= ?", (amount, player_id, amount)
        )
        self.db.commit()
        return cur.rowcount == 1

    def owns(self, player_id: str, item_id: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM inventory WHERE player_id=? AND item_id=?", (player_id, item_id)
        ).fetchone() is not None

    def add_item(self, player_id: str, item_id: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO inventory VALUES (?, ?)", (player_id, item_id))
        self.db.commit()

    def equip(self, player_id: str, slot: str, item_id: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO equipped VALUES (?, ?, ?)", (player_id, slot, item_id))
        self.db.commit()

    def inventory(self, player_id: str) -> list[str]:
        rows = self.db.execute("SELECT item_id FROM inventory WHERE player_id=?", (player_id,)).fetchall()
        return [r["item_id"] for r in rows]

    def equipped(self, player_id: str) -> dict:
        rows = self.db.execute("SELECT slot, item_id FROM equipped WHERE player_id=?", (player_id,)).fetchall()
        return {r["slot"]: r["item_id"] for r in rows}

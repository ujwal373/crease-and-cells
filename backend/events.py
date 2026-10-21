"""In-process event bus. Agents subscribe to events and never call each other."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from .tracing import trace

MISSION_ASSIGNED = "mission_assigned"
ANSWER_SUBMITTED = "answer_submitted"
ANSWER_REJECTED = "answer_rejected"
MISSION_PASSED = "mission_passed"
COINS_AWARDED = "coins_awarded"
ITEM_PURCHASED = "item_purchased"
HINT_USED = "hint_used"

Handler = Callable[[dict], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event: str, handler: Handler) -> None:
        self._subs[event].append(handler)

    def publish(self, event: str, payload: dict) -> None:
        """Handlers receive the same dict and may add keys to it."""
        trace("bus." + event, player_id=payload.get("player_id"), mission_id=payload.get("mission_id"))
        for handler in self._subs[event]:
            handler(payload)

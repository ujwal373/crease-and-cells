"""FastAPI layer wrapping GameService.

Environment variables:
  CC_DB_PATH             SQLite database file (default: game.db)
  CC_CORS_ORIGINS        JSON array or comma-separated list of allowed origins
                         (default: ["http://localhost:5173"])
  ANTHROPIC_API_KEY      If set, the Tutor Agent is enabled for live hints.
  CC_TRUSTED_PROXIES     Number of trusted reverse proxies in front of this
                         server (default: 0). When set to N > 0, the Nth IP
                         from the right in X-Forwarded-For is used as the
                         client IP. Set this only when you control the proxy
                         chain; trusting X-Forwarded-For from untrusted clients
                         allows IP spoofing.
  CC_IP_TUTOR_DAILY      Max live tutor calls per IP per day (default: 20,
                         read by ai_config.DEFAULT_IP_DAILY_CAP).
  CC_IP_NEW_PLAYER_HOURLY Max new player registrations per IP per hour
                         (default: 10).

Rate limiting note: the in-memory limiters work for a single process.
For multi-instance deployments, replace _RateLimiter with a Redis-backed
counter (e.g. Upstash Redis with INCR + EXPIRE per key).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from .service import GameService
from . import tracing

_MAX_BODY_BYTES = 10 * 1024  # 10 KB


# ---------------------------------------------------------------------------
# Rate limiter: sliding window, in-memory (needs Redis for multi-instance)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, max_calls: int, window_secs: float) -> None:
        self._max = max_calls
        self._window = window_secs
        self._calls: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._call_count = 0

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            # Lazy eviction every 1 000 calls: drain expired entries from ALL
            # deques, then remove any that became empty.  This keeps the dict
            # bounded even for keys that were only called once long ago.
            self._call_count += 1
            if self._call_count >= 1000:
                self._call_count = 0
                cutoff = now - self._window
                for dq in self._calls.values():
                    while dq and dq[0] < cutoff:
                        dq.popleft()
                stale = [k for k, dq in self._calls.items() if not dq]
                for k in stale:
                    del self._calls[k]
            dq = self._calls[key]
            while dq and dq[0] < now - self._window:
                dq.popleft()
            if len(dq) >= self._max:
                return False
            dq.append(now)
            return True

    def evict(self) -> int:
        """Drain expired entries from all deques, then remove empty keys.

        Returns the number of keys removed. Called automatically every
        1 000 is_allowed() calls; also callable directly from tests or
        maintenance tasks.
        """
        now = time.monotonic()
        with self._lock:
            cutoff = now - self._window
            for dq in self._calls.values():
                while dq and dq[0] < cutoff:
                    dq.popleft()
            stale = [k for k, dq in self._calls.items() if not dq]
            for k in stale:
                del self._calls[k]
            return len(stale)


_player_limiter = _RateLimiter(60, 60)         # 60 req/min per player
_preview_limiter = _RateLimiter(20, 60)        # 20 req/min per player (preview only)
_ip_limiter = _RateLimiter(200, 60)            # 200 req/min per IP
_new_player_ip_limiter = _RateLimiter(
    int(os.environ.get("CC_IP_NEW_PLAYER_HOURLY", "10")), 3600
)                                              # 10 new players/IP/hour

# Tracks player IDs already seen this process run, to detect first appearances.
# Maps player_id -> monotonic timestamp of first sight; evicted after 2 h.
_seen_players: dict[str, float] = {}
_seen_players_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Client IP resolution
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """Return the real client IP, honouring CC_TRUSTED_PROXIES when set.

    Without CC_TRUSTED_PROXIES (or when set to 0), always return the direct
    connection address. Setting it to N > 0 trusts the Nth IP from the right
    in the X-Forwarded-For header, which is correct when exactly N reverse
    proxies sit in front of this server. Never trust client-supplied
    X-Forwarded-For without this setting.
    """
    n_proxies = int(os.environ.get("CC_TRUSTED_PROXIES", "0"))
    if n_proxies > 0:
        xff = request.headers.get("x-forwarded-for", "")
        ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        # The rightmost N entries were added by trusted proxies; the one
        # just to the left of those is the actual client.
        idx = len(ips) - n_proxies
        if idx > 0:
            return ips[idx - 1]
    return request.client.host if request.client else "unknown"


def _check_rate(player_id: str, request: Request, *, preview: bool = False) -> str:
    """Run all rate-limit checks. Returns the resolved client IP."""
    ip = _get_client_ip(request)
    if not _ip_limiter.is_allowed(ip):
        raise HTTPException(status_code=429, detail={"error": "rate_limit_exceeded"})
    limiter = _preview_limiter if preview else _player_limiter
    if not limiter.is_allowed(player_id):
        raise HTTPException(status_code=429, detail={"error": "rate_limit_exceeded"})
    return ip


def _check_new_player(player_id: str, ip: str) -> None:
    """Limit new player registrations per IP per hour."""
    now = time.monotonic()
    with _seen_players_lock:
        # Evict entries older than 2 h to keep the dict bounded
        cutoff = now - 7200
        stale = [k for k, t in _seen_players.items() if t < cutoff]
        for k in stale:
            del _seen_players[k]
        if player_id in _seen_players:
            return  # known player, no limit applies
        if not _new_player_ip_limiter.is_allowed(ip):
            raise HTTPException(status_code=429, detail={"error": "too_many_players_from_ip"})
        _seen_players[player_id] = now


# ---------------------------------------------------------------------------
# Player ID validation
# ---------------------------------------------------------------------------

def _validate_player_id(player_id: str) -> str:
    # Auth will plug in here once Supabase / Clerk is wired up.
    try:
        parsed = uuid.UUID(player_id, version=4)
        if str(parsed) != player_id.lower():
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_player_id"})
    return player_id


# ---------------------------------------------------------------------------
# Pydantic response models — extra="ignore" strips any unlisted field,
# so a new private field in the service layer can never leak here.
# ---------------------------------------------------------------------------

class MissionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # mission case
    id: str | None = None
    level: int | None = None
    zone: str | None = None
    npc: str | None = None
    title: str | None = None
    story: str | None = None
    task: str | None = None
    dataset: dict | None = None
    hints_available: int | None = None
    sheet_name: str | None = None
    sheet: list[Any] | None = None
    reward: dict | None = None
    # all-done case
    done: bool | None = None
    message: str | None = None


class SubmitOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passed: bool
    reason: str
    your_value: Any = None
    already_completed: bool | None = None
    coins_awarded: int | None = None
    no_hint_bonus: int | None = None
    xp_awarded: int | None = None
    wallet: dict | None = None
    next_mission: dict | None = None


class HintOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hint: str
    hint_number: int
    of: int
    no_hint_bonus_lost: bool


class CoachOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # hint path
    hint: str | None = None
    hint_number: int | None = None
    of: int | None = None
    no_hint_bonus_lost: bool | None = None
    # blocked path
    blocked: bool | None = None
    reply: str | None = None


class PreviewOut(BaseModel):
    value: Any = None
    error: str | None = None


class WalletOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    coins: int
    xp: int
    level: int
    outfit: dict


class StoreItemOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    slot: str
    tier: str
    price: int
    owned: bool


class BuyOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ok: bool
    reason: str | None = None
    item: str | None = None
    wallet: dict | None = None
    equipped: dict | None = None


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class SubmitBody(BaseModel):
    player_id: str
    formula: str = ""


class HintBody(BaseModel):
    player_id: str


class CoachBody(BaseModel):
    player_id: str
    message: str


class PreviewBody(BaseModel):
    player_id: str
    formula: str = ""


class BuyBody(BaseModel):
    player_id: str
    item_id: str


# ---------------------------------------------------------------------------
# App factory helpers
# ---------------------------------------------------------------------------

def _cors_origins() -> list[str]:
    raw = os.environ.get("CC_CORS_ORIGINS", "")
    if not raw:
        return ["http://localhost:5173"]
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]


def _make_tutor_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def _db_path() -> str:
    return os.environ.get("CC_DB_PATH", "game.db")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.svc = GameService(_db_path(), tutor_client=_make_tutor_client())
    yield


app = FastAPI(title="Crease and Cells API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def _request_id_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    tracing.set_request_id(req_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = req_id
    return response


@app.middleware("http")
async def _body_size_middleware(request: Request, call_next):
    """Enforce the body-size limit on the bytes actually received.

    Reading the stream rather than trusting Content-Length means the limit
    is enforced for chunked transfer-encoded bodies too.
    """
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > _MAX_BODY_BYTES:
            return JSONResponse({"error": "request_too_large"}, status_code=413)
    # Re-cache the body so downstream route handlers can read it via request.body()
    request._body = body  # type: ignore[attr-defined]
    return await call_next(request)


@app.exception_handler(KeyError)
async def _key_error_handler(_request: Request, exc: KeyError):
    return JSONResponse({"error": "not_found", "detail": str(exc)}, status_code=404)


@app.exception_handler(Exception)
async def _generic_error_handler(_request: Request, exc: Exception):
    tracing.trace("api.error", error=type(exc).__name__, detail=str(exc))
    return JSONResponse({"error": "internal_error"}, status_code=500)


def _svc(request: Request) -> GameService:
    return request.app.state.svc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/mission", response_model=MissionOut)
def get_mission(request: Request, player_id: str, name: str | None = None):
    _validate_player_id(player_id)
    ip = _check_rate(player_id, request)
    _check_new_player(player_id, ip)
    return _svc(request).get_next_mission(player_id, name)


@app.post("/api/mission/{mission_id}/submit", response_model=SubmitOut)
def submit_answer(mission_id: str, body: SubmitBody, request: Request):
    _validate_player_id(body.player_id)
    _check_rate(body.player_id, request)
    return _svc(request).submit_answer(body.player_id, mission_id, body.formula)


@app.post("/api/mission/{mission_id}/hint", response_model=HintOut)
def get_hint(mission_id: str, body: HintBody, request: Request):
    _validate_player_id(body.player_id)
    ip = _check_rate(body.player_id, request)
    return _svc(request).get_hint(body.player_id, mission_id, requester_ip=ip)


@app.post("/api/mission/{mission_id}/coach", response_model=CoachOut)
def ask_coach(mission_id: str, body: CoachBody, request: Request):
    _validate_player_id(body.player_id)
    ip = _check_rate(body.player_id, request)
    return _svc(request).ask_coach(body.player_id, mission_id, body.message, requester_ip=ip)


@app.post("/api/mission/{mission_id}/preview", response_model=PreviewOut)
def preview_formula(mission_id: str, body: PreviewBody, request: Request):
    _validate_player_id(body.player_id)
    _check_rate(body.player_id, request, preview=True)
    return _svc(request).preview_formula(body.player_id, mission_id, body.formula)


@app.get("/api/wallet", response_model=WalletOut)
def get_wallet(request: Request, player_id: str):
    _validate_player_id(player_id)
    _check_rate(player_id, request)
    return _svc(request).get_wallet(player_id)


@app.get("/api/store", response_model=list[StoreItemOut])
def list_store(request: Request, player_id: str):
    _validate_player_id(player_id)
    _check_rate(player_id, request)
    return _svc(request).list_store(player_id)


@app.post("/api/store/buy", response_model=BuyOut)
def buy_item(body: BuyBody, request: Request):
    _validate_player_id(body.player_id)
    _check_rate(body.player_id, request)
    return _svc(request).buy_item(body.player_id, body.item_id)

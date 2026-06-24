"""
main.py — FastAPI backend for the Scotland World Cup tracker.

  GET /api/state   JSON the React app polls
  GET /healthz     liveness
  GET /*           the built React app (frontend/dist), once it exists

The tracker logic lives in tracker.py (stdlib only). State is cached with a
short TTL so a roomful of friends refreshing doesn't hammer ESPN; the TTL drops
while Scotland are playing. The /api/state handler is a plain `def`, so Starlette
runs the blocking urllib fetch in its threadpool — no async needed for this.
"""

import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from tracker import Fetcher, build_state

TTL_DEFAULT = 90      # seconds between refreshes normally
TTL_LIVE = 20         # seconds while Scotland are on the pitch
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="Scotland · Road to the Round of 32")

_fetcher = Fetcher(cache_path="espn_cache.json")
_lock = threading.Lock()
_cache: dict = {"state": None, "ts": 0.0}


def _ttl(state) -> int:
    return TTL_LIVE if state and state.get("phase") == "live" else TTL_DEFAULT


def get_state(force: bool = False) -> dict:
    with _lock:
        age = time.time() - _cache["ts"]
        if force or _cache["state"] is None or age > _ttl(_cache["state"]):
            try:
                _cache["state"] = build_state(_fetcher)
                _cache["ts"] = time.time()
                _cache["state"]["stale"] = False
            except Exception as exc:                  # keep serving last good copy
                if _cache["state"] is not None:
                    _cache["state"]["stale"] = True
                    _cache["state"]["error"] = str(exc)
                else:
                    raise
        return _cache["state"]


@app.get("/api/state")
def api_state() -> JSONResponse:
    return JSONResponse(get_state())


@app.get("/healthz")
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


# Serve the built React app last, so the API routes above take precedence.
# In dev you run Vite separately (it proxies /api to here), so dist may be absent.
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")

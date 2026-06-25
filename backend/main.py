"""
main.py — FastAPI backend for the World Cup tracker.

  GET /api/state?team=SCO   JSON the React app polls (default team: SCO)
  GET /healthz              liveness
  GET /*                    the built React app (frontend/dist), once it exists

State is cached per team with a short TTL. The model is parsed once per
refresh cycle and shared between analyse() and qualification_probability(),
so ESPN is only hit once regardless of which team is selected.
"""

import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from tracker import Fetcher, build_model, analyse
from odds import EloOdds, NeutralOdds
from simulate import qualification_probability

TTL_DEFAULT = 90      # seconds between refreshes normally
TTL_LIVE = 20         # seconds while the target team's match is live
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="World Cup 2026 Tracker")

_fetcher = Fetcher(cache_path="espn_cache.json")
_odds = EloOdds() if os.getenv("ODDS", "elo") == "elo" else NeutralOdds()
_lock = threading.Lock()
_cache: dict[str, dict] = {}   # team abbr -> {"state": dict, "ts": float}

# Shared parsed model cache: rebuilt once per data refresh (all teams share it).
_model_cache: dict = {"model": None, "ts": 0.0}


def _ttl(state) -> int:
    return TTL_LIVE if state and state.get("live") else TTL_DEFAULT


def _fresh_model():
    """Return a WorldCupModel, rebuilding from ESPN only when stale."""
    now = time.time()
    if _model_cache["model"] is None or (now - _model_cache["ts"]) > TTL_DEFAULT:
        _model_cache["model"] = build_model(_fetcher)
        _model_cache["ts"] = now
    return _model_cache["model"]


def get_state(team: str) -> dict:
    with _lock:
        entry = _cache.get(team, {"state": None, "ts": 0.0})
        age = time.time() - entry["ts"]
        if entry["state"] is None or age > _ttl(entry["state"]):
            try:
                model = _fresh_model()
                if team not in model.teams:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Unknown team abbreviation: {team!r}. "
                               "Use the all_teams list from any valid team's response.",
                    )
                state = analyse(model, team)
                state["qualification"] = qualification_probability(model, team, _odds)
                state["stale"] = False
                _cache[team] = {"state": state, "ts": time.time()}
            except HTTPException:
                raise
            except Exception as exc:       # keep serving last good copy
                if entry["state"] is not None:
                    entry["state"]["stale"] = True
                    entry["state"]["error"] = str(exc)
                    _cache[team] = entry
                else:
                    raise
        return _cache[team]["state"]


@app.get("/api/state")
def api_state(team: str = "SCO") -> JSONResponse:
    return JSONResponse(get_state(team.upper()))


@app.get("/healthz")
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


# Serve the built React app last, so the API routes above take precedence.
# In dev you run Vite separately (it proxies /api to here), so dist may be absent.
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")

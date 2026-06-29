"""
main.py — FastAPI backend for the World Cup tracker.

  GET /api/state?team=SCO   JSON the React app polls (default team: SCO)
  GET /healthz              liveness
  GET /*                    the built React app (frontend/dist), once it exists

State is cached per team with a short TTL. The model is parsed once per
refresh cycle and shared between analyse() and qualification_probability(),
so ESPN is only hit once regardless of which team is selected.
"""

import copy
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from tracker import (
    Fetcher, WorldCupModel, parse_matches, parse_knockout_matches,
    analyse, tournament_phase,
)
from odds import EloOdds, NeutralOdds
from qualify import qualification_probability
import bracket as kbracket

TTL_DEFAULT = 90      # seconds between refreshes normally
TTL_LIVE = 20         # seconds while the target team's match is live
TITLE_ODDS_TOP = 8    # leaderboard length
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

_fetcher = Fetcher(cache_path="espn_cache.json")
_odds = EloOdds() if os.getenv("ODDS", "elo") == "elo" else NeutralOdds()
_lock = threading.Lock()
_cache: dict[str, dict] = {}   # team abbr -> {"state": dict, "ts": float}

# Shared per-refresh cache: model + prebuilt knockout engine output (all teams
# share it, so ESPN and the Elo provider are hit once regardless of selection).
_model_cache: dict = {"model": None, "knockout": None, "ts": 0.0}


def _refresh_loop() -> None:
    """Warm the model cache immediately on startup, then refresh every TTL_DEFAULT
    seconds in the background so user requests never trigger a cold build."""
    with _lock:
        _fresh_model()
    while True:
        time.sleep(TTL_DEFAULT)
        with _lock:
            _model_cache["ts"] = 0.0  # force rebuild even if within normal TTL
            _cache.clear()            # drop per-team cache so next poll sees fresh data
            try:
                _fresh_model()
            except Exception:
                pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=_refresh_loop, daemon=True).start()
    yield


app = FastAPI(title="World Cup 2026 Tracker", lifespan=lifespan)


def _ttl(state) -> int:
    return TTL_LIVE if state and state.get("live") else TTL_DEFAULT


def _fresh_model():
    """Return a WorldCupModel, rebuilding from ESPN only when stale. Builds the
    knockout engine output on the same cycle so the Elo matchups are fetched
    once per refresh, not per request."""
    now = time.time()
    if _model_cache["model"] is None or (now - _model_cache["ts"]) > TTL_DEFAULT:
        events = _fetcher.all_events()
        model = WorldCupModel(parse_matches(events))
        _model_cache["model"] = model
        _model_cache["knockout"] = _build_knockout(model, events)
        _model_cache["ts"] = now
    return _model_cache["model"]


def _build_knockout(model: WorldCupModel, events: list) -> dict | None:
    """Precompute the bracket, advance distributions and title odds once. Returns
    None until the group stage is complete (knockout panel then shows a
    placeholder)."""
    if tournament_phase(model) != "knockout":
        return None
    km = parse_knockout_matches(events)
    valid = set(model.teams)
    b = kbracket.build_bracket(km, valid)
    adv = kbracket.advance_distributions(b, _odds)
    todds = kbracket.title_odds(b, _odds, adv)
    r32 = {}
    for m in km:
        if m.round == "R32":
            r32[m.home] = m
            r32[m.away] = m
    kdata = {
        "bracket": b,
        "adv": adv,
        "title_odds": todds,
        "default_team": max(todds, key=todds.get) if todds else None,
        "r32": r32,
        "names": {a: model.teams[a].name for a in valid},
    }
    kdata["tree"] = _bracket_tree(kdata)
    return kdata


BRACKET_SLOT_OCCUPANTS = 4  # likely occupants shown per undecided later-round slot


def _bracket_tree(kdata: dict) -> dict:
    """Serialise the whole bracket for the frontend diagram (team-independent).

    R32 slots carry concrete teams plus live score/state from their fixtures;
    later rounds carry the top likely occupants from the advance distribution
    (or the anchored winner once a tie is decided). ``children`` reshapes the
    fixed wiring so the frontend can draw connectors without hardcoding it."""
    b, adv, names, r32 = kdata["bracket"], kdata["adv"], kdata["names"], kdata["r32"]

    children: dict[str, list[list[int]]] = {}
    for (prnd, pidx), kids in kbracket.CHILDREN.items():
        children.setdefault(prnd, [])
        while len(children[prnd]) <= pidx:
            children[prnd].append([])
        children[prnd][pidx] = [cidx for _crnd, cidx in kids]

    slots: dict[str, list[dict]] = {}
    for rnd in kbracket.ROUNDS:
        out = []
        for slot in b.get(rnd, []):
            if rnd == "R32":
                m = r32.get(slot.team_a) or r32.get(slot.team_b)
                r32_dist = adv.get(("R32", slot.index), {})
                r32_top = sorted(r32_dist.items(), key=lambda x: -x[1])[:1]
                out.append({
                    "index": slot.index,
                    "team_a": slot.team_a,
                    "team_b": slot.team_b,
                    "name_a": names.get(slot.team_a, slot.team_a) if slot.team_a else None,
                    "name_b": names.get(slot.team_b, slot.team_b) if slot.team_b else None,
                    "winner": slot.winner,
                    "home_score": m.home_score if m else None,
                    "away_score": m.away_score if m else None,
                    "state": m.state if m else None,
                    "kickoff": m.kickoff if m else None,
                    "adv": [
                        {"abbr": a, "name": names.get(a, a), "p": p}
                        for a, p in r32_top if p > 1e-9
                    ],
                })
            else:
                dist = adv.get((rnd, slot.index), {})
                top = sorted(dist.items(), key=lambda x: -x[1])[:BRACKET_SLOT_OCCUPANTS]
                out.append({
                    "index": slot.index,
                    "winner": slot.winner,
                    "adv": [
                        {"abbr": a, "name": names.get(a, a), "p": p}
                        for a, p in top if p > 1e-9
                    ],
                })
        slots[rnd] = out

    return {"rounds": list(kbracket.ROUNDS), "children": children, "slots": slots}


def _knockout_payload(team: str, kdata: dict | None) -> dict | None:
    """Per-team knockout view: reach probabilities, R32 tie and likely opponents
    per upcoming round. None when the group stage isn't complete."""
    if kdata is None:
        return None
    b, adv, names = kdata["bracket"], kdata["adv"], kdata["names"]
    reach = kbracket.reach_probabilities(b, _odds, team, adv)
    in_bracket = team in kdata["r32"]
    payload = {
        "in_bracket": in_bracket,
        "default_team": kdata["default_team"],
        "reach": reach,
        "r32_tie": None,
        "opponents": {},
        "path": [[s.round, s.index] for s in kbracket.target_path(b, team)],
    }
    if not in_bracket:
        payload["reach"] = {k: 0.0 for k in reach}
        return payload

    m = kdata["r32"][team]
    payload["r32_tie"] = {
        "home": m.home, "away": m.away,
        "home_name": m.home_name, "away_name": m.away_name,
        "home_score": m.home_score, "away_score": m.away_score,
        "state": m.state, "kickoff": m.kickoff, "winner": m.winner,
    }
    for rnd in ("R16", "QF", "SF", "F"):
        if reach.get(rnd, 0.0) <= 1e-9:
            continue
        dist = kbracket.opponent_distribution(b, _odds, team, rnd, adv)
        top = sorted(dist.items(), key=lambda x: -x[1])[:3]
        payload["opponents"][rnd] = [
            {"abbr": a, "name": names.get(a, a), "p": p} for a, p in top if p > 1e-9
        ]
    return payload


def _title_odds_list(kdata: dict | None) -> list | None:
    if kdata is None:
        return None
    names, todds = kdata["names"], kdata["title_odds"]
    top = sorted(todds.items(), key=lambda x: -x[1])[:TITLE_ODDS_TOP]
    return [{"abbr": a, "name": names.get(a, a), "p": p} for a, p in top]


def _forced_kdata(base: dict | None, team: str, result: str) -> dict | None:
    """A knockout dataset with ``team``'s R32 tie forced to win/lose, recomputed.

    Returns None (caller falls back to live odds) when there's no undecided R32
    tie to condition on. Pure and in-memory: clones the bracket, pins the slot
    winner — the same lever the engine already uses for decided ties — then
    recomputes the advance distributions and title odds. Elo matchups are
    memoised in the provider, so no network is hit."""
    if base is None:
        return None
    src = base["bracket"]
    slot = next((s for s in src["R32"] if team in (s.team_a, s.team_b)), None)
    if slot is None or slot.winner is not None:
        return None
    opp = slot.team_b if slot.team_a == team else slot.team_a
    if result == "lose" and opp is None:
        return None  # bye — can't lose to nobody

    b2 = copy.deepcopy(src)
    s2 = b2["R32"][slot.index]
    s2.winner = team if result == "win" else opp
    adv2 = kbracket.advance_distributions(b2, _odds)
    todds2 = kbracket.title_odds(b2, _odds, adv2)
    forced = {
        **base,
        "bracket": b2,
        "adv": adv2,
        "title_odds": todds2,
        "default_team": max(todds2, key=todds2.get) if todds2 else None,
    }
    forced["tree"] = _bracket_tree(forced)
    return forced


def get_state(team: str, whatif: str | None = None) -> dict:
    key = f"{team}|{whatif or ''}"
    with _lock:
        entry = _cache.get(key, {"state": None, "ts": 0.0})
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
                kdata = _model_cache["knockout"]
                if whatif:
                    kdata = _forced_kdata(kdata, team, whatif) or kdata
                state["knockout"] = _knockout_payload(team, kdata)
                state["title_odds"] = _title_odds_list(kdata)
                state["bracket"] = kdata["tree"] if kdata else None
                state["whatif"] = whatif
                state["stale"] = False
                _cache[key] = {"state": state, "ts": time.time()}
            except HTTPException:
                raise
            except Exception as exc:       # keep serving last good copy
                if entry["state"] is not None:
                    entry["state"]["stale"] = True
                    entry["state"]["error"] = str(exc)
                    _cache[key] = entry
                else:
                    raise
        return _cache[key]["state"]


@app.get("/api/state")
def api_state(team: str = "SCO", whatif: str | None = None) -> JSONResponse:
    if whatif not in ("win", "lose"):
        whatif = None
    return JSONResponse(get_state(team.upper(), whatif))


@app.get("/healthz")
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


# Serve the built React app last, so the API routes above take precedence.
# In dev you run Vite separately (it proxies /api to here), so dist may be absent.
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")

"""
tracker.py — World Cup 2026 data layer + qualification logic.

No third-party deps (stdlib only). The FastAPI app imports WorldCupModel and
analyse(). All numbers are computed from completed match results pulled from
ESPN's free, unauthenticated scoreboard endpoint, so the third-place table and
the FIFA tie-breakers are derived here rather than trusted from an opaque feed.

Tie-breakers implemented:
  Group order  : points -> head-to-head(points, GD, GF) -> overall GD -> overall GF
  Best thirds  : points -> overall GD -> overall GF
(The final FIFA steps — fair-play/conduct score, then world ranking — are not in
 the free feed; they're flagged in the output and only ever matter on an exact
 points+GD+GF tie, which is rare.)
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta

# --- tournament constants -------------------------------------------------

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)
GROUP_STAGE_START = date(2026, 6, 11)
GROUP_STAGE_END = date(2026, 6, 27)
THIRDS_ADVANCING = 8          # best 8 of 12 third-placed teams reach the Round of 32
ASSUMED_MARGIN = 1            # goal margin used in hypothetical win/loss scenarios
HTTP_TIMEOUT = 8              # seconds

QUALIFY_OUTCOMES = ("win_group", "runner_up", "third_in", "third_out", "fourth_out")


def group_stage_dates() -> list[str]:
    days, d = [], GROUP_STAGE_START
    while d <= GROUP_STAGE_END:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return days


# --- parsed records -------------------------------------------------------

@dataclass
class Match:
    group: str
    home: str
    away: str
    home_score: int | None
    away_score: int | None
    state: str                # "pre" | "in" | "post"
    completed: bool
    kickoff: str              # ISO timestamp
    home_name: str = ""
    away_name: str = ""

    @property
    def finished(self) -> bool:
        return self.completed and self.home_score is not None


@dataclass
class TeamRow:
    abbr: str
    name: str
    group: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0
    # opponent -> (goals_for, goals_against), used for head-to-head
    h2h: dict = field(default_factory=dict)

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    def as_dict(self) -> dict:
        return {
            "abbr": self.abbr, "name": self.name, "group": self.group,
            "played": self.played, "won": self.won, "drawn": self.drawn,
            "lost": self.lost, "gf": self.gf, "ga": self.ga,
            "gd": self.gd, "points": self.points,
        }


# --- fetching -------------------------------------------------------------

class Fetcher:
    """Pulls the scoreboard one day at a time and caches finished days forever
    (a completed day never changes), so each refresh only re-hits ESPN for
    today's date. Keeps a last-good copy on disk to survive feed blips."""

    def __init__(self, cache_path: str = "espn_cache.json"):
        self.cache_path = cache_path
        self._day_cache: dict[str, list] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.cache_path) as fh:
                self._day_cache = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            self._day_cache = {}

    def _save(self) -> None:
        try:
            with open(self.cache_path, "w") as fh:
                json.dump(self._day_cache, fh)
        except OSError:
            pass  # cache is a nicety, not a requirement

    def _fetch_day(self, day: str) -> list:
        url = f"{ESPN_SCOREBOARD}?dates={day}&limit=200"
        req = urllib.request.Request(url, headers={"User-Agent": "wc-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("events", [])

    def all_events(self) -> list:
        """Return raw ESPN events for the whole group stage, refreshing only
        days that aren't fully finished yet."""
        today = date.today().strftime("%Y%m%d")
        events: list = []
        for day in group_stage_dates():
            cached = self._day_cache.get(day)
            day_is_past_and_done = cached is not None and day < today and _all_done(cached)
            if day_is_past_and_done:
                events.extend(cached)
                continue
            try:
                fresh = self._fetch_day(day)
                self._day_cache[day] = fresh
                events.extend(fresh)
            except Exception:
                if cached is not None:        # fall back to last good copy
                    events.extend(cached)
        self._save()
        return events


def _all_done(events: list) -> bool:
    for ev in events:
        comp = ev["competitions"][0]
        if not comp["status"]["type"]["completed"]:
            return False
    return True


def _parse_group(comp: dict) -> str | None:
    note = comp.get("altGameNote") or ""
    if "Group" in note:
        return note.strip().split("Group")[-1].strip()[:1]
    return None


def parse_matches(events: list) -> list[Match]:
    matches: list[Match] = []
    for ev in events:
        comp = ev["competitions"][0]
        group = _parse_group(comp)
        if not group:
            continue  # knockout or non-group fixture
        sides = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in sides or "away" not in sides:
            continue
        home, away = sides["home"], sides["away"]
        state = comp["status"]["type"]["state"]
        completed = comp["status"]["type"]["completed"]

        def score(side):
            try:
                return int(side.get("score"))
            except (TypeError, ValueError):
                return None

        matches.append(Match(
            group=group,
            home=home["team"]["abbreviation"],
            away=away["team"]["abbreviation"],
            home_name=home["team"].get("shortDisplayName", home["team"]["abbreviation"]),
            away_name=away["team"].get("shortDisplayName", away["team"]["abbreviation"]),
            home_score=score(home),
            away_score=score(away),
            state=state,
            completed=completed,
            kickoff=ev.get("date", ""),
        ))
    return matches


# --- model ----------------------------------------------------------------

class WorldCupModel:
    def __init__(self, matches: list[Match]):
        self.matches = matches
        self.teams: dict[str, TeamRow] = {}
        self._build()

    def _team(self, abbr: str, name: str, group: str) -> TeamRow:
        if abbr not in self.teams:
            self.teams[abbr] = TeamRow(abbr=abbr, name=name, group=group)
        return self.teams[abbr]

    def _build(self) -> None:
        for m in self.matches:
            h = self._team(m.home, m.home_name, m.group)
            a = self._team(m.away, m.away_name, m.group)
            if not m.finished:
                continue
            hs, as_ = m.home_score, m.away_score
            h.played += 1; a.played += 1
            h.gf += hs; h.ga += as_
            a.gf += as_; a.ga += hs
            h.h2h[m.away] = (hs, as_)
            a.h2h[m.home] = (as_, hs)
            if hs > as_:
                h.won += 1; a.lost += 1
            elif hs < as_:
                a.won += 1; h.lost += 1
            else:
                h.drawn += 1; a.drawn += 1

    # ---- ordering ----

    def groups(self) -> dict[str, list[TeamRow]]:
        out: dict[str, list[TeamRow]] = {}
        for t in self.teams.values():
            out.setdefault(t.group, []).append(t)
        return {g: self._order_group(rows) for g, rows in sorted(out.items())}

    @staticmethod
    def _order_group(rows: list[TeamRow]) -> list[TeamRow]:
        # First pass: points only, then resolve point-ties by head-to-head.
        def sort_key(t: TeamRow):
            return (t.points, t.gd, t.gf)
        rows = sorted(rows, key=sort_key, reverse=True)

        # Re-rank any block of teams level on points using H2H mini-table,
        # falling back to overall GD/GF.
        ordered: list[TeamRow] = []
        i = 0
        while i < len(rows):
            j = i
            while j + 1 < len(rows) and rows[j + 1].points == rows[i].points:
                j += 1
            block = rows[i:j + 1]
            if len(block) > 1:
                block = sorted(block, key=lambda t: _h2h_key(t, block), reverse=True)
            ordered.extend(block)
            i = j + 1
        return ordered

    def group_complete(self, group: str) -> bool:
        return all(m.finished for m in self.matches if m.group == group)

    def third_placed(self, exclude: set[str] | None = None) -> list[dict]:
        """Ranked list of every group's 3rd-placed team."""
        exclude = exclude or set()
        thirds = []
        for g, rows in self.groups().items():
            if g in exclude or len(rows) < 3:
                continue
            t = rows[2]
            d = t.as_dict()
            d["group_complete"] = self.group_complete(g)
            thirds.append(d)
        thirds.sort(key=lambda d: (d["points"], d["gd"], d["gf"]), reverse=True)
        return thirds


def _h2h_key(team: TeamRow, block: list[TeamRow]):
    """Mini-table among the tied teams: (h2h pts, h2h gd, h2h gf, overall gd, overall gf)."""
    others = {t.abbr for t in block} - {team.abbr}
    pts = gd = gf = 0
    for opp in others:
        if opp in team.h2h:
            f, ag = team.h2h[opp]
            gf += f; gd += (f - ag)
            pts += 3 if f > ag else (1 if f == ag else 0)
    return (pts, gd, gf, team.gd, team.gf)


# --- shared classifier (used by both Step 1 scenarios and Step 2 simulation) ---

def team_qualifies(model: WorldCupModel, target: str) -> str:
    """Classify target's fate assuming all group games in model are final.

    Returns one of QUALIFY_OUTCOMES. Safe to call on provisional models
    (groups still in progress); callers decide how much to trust the result.
    """
    group = model.teams[target].group
    order = model.groups()[group]
    pos = [t.abbr for t in order].index(target) + 1
    if pos == 1:
        return "win_group"
    if pos == 2:
        return "runner_up"
    if pos == 3:
        thirds = model.third_placed()
        rank = next(i for i, t in enumerate(thirds) if t["abbr"] == target) + 1
        return "third_in" if rank <= THIRDS_ADVANCING else "third_out"
    return "fourth_out"


def with_result(model: WorldCupModel, match: Match, home_goals: int, away_goals: int) -> WorldCupModel:
    """Return a new WorldCupModel with match resolved to the given score."""
    new_matches = []
    for m in model.matches:
        if id(m) == id(match):
            new_matches.append(Match(
                group=m.group, home=m.home, away=m.away,
                home_score=home_goals, away_score=away_goals,
                state="post", completed=True,
                kickoff=m.kickoff, home_name=m.home_name, away_name=m.away_name,
            ))
        else:
            new_matches.append(m)
    return WorldCupModel(new_matches)


# --- scenario helpers --------------------------------------------------------

def _hypothetical_scores(match: Match, target: str) -> dict[str, tuple[int, int]]:
    """Return (home_goals, away_goals) for win/draw/loss from target's perspective."""
    target_is_home = match.home == target
    if target_is_home:
        return {
            "win":  (ASSUMED_MARGIN, 0),
            "draw": (1, 1),
            "loss": (0, ASSUMED_MARGIN),
        }
    return {
        "win":  (0, ASSUMED_MARGIN),
        "draw": (1, 1),
        "loss": (ASSUMED_MARGIN, 0),
    }


def _third_rank_if_applicable(model: WorldCupModel, target: str) -> int | None:
    """Return target's 1-based rank among thirds only when target is currently 3rd."""
    group = model.teams[target].group
    order = model.groups().get(group, [])
    if not order or [t.abbr for t in order].index(target) + 1 != 3:
        return None
    thirds = model.third_placed()
    try:
        return next(i for i, t in enumerate(thirds) if t["abbr"] == target) + 1
    except StopIteration:
        return None


def _all_same_qualified(outcomes: dict) -> bool:
    qualified = {"win_group", "runner_up", "third_in"}
    return all(o["verdict"] in qualified for o in outcomes.values())


def _all_eliminated(outcomes: dict) -> bool:
    eliminated = {"third_out", "fourth_out"}
    return all(o["verdict"] in eliminated for o in outcomes.values())


def target_scenarios(model: WorldCupModel, target: str) -> dict:
    """Return scenario structure for target team — works for all four states:
    already through, already out, pending match, or fully played."""
    group = model.teams[target].group
    remaining = [
        m for m in model.matches
        if not m.finished and m.group == group and target in (m.home, m.away)
    ]

    if not remaining:
        return {
            "phase": "final",
            "verdict": team_qualifies(model, target),
            "third_rank": _third_rank_if_applicable(model, target),
        }

    outcomes = {}
    for label, (hg, ag) in _hypothetical_scores(remaining[0], target).items():
        hypo = with_result(model, remaining[0], hg, ag)
        outcomes[label] = {
            "verdict": team_qualifies(hypo, target),
            "third_rank": _third_rank_if_applicable(hypo, target),
            "assumed": label in ("win", "loss"),
        }

    return {
        "phase": "pending",
        "remaining": _match_view(remaining[0]),
        "outcomes": outcomes,
        "clinched": _all_same_qualified(outcomes),
        "dead": _all_eliminated(outcomes),
    }


# --- main analysis entry point -----------------------------------------------

def analyse(model: WorldCupModel, target: str) -> dict:
    if target not in model.teams:
        raise KeyError(f"Unknown team abbreviation: {target!r}")

    group = model.teams[target].group
    target_match = next(
        (m for m in model.matches
         if not m.finished and m.group == group and target in (m.home, m.away)),
        None,
    )
    other_match = next(
        (m for m in model.matches
         if m.group == group and target not in (m.home, m.away)),
        None,
    )
    live = any(
        m.state == "in" and m.group == group and target in (m.home, m.away)
        for m in model.matches
    )

    return {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "live": live,
        "target": target,
        "group": group,
        "group_table": [t.as_dict() for t in model.groups().get(group, [])],
        "target_match": _match_view(target_match),
        "other_group_match": _match_view(other_match),
        "scenarios": target_scenarios(model, target),
        "live_thirds": model.third_placed(),
        "cutoff": THIRDS_ADVANCING,
        "all_teams": sorted(
            [{"abbr": t.abbr, "name": t.name, "group": t.group}
             for t in model.teams.values()],
            key=lambda t: (t["group"], t["abbr"]),
        ),
        "note_tiebreak": (
            "Ranking uses points, goal difference, then goals scored. "
            "FIFA's further tie-breakers (fair-play score, then world ranking) "
            "aren't in the free feed and only bite on an exact tie."
        ),
    }


def _match_view(m: Match | None) -> dict | None:
    if not m:
        return None
    return {
        "home": m.home, "away": m.away,
        "home_name": m.home_name, "away_name": m.away_name,
        "home_score": m.home_score, "away_score": m.away_score,
        "state": m.state, "kickoff": m.kickoff,
    }


def build_model(fetcher: Fetcher) -> WorldCupModel:
    return WorldCupModel(parse_matches(fetcher.all_events()))


def build_state(fetcher: Fetcher, target: str) -> dict:
    return analyse(build_model(fetcher), target)

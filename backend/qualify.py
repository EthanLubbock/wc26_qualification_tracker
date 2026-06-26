"""
qualify.py — Exact qualification probability + "important games" requirements.

Replaces the old Monte Carlo (simulate.py). Group-stage groups are independent
(no cross-group matches), so qualification decomposes exactly:

    P(qualify) = P(win group) + P(runner-up) + P(3rd AND among the best-8 thirds)

The target advances as a third iff at most (THIRDS_ADVANCING - 1) of the other
groups' thirds rank above it — equivalently at least `k` of the other groups
produce a third finishing *below* the target. Each other group is an independent
Bernoulli event with probability p_i, computed by enumerating that group's
remaining matches' scorelines (Poisson-weighted from Elo supremacy). "At least k
successes" over independent p_i is a Poisson-binomial tail, computed exactly.

This makes irrelevant results disappear: a group whose third can no longer change
relative to the target has p_i = 0 or 1 and is never listed as a requirement.

No network calls here — odds are fetched per fixture via the passed OddsProvider,
which caches. No global Monte Carlo, so output is exact and deterministic.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from itertools import product

from tracker import Match, WorldCupModel, THIRDS_ADVANCING, QUALIFY_OUTCOMES

MEAN_TOTAL_GOALS = 2.6     # tournament average; tunable (matches old goal model)
GOAL_CAP = 6               # per-side goal cap for the per-match distribution
MAX_ENUM_COMBOS = 50_000   # above this, sample a group instead of enumerating
SAMPLE_N = 4000            # samples used in the (rare) early-tournament fallback
_EPS = 1e-9
_TIE_WARN = 0.01           # exact-tie mass that triggers the fair-play warning


# --- per-match scoreline distribution ---------------------------------------

def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _match_scoreline_dist(odds, m: Match, cap: int = GOAL_CAP) -> dict[tuple[int, int], float]:
    """{(home_goals, away_goals): probability} from independent Poisson means
    implied by Elo supremacy, capped at `cap` per side and renormalised."""
    p = odds.match_probabilities(m.home, m.away)
    S = p["supremacy"]
    lam_home = max(0.05, (MEAN_TOTAL_GOALS + S) / 2)
    lam_away = max(0.05, (MEAN_TOTAL_GOALS - S) / 2)
    home = [_poisson_pmf(k, lam_home) for k in range(cap + 1)]
    away = [_poisson_pmf(k, lam_away) for k in range(cap + 1)]
    dist: dict[tuple[int, int], float] = {}
    total = 0.0
    for i in range(cap + 1):
        for j in range(cap + 1):
            w = home[i] * away[j]
            dist[(i, j)] = w
            total += w
    return {k: v / total for k, v in dist.items()}


# --- enumeration over a set of remaining matches ----------------------------

def _enumerate_combos(rem: list[Match], odds, callback) -> None:
    """Call callback(scorelines, probability) for each joint outcome of `rem`.

    Enumerates exactly when the combo space is small; otherwise samples with a
    fixed seed (only reachable very early in the tournament, when third-place
    requirements aren't meaningful yet anyway)."""
    if not rem:
        callback((), 1.0)
        return
    dists = [_match_scoreline_dist(odds, m) for m in rem]
    count = math.prod(len(d) for d in dists)
    if count <= MAX_ENUM_COMBOS:
        items = [list(d.items()) for d in dists]
        for combo in product(*items):
            scs = tuple(c[0] for c in combo)
            prob = 1.0
            for c in combo:
                prob *= c[1]
            callback(scs, prob)
    else:
        rng = random.Random(12345)
        pops = [list(d.keys()) for d in dists]
        wts = [list(d.values()) for d in dists]
        w = 1.0 / SAMPLE_N
        for _ in range(SAMPLE_N):
            scs = tuple(rng.choices(pop, weights=ww, k=1)[0] for pop, ww in zip(pops, wts))
            callback(scs, w)


def _resolve_rows(fin: list[Match], rem: list[Match], scs: tuple, group: str) -> list:
    """Ordered rows for `group` after applying scorelines `scs` to `rem`."""
    ms = list(fin)
    for m, (hg, ag) in zip(rem, scs):
        ms.append(Match(
            group=m.group, home=m.home, away=m.away,
            home_score=hg, away_score=ag, state="post", completed=True,
            kickoff=m.kickoff, home_name=m.home_name, away_name=m.away_name,
        ))
    return WorldCupModel(ms).groups().get(group, [])


def _third_record(fin, rem, scs, group) -> tuple[int, int, int] | None:
    rows = _resolve_rows(fin, rem, scs, group)
    if len(rows) < 3:
        return None
    t = rows[2]
    return (t.points, t.gd, t.gf)


# --- per-group third-record distribution ------------------------------------

def _group_matches(model: WorldCupModel, group: str):
    gm = [m for m in model.matches if m.group == group]
    return [m for m in gm if m.finished], [m for m in gm if not m.finished]


def _third_record_dist(model: WorldCupModel, group: str, odds):
    """Distribution {(points, gd, gf): probability} of `group`'s eventual third,
    plus the group's remaining matches (for descriptions)."""
    fin, rem = _group_matches(model, group)
    out: dict[tuple[int, int, int], float] = defaultdict(float)

    def cb(scs, prob):
        rec = _third_record(fin, rem, scs, group)
        if rec is not None:
            out[rec] += prob

    _enumerate_combos(rem, odds, cb)
    return dict(out), rem


def _p_below(dist: dict, R: tuple) -> float:
    return sum(p for rec, p in dist.items() if rec < R)


def _tie_mass(dist: dict, R: tuple) -> float:
    return sum(p for rec, p in dist.items() if rec == R)


# --- target's own group: position distribution ------------------------------

def _own_distribution(model: WorldCupModel, target: str, odds):
    """Returns dict with p1/p2/p4, a {record: prob} map of 3rd-place branches,
    and whether the target still has matches to play."""
    group = model.teams[target].group
    fin, rem = _group_matches(model, group)
    res = {"p1": 0.0, "p2": 0.0, "p4": 0.0, "thirds": defaultdict(float)}

    def cb(scs, prob):
        rows = _resolve_rows(fin, rem, scs, group)
        pos = [t.abbr for t in rows].index(target) + 1
        if pos == 1:
            res["p1"] += prob
        elif pos == 2:
            res["p2"] += prob
        elif pos == 4:
            res["p4"] += prob
        else:
            t = rows[2]
            res["thirds"][(t.points, t.gd, t.gf)] += prob

    _enumerate_combos(rem, odds, cb)
    res["thirds"] = dict(res["thirds"])
    res["still_playing"] = bool(rem)
    return res


# --- Poisson-binomial tail --------------------------------------------------

def _pb_at_least(probs: list[float], k: int) -> float:
    """P(at least k successes) over independent Bernoulli trials `probs`."""
    if k <= 0:
        return 1.0
    n = len(probs)
    if k > n:
        return 0.0
    dp = [1.0] + [0.0] * n
    cur = 0
    for p in probs:
        cur += 1
        for j in range(cur, 0, -1):
            dp[j] = dp[j] * (1 - p) + dp[j - 1] * p
        dp[0] *= (1 - p)
    return sum(dp[k:cur + 1])


# --- requirement descriptions -----------------------------------------------

def _run_phrase(lo: int, hi: int, home: str, away: str, cap: int) -> str:
    """Describe a contiguous run of favourable home-minus-away margins [lo, hi]."""
    unb_lo, unb_hi = lo == -cap, hi == cap
    if lo >= 1:                                  # home must win
        if unb_hi:
            return f"{home} to win" if lo == 1 else f"{home} to win by at least {lo} goals"
        if lo == hi:
            return f"{home} to win by exactly {lo}"
        return f"{home} to win by {lo}–{hi} goals"
    if hi <= -1:                                 # home must lose
        a, b = -hi, -lo
        if unb_lo:
            return f"{away} to win" if a == 1 else f"{home} to lose by at least {a} goals"
        if a == b:
            return f"{home} to lose by exactly {a}"
        return f"{home} to lose by {a}–{b} goals"
    # run spans the draw (lo <= 0 <= hi)
    if lo == 0 and hi == 0:
        return f"{home} v {away} to be a draw"
    if unb_lo and unb_hi:
        return "any result"
    if unb_hi:                                   # m >= lo, lo <= 0
        if lo == 0:
            return f"{home} to win or draw"
        return f"{home} not to lose by more than {-lo} goals"
    if unb_lo:                                   # m <= hi, hi >= 0
        if hi == 0:
            return f"{home} to lose or draw"
        return f"{home} to win by no more than {hi} goals"
    parts = []
    if lo < 0:
        parts.append(f"{away} win by up to {-lo}")
    parts.append("draw")
    if hi > 0:
        parts.append(f"{home} win by up to {hi}")
    return f"{home} v {away}: " + ", ".join(parts)


def _describe_single_match(home: str, away: str, fav_margins: set[int], cap: int) -> str:
    full = set(range(-cap, cap + 1))
    if not fav_margins or fav_margins == full:
        return f"{home} v {away} to go your way"
    fav = sorted(fav_margins)
    runs = []
    start = prev = fav[0]
    for x in fav[1:]:
        if x == prev + 1:
            prev = x
        else:
            runs.append((start, prev))
            start = prev = x
    runs.append((start, prev))
    return " or ".join(_run_phrase(lo, hi, home, away, cap) for lo, hi in runs)


def _favourable_margins(fin, rem, fixed_others, var_idx, group, R, odds) -> set[int]:
    """Favourable home-minus-away margins for match `var_idx` in `rem`, holding
    the other remaining matches at `fixed_others` (a tuple of scorelines)."""
    m = rem[var_idx]
    dist = _match_scoreline_dist(odds, m)
    fav = defaultdict(float)
    tot = defaultdict(float)
    for (hg, ag), p in dist.items():
        scs = list(fixed_others)
        scs.insert(var_idx, (hg, ag))
        rec = _third_record(fin, rem, tuple(scs), group)
        margin = hg - ag
        tot[margin] += p
        if rec is not None and rec < R:
            fav[margin] += p
    return {mg for mg in tot if tot[mg] > 0 and fav[mg] / tot[mg] > 0.5}


def _describe_group_requirement(model, group, rem, R, odds) -> str:
    fin, _ = _group_matches(model, group)
    names = lambda m: (m.home_name or m.home, m.away_name or m.away)

    if len(rem) == 1:
        home, away = names(rem[0])
        favm = _favourable_margins(fin, rem, (), 0, group, R, odds)
        return _describe_single_match(home, away, favm, GOAL_CAP)

    if len(rem) == 2:
        # Detect whether favourability hinges on just one of the two matches.
        d0 = _match_scoreline_dist(odds, rem[0])
        d1 = _match_scoreline_dist(odds, rem[1])
        modal0 = max(d0, key=d0.get)
        modal1 = max(d1, key=d1.get)
        grid = {}
        for s0 in d0:
            for s1 in d1:
                rec = _third_record(fin, rem, (s0, s1), group)
                grid[(s0, s1)] = rec is not None and rec < R
        m0_matters = any(grid[(s0, s1)] != grid[(s0b, s1)]
                         for s1 in d1 for s0 in d0 for s0b in d0)
        m1_matters = any(grid[(s0, s1)] != grid[(s0, s1b)]
                         for s0 in d0 for s1 in d1 for s1b in d1)
        if m0_matters and not m1_matters:
            home, away = names(rem[0])
            favm = _favourable_margins(fin, rem, (modal1,), 0, group, R, odds)
            return _describe_single_match(home, away, favm, GOAL_CAP)
        if m1_matters and not m0_matters:
            home, away = names(rem[1])
            favm = _favourable_margins(fin, rem, (modal0,), 1, group, R, odds)
            return _describe_single_match(home, away, favm, GOAL_CAP)
        h0, a0 = names(rem[0])
        h1, a1 = names(rem[1])
        return f"Results in Group {group} ({h0} v {a0} and {h1} v {a1}) to go your way"

    return f"Results in Group {group} to go your way"


def _match_meta(m: Match) -> dict:
    return {
        "group": m.group, "home": m.home, "away": m.away,
        "home_name": m.home_name or m.home, "away_name": m.away_name or m.away,
        "kickoff": m.kickoff,
    }


# --- public entry point -----------------------------------------------------

def qualification_probability(model: WorldCupModel, target: str, odds) -> dict:
    """Exact P(qualify) and per-position buckets for `target`, plus a BBC-style
    `requirements` structure naming the pivotal other-group games.

    Returns the QUALIFY_OUTCOMES keys, `qualify` (overall), and `requirements`
    (or None when the target has no live third-place decision)."""
    group = model.teams[target].group
    own = _own_distribution(model, target, odds)
    other_groups = [g for g in model.groups() if g != group]

    other_dists: dict[str, dict] = {}
    other_rem: dict[str, list] = {}
    for g in other_groups:
        d, rem = _third_record_dist(model, g, odds)
        other_dists[g] = d
        other_rem[g] = rem

    # Need at least k of the other thirds below the target to make the top 8.
    k = max(0, len(other_groups) - (THIRDS_ADVANCING - 1))

    third_in = 0.0
    for R, probR in own["thirds"].items():
        contested, settled_below = [], 0
        for g in other_groups:
            pi = _p_below(other_dists[g], R)
            if pi >= 1 - _EPS:
                settled_below += 1
            elif pi > _EPS:
                contested.append(pi)
        need = max(0, k - settled_below)
        third_in += probR * _pb_at_least(contested, need)

    p3_total = sum(own["thirds"].values())
    buckets = {
        "win_group": own["p1"],
        "runner_up": own["p2"],
        "third_in": third_in,
        "third_out": max(0.0, p3_total - third_in),
        "fourth_out": own["p4"],
    }
    buckets["qualify"] = own["p1"] + own["p2"] + third_in
    buckets["requirements"] = _requirements(
        model, target, own, other_groups, other_dists, other_rem, k, odds
    )
    return buckets


def _representative_record(thirds: dict) -> tuple:
    """Probability-weighted median 3rd-place record. For a team that has finished
    there's a single branch (exact); for a still-playing team this gives a typical
    "if you finish 3rd" record rather than the luckiest (modal) one."""
    items = sorted(thirds.items())          # ascending by (points, gd, gf)
    half = sum(p for _, p in items) / 2
    acc = 0.0
    for rec, p in items:
        acc += p
        if acc >= half:
            return rec
    return items[-1][0]


def _requirements(model, target, own, other_groups, other_dists, other_rem, k, odds):
    """Build the requirements view at the target's representative 3rd-place record."""
    if not own["thirds"]:
        return None
    R = _representative_record(own["thirds"])

    settled_below, tie_mass = 0, 0.0
    groups = []
    for g in other_groups:
        d = other_dists[g]
        tie_mass += _tie_mass(d, R)
        pi = _p_below(d, R)
        if pi >= 1 - _EPS:
            settled_below += 1
        elif pi > _EPS:
            rem = other_rem[g]
            groups.append({
                "group": g,
                "probability": pi,
                "description": _describe_group_requirement(model, g, rem, R, odds),
                "matches": [_match_meta(m) for m in rem],
            })
    groups.sort(key=lambda c: c["probability"], reverse=True)
    need = max(0, k - settled_below)
    if need > len(groups):
        # Even if every contested result goes the target's way, it still can't
        # reach enough "below" thirds to make the top 8 — path is impossible.
        return None
    return {
        "need": need,
        "settled_favourable": settled_below,
        "conditional": own["still_playing"],
        "tie_warning": tie_mass > _TIE_WARN,
        "groups": groups,
    }

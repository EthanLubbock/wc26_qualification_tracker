"""
simulate.py — Monte Carlo qualification probability.

Simulates unplayed group-stage matches using Poisson-distributed scorelines
derived from Elo supremacy. Calls tracker.team_qualifies() on each simulated
world to tally outcome frequencies for the target team.

Performance note: each iteration rebuilds a WorldCupModel from scratch. This
is acceptable for n=2000-5000 on modern hardware; for a Raspberry Pi 3B+ run
the Pi performance check (Checkpoint 2) and reduce DEFAULT_SAMPLES if needed.
A dict-based scorer that avoids rebuilding the model would be the next
optimisation step if latency becomes a problem.
"""

from __future__ import annotations

import math
import random
from collections import Counter

from tracker import Match, WorldCupModel, team_qualifies, QUALIFY_OUTCOMES

MEAN_TOTAL_GOALS = 2.6   # tournament average; tunable
DEFAULT_SAMPLES = 5000
_QUALIFY_SET = {"win_group", "runner_up", "third_in"}


def _outcome_label(hg: int, ag: int, home: str, away: str,
                   home_name: str | None, away_name: str | None,
                   target: str) -> str:
    """Short result label, framed from target's perspective when involved."""
    hn = home_name or home
    an = away_name or away
    if target in (home, away):
        if hg == ag:
            return "draw"
        return "win" if (hg > ag) == (target == home) else "lose"
    if hg > ag:
        return f"{hn} win"
    if hg < ag:
        return f"{an} win"
    return "draw"


def _third_place_path_matches(
    model: WorldCupModel, target: str, target_group: str, unplayed: list[Match]
) -> list[Match]:
    """For a team that has finished playing, return the most impactful unplayed
    other-group matches for third-place qualification path tracking.

    Only applies when the target is currently 3rd in their group. Picks the
    two other groups whose 3rd-placed teams are closest (in points) to the
    target — the groups most likely to change their rank among thirds.
    """
    group_rows = model.groups().get(target_group, [])
    target_idx = next((i for i, t in enumerate(group_rows) if t.abbr == target), None)
    if target_idx != 2:
        return []  # not 3rd — qualifies directly or can't qualify via thirds

    target_pts = group_rows[2].points

    # Gather unplayed matches keyed by group
    other_by_group: dict[str, list[Match]] = {}
    for m in unplayed:
        if m.group != target_group:
            other_by_group.setdefault(m.group, []).append(m)

    if not other_by_group:
        return []

    # Score relevance: groups whose 3rd can still affect whether target makes top 8.
    # A group's 3rd is relevant if their max achievable points >= target's points.
    scored: list[tuple[int, str, list[Match]]] = []
    for group_name, matches in other_by_group.items():
        rows = model.groups().get(group_name, [])
        if len(rows) < 3:
            continue
        third = rows[2]
        max_pts = third.points + 3 * len(matches)
        if max_pts < target_pts:
            continue  # can never reach target — irrelevant
        closeness = -abs(third.points - target_pts)
        scored.append((closeness, group_name, matches))

    scored.sort(key=lambda x: x[0], reverse=True)
    result: list[Match] = []
    for _, _, matches in scored[:2]:   # at most 2 groups → ≤4 matches → 3^4=81 combos
        result.extend(matches)
    return result


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson(lam) using Knuth's algorithm. Pure stdlib."""
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        p *= random.random()
        k += 1
    return k - 1


def _sample_scoreline(p: dict) -> tuple[int, int]:
    """Return (home_goals, away_goals) sampled from Poisson means implied by supremacy."""
    S = p["supremacy"]
    lam_home = max(0.05, (MEAN_TOTAL_GOALS + S) / 2)
    lam_away = max(0.05, (MEAN_TOTAL_GOALS - S) / 2)
    return _poisson_sample(lam_home), _poisson_sample(lam_away)


def _apply_all(
    model: WorldCupModel,
    unplayed: list[Match],
    results: dict[int, tuple[int, int]],
) -> WorldCupModel:
    """Return a new WorldCupModel with all unplayed matches resolved to sampled scores."""
    unplayed_ids = {id(m) for m in unplayed}
    new_matches = []
    for m in model.matches:
        if id(m) in unplayed_ids:
            hg, ag = results[id(m)]
            new_matches.append(Match(
                group=m.group, home=m.home, away=m.away,
                home_score=hg, away_score=ag,
                state="post", completed=True,
                kickoff=m.kickoff, home_name=m.home_name, away_name=m.away_name,
            ))
        else:
            new_matches.append(m)
    return WorldCupModel(new_matches)


def qualification_probability(
    model: WorldCupModel,
    target: str,
    odds,
    n: int = DEFAULT_SAMPLES,
    collect=None,
) -> dict:
    """Estimate P(qualify) and bucket probabilities for target via Monte Carlo.

    Args:
        model:   Current WorldCupModel (finished + unplayed matches).
        target:  Team abbreviation to classify.
        odds:    OddsProvider instance (pre-warmed; never hits network inside the loop).
        n:       Number of simulations.
        collect: Optional callback(sim_model, target) called each iteration.
                 Reserved for future R32 opponent-prediction extension; pass None.

    Returns dict with QUALIFY_OUTCOMES keys + "qualify" (overall) + "samples".
    """
    unplayed = [m for m in model.matches if not m.finished]
    # Pre-fetch all odds ONCE outside the loop — must never hit network inside.
    probs = {id(m): odds.match_probabilities(m.home, m.away) for m in unplayed}

    # Determine which matches to track for path analysis.
    # Teams still playing → own group matches.
    # Teams that have finished → most impactful other-group matches (third-place race).
    target_group = model.teams[target].group
    group_unplayed = sorted(
        [m for m in unplayed if m.group == target_group],
        key=lambda m: (0 if target in (m.home, m.away) else 1),
    )
    path_matches = group_unplayed or _third_place_path_matches(
        model, target, target_group, unplayed
    )

    counts: Counter = Counter()
    path_counts: Counter = Counter()
    for _ in range(n):
        results = {id(m): _sample_scoreline(probs[id(m)]) for m in unplayed}
        sim = _apply_all(model, unplayed, results)
        outcome = team_qualifies(sim, target)
        counts[outcome] += 1
        if outcome in _QUALIFY_SET and path_matches:
            path_key = tuple(
                _outcome_label(
                    results[id(m)][0], results[id(m)][1],
                    m.home, m.away, m.home_name, m.away_name,
                    target,
                )
                for m in path_matches
            )
            path_counts[path_key] += 1
        if collect is not None:
            collect(sim, target)

    total = n
    buckets = {k: counts.get(k, 0) / total for k in QUALIFY_OUTCOMES}
    buckets["qualify"] = (
        counts.get("win_group", 0) +
        counts.get("runner_up", 0) +
        counts.get("third_in", 0)
    ) / total
    buckets["samples"] = total

    # Top qualifying paths: each step is one tracked match result.
    match_meta = [
        {
            "group": m.group,
            "home_name": m.home_name or m.home,
            "away_name": m.away_name or m.away,
            "is_target": target in (m.home, m.away),
        }
        for m in path_matches
    ]
    top_paths = []
    for path_key, count in path_counts.most_common(3):
        top_paths.append({
            "probability": count / total,
            "steps": [
                {**meta, "outcome": label}
                for meta, label in zip(match_meta, path_key)
            ],
        })
    buckets["top_paths"] = top_paths

    return buckets
